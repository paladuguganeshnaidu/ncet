"""Private BCA enrollment and student cases; never included in public search endpoints."""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, UniqueConstraint, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base, utcnow

class BCAStudent(Base):
    __tablename__ = 'bca_students'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),unique=True,index=True)
    usn: Mapped[str] = mapped_column(String(24),unique=True,index=True)
    semester: Mapped[int] = mapped_column(Integer)
    must_change_password: Mapped[bool] = mapped_column(Boolean,default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

class StudentCase(Base):
    __tablename__ = 'student_cases'
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(34),unique=True,index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id',ondelete='RESTRICT'),index=True)
    department: Mapped[str] = mapped_column(String(160),index=True)
    category: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(22),default='submitted',index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
    student = relationship('User', foreign_keys=[student_id])
    messages = relationship('StudentCaseMessage',back_populates='case',order_by='StudentCaseMessage.id',cascade='all, delete-orphan')
    __table_args__=(
        Index('ix_student_case_department_status','department','status'),
        Index('ix_student_case_department_created','department','created_at','id'),
        Index('ix_student_case_student_created','student_id','created_at','id'),
    )

class StudentCaseMessage(Base):
    __tablename__='student_case_messages'
    id: Mapped[int]=mapped_column(primary_key=True)
    case_id: Mapped[int]=mapped_column(ForeignKey('student_cases.id',ondelete='CASCADE'),index=True)
    actor_id: Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='RESTRICT'))
    body: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    case=relationship('StudentCase',back_populates='messages')
    actor=relationship('User')
    __table_args__=(Index('ix_student_case_message_case_id_id','case_id','id'),)
