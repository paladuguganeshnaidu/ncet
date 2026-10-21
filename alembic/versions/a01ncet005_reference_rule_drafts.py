"""Add durable per-reference AI rule proposals, no existing task edits.

Revision ID: a01ncet005
Revises: 9e1ncet004
"""
from alembic import op
import sqlalchemy as sa
revision="a01ncet005"
down_revision="9e1ncet004"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("task_rule_drafts",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("task_id",sa.Integer(),sa.ForeignKey("task_items.id",ondelete="CASCADE"),nullable=False),
        sa.Column("state",sa.String(20),nullable=False),
        sa.Column("rules_json",sa.Text(),nullable=False),
        sa.Column("summary",sa.Text(),nullable=False),
        sa.Column("error",sa.String(220),nullable=False),
        sa.Column("model_name",sa.String(180),nullable=False),
        sa.Column("started_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("completed_at",sa.DateTime(timezone=True),nullable=True))
    op.create_index("ix_task_rule_drafts_task_id","task_rule_drafts",["task_id"],unique=True)
    op.create_index("ix_task_rule_drafts_state","task_rule_drafts",["state"])

def downgrade():
    op.drop_index("ix_task_rule_drafts_state",table_name="task_rule_drafts")
    op.drop_index("ix_task_rule_drafts_task_id",table_name="task_rule_drafts")
    op.drop_table("task_rule_drafts")
