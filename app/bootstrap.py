"""One-time bootstrap. No default passwords, passwords must be set via private environment variables."""
import os
import hashlib
import re
from sqlalchemy.exc import IntegrityError
from .database import DBSession, User, Session, AuditLog, utcnow
from .security import hash_password

DEFAULT_DEPARTMENT='Computer Science & Engineering'
ROLES={
    'admin': 'System Administrator',
    'principal': 'Office of the Principal',
    'hod': 'Head of Department',
    'staff': 'Faculty Member',
    'iqac': 'IQAC Coordinator',
}



def recover_admin_once(db):
    """Apply a one-time operator-authorized admin password recovery.

    No public recovery endpoints, no plaintext credentials in Git, logs or SQL.
    The nonce digest in the audit log makes recovery idempotent across deploys.
    """
    password = os.environ.get('NCET_ADMIN_RECOVERY_PASSWORD', '')
    nonce = os.environ.get('NCET_ADMIN_RECOVERY_NONCE', '')
    if not password and not nonce:
        return
    if not (24 <= len(password) <= 128 and re.fullmatch(r'[0-9a-f]{32,64}', nonce)):
        raise RuntimeError('Incomplete admin recovery configuration; password unchanged.')
    fingerprint = hashlib.sha256(nonce.encode('ascii')).hexdigest()
    username = os.environ.get('NCET_BOOTSTRAP_ADMIN_USERNAME', 'admin')
    admin = (db.query(User).filter(User.username == username, User.role == 'admin')
             .with_for_update().one_or_none())
    if admin is None or not admin.active:
        raise RuntimeError('The active administrator account was not found; password unchanged.')
    previously_applied = db.query(AuditLog.id).filter(
        AuditLog.event == 'auth.admin_recovery',
        AuditLog.detail == fingerprint
    ).first()
    if previously_applied:
        print('One-time administrator recovery previously applied; password unchanged.')
        return
    admin.password_hash = hash_password(password)
    admin.password_changed_at = utcnow()
    db.query(Session).filter(Session.user_id == admin.id).delete(synchronize_session=False)
    db.add(AuditLog(actor_id=admin.id, event='auth.admin_recovery', detail=fingerprint))
    db.commit()
    print('One-time administrator recovery applied; old sessions revoked.')


def main():
    with DBSession() as db:
        for role,name in ROLES.items():
            value = os.environ.get(f'NCET_BOOTSTRAP_{role.upper()}_PASSWORD')
            username = os.environ.get(f'NCET_BOOTSTRAP_{role.upper()}_USERNAME', role)
            if not value:
                continue
            if db.query(User).filter(User.username == username).first():
                print(f'{role}: account exists; bootstrap did not reset its password')
                continue
            u=User(username=username, display_name=name, role=role,department=DEFAULT_DEPARTMENT,
                   password_hash=hash_password(value))
            db.add(u)
            db.commit()
            print(f'Created {role} account: {username}')
        recover_admin_once(db)

if __name__=='__main__': main()
