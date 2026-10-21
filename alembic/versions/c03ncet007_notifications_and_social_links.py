"""BCA profile links and persistent in-app notifications.
Revision ID: c03ncet007
Revises: b02ncet006
"""
from alembic import op
import sqlalchemy as sa
revision='c03ncet007'
down_revision='b02ncet006'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('app_notifications',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('recipient_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('text',sa.String(280),nullable=False),
        sa.Column('link',sa.String(220),nullable=False),
        sa.Column('category',sa.String(32),nullable=False),
        sa.Column('seen',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_app_notifications_recipient_id','app_notifications',['recipient_id'])
    op.create_index('ix_app_notifications_category','app_notifications',['category'])
    op.create_index('ix_app_notifications_created_at','app_notifications',['created_at'])
    op.add_column('bca_student_showcases',sa.Column('social_links_json',sa.Text(),nullable=False,server_default='{}'))

def downgrade():
    op.drop_column('bca_student_showcases','social_links_json')
    op.drop_index('ix_app_notifications_created_at',table_name='app_notifications')
    op.drop_index('ix_app_notifications_category',table_name='app_notifications')
    op.drop_index('ix_app_notifications_recipient_id',table_name='app_notifications')
    op.drop_table('app_notifications')
