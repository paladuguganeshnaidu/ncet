"""Record idempotent delivery of HOD task reminders.

Revision ID: i09ncet013
Revises: h08ncet012
"""
from alembic import op
import sqlalchemy as sa

revision='i09ncet013'
down_revision='h08ncet012'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('task_reminder_deliveries',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('task_id',sa.Integer(),sa.ForeignKey('task_items.id',ondelete='CASCADE'),nullable=False),
        sa.Column('recipient_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('kind',sa.String(20),nullable=False),
        sa.Column('delivery_key',sa.String(220),nullable=False),
        sa.Column('sent_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('delivery_key',name='uq_task_reminder_delivery_key'))
    op.create_index('ix_task_reminder_deliveries_task_id','task_reminder_deliveries',['task_id'])
    op.create_index('ix_task_reminder_deliveries_recipient_id','task_reminder_deliveries',['recipient_id'])
    op.create_index('ix_task_reminder_deliveries_sent_at','task_reminder_deliveries',['sent_at'])


def downgrade():
    op.drop_index('ix_task_reminder_deliveries_sent_at',table_name='task_reminder_deliveries')
    op.drop_index('ix_task_reminder_deliveries_recipient_id',table_name='task_reminder_deliveries')
    op.drop_index('ix_task_reminder_deliveries_task_id',table_name='task_reminder_deliveries')
    op.drop_table('task_reminder_deliveries')
