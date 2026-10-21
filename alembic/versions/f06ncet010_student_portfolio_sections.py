"""Optional projects and interest sections for student portfolios.

Revision ID: f06ncet010
Revises: e05ncet009
"""
from alembic import op
import sqlalchemy as sa

revision='f06ncet010'
down_revision='e05ncet009'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('bca_student_showcases', sa.Column('projects_json',sa.Text(),nullable=False,server_default='[]'))
    op.add_column('bca_student_showcases', sa.Column('interests_json',sa.Text(),nullable=False,server_default='[]'))

def downgrade():
    op.drop_column('bca_student_showcases','interests_json')
    op.drop_column('bca_student_showcases','projects_json')
