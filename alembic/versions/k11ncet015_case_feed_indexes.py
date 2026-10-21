"""Index private case feeds and latest-message lookups.

Revision ID: k11ncet015
Revises: j10ncet014
"""
from alembic import op

revision='k11ncet015'
down_revision='j10ncet014'
branch_labels=None
depends_on=None


def upgrade():
    op.create_index('ix_student_case_department_created','student_cases',
                    ['department','created_at','id'])
    op.create_index('ix_student_case_student_created','student_cases',
                    ['student_id','created_at','id'])
    op.create_index('ix_student_case_message_case_id_id','student_case_messages',
                    ['case_id','id'])


def downgrade():
    op.drop_index('ix_student_case_message_case_id_id',table_name='student_case_messages')
    op.drop_index('ix_student_case_student_created',table_name='student_cases')
    op.drop_index('ix_student_case_department_created',table_name='student_cases')
