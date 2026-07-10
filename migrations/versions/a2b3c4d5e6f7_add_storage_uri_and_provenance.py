"""Add storage URI and provenance

Revision ID: a2b3c4d5e6f7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-09 15:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add storage columns to raw_storage
    op.add_column("raw_storage", sa.Column("storage_uri", sa.String(length=2048), nullable=True))
    op.add_column("raw_storage", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("raw_storage", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.drop_column("raw_storage", "raw_html")
    op.drop_column("raw_storage", "raw_json")

    # Add storage columns to competitor_pages
    op.add_column(
        "competitor_pages", sa.Column("storage_uri", sa.String(length=2048), nullable=True)
    )
    op.add_column("competitor_pages", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("competitor_pages", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.drop_column("competitor_pages", "raw_html")

    # Add provenance to entities
    entities = [
        "competitor_services",
        "competitor_pricing",
        "competitor_content",
        "competitor_social_profiles",
        "competitor_team_members",
        "competitor_certifications",
        "competitor_service_areas",
    ]

    for table in entities:
        # Check if table exists (SQLite might not have all depending on setup, but PG does)
        op.add_column(table, sa.Column("provenance", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Reverse provenance
    entities = [
        "competitor_services",
        "competitor_pricing",
        "competitor_content",
        "competitor_social_profiles",
        "competitor_team_members",
        "competitor_certifications",
        "competitor_service_areas",
    ]
    for table in entities:
        op.drop_column(table, "provenance")

    # Reverse competitor_pages
    op.add_column("competitor_pages", sa.Column("raw_html", sa.Text(), nullable=True))
    op.drop_column("competitor_pages", "file_size_bytes")
    op.drop_column("competitor_pages", "mime_type")
    op.drop_column("competitor_pages", "storage_uri")

    # Reverse raw_storage
    op.add_column("raw_storage", sa.Column("raw_json", sa.JSON(), nullable=True))
    op.add_column("raw_storage", sa.Column("raw_html", sa.Text(), nullable=True))
    op.drop_column("raw_storage", "file_size_bytes")
    op.drop_column("raw_storage", "mime_type")
    op.drop_column("raw_storage", "storage_uri")
