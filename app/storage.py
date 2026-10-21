"""Private file storage. Choose object storage or a persistent mounted disk for production."""
import io
import os
import secrets
import hashlib
from pathlib import Path
from fastapi import HTTPException, UploadFile

MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {
    '.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
}


def validate_upload(name: str, data: bytes):
    clean = Path(name.replace('\\', '/')).name.strip()[:190]
    ext = Path(clean).suffix.lower()
    if ext not in ALLOWED or not clean or not data or len(data) > MAX_BYTES:
        raise HTTPException(422, 'Provide a PDF, DOCX, TXT, PNG or JPG attachment up to 10 MB.')
    signature = (ext == '.pdf' and data.startswith(b'%PDF-')) or \
        (ext == '.png' and data.startswith(b'\x89PNG\r\n\x1a\n')) or \
        (ext in {'.jpg', '.jpeg'} and data.startswith(b'\xff\xd8\xff')) or \
        (ext == '.txt' and b'\x00' not in data[:1000]) or \
        (ext == '.docx' and data.startswith(b'PK\x03\x04'))
    if not signature:
        raise HTTPException(422, 'Attachment content does not match the selected file format.')
    if ext == '.docx':
        from zipfile import ZipFile, BadZipFile
        try:
            with ZipFile(io.BytesIO(data)) as z:
                if '[Content_Types].xml' not in z.namelist() or 'word/document.xml' not in z.namelist():
                    raise HTTPException(422, 'The Word document is not valid.')
                if len(z.namelist()) > 1500 or sum(i.file_size for i in z.infolist()) > 150 * 1024 * 1024:
                    raise HTTPException(422, 'The Word document is too complex.')
        except BadZipFile:
            raise HTTPException(422, 'The Word document is corrupt.')
    scan_for_malware(data)
    return clean, ALLOWED[ext]


async def read_upload(file: UploadFile):
    data = await file.read(MAX_BYTES + 1)
    await file.close()
    name, mime = validate_upload(file.filename or '', data)
    return name, mime, data


def scan_for_malware(data: bytes):
    """Optional ClamAV INSTREAM scanner. Enable with SCAN_MODE=clamav.

    When enabled, failure to scan *rejects* the upload (fail closed).
    """
    if os.getenv('SCAN_MODE', 'off') != 'clamav':
        return
    import socket
    import struct
    host=os.getenv('CLAMAV_HOST')
    port=int(os.getenv('CLAMAV_PORT', '3310'))
    if not host:
        raise HTTPException(503, 'Document scanner has not been configured.')
    try:
        with socket.create_connection((host,port),timeout=12) as sock:
            sock.settimeout(25)
            sock.sendall(b'zINSTREAM\0')
            sock.sendall(struct.pack('!I',len(data))+data+struct.pack('!I',0))
            reply=sock.recv(1000)
            if b'FOUND' in reply:
                raise HTTPException(422, 'This attachment did not pass security scanning.')
            if b'OK' not in reply:
                raise HTTPException(503, 'The document scanner did not return a clean result.')
    except HTTPException:
        raise
    except (OSError, ValueError):
        raise HTTPException(503, 'Document scanning temporarily unavailable.')


def mode():
    return os.getenv('STORAGE_BACKEND', 'database').lower()


def store(data: bytes, mime: str):
    key = secrets.token_hex(24)
    kind = mode()
    if kind == 'database':
        return key, data
    if kind == 'disk':
        root = Path(os.getenv('UPLOAD_DIR', '/var/data/ncet-uploads')).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = root / key
        with target.open('xb') as output:
            output.write(data)
        target.chmod(0o600)
        return key, None
    if kind == 's3':
        import boto3
        client = _s3()
        bucket = os.environ['S3_BUCKET']
        options={'Bucket':bucket,'Key':'private/'+key,'Body':data,'ContentType':mime}
        if os.getenv('S3_SSE'):options['ServerSideEncryption']=os.environ['S3_SSE']
        client.put_object(**options)
        return key, None
    raise RuntimeError('Unsupported STORAGE_BACKEND')


def retrieve(attachment):
    kind = mode()
    if kind == 'database':
        return attachment.bytes_content
    if kind == 'disk':
        return (Path(os.getenv('UPLOAD_DIR', '/var/data/ncet-uploads')) / attachment.storage_key).read_bytes()
    if kind == 's3':
        return _s3().get_object(Bucket=os.environ['S3_BUCKET'], Key='private/'+attachment.storage_key)['Body'].read()
    raise RuntimeError('Unsupported storage')


def _s3():
    import boto3
    return boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
                        region_name=os.environ.get('S3_REGION', 'auto'))


def remove_key(key):
    if mode() == 'disk':
        (Path(os.getenv('UPLOAD_DIR', '/var/data/ncet-uploads')) / key).unlink(missing_ok=True)
    elif mode() == 's3':
        _s3().delete_object(Bucket=os.environ['S3_BUCKET'], Key='private/'+key)


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()
