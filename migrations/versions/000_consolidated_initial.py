"""consolidated initial schema

Revision ID: 000_initial
Revises: 
Create Date: 2025-07-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "000_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("frequency", sa.String(50), nullable=False, server_default="daily"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("page_type", sa.String(50), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("etag", sa.String(255), nullable=True),
        sa.Column("last_modified", sa.String(255), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_service_hash"),
    )

    op.create_table(
        "competitor_pricing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_name", sa.String(255), nullable=False),
        sa.Column("plan_name", sa.String(255), nullable=True),
        sa.Column("price", sa.String(100), nullable=True),
        sa.Column("period", sa.String(50), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_pricing_hash"),
    )

    op.create_table(
        "competitor_content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_social",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tech_stacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technology", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "collection_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("pages_collected", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "raw_storage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("storage_uri", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_team_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_team_member_hash"),
    )

    op.create_table(
        "competitor_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("obtained_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_certification_hash"),
    )

    op.create_table(
        "competitor_service_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("area_name", sa.String(255), nullable=False),
        sa.Column("area_type", sa.String(50), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_service_area_hash"),
    )

    op.create_index("ix_competitors_name", "competitors", ["name"])
    op.create_index("ix_competitors_status", "competitors", ["status"])
    op.create_index("ix_competitor_sources_competitor_id", "competitor_sources", ["competitor_id"])
    op.create_index("ix_competitor_pages_competitor_id", "competitor_pages", ["competitor_id"])
    op.create_index("ix_competitor_services_competitor_id", "competitor_services", ["competitor_id"])
    op.create_index("ix_competitor_pricing_competitor_id", "competitor_pricing", ["competitor_id"])
    op.create_index("ix_competitor_content_competitor_id", "competitor_content", ["competitor_id"])
    op.create_index("ix_competitor_social_competitor_id", "competitor_social", ["competitor_id"])
    op.create_index("ix_tech_stacks_competitor_id", "tech_stacks", ["competitor_id"])
    op.create_index("ix_collection_logs_competitor_id", "collection_logs", ["competitor_id"])
    op.create_index("ix_raw_storage_competitor_id", "raw_storage", ["competitor_id"])
    op.create_index("ix_competitor_team_members_competitor_id", "competitor_team_members", ["competitor_id"])
    op.create_index("ix_competitor_certifications_competitor_id", "competitor_certifications", ["competitor_id"])
    op.create_index("ix_competitor_service_areas_competitor_id", "competitor_service_areas", ["competitor_id"])


def downgrade() -> None:
    op.drop_table("competitor_service_areas")
    op.drop_table("competitor_certifications")
    op.drop_table("competitor_team_members")
    op.drop_table("raw_storage")
    op.drop_table("collection_logs")
    op.drop_table("tech_stacks")
    op.drop_table("competitor_social")
    op.drop_table("competitor_content")
    op.drop_table("competitor_pricing")
    op.drop_table("competitor_services")
    op.drop_table("competitor_pages")
    op.drop_table("competitor_sources")
    op.drop_table("competitors")
