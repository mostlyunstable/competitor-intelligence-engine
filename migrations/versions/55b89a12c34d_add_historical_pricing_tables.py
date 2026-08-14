"""Add historical pricing and taxonomy tables

Revision ID: 55b89a12c34d
Revises: 2c219025a773
Create Date: 2026-08-14 20:48:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '55b89a12c34d'
down_revision: str | None = '2c219025a773'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'canonical_services',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category', sa.String(length=255), nullable=False),
        sa.Column('subcategory', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('pricing_unit', sa.String(length=50), nullable=False, server_default='per_service'),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        comment='Standardized canonical service taxonomy'
    )
    with op.batch_alter_table('canonical_services', schema=None) as batch_op:
        batch_op.create_index('ix_canonical_services_category', ['category'], unique=False)
        batch_op.create_index('ix_canonical_services_subcategory', ['subcategory'], unique=False)
        batch_op.create_index('ix_canonical_services_name', ['name'], unique=True)

    op.create_table(
        'service_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('original_service_name', sa.String(length=500), nullable=False),
        sa.Column('canonical_service_id', sa.Integer(), nullable=False),
        sa.Column('competitor_id', sa.Integer(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('matching_methodology', sa.String(length=100), nullable=False, server_default='exact_match'),
        sa.Column('human_validation_status', sa.String(length=50), nullable=False, server_default='validated'),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['canonical_service_id'], ['canonical_services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='Mappings from raw service names to canonical services'
    )
    with op.batch_alter_table('service_mappings', schema=None) as batch_op:
        batch_op.create_index('ix_service_mappings_original_name', ['original_service_name'], unique=False)
        batch_op.create_index('ix_service_mappings_canonical_id', ['canonical_service_id'], unique=False)
        batch_op.create_index('ix_service_mappings_competitor_id', ['competitor_id'], unique=False)
        batch_op.create_index('ix_service_mapping_comp_canonical', ['competitor_id', 'canonical_service_id'], unique=False)

    op.create_table(
        'price_observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('competitor_id', sa.Integer(), nullable=False),
        sa.Column('canonical_service_id', sa.Integer(), nullable=True),
        sa.Column('original_service_name', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=False, server_default='Pan India'),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('pricing_unit', sa.String(length=50), nullable=False, server_default='per_service'),
        sa.Column('price_type', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='website'),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('validation_status', sa.String(length=50), nullable=False, server_default='validated'),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['canonical_service_id'], ['canonical_services.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['competitor_services.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='Immutable time-series pricing observations'
    )
    with op.batch_alter_table('price_observations', schema=None) as batch_op:
        batch_op.create_index('ix_price_observations_competitor_id', ['competitor_id'], unique=False)
        batch_op.create_index('ix_price_observations_canonical_id', ['canonical_service_id'], unique=False)
        batch_op.create_index('ix_price_observations_collected_at', ['collected_at'], unique=False)
        batch_op.create_index('ix_price_obs_comp_canonical_date', ['competitor_id', 'canonical_service_id', 'collected_at'], unique=False)

    op.create_table(
        'pricing_resolution_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('canonical_service_id', sa.Integer(), nullable=False),
        sa.Column('conflicting_observations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('resolved_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('promotional_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_type', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('resolution_reason', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['canonical_service_id'], ['canonical_services.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Audit trail of conflicting pricing discrepancy resolutions'
    )
    with op.batch_alter_table('pricing_resolution_records', schema=None) as batch_op:
        batch_op.create_index('ix_pricing_resolution_canonical_id', ['canonical_service_id'], unique=False)

    op.create_table(
        'data_quality_score_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('observation_id', sa.Integer(), nullable=False),
        sa.Column('completeness', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('accuracy', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('consistency', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('timeliness', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('validity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('uniqueness', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('comparability', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['observation_id'], ['price_observations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('observation_id'),
        comment='Detailed 7-dimension data quality scores'
    )
    with op.batch_alter_table('data_quality_score_records', schema=None) as batch_op:
        batch_op.create_index('ix_data_quality_observation_id', ['observation_id'], unique=True)


def downgrade() -> None:
    op.drop_table('data_quality_score_records')
    op.drop_table('pricing_resolution_records')
    op.drop_table('price_observations')
    op.drop_table('service_mappings')
    op.drop_table('canonical_services')
