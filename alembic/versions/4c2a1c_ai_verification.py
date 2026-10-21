"""Versioned departmental policies, verification jobs, encrypted integration settings.
Revision ID: 4c2a1c
Revises: 3bfb96d661c6
"""
from alembic import op
import sqlalchemy as sa
revision='4c2a1c'
down_revision='3bfb96d661c6'
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table('documents') as batch:
        batch.alter_column('status', existing_type=sa.String(length=12),type_=sa.String(length=24),existing_nullable=False)
    op.create_table('rule_policies',sa.Column('id',sa.Integer,primary_key=True),sa.Column('department',sa.String(160),nullable=False),sa.Column('version',sa.Integer,nullable=False),sa.Column('rules_json',sa.Text,nullable=False),sa.Column('created_by',sa.Integer,sa.ForeignKey('users.id'),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('department','version'))
    op.create_index('ix_rule_policies_department','rule_policies',['department'])
    op.create_table('verifications',sa.Column('id',sa.Integer,primary_key=True),sa.Column('document_id',sa.Integer,sa.ForeignKey('documents.id',ondelete='CASCADE'),nullable=False),sa.Column('revision',sa.Integer,nullable=False),sa.Column('policy_id',sa.Integer,sa.ForeignKey('rule_policies.id'),nullable=True),sa.Column('state',sa.String(20),nullable=False),sa.Column('report_json',sa.Text,nullable=False),sa.Column('error_code',sa.String(90),nullable=True),sa.Column('model',sa.String(130),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('started_at',sa.DateTime(timezone=True),nullable=True),sa.Column('completed_at',sa.DateTime(timezone=True),nullable=True),sa.UniqueConstraint('document_id','revision'))
    op.create_index('ix_verifications_document_id','verifications',['document_id'])
    op.create_index('ix_verifications_state','verifications',['state'])
    op.create_index('ix_verify_state_created','verifications',['state','created_at'])
    op.create_table('integration_settings',sa.Column('key',sa.String(100),primary_key=True),sa.Column('encrypted_value',sa.Text,nullable=False),sa.Column('updated_by',sa.Integer,sa.ForeignKey('users.id'),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    with op.batch_alter_table('documents') as batch:
        batch.alter_column('status',existing_type=sa.String(length=24),type_=sa.String(length=12),existing_nullable=False)
    op.drop_table('integration_settings')
    op.drop_index('ix_verify_state_created',table_name='verifications')
    op.drop_index('ix_verifications_state',table_name='verifications')
    op.drop_index('ix_verifications_document_id',table_name='verifications')
    op.drop_table('verifications')
    op.drop_index('ix_rule_policies_department',table_name='rule_policies')
    op.drop_table('rule_policies')
