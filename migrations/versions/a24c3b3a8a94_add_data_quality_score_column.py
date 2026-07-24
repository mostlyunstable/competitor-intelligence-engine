"""add data_quality_score column

Revision ID: a24c3b3a8a94
Revises: c3d4e5f6a7b8
Create Date: 2026-07-25 04:46:02.139446
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a24c3b3a8a94'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'competitor_ai_insights',
        sa.Column('data_quality_score', sa.Float(), nullable=False, server_default='0.0'),
    )
    op.alter_column('competitor_ai_insights', 'data_quality_score', server_default=None)


def downgrade() -> None:
    op.drop_column('competitor_ai_insights', 'data_quality_score')
