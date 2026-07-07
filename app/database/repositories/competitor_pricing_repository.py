from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CompetitorPricing
from app.database.repositories.base import BaseRepository


class CompetitorPricingRepository(BaseRepository[CompetitorPricing]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorPricing)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorPricing]:
        stmt = (
            select(CompetitorPricing)
            .where(CompetitorPricing.competitor_id == competitor_id)
            .order_by(CompetitorPricing.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(self, competitor_id: int, category: str) -> list[CompetitorPricing]:
        stmt = (
            select(CompetitorPricing)
            .where(
                CompetitorPricing.competitor_id == competitor_id,
                CompetitorPricing.category == category,
            )
            .order_by(CompetitorPricing.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_hash(self, competitor_id: int, content_hash: str) -> CompetitorPricing | None:
        """Find a pricing entry by its content hash within a competitor scope."""
        stmt = select(CompetitorPricing).where(
            CompetitorPricing.competitor_id == competitor_id,
            CompetitorPricing.content_hash == content_hash,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        content_hash: str,
        service_name: str,
        category: str | None = None,
        base_price: float | None = None,
        promotional_price: float | None = None,
        currency: str = "USD",
        discount: float | None = None,
        membership_pricing: dict[str, object] | None = None,
        subscription_plans: dict[str, object] | None = None,
    ) -> CompetitorPricing:
        """Insert or update a pricing entry based on content hash.

        If an identical pricing entry (same competitor and content hash) exists,
        update its collected_at timestamp. Otherwise, create a new record.
        """
        existing = await self.get_by_hash(competitor_id, content_hash)
        if existing:
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing
        return await self.create(
            competitor_id=competitor_id,
            content_hash=content_hash,
            service_name=service_name,
            category=category,
            base_price=base_price,
            promotional_price=promotional_price,
            currency=currency,
            discount=discount,
            membership_pricing=membership_pricing,
            subscription_plans=subscription_plans or {},
        )

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorPricing).where(CompetitorPricing.competitor_id == competitor_id)
        await self._session.execute(stmt)
        await self._session.flush()
