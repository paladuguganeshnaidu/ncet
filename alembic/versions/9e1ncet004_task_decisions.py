"""Retain immutable HOD decisions and each PDF-review report.

Revision ID: 9e1ncet004
Revises: 8d0ncet003

The initial task migration is already applied in production. This additive
revision does not modify or delete existing accounts, documents or task records.
"""
from alembic import op
import sqlalchemy as sa

revision = '9e1ncet004'
down_revision = '8d0ncet003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task_submissions',
                  sa.Column('report_json', sa.Text(), nullable=False,
                            server_default=sa.text("'{}'")))
    op.create_table(
        'task_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('task_items.id'), nullable=False),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('decision', sa.String(25), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_task_decisions_task_id', 'task_decisions', ['task_id'])


def downgrade():
    op.drop_index('ix_task_decisions_task_id', table_name='task_decisions')
    op.drop_table('task_decisions')
    op.drop_column('task_submissions', 'report_json')
