"""Add AI insight feedback table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-07-25
"""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_insight_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("insight_id", sa.Integer(), sa.ForeignKey("competitor_ai_insights.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ai_insight_feedback")
