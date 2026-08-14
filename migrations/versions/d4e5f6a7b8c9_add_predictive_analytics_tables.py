"""Add predictive analytics tables and composite indexes

Revision ID: d4e5f6a7b8c9
Revises: a24c3b3a8a94
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "a24c3b3a8a94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Composite temporal indexes on existing tables ──────────────────────
    op.create_index(
        "ix_services_comp_date",
        "competitor_services",
        ["competitor_id", "collected_at"],
    )
    op.create_index(
        "ix_pricing_comp_date",
        "competitor_pricing",
        ["competitor_id", "collected_at"],
    )

    # ── competitor_change_events table ─────────────────────────────────────
    op.create_table(
        "competitor_change_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "competitor_id",
            sa.Integer(),
            sa.ForeignKey("competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("magnitude", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("metadata", JSONB, nullable=True),
    )
    op.create_index("ix_change_event_competitor_id", "competitor_change_events", ["competitor_id"])
    op.create_index("ix_change_event_event_type", "competitor_change_events", ["event_type"])
    op.create_index("ix_change_event_detected_at", "competitor_change_events", ["detected_at"])
    op.create_index(
        "ix_change_event_comp_date",
        "competitor_change_events",
        ["competitor_id", "detected_at"],
    )

    # ── prediction_evaluations table ───────────────────────────────────────
    op.create_table(
        "prediction_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "competitor_id",
            sa.Integer(),
            sa.ForeignKey("competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prediction_type", sa.String(50), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("error_margin", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("evaluation_notes", sa.Text(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pred_eval_competitor_id", "prediction_evaluations", ["competitor_id"])
    op.create_index("ix_pred_eval_prediction_type", "prediction_evaluations", ["prediction_type"])
    op.create_index("ix_pred_eval_evaluated_at", "prediction_evaluations", ["evaluated_at"])


def downgrade() -> None:
    op.drop_table("prediction_evaluations")
    op.drop_table("competitor_change_events")
    op.drop_index("ix_pricing_comp_date", "competitor_pricing")
    op.drop_index("ix_services_comp_date", "competitor_services")
