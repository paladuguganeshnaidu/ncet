"""Add private HOD-set student priority ratings.

Revision ID: m13ncet017
Revises: l12ncet016
"""
from alembic import op
import sqlalchemy as sa

revision='m13ncet017'
down_revision='l12ncet016'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('bca_student_priorities',
        sa.Column('id',sa.Integer(),nullable=False),
        sa.Column('student_id',sa.Integer(),nullable=False),
        sa.Column('department',sa.String(length=160),nullable=False),
        sa.Column('stars',sa.Integer(),nullable=False),
        sa.Column('updated_by_hod_id',sa.Integer(),nullable=True),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint('stars >= 1 AND stars <= 3',name='ck_bca_student_priority_stars'),
        sa.ForeignKeyConstraint(['student_id'],['users.id'],ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_hod_id'],['users.id'],ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'))
    op.create_index(op.f('ix_bca_student_priorities_department'),
                    'bca_student_priorities',['department'],unique=False)
    op.create_index(op.f('ix_bca_student_priorities_student_id'),
                    'bca_student_priorities',['student_id'],unique=True)


def downgrade():
    op.drop_index(op.f('ix_bca_student_priorities_student_id'),table_name='bca_student_priorities')
    op.drop_index(op.f('ix_bca_student_priorities_department'),table_name='bca_student_priorities')
    op.drop_table('bca_student_priorities')
