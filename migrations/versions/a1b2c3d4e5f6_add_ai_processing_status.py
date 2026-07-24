"""Add processing_status to competitor_ai_insights

Revision ID: a1b2c3d4e5f6
Revises: 712fdbe261ba
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "712fdbe261ba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "competitor_ai_insights",
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="completed"),
    )
    op.create_index(
        "ix_competitor_ai_insights_processing_status",
        "competitor_ai_insights",
        ["processing_status"],
    )
    # market_position was VARCHAR(255), LLM generates longer text
    op.alter_column("competitor_ai_insights", "market_position", type_=sa.Text())


def downgrade() -> None:
    op.drop_index("ix_competitor_ai_insights_processing_status", table_name="competitor_ai_insights")
    op.drop_column("competitor_ai_insights", "processing_status")
    op.alter_column("competitor_ai_insights", "market_position", type_=sa.String(255))
