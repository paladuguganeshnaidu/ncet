"""Exercise the actual Render entrypoint, not only uvicorn app.main:app.

Regression for a deployed failure where literal backslash-n sequences in a
comment swallowed both `host` and `programs` assignments while compileall
(and the app's regular pytest suite) still passed.
"""
import sys

import pytest

from app import serve


class FinishedProcess:
    def __init__(self, cmd):
        self.cmd = cmd
        self.pid = 1234
        self.terminated = False

    def poll(self):
        return 0  # Process stopped: serve.main should detect/report it.

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.terminated = True


@pytest.mark.parametrize('production,expected_host,run_worker', [
    (False, '127.0.0.1', False),
    (True, '0.0.0.0', True),
])
def test_render_entrypoint_initializes_executable_commands(
        monkeypatch, production, expected_host, run_worker):
    monkeypatch.setenv('APP_ENV', 'production' if production else 'development')
    monkeypatch.setenv('PORT', '10000')
    monkeypatch.setenv('APP_RUN_WORKER_IN_WEB', 'true' if run_worker else 'false')
    monkeypatch.delenv('LISTEN_HOST', raising=False)

    # Keep this smoke test deterministic and offline: NEVER touch migrations,
    # users, Render, or the actual worker/service.
    monkeypatch.setattr(serve, 'validate_configuration', lambda: None)
    monkeypatch.setattr(serve, 'ensure_admin_account', lambda: None)
    setup = []
    monkeypatch.setattr(serve.subprocess, 'run',
                        lambda args, check: setup.append((args, check)))
    processes = []
    def launch(cmd):
        item = FinishedProcess(cmd)
        processes.append(item)
        return item
    monkeypatch.setattr(serve.subprocess, 'Popen', launch)
    monkeypatch.setattr(serve.signal, 'signal', lambda *_: None)

    # A fake web process exits immediately; the supervisor should notice it
    # rather than raising NameError before processes are launched.
    result = serve.main()
    assert result == 1
    assert setup == [
        ([sys.executable, '-m', 'alembic', 'upgrade', 'head'], True),
        ([sys.executable, '-m', 'app.bootstrap'], True),
    ]
    web = processes[0].cmd
    assert web[:4] == [sys.executable, '-m', 'uvicorn', 'app.main:app']
    assert web[web.index('--host') + 1] == expected_host
    assert web[web.index('--port') + 1] == '10000'
    # The supervisor must not terminate a process already exited: the fake
    # poll() reports exit code 0, rather than a still-running child.
    assert all(item.poll() == 0 for item in processes)
    assert len(processes) == (2 if run_worker else 1)
    if run_worker:
        assert processes[1].cmd == [sys.executable, '-m', 'app.worker']


def test_render_entrypoint_rejects_invalid_ports_without_spawning(
        monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('PORT', '99999')
    monkeypatch.setattr(serve, 'validate_configuration', lambda: None)
    monkeypatch.setattr(serve, 'ensure_admin_account', lambda: None)
    monkeypatch.setattr(serve.subprocess, 'run', lambda *_a, **_kw: None)
    monkeypatch.setattr(serve.subprocess, 'Popen',
                        lambda *_: pytest.fail('Must reject before launching'))
    with pytest.raises(RuntimeError, match='PORT'):
        serve.main()
