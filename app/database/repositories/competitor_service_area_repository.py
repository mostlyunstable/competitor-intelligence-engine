from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CompetitorServiceArea
from app.database.repositories.base import BaseRepository


class CompetitorServiceAreaRepository(BaseRepository[CompetitorServiceArea]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorServiceArea)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorServiceArea]:
        stmt = (
            select(CompetitorServiceArea)
            .where(CompetitorServiceArea.competitor_id == competitor_id)
            .order_by(CompetitorServiceArea.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_area_type(self, competitor_id: int, area_type: str) -> list[CompetitorServiceArea]:
        stmt = (
            select(CompetitorServiceArea)
            .where(
                CompetitorServiceArea.competitor_id == competitor_id,
                CompetitorServiceArea.area_type == area_type,
            )
            .order_by(CompetitorServiceArea.area_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_hash(self, competitor_id: int, content_hash: str) -> CompetitorServiceArea | None:
        stmt = select(CompetitorServiceArea).where(
            CompetitorServiceArea.competitor_id == competitor_id,
            CompetitorServiceArea.content_hash == content_hash,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        content_hash: str,
        area_name: str,
        area_type: str = "city",
        state: str | None = None,
        country: str | None = None,
        service_id: int | None = None,
    ) -> CompetitorServiceArea:
        existing = await self.get_by_hash(competitor_id, content_hash)
        if existing:
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing
        return await self.create(
            competitor_id=competitor_id,
            content_hash=content_hash,
            area_name=area_name,
            area_type=area_type,
            state=state,
            country=country,
            service_id=service_id,
        )

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorServiceArea).where(CompetitorServiceArea.competitor_id == competitor_id)
        await self._session.execute(stmt)
        await self._session.flush()
