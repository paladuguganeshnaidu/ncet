"""NCMS VerifyFlow entrypoint for a single Render web service.

The API and document verifier share one container for low-traffic trials.
For institution-wide deployments use separate always-on web and worker instances.
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
log = logging.getLogger('ncet.serve')


def validate_configuration(env: dict[str, str] | None = None) -> None:
    """Validate configuration without revealing secret contents in logs."""
    config = os.environ if env is None else env
    if config.get('APP_ENV', 'development') != 'production':
        return

    url = (config.get('DATABASE_URL') or '').strip()
    if not url.startswith(('postgresql://', 'postgres://', 'postgresql+psycopg://')):
        raise RuntimeError('Production requires DATABASE_URL pointing to PostgreSQL.')
    parsed = urlsplit(url)
    if not parsed.hostname or not parsed.path or parsed.path == '/':
        raise RuntimeError('DATABASE_URL is incomplete (host or database name missing).')
    # Private Render connections do not need TLS; *external* Render endpoints do.
    if parsed.hostname.endswith('.render.com') and 'require' not in parse_qs(parsed.query).get('sslmode', []):
        raise RuntimeError('External Render PostgreSQL URLs must include sslmode=require.')

    origin = (config.get('PUBLIC_ORIGIN') or '').strip().rstrip('/')
    parsed_origin = urlsplit(origin)
    if (parsed_origin.scheme != 'https' or not parsed_origin.hostname
            or parsed_origin.username or parsed_origin.password
            or parsed_origin.path or parsed_origin.query or parsed_origin.fragment):
        raise RuntimeError('PUBLIC_ORIGIN must be the exact public HTTPS origin (no path).')

    key = config.get('SETTINGS_ENCRYPTION_KEY') or ''
    try:
        Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError('SETTINGS_ENCRYPTION_KEY must be a valid Fernet key.') from exc


def ensure_admin_account() -> None:
    """Fail rather than exposing a live site with no administrative login."""
    if os.getenv('APP_ENV', 'development') != 'production':
        return
    from .database import DBSession, User
    with DBSession() as db:
        has_admin = db.query(User.id).filter(User.role == 'admin', User.active.is_(True)).first()
    if not has_admin:
        raise RuntimeError('No active administrator. Configure NCET_BOOTSTRAP_ADMIN_PASSWORD for initial setup.')


def main() -> int:
    validate_configuration()
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
    subprocess.run([sys.executable, '-m', 'app.bootstrap'], check=True)
    ensure_admin_account()

    run_worker = os.getenv('APP_RUN_WORKER_IN_WEB', 'false').strip().lower() == 'true'
    port = int(os.getenv('PORT', '10000'))
    if port <= 0 or port > 65535:
        raise RuntimeError('PORT must be a valid TCP port.')
    # The production container must listen on all interfaces for Render ingress.
    # On developer machines, default to loopback to avoid exposing the app.
    host = os.getenv('LISTEN_HOST') or ('0.0.0.0' if os.getenv('APP_ENV') == 'production' else '127.0.0.1')  # nosec B104 - required only for production ingress
    programs = [[sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', host, '--port', str(port), '--proxy-headers']]
    if run_worker:
        programs.append([sys.executable, '-m', 'app.worker'])
    children: list[subprocess.Popen] = []
    interrupted = False

    def terminate_children(*_):
        nonlocal interrupted
        interrupted = True
        for child in children:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGTERM, terminate_children)
    signal.signal(signal.SIGINT, terminate_children)
    try:
        for command in programs:
            child = subprocess.Popen(command)
            children.append(child)
            log.info('Started %s (pid %s)', command[2] if len(command) > 2 else command[0], child.pid)
        while not interrupted:
            for child in children:
                code = child.poll()
                if code is not None:
                    log.error('Required process %s exited (code %s)', child.pid, code)
                    terminate_children()
                    return code if code else 1
            time.sleep(1)
    finally:
        terminate_children()
        for child in children:
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
