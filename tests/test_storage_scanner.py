import socket
import struct

import pytest
from fastapi import HTTPException

from app.storage import scan_for_malware


class ReplySocket:
    def __init__(self, reply):
        self.reply = reply
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def settimeout(self, _seconds):
        pass

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, _size):
        return self.reply


def configure_scanner(monkeypatch, reply):
    monkeypatch.setenv('SCAN_MODE', 'clamav')
    monkeypatch.setenv('CLAMAV_HOST', 'clamav')
    monkeypatch.setenv('CLAMAV_PORT', '3310')
    scanner = ReplySocket(reply)
    monkeypatch.setattr(socket, 'create_connection', lambda *_args, **_kwargs: scanner)
    return scanner


def test_clamav_sends_instream_and_accepts_clean_result(monkeypatch):
    data = b'%PDF-1.7\nexample'
    scanner = configure_scanner(monkeypatch, b'stream: OK\0')

    scan_for_malware(data)

    assert scanner.sent == [
        b'zINSTREAM\0',
        struct.pack('!I', len(data)) + data + b'\0\0\0\0',
    ]


def test_clamav_rejects_detected_malware(monkeypatch):
    configure_scanner(monkeypatch, b'stream: Eicar-Test-Signature FOUND\0')

    with pytest.raises(HTTPException) as error:
        scan_for_malware(b'test payload')

    assert error.value.status_code == 422


@pytest.mark.parametrize('reply', [b'', b'ERROR\0'])
def test_clamav_fails_closed_on_invalid_reply(monkeypatch, reply):
    configure_scanner(monkeypatch, reply)

    with pytest.raises(HTTPException) as error:
        scan_for_malware(b'test payload')

    assert error.value.status_code == 503


def test_clamav_fails_closed_when_daemon_is_unreachable(monkeypatch):
    monkeypatch.setenv('SCAN_MODE', 'clamav')
    monkeypatch.setenv('CLAMAV_HOST', 'clamav')
    monkeypatch.setattr(socket, 'create_connection', lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('offline')))

    with pytest.raises(HTTPException) as error:
        scan_for_malware(b'test payload')

    assert error.value.status_code == 503
