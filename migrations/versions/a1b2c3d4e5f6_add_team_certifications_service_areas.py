"""add team_members, certifications, service_areas

Revision ID: a1b2c3d4e5f6
Revises: 37805048ca15
Create Date: 2026-07-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str = "37805048ca15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "competitor_team_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.String(2048), nullable=True),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="Team members and leadership collected from competitors",
    )
    op.create_index("ix_competitor_team_member_competitor_id", "competitor_team_members", ["competitor_id"])
    op.create_index("ix_competitor_team_member_content_hash", "competitor_team_members", ["content_hash"])

    op.create_table(
        "competitor_certifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="certification"),
        sa.Column("issuing_body", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="Certifications, awards, and trust signals collected from competitors",
    )
    op.create_index("ix_competitor_certification_competitor_id", "competitor_certifications", ["competitor_id"])
    op.create_index("ix_competitor_certification_content_hash", "competitor_certifications", ["content_hash"])

    op.create_table(
        "competitor_service_areas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("competitor_services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("area_name", sa.String(500), nullable=False),
        sa.Column("area_type", sa.String(50), nullable=False, server_default="city"),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="Service areas and coverage regions collected from competitors",
    )
    op.create_index("ix_competitor_service_area_competitor_id", "competitor_service_areas", ["competitor_id"])
    op.create_index("ix_competitor_service_area_content_hash", "competitor_service_areas", ["content_hash"])


def downgrade() -> None:
    op.drop_table("competitor_service_areas")
    op.drop_table("competitor_certifications")
    op.drop_table("competitor_team_members")
