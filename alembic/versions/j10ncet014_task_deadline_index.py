"""Index task deadlines for the recurring reminder scan.

Revision ID: j10ncet014
Revises: i09ncet013
"""
from alembic import op

revision='j10ncet014'
down_revision='i09ncet013'
branch_labels=None
depends_on=None


def upgrade():
    op.create_index('ix_task_items_deadline','task_items',['deadline'])


def downgrade():
    op.drop_index('ix_task_items_deadline',table_name='task_items')
