"""Add immutable HOD task timeline events.

Revision ID: g07ncet011
Revises: f06ncet010
"""
from alembic import op
import sqlalchemy as sa

revision='g07ncet011'
down_revision='f06ncet010'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('task_events',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('task_id',sa.Integer(),sa.ForeignKey('task_items.id'),nullable=False),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=True),
        sa.Column('event',sa.String(32),nullable=False),
        sa.Column('state',sa.String(26),nullable=False),
        sa.Column('detail',sa.String(250),nullable=False),
        sa.Column('at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_task_events_task_id','task_events',['task_id'])
    op.create_index('ix_task_events_at','task_events',['at'])

def downgrade():
    raise RuntimeError('Non-destructive rollback: preserve task audit timelines and take an archival backup.')
