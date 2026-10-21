"""Managed academic departments: mutable display names and stable codes.
Revision ID: e05ncet009
Revises: d04ncet008
"""
from alembic import op
import sqlalchemy as sa

revision='e05ncet009'
down_revision='d04ncet008'
branch_labels=None
depends_on=None

def upgrade():
    departments=op.create_table('academic_departments',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('code',sa.String(160),nullable=False),
        sa.Column('name',sa.String(160),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False,server_default=sa.true()))
    op.create_index('ix_academic_departments_code','academic_departments',['code'],unique=True)
    op.create_index('ix_academic_departments_name','academic_departments',['name'],unique=True)
    connection=op.get_bind()
    names=['Computer Applications','Computer Science & Engineering','Mechanical Engineering']
    # Preserve any other existing institutionally defined user departments.
    rows=connection.execute(sa.text("SELECT DISTINCT department FROM users WHERE role IN ('student','hod','staff')")).all()
    for row in rows:
        name=(row[0] or '').strip()
        if name and name.lower() not in {v.lower() for v in names}:
            names.append(name)
    for name in names:
        connection.execute(departments.insert().values(code=name,name=name,active=True))

def downgrade():
    op.drop_index('ix_academic_departments_name',table_name='academic_departments')
    op.drop_index('ix_academic_departments_code',table_name='academic_departments')
    op.drop_table('academic_departments')
