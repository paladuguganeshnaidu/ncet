"""Private BCA student profiles and group collaboration threads.

Revision ID: 7c9bca002
Revises: 6bcabca001
"""
from alembic import op
import sqlalchemy as sa
revision = '7c9bca002'
down_revision = '6bcabca001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('collaboration_profiles',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('student_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('bio',sa.String(360),nullable=False),
        sa.Column('skills',sa.String(220),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_collaboration_profiles_student_id','collaboration_profiles',['student_id'],unique=True)
    op.create_table('collaboration_posts',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('student_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('title',sa.String(140),nullable=False),
        sa.Column('description',sa.Text(),nullable=False),
        sa.Column('help_needed',sa.String(280),nullable=False),
        sa.Column('state',sa.String(18),nullable=False),
        sa.Column('hidden',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for name in ('student_id','state','hidden','created_at'):
        op.create_index('ix_collaboration_posts_'+name,'collaboration_posts',[name])
    op.create_table('collaboration_comments',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('post_id',sa.Integer(),sa.ForeignKey('collaboration_posts.id',ondelete='CASCADE'),nullable=False),
        sa.Column('author_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('message',sa.Text(),nullable=False),
        sa.Column('hidden',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    for name in ('post_id','author_id'):
        op.create_index('ix_collaboration_comments_'+name,'collaboration_comments',[name])


def downgrade():
    op.drop_index('ix_collaboration_comments_author_id',table_name='collaboration_comments')
    op.drop_index('ix_collaboration_comments_post_id',table_name='collaboration_comments')
    op.drop_table('collaboration_comments')
    for name in ('created_at','hidden','state','student_id'):
        op.drop_index('ix_collaboration_posts_'+name,table_name='collaboration_posts')
    op.drop_table('collaboration_posts')
    op.drop_index('ix_collaboration_profiles_student_id',table_name='collaboration_profiles')
    op.drop_table('collaboration_profiles')
