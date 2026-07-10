"""add unique constraints for native upsert on service, pricing, team, cert, area

Revision ID: b2c3d4e5f6g7
Revises: a2b3c4d5e6f7
Create Date: 2026-07-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: str = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop non-unique indexes (redundant after unique constraint)
    op.drop_index("ix_competitor_service_content_hash", table_name="competitor_services")
    op.drop_index("ix_competitor_pricing_content_hash", table_name="competitor_pricing")
    op.drop_index("ix_competitor_team_member_content_hash", table_name="competitor_team_members")
    op.drop_index(
        "ix_competitor_certification_content_hash", table_name="competitor_certifications"
    )
    op.drop_index("ix_competitor_service_area_content_hash", table_name="competitor_service_areas")

    # Add unique composite indexes for native upsert (INSERT ... ON CONFLICT DO UPDATE)
    op.create_unique_constraint(
        "uq_competitor_service_hash",
        "competitor_services",
        ["competitor_id", "content_hash"],
    )
    op.create_unique_constraint(
        "uq_competitor_pricing_hash",
        "competitor_pricing",
        ["competitor_id", "content_hash"],
    )
    op.create_unique_constraint(
        "uq_competitor_team_member_hash",
        "competitor_team_members",
        ["competitor_id", "content_hash"],
    )
    op.create_unique_constraint(
        "uq_competitor_certification_hash",
        "competitor_certifications",
        ["competitor_id", "content_hash"],
    )
    op.create_unique_constraint(
        "uq_competitor_service_area_hash",
        "competitor_service_areas",
        ["competitor_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_competitor_service_area_hash", "competitor_service_areas", type_="unique"
    )
    op.drop_constraint(
        "uq_competitor_certification_hash", "competitor_certifications", type_="unique"
    )
    op.drop_constraint("uq_competitor_team_member_hash", "competitor_team_members", type_="unique")
    op.drop_constraint("uq_competitor_pricing_hash", "competitor_pricing", type_="unique")
    op.drop_constraint("uq_competitor_service_hash", "competitor_services", type_="unique")

    # Recreate the original non-unique indexes
    op.create_index("ix_competitor_service_content_hash", "competitor_services", ["content_hash"])
    op.create_index("ix_competitor_pricing_content_hash", "competitor_pricing", ["content_hash"])
    op.create_index(
        "ix_competitor_team_member_content_hash", "competitor_team_members", ["content_hash"]
    )
    op.create_index(
        "ix_competitor_certification_content_hash", "competitor_certifications", ["content_hash"]
    )
    op.create_index(
        "ix_competitor_service_area_content_hash", "competitor_service_areas", ["content_hash"]
    )
