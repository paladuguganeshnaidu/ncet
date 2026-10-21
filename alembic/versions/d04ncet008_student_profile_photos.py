"""Student profile photos (optional and private until profile publication).

Revision ID: d04ncet008
Revises: c03ncet007
"""
from alembic import op
import sqlalchemy as sa

revision='d04ncet008'
down_revision='c03ncet007'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('bca_student_showcases',sa.Column('photo_bytes',sa.LargeBinary(),nullable=True))
    op.add_column('bca_student_showcases',sa.Column('photo_mime',sa.String(32),nullable=True))

def downgrade():
    op.drop_column('bca_student_showcases','photo_mime')
    op.drop_column('bca_student_showcases','photo_bytes')
