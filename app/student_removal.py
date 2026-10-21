"""High-assurance, two-step bulk student removal.

Disable is reversible and preserves complaints/academic/audit history. Permanent
deletion is admin-only and refuses any account referenced by durable records.
All decisions are repeated inside an execution transaction: the browser is never
an authority for what may be removed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from .database import Base, User, Session, AuditLog, LoginFailure, get_db, utcnow
from .security import csrf_required, verify_password
from .student_services import BCA_DEPARTMENT_NAMES
from .student_models import BCAStudent
from .student_profiles import StudentShowcase

router = APIRouter(prefix='/api/bca/students/removal',
                   tags=['Controlled student access removal'])
MAX_SELECTED = 50
PREVIEW_TTL = 300
# These are strictly dependent/ephemeral records or user-owned portfolio data.
# All other future user-FKs become blockers automatically (fail closed).
DELETE_OWNED = frozenset({
    'sessions', 'bca_students', 'bca_student_showcases',
    'app_notifications', 'task_notifications',
})


class Selection(BaseModel):
    usns: list[str] = Field(min_length=1, max_length=MAX_SELECTED)
    mode: Literal['disable', 'delete'] = 'disable'

    @field_validator('usns')
    @classmethod
    def valid_usns(cls, value: list[str]) -> list[str]:
        import re
        canonical = [v.strip().upper() for v in value]
        if any(not re.fullmatch(r'1NC[A-Z0-9]{5,14}', usn) for usn in canonical):
            raise ValueError('Invalid student USN.')
        if len(set(canonical)) != len(canonical):
            raise ValueError('Duplicate student USNs are not permitted.')
        return sorted(canonical)


class Execute(Selection):
    preview_token: str = Field(min_length=30, max_length=500)
    confirmation: str = Field(min_length=12, max_length=70)
    current_password: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=12, max_length=300)
    backup_confirmed: bool = False


def require_manager(actor: User, mode: str) -> None:
    if actor.role == 'admin':
        return
    if actor.role == 'hod' and actor.department.strip().lower() in BCA_DEPARTMENT_NAMES:
        if mode == 'disable':
            return
        raise HTTPException(403, 'Only administrators may permanently delete student accounts.')
    raise HTTPException(403, 'Only BCA HODs or administrators can remove student access.')


def selected_students(db: DbSession, actor: User, usns: list[str], lock=False):
    q = db.query(User, BCAStudent).join(BCAStudent, BCAStudent.user_id == User.id).filter(
        User.role == 'student', BCAStudent.usn.in_(usns))
    if actor.role != 'admin':
        q = q.filter(User.department == 'Computer Applications')
    if lock:
        q = q.with_for_update(of=User)
    rows = q.all()
    if len(rows) != len(usns):
        # Do not disclose which out-of-scope USN exists.
        raise HTTPException(404, 'One or more selected students are not accessible.')
    return sorted(rows, key=lambda pair: pair[1].usn)


def blockers_for(db: DbSession, ids: list[int]) -> dict[int, list[str]]:
    """Inspect EVERY declared user reference, including those added in future."""
    blockers: dict[int, list[str]] = {identifier: [] for identifier in ids}
    for table in Base.metadata.tables.values():
        if table.name in DELETE_OWNED:
            continue
        for column in table.columns:
            if not any(fk.target_fullname == 'users.id' for fk in column.foreign_keys):
                continue
            # Avoid fetching private payload: request only the referencing user id.
            found = db.execute(select(column).where(column.in_(ids)).distinct()).scalars()
            for uid in found:
                if uid in blockers and table.name not in blockers[uid]:
                    blockers[uid].append(table.name)
    return blockers


def snapshot(db: DbSession, actor: User, selection: Selection, lock=False):
    require_manager(actor, selection.mode)
    rows = selected_students(db, actor, selection.usns, lock=lock)
    if selection.mode == 'disable' and any(not user.active for user, _ in rows):
        raise HTTPException(409, 'One or more accounts are already inactive. Select only active students for access removal.')
    ids = [user.id for user, _ in rows]
    blocking = blockers_for(db, ids) if selection.mode == 'delete' else {}
    published = dict(db.query(StudentShowcase.student_id, StudentShowcase.published)
                     .filter(StudentShowcase.student_id.in_(ids)).all())
    items = [{'usn':student.usn, 'name':user.display_name, 'department':user.department,
              'active':bool(user.active), 'published':bool(published.get(user.id, False)),
              'deletion_blockers':blocking.get(user.id, [])}
             for user, student in rows]
    data = {'mode':selection.mode, 'items':items, 'count':len(items),
            'blocked':sum(bool(item['deletion_blockers']) for item in items),
            'confirmation':('DELETE' if selection.mode=='delete' else 'REMOVE')+
                           ' '+str(len(items))+(' STUDENT' if len(items)==1 else ' STUDENTS')}
    return data, ids


def digest_for(data: dict) -> str:
    serial = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(serial.encode('utf-8')).hexdigest()


def challenge(session: Session, actor: User, data: dict, exp: int) -> str:
    payload = json.dumps({'actor':actor.id, 'mode':data['mode'], 'exp':exp,
                          'digest':digest_for(data)}, separators=(',', ':')).encode()
    signature = hmac.new(session.csrf_token.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload+signature).decode().rstrip('=')


def valid_challenge(token: str, session: Session, actor: User, data: dict) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token+'='*((-len(token)) % 4))
        payload, signature = raw[:-32], raw[-32:]
        expected = hmac.new(session.csrf_token.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return False
        decoded = json.loads(payload)
        return (decoded['actor']==actor.id and decoded['mode']==data['mode'] and
                decoded['digest']==digest_for(data) and
                isinstance(decoded['exp'], int) and time.time() <= decoded['exp'] <= time.time()+PREVIEW_TTL)
    except (ValueError, KeyError, TypeError, OverflowError):
        return False


@router.post('/preview')
def preview(body: Selection, request: Request, actor: User = Depends(csrf_required),
            db: DbSession = Depends(get_db)):
    info, _ = snapshot(db, actor, body)
    info['preview_token'] = challenge(request.state.session, actor, info, int(time.time())+PREVIEW_TTL)
    info['expires_in_seconds'] = PREVIEW_TTL
    info['requires_password'] = True
    info['requires_backup'] = body.mode == 'delete'
    info['note'] = (
        'Permanent deletion is blocked for students referenced by academic, complaint or audit records. '
        'Deleted accounts and portfolios cannot be recovered without a database backup.'
        if body.mode == 'delete' else
        'Disables sign-in, immediately revokes sessions and hides public portfolios. '
        'Complaint and academic history is retained; an administrator may restore access.'
    )
    return info


def throttle(db: DbSession, actor: User) -> None:
    # Across all client IPs: never allow rapid online password guessing through
    # a sensitive mutation endpoint. The key is a one-way salted identifier.
    marker = 'student-remove:'+str(actor.id)
    failures = db.query(func.count(LoginFailure.id)).filter(
        LoginFailure.username == marker,
        LoginFailure.at >= utcnow()-timedelta(minutes=15)).scalar() or 0
    if failures >= 5:
        raise HTTPException(429, 'Too many failed confirmations. Try again later.')


def record_failure(db: DbSession, actor: User) -> None:
    db.add(LoginFailure(username='student-remove:'+str(actor.id),
        ip_hash=hashlib.sha256(('removal:' + str(actor.id)).encode()).hexdigest(),
        at=utcnow()))
    db.commit()


@router.post('/execute')
def execute(body: Execute, request: Request, actor: User = Depends(csrf_required),
            db: DbSession = Depends(get_db)):
    require_manager(actor, body.mode)
    throttle(db, actor)
    # Lock actor to serialize concurrent removals by the same institution role;
    # locks below also ensure target accounts are stable until commit in Postgres.
    db.query(User).filter(User.id == actor.id).with_for_update().one()
    info, ids = snapshot(db, actor, body, lock=True)
    if not valid_challenge(body.preview_token, request.state.session, actor, info):
        raise HTTPException(409, 'Selection or record state changed, or preview expired. Preview again.')
    if body.confirmation != info['confirmation']:
        raise HTTPException(422, 'Enter the exact displayed confirmation phrase.')
    if body.mode == 'delete' and not body.backup_confirmed:
        raise HTTPException(422, 'A recoverable offline backup must be verified before permanent deletion.')
    if info['blocked']:
        raise HTTPException(409, 'One or more selected accounts have retained academic or audit history. '
                                'Use Remove access instead; permanent deletion cannot proceed.')
    if not verify_password(body.current_password, actor.password_hash):
        record_failure(db, actor)
        raise HTTPException(403, 'Current password is incorrect.')
    # Operation is atomic. Do not half-remove a student cohort.
    try:
        db.query(Session).filter(Session.user_id.in_(ids)).delete(synchronize_session=False)
        db.query(StudentShowcase).filter(StudentShowcase.student_id.in_(ids)).update(
            {StudentShowcase.published:False}, synchronize_session=False)
        if body.mode == 'disable':
            db.query(User).filter(User.id.in_(ids), User.role=='student').update(
                {User.active:False}, synchronize_session=False)
        else:
            from .notifications import AppNotification
            from .taskflow import TaskNotification
            for model, column in ((AppNotification, AppNotification.recipient_id),
                                  (TaskNotification, TaskNotification.user_id),
                                  (StudentShowcase, StudentShowcase.student_id),
                                  (BCAStudent, BCAStudent.user_id)):
                db.query(model).filter(column.in_(ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(ids), User.role=='student').delete(synchronize_session=False)
        from .database import AuditLog
        db.add(AuditLog(actor_id=actor.id, event='bca.students.'+body.mode,
                        detail=('Count '+str(len(ids))+'; USNs '+', '.join(body.usns)+
                                '; reason: '+body.reason.strip())[:500]))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Dependent records prevent permanent deletion. Use Remove access instead.')
    return {'ok':True, 'action':body.mode, 'affected':len(ids),
            'records_retained':body.mode=='disable'}
