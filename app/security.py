import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import delete
from .database import Session, User, db_url, get_db, utcnow

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
COOKIE = 'ncet_session'
ROLES = {'admin', 'principal', 'hod', 'staff', 'iqac', 'student'}


def hash_secret(s):
    return hashlib.sha256(s.encode()).hexdigest()


def hash_password(password):
    if not (12 <= len(password) <= 128):
        raise HTTPException(422, 'Password must be between 12 and 128 characters.')
    return hasher.hash(password)


def verify_password(password, hashed):
    try:
        return hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def set_session(db: DbSession, user: User, response):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.add(Session(user_id=user.id, token_hash=hash_secret(token), csrf_token=csrf,
                   expires_at=utcnow()+timedelta(hours=8)))
    db.commit()
    secure = os.getenv('APP_ENV', 'development') == 'production'
    response.set_cookie(COOKIE, token, httponly=True, secure=secure, samesite='lax',
                        max_age=8*3600, path='/')
    return csrf


def current(request: Request, db: DbSession = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, 'Sign in to continue.')
    sess = db.query(Session).filter(Session.token_hash == hash_secret(token), Session.expires_at > utcnow()).first()
    if not sess or not sess.user.active:
        raise HTTPException(401, 'Session has expired. Please sign in again.')
    request.state.session = sess
    return sess.user


def csrf_required(request: Request, user: User = Depends(current)):
    value = request.headers.get('X-CSRF-Token', '')
    if not value or not hmac.compare_digest(value, request.state.session.csrf_token):
        raise HTTPException(403, 'Missing or invalid request verification token.')
    return user


def as_role(*roles):
    def check(user=Depends(current)):
        if user.role not in roles:
            raise HTTPException(403, 'Your account cannot perform this action.')
        return user
    return check


def as_role_mutation(*roles):
    def check(user=Depends(csrf_required)):
        if user.role not in roles:
            raise HTTPException(403, 'Your account cannot perform this action.')
        return user
    return check
