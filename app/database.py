import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, String, Integer, DateTime, ForeignKey, Text, Boolean, LargeBinary,
    Index, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


def utcnow():
    return datetime.now(timezone.utc)


def db_url():
    url = os.getenv('DATABASE_URL')
    if not url:
        if os.getenv('APP_ENV', 'development') == 'production':
            raise RuntimeError('DATABASE_URL must be configured for production; refusing ephemeral SQLite fallback.')
        url = 'sqlite:///./ncet-dev.sqlite3'
    if url.startswith('postgres://'):
        url = 'postgresql+psycopg://' + url[len('postgres://'):]
    elif url.startswith('postgresql://'):
        url = 'postgresql+psycopg://' + url[len('postgresql://'):]
    return url


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(130))
    role: Mapped[str] = mapped_column(String(15), index=True)
    department: Mapped[str] = mapped_column(String(160), default='Computer Science & Engineering', index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship()


class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(140))
    category: Mapped[str] = mapped_column(String(100), index=True)
    department: Mapped[str] = mapped_column(String(160), index=True)
    academic_year: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default='verifying', index=True)
    submitter_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    submitter: Mapped[User] = relationship()
    events: Mapped[list['DocumentEvent']] = relationship(back_populates='document', order_by='DocumentEvent.id', cascade='all, delete-orphan')
    verifications: Mapped[list['Verification']] = relationship(order_by='Verification.id', cascade='all, delete-orphan')
    attachments: Mapped[list['Attachment']] = relationship(back_populates='document', order_by='Attachment.version', cascade='all, delete-orphan')
    __table_args__ = (Index('ix_documents_scope_created', 'department', 'status', 'created_at'),)


class DocumentEvent(Base):
    __tablename__ = 'document_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default='')
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    document: Mapped[Document] = relationship(back_populates='events')
    actor: Mapped[User] = relationship()


class Attachment(Base):
    __tablename__ = 'attachments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(120))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(180), unique=True)
    bytes_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    document: Mapped[Document] = relationship(back_populates='attachments')
    __table_args__ = (UniqueConstraint('document_id', 'version'),)


class LoginFailure(Base):
    __tablename__ = 'login_failures'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    username: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), index=True, nullable=True)
    event: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[str] = mapped_column(String(500), default='')
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


def create_database_engine():
    url = db_url()
    cfg = {'pool_pre_ping': True}
    if url.startswith('sqlite'):
        cfg['connect_args'] = {'check_same_thread': False}
        if ':memory:' in url:
            cfg['poolclass'] = StaticPool
    else:
        cfg.update({'pool_size': 5, 'max_overflow': 5, 'pool_recycle': 1800})
    return create_engine(url, **cfg)


engine = create_database_engine()
DBSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with DBSession() as db:
        yield db


class RulePolicy(Base):
    """Immutable version of a department rulebook."""
    __tablename__ = 'rule_policies'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department: Mapped[str] = mapped_column(String(160), index=True)
    version: Mapped[int] = mapped_column(Integer)
    rules_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('department','version'),)


class Verification(Base):
    __tablename__ = 'verifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    policy_id: Mapped[int | None] = mapped_column(ForeignKey('rule_policies.id'), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    report_json: Mapped[str] = mapped_column(Text, default='{}')
    error_code: Mapped[str | None] = mapped_column(String(90), nullable=True)
    model: Mapped[str] = mapped_column(String(130), default='google/gemma-4-31b-it:free')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint('document_id','revision'),Index('ix_verify_state_created','state','created_at'))


class IntegrationSetting(Base):
    __tablename__ = 'integration_settings'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    encrypted_value: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
