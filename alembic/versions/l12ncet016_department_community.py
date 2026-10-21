"""Scope project collaboration posts to the author's department.

Revision ID: l12ncet016
Revises: k11ncet015
"""
from alembic import op
import sqlalchemy as sa

revision='l12ncet016'
down_revision='k11ncet015'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('collaboration_posts', sa.Column(
        'department', sa.String(length=160), nullable=True))
    bind=op.get_bind()
    posts=sa.table('collaboration_posts',
        sa.column('id',sa.Integer),sa.column('student_id',sa.Integer),sa.column('department',sa.String))
    users=sa.table('users',sa.column('id',sa.Integer),sa.column('department',sa.String))
    author_department=sa.select(users.c.department).where(users.c.id==posts.c.student_id).scalar_subquery()
    bind.execute(posts.update().values(
        department=sa.func.coalesce(author_department,'Computer Applications')))
    with op.batch_alter_table('collaboration_posts') as batch:
        batch.alter_column('department',existing_type=sa.String(length=160),nullable=False)
    op.create_index('ix_collaboration_posts_department_created',
                    'collaboration_posts',['department','created_at','id'])


def downgrade():
    op.drop_index('ix_collaboration_posts_department_created',table_name='collaboration_posts')
    op.drop_column('collaboration_posts','department')
