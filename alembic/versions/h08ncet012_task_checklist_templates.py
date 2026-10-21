"""Add reusable, versioned HOD checklist templates.

Revision ID: h08ncet012
Revises: g07ncet011
"""
from alembic import op
import sqlalchemy as sa

revision='h08ncet012'
down_revision='g07ncet011'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('task_checklist_templates',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('template_id',sa.String(32),nullable=False),
        sa.Column('department',sa.String(160),nullable=False),
        sa.Column('name',sa.String(100),nullable=False),
        sa.Column('version',sa.Integer(),nullable=False),
        sa.Column('rules_json',sa.Text(),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('template_id','version',name='uq_task_checklist_template_version'))
    op.create_index('ix_task_checklist_templates_template_id','task_checklist_templates',['template_id'])
    op.create_index('ix_task_checklist_templates_department','task_checklist_templates',['department'])
    op.create_index('ix_task_checklist_templates_active','task_checklist_templates',['active'])

def downgrade():
    op.drop_index('ix_task_checklist_templates_active',table_name='task_checklist_templates')
    op.drop_index('ix_task_checklist_templates_department',table_name='task_checklist_templates')
    op.drop_index('ix_task_checklist_templates_template_id',table_name='task_checklist_templates')
    op.drop_table('task_checklist_templates')
