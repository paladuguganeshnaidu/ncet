"""Add department tasks, revisions, notifications and community digests.

Revision ID: 8d0ncet003
Revises: 7c9bca002
"""
from alembic import op
import sqlalchemy as sa
revision='8d0ncet003'
down_revision='7c9bca002'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('task_batches',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('department',sa.String(160),nullable=False),
        sa.Column('title',sa.String(140),nullable=False),sa.Column('created_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_task_batches_department','task_batches',['department'])
    op.create_table('task_items',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('batch_id',sa.Integer(),sa.ForeignKey('task_batches.id'),nullable=False),
        sa.Column('department',sa.String(160),nullable=False),sa.Column('filename',sa.String(200),nullable=False),
        sa.Column('reference_pdf',sa.LargeBinary(),nullable=False),sa.Column('assigned_to',sa.Integer(),sa.ForeignKey('users.id'),nullable=True),
        sa.Column('assigned_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=True),sa.Column('notes',sa.Text(),nullable=False),
        sa.Column('rules_json',sa.Text(),nullable=False),sa.Column('state',sa.String(26),nullable=False),
        sa.Column('deadline',sa.DateTime(timezone=True),nullable=True),sa.Column('score',sa.Integer(),nullable=True),
        sa.Column('report_json',sa.Text(),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('batch_id','filename',name='uq_task_batch_file'))
    for col in ('batch_id','department','assigned_to','state'):
        op.create_index('ix_task_items_'+col,'task_items',[col])
    op.create_table('task_submissions',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('task_id',sa.Integer(),sa.ForeignKey('task_items.id'),nullable=False),
        sa.Column('uploaded_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),sa.Column('filename',sa.String(200),nullable=False),
        sa.Column('content',sa.LargeBinary(),nullable=False),sa.Column('state',sa.String(22),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('started_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('completed_at',sa.DateTime(timezone=True),nullable=True),
        sa.UniqueConstraint('task_id','revision',name='uq_task_revision'))
    for col in ('task_id','state'):
        op.create_index('ix_task_submissions_'+col,'task_submissions',[col])
    op.create_table('task_notifications',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('task_id',sa.Integer(),sa.ForeignKey('task_items.id'),nullable=True),
        sa.Column('text',sa.String(300),nullable=False),sa.Column('seen',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    for col in ('user_id','seen'):
        op.create_index('ix_task_notifications_'+col,'task_notifications',[col])
    op.create_table('discussion_digests',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('slot',sa.String(20),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),sa.Column('summary',sa.Text(),nullable=False),
        sa.Column('topics_json',sa.Text(),nullable=False),sa.Column('review_flags_json',sa.Text(),nullable=False),
        sa.Column('post_count',sa.Integer(),nullable=False),sa.Column('comment_count',sa.Integer(),nullable=False),
        sa.Column('model',sa.String(130),nullable=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('completed_at',sa.DateTime(timezone=True),nullable=True))
    op.create_index('ix_discussion_digests_slot','discussion_digests',['slot'],unique=True)


def downgrade():
    # Non-destructive schema rollback: explicit downgrade to drop tables must
    # only be performed after taking an archival database backup.
    raise RuntimeError('Destructive downgrade is disabled: take a backup and plan an archival migration.')
