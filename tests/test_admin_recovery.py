"""One-time production-style admin recovery never exposes passwords in code/logs."""
import hashlib
import pytest
from app.bootstrap import recover_admin_once
from app.database import DBSession, User, AuditLog, Session
from app.security import verify_password


def test_admin_recovery_only_once_and_revokes_sessions(monkeypatch, client):
    old_password = 'SecurePassword-123!'
    password = 'OnlyForTestLongTemporaryPassword-2026!'
    nonce = 'ab' * 16
    response = client.post('/api/auth/login', json={
        'username':'admin', 'password':old_password, 'role':None,
    })
    assert response.status_code == 200
    with DBSession() as db:
        admin = db.query(User).filter_by(username='admin').one()
        assert db.query(Session).filter_by(user_id=admin.id).count() == 1

    monkeypatch.setenv('NCET_ADMIN_RECOVERY_PASSWORD', password)
    monkeypatch.setenv('NCET_ADMIN_RECOVERY_NONCE', nonce)
    with DBSession() as db:
        recover_admin_once(db)

    with DBSession() as db:
        admin = db.query(User).filter_by(username='admin').one()
        assert not verify_password(old_password, admin.password_hash)
        assert verify_password(password, admin.password_hash)
        assert db.query(Session).filter_by(user_id=admin.id).count() == 0
        log = db.query(AuditLog).filter_by(event='auth.admin_recovery').one()
        assert log.detail == hashlib.sha256(nonce.encode()).hexdigest()
        assert password not in log.detail

    monkeypatch.setenv('NCET_ADMIN_RECOVERY_PASSWORD', 'OtherLongTemporaryPassword-2026')
    with DBSession() as db:
        recover_admin_once(db)
    with DBSession() as db:
        admin = db.query(User).filter_by(username='admin').one()
        assert verify_password(password, admin.password_hash)
        assert db.query(AuditLog).filter_by(event='auth.admin_recovery').count() == 1


def test_invalid_recovery_configuration_cannot_change_password(monkeypatch):
    monkeypatch.setenv('NCET_ADMIN_RECOVERY_PASSWORD', 'too-short')
    monkeypatch.setenv('NCET_ADMIN_RECOVERY_NONCE', 'short')
    with DBSession() as db, pytest.raises(RuntimeError, match='Incomplete'):
        recover_admin_once(db)
    with DBSession() as db:
        admin = db.query(User).filter_by(username='admin').one()
        assert verify_password('SecurePassword-123!', admin.password_hash)
        assert db.query(AuditLog).filter_by(event='auth.admin_recovery').count() == 0


def test_no_recovery_env_is_noop(monkeypatch):
    monkeypatch.delenv('NCET_ADMIN_RECOVERY_PASSWORD', raising=False)
    monkeypatch.delenv('NCET_ADMIN_RECOVERY_NONCE', raising=False)
    with DBSession() as db:
        recover_admin_once(db)
    with DBSession() as db:
        assert db.query(AuditLog).filter_by(event='auth.admin_recovery').count() == 0
