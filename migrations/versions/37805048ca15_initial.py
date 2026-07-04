"""initial

Revision ID: 37805048ca15
Revises:
Create Date: 2026-07-02 21:16:29.438204
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "37805048ca15"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types using safe PL/pgSQL blocks if they don't already exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'collection_frequency_enum') THEN
                CREATE TYPE collection_frequency_enum AS ENUM ('HOURLY', 'DAILY', 'WEEKLY');
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'collection_status_enum') THEN
                CREATE TYPE collection_status_enum AS ENUM ('SUCCESS', 'FAILED', 'PARTIAL');
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'social_platform_enum') THEN
                CREATE TYPE social_platform_enum AS ENUM ('LINKEDIN', 'FACEBOOK', 'INSTAGRAM', 'TWITTER', 'YOUTUBE', 'PINTEREST', 'THREADS');
            END IF;
        END$$;
        """
    )

    # Reference enum types by name in columns (no create_type)
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=2048), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "collection_frequency",
            postgresql.ENUM(
                "HOURLY", "DAILY", "WEEKLY", name="collection_frequency_enum", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("modules", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        comment="Registered competitor websites",
    )
    op.create_table(
        "collection_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("records_collected", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Audit trail of all collection runs",
    )
    op.create_index(
        "ix_collection_log_competitor_id", "collection_logs", ["competitor_id"], unique=False
    )
    op.create_index("ix_collection_log_start_time", "collection_logs", ["start_time"], unique=False)
    op.create_table(
        "competitor_content",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competitor_id", "url", name="uq_competitor_content_url"),
        comment="Blog posts, articles, and press releases",
    )
    op.create_index(
        "ix_competitor_content_competitor_id", "competitor_content", ["competitor_id"], unique=False
    )
    op.create_index(
        "ix_competitor_content_content_hash", "competitor_content", ["content_hash"], unique=False
    )
    op.create_index("ix_competitor_content_url", "competitor_content", ["url"], unique=False)
    op.create_table(
        "competitor_pricing",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("service_name", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("base_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("promotional_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("discount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("membership_pricing", sa.JSON(), nullable=True),
        sa.Column("subscription_plans", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Pricing data collected from competitors",
    )
    op.create_index(
        "ix_competitor_pricing_competitor_id", "competitor_pricing", ["competitor_id"], unique=False
    )
    op.create_index(
        "ix_competitor_pricing_content_hash", "competitor_pricing", ["content_hash"], unique=False
    )
    op.create_table(
        "competitor_services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("service_category", sa.String(length=255), nullable=True),
        sa.Column("service_name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_duration", sa.String(length=100), nullable=True),
        sa.Column("starting_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("available_add_ons", sa.JSON(), nullable=False),
        sa.Column("membership_available", sa.Boolean(), nullable=False),
        sa.Column("offers", sa.JSON(), nullable=False),
        sa.Column("discounts", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Service listings collected from competitors",
    )
    op.create_index(
        "ix_competitor_service_competitor_id",
        "competitor_services",
        ["competitor_id"],
        unique=False,
    )
    op.create_index(
        "ix_competitor_service_content_hash", "competitor_services", ["content_hash"], unique=False
    )
    op.create_table(
        "competitor_social",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM(
                "LINKEDIN",
                "FACEBOOK",
                "INSTAGRAM",
                "TWITTER",
                "YOUTUBE",
                "PINTEREST",
                "THREADS",
                name="social_platform_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("profile_url", sa.String(length=2048), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competitor_id", "platform", name="uq_competitor_social_platform"),
        comment="Social media profiles per competitor",
    )
    op.create_index(
        "ix_competitor_social_competitor_id", "competitor_social", ["competitor_id"], unique=False
    )
    op.create_table(
        "competitor_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("page_type", sa.String(length=100), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competitor_id", "url", name="uq_competitor_source_url"),
        comment="Discovered URLs per competitor",
    )
    op.create_index(
        "ix_competitor_source_competitor_id", "competitor_sources", ["competitor_id"], unique=False
    )
    op.create_index("ix_competitor_source_url", "competitor_sources", ["url"], unique=False)
    op.create_table(
        "raw_storage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "collection_status",
            postgresql.ENUM(
                "SUCCESS", "FAILED", "PARTIAL", name="collection_status_enum", create_type=False
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competitor_id", "source_url", name="uq_raw_storage_competitor_url"),
        comment="Original HTML snapshots and raw data",
    )
    op.create_index("ix_raw_storage_competitor_id", "raw_storage", ["competitor_id"], unique=False)
    op.create_index("ix_raw_storage_content_hash", "raw_storage", ["content_hash"], unique=False)
    op.create_index("ix_raw_storage_source_url", "raw_storage", ["source_url"], unique=False)
    op.create_table(
        "competitor_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "collection_status",
            postgresql.ENUM(
                "SUCCESS", "FAILED", "PARTIAL", name="collection_status_enum", create_type=False
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["competitor_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competitor_id", "source_id", name="uq_competitor_page_source"),
        comment="Raw page snapshots collected from competitors",
    )
    op.create_index(
        "ix_competitor_page_competitor_id", "competitor_pages", ["competitor_id"], unique=False
    )
    op.create_index("ix_competitor_page_source_id", "competitor_pages", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_competitor_page_source_id", table_name="competitor_pages")
    op.drop_index("ix_competitor_page_competitor_id", table_name="competitor_pages")
    op.drop_table("competitor_pages")
    op.drop_index("ix_raw_storage_source_url", table_name="raw_storage")
    op.drop_index("ix_raw_storage_content_hash", table_name="raw_storage")
    op.drop_index("ix_raw_storage_competitor_id", table_name="raw_storage")
    op.drop_table("raw_storage")
    op.drop_index("ix_competitor_source_url", table_name="competitor_sources")
    op.drop_index("ix_competitor_source_competitor_id", table_name="competitor_sources")
    op.drop_table("competitor_sources")
    op.drop_index("ix_competitor_social_competitor_id", table_name="competitor_social")
    op.drop_table("competitor_social")
    op.drop_index("ix_competitor_service_content_hash", table_name="competitor_services")
    op.drop_index("ix_competitor_service_competitor_id", table_name="competitor_services")
    op.drop_table("competitor_services")
    op.drop_index("ix_competitor_pricing_content_hash", table_name="competitor_pricing")
    op.drop_index("ix_competitor_pricing_competitor_id", table_name="competitor_pricing")
    op.drop_table("competitor_pricing")
    op.drop_index("ix_competitor_content_url", table_name="competitor_content")
    op.drop_index("ix_competitor_content_content_hash", table_name="competitor_content")
    op.drop_index("ix_competitor_content_competitor_id", table_name="competitor_content")
    op.drop_table("competitor_content")
    op.drop_index("ix_collection_log_start_time", table_name="collection_logs")
    op.drop_index("ix_collection_log_competitor_id", table_name="collection_logs")
    op.drop_table("collection_logs")
    op.drop_table("competitors")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS collection_frequency_enum")
    op.execute("DROP TYPE IF EXISTS collection_status_enum")
    op.execute("DROP TYPE IF EXISTS social_platform_enum")
