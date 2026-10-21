"""Private BCA student enrollment and student request/case workflow.
Revision ID: 6bcabca001
Revises: 4c2a1c
"""
from alembic import op
import sqlalchemy as sa
revision='6bcabca001'
down_revision='4c2a1c'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('bca_students',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('usn',sa.String(24),nullable=False),
        sa.Column('semester',sa.Integer(),nullable=False),
        sa.Column('must_change_password',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        )
    op.create_index('ix_bca_students_user_id','bca_students',['user_id'],unique=True)
    op.create_index('ix_bca_students_usn','bca_students',['usn'],unique=True)
    op.create_table('student_cases',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('reference',sa.String(34),nullable=False),
        sa.Column('student_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('department',sa.String(160),nullable=False),
        sa.Column('category',sa.String(30),nullable=False),
        sa.Column('subject',sa.String(160),nullable=False),
        sa.Column('description',sa.Text(),nullable=False),
        sa.Column('status',sa.String(22),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for col in ('reference','student_id','department','status','created_at'):
        op.create_index('ix_student_cases_'+col,'student_cases',[col],unique=(col=='reference'))
    op.create_index('ix_student_case_department_status','student_cases',['department','status'])
    op.create_table('student_case_messages',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('case_id',sa.Integer(),sa.ForeignKey('student_cases.id',ondelete='CASCADE'),nullable=False),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('body',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_student_case_messages_case_id','student_case_messages',['case_id'])

def downgrade():
    op.drop_index('ix_student_case_messages_case_id',table_name='student_case_messages')
    op.drop_table('student_case_messages')
    op.drop_index('ix_student_case_department_status',table_name='student_cases')
    for col in ('created_at','status','department','student_id','reference'):
        op.drop_index('ix_student_cases_'+col,table_name='student_cases')
    op.drop_table('student_cases')
    op.drop_index('ix_bca_students_usn',table_name='bca_students')
    op.drop_index('ix_bca_students_user_id',table_name='bca_students')
    op.drop_table('bca_students')
