from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
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

    async def get_by_area_type(
        self, competitor_id: int, area_type: str
    ) -> list[CompetitorServiceArea]:
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
        """Native PostgreSQL upsert: single INSERT ... ON CONFLICT DO UPDATE query."""
        now = datetime.now(UTC)
        stmt = (
            insert(CompetitorServiceArea)
            .values(
                competitor_id=competitor_id,
                content_hash=content_hash,
                area_name=area_name,
                area_type=area_type,
                state=state,
                country=country,
                service_id=service_id,
                collected_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_competitor_service_area_hash",
                set_={"collected_at": now},
            )
            .returning(CompetitorServiceArea)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorServiceArea).where(
            CompetitorServiceArea.competitor_id == competitor_id
        )
        await self._session.execute(stmt)
        await self._session.flush()
