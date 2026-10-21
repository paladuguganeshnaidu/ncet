"""Add private student contact details and opt-in public student showcase.

Revision ID: b02ncet006
Revises: a01ncet005
"""
from alembic import op
import sqlalchemy as sa

revision='b02ncet006'
down_revision='a01ncet005'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('bca_student_showcases',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('student_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('mobile_private',sa.String(20),nullable=False),
        sa.Column('email_private',sa.String(180),nullable=False),
        sa.Column('about',sa.Text(),nullable=False),
        sa.Column('skills_json',sa.Text(),nullable=False),
        sa.Column('certificates_json',sa.Text(),nullable=False),
        sa.Column('published',sa.Boolean(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_bca_student_showcases_student_id','bca_student_showcases',['student_id'],unique=True)
    op.create_index('ix_bca_student_showcases_published','bca_student_showcases',['published'])

def downgrade():
    op.drop_index('ix_bca_student_showcases_published',table_name='bca_student_showcases')
    op.drop_index('ix_bca_student_showcases_student_id',table_name='bca_student_showcases')
    op.drop_table('bca_student_showcases')
