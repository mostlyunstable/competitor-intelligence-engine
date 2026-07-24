"""Add cost tracking columns to competitor_ai_insights

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-07-25
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("competitor_ai_insights", sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("competitor_ai_insights", sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("competitor_ai_insights", sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("competitor_ai_insights", sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    op.drop_column("competitor_ai_insights", "estimated_cost_usd")
    op.drop_column("competitor_ai_insights", "total_tokens")
    op.drop_column("competitor_ai_insights", "completion_tokens")
    op.drop_column("competitor_ai_insights", "prompt_tokens")
