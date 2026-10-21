"""Administrator-only cleanup with impact preview and explicit confirmation.

Nothing in this module runs on startup. Bulk access removal retains dependent
academic records and audit history; approved PDF document removal is irreversible.
"""
from datetime import timedelta
from typing import Literal
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .database import (
    User, Session, Document, Attachment, AuditLog, LoginFailure, Verification,
    get_db, utcnow,
)
from .security import as_role, as_role_mutation, verify_password
from .student_profiles import StudentShowcase
from .storage import remove_key

router = APIRouter()
logger = logging.getLogger("ncet.cleanup")

ACTION_INFO = {
    "unpublish_profiles": ("Unpublish every public student portfolio",
                           "UNPUBLISH STUDENT PROFILES", False,
                           "Hide voluntarily published student profiles from the directory, sitemap and search engines. Existing search cache may take time to clear."),
    "disable_staff": ("Disable all active staff accounts",
                      "DISABLE STAFF ACCOUNTS", False,
                      "Revoke sign-in for staff accounts. Academic documents, reviews and audit history remain intact."),
    "disable_students": ("Disable all active student accounts",
                         "DISABLE STUDENT ACCOUNTS", False,
                         "Revoke student sign-in and unpublish public portfolios. Private student requests are retained."),
    "delete_approved_pdf_documents": ("Permanently delete approved PDF document records",
                                      "DELETE APPROVED PDF DOCUMENTS", True,
                                      "Delete approved document records that contain PDF attachments, all their revisions, verifications and stored files. Requires a verified offline backup."),
    "clear_expired_sessions": ("Remove expired login sessions",
                               "CLEAR EXPIRED SESSIONS", False,
                               "Remove only sessions whose expiry has passed."),
    "clear_old_login_failures": ("Remove login-failure records older than 30 days",
                                 "CLEAR OLD LOGIN FAILURES", False,
                                 "Keep recent login-security data and all immutable admin audit events."),
}


def _pdf_query(db: DbSession):
    # Approval is an internal workflow status, not permission to publish PDFs.
    return db.query(Document).filter(
        Document.status == "approved",
        Document.attachments.any(Attachment.name.ilike("%.pdf")),
    )


def _count(db: DbSession, action: str) -> int:
    if action == "unpublish_profiles":
        return db.query(StudentShowcase).filter(StudentShowcase.published.is_(True)).count()
    if action == "disable_staff":
        return db.query(User).filter(User.role == "staff", User.active.is_(True)).count()
    if action == "disable_students":
        return db.query(User).filter(User.role == "student", User.active.is_(True)).count()
    if action == "delete_approved_pdf_documents":
        return _pdf_query(db).count()
    if action == "clear_expired_sessions":
        return db.query(Session).filter(Session.expires_at < utcnow()).count()
    if action == "clear_old_login_failures":
        return db.query(LoginFailure).filter(
            LoginFailure.at < utcnow() - timedelta(days=30)
        ).count()
    raise HTTPException(422, "Unsupported cleanup action.")


@router.get("/api/admin/cleanup/preview")
def cleanup_preview(
    actor: User = Depends(as_role("admin")),
    db: DbSession = Depends(get_db),
):
    return {"actions": [
        {"id": key, "label": info[0], "confirmation": info[1],
         "requires_backup": info[2], "description": info[3],
         "count": _count(db, key)}
        for key, info in ACTION_INFO.items()
    ]}


class CleanupRequest(BaseModel):
    action: Literal[
        "unpublish_profiles", "disable_staff", "disable_students",
        "delete_approved_pdf_documents", "clear_expired_sessions",
        "clear_old_login_failures"
    ]
    confirmation: str = Field(min_length=8, max_length=100)
    expected_count: int = Field(ge=0, le=10_000_000)
    backup_confirmed: bool = False
    admin_password: str = Field(default='', max_length=128)


@router.post("/api/admin/cleanup/execute")
def cleanup_execute(
    body: CleanupRequest,
    actor: User = Depends(as_role_mutation("admin")),
    db: DbSession = Depends(get_db),
):
    label, phrase, backup_required, _ = ACTION_INFO[body.action]
    if body.confirmation != phrase:
        raise HTTPException(422, "Type the exact confirmation phrase shown in the dialog.")
    if backup_required and not body.backup_confirmed:
        raise HTTPException(422, "Confirm that you verified a recent recoverable offline backup.")
    if backup_required and not verify_password(body.admin_password, actor.password_hash):
        raise HTTPException(403, "Re-enter your administrator password to delete document records.")

    # Serializes concurrent cleanup requests from the same administrator.
    db.query(User).filter(User.id == actor.id).with_for_update().one()
    count = _count(db, body.action)
    if count != body.expected_count:
        raise HTTPException(409, "Records changed since preview. Refresh the counts before continuing.")
    keys = []
    if body.action == "unpublish_profiles":
        db.query(StudentShowcase).filter(
            StudentShowcase.published.is_(True)
        ).update({StudentShowcase.published: False}, synchronize_session=False)
    elif body.action in ("disable_staff", "disable_students"):
        role = "staff" if body.action == "disable_staff" else "student"
        db.query(User).filter(User.role == role, User.active.is_(True)).update(
            {User.active: False}, synchronize_session=False
        )
        ids = select(User.id).where(User.role == role)
        db.query(Session).filter(Session.user_id.in_(ids)).delete(synchronize_session=False)
        if role == "student":
            db.query(StudentShowcase).filter(
                StudentShowcase.student_id.in_(ids),
                StudentShowcase.published.is_(True),
            ).update({StudentShowcase.published: False}, synchronize_session=False)
    elif body.action == "delete_approved_pdf_documents":
        # Cascades through ORM relationships; deletes neither user accounts nor audit history.
        for doc in _pdf_query(db).all():
            keys.extend(file.storage_key for file in doc.attachments)
            db.delete(doc)
    elif body.action == "clear_expired_sessions":
        db.query(Session).filter(Session.expires_at < utcnow()).delete(synchronize_session=False)
    elif body.action == "clear_old_login_failures":
        db.query(LoginFailure).filter(
            LoginFailure.at < utcnow() - timedelta(days=30)
        ).delete(synchronize_session=False)

    db.add(AuditLog(
        actor_id=actor.id, event="admin.cleanup." + body.action,
        detail=f"{label}; affected={count}",
    ))
    db.commit()
    # Best effort cleanup for external object storage after DB commit.
    failed_storage = 0
    for key in keys:
        try:
            remove_key(key)
        except Exception:
            failed_storage += 1
            logger.exception("Orphaned storage key after approved PDF cleanup")
    return {"ok": True, "action": body.action, "affected": count,
            "storage_cleanup_failures": failed_storage}


@router.get("/api/admin/ai/overview")
def ai_overview(
    actor: User = Depends(as_role("admin")),
    db: DbSession = Depends(get_db),
):
    from .ai_gateway import select_provider
    provider = select_provider(db)
    document_counts = dict(
        db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
    )
    states = dict(db.query(Verification.state, func.count(Verification.id)).
                  group_by(Verification.state).all())
    return {
        "provider_configured": provider is not None,
        "provider": provider.name if provider else None,
        "model": provider.model if provider else None,
        "document_statuses": document_counts,
        "verification_states": states,
        "note": "AI findings assist reviewers. Incomplete or uncertain reports need a human decision.",
    }
