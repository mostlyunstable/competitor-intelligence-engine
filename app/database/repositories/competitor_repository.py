from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.base import BaseRepository


class CompetitorRepository(BaseRepository[Competitor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Competitor)

    async def get_by_name(self, name: str) -> Competitor | None:
        stmt = select(Competitor).where(Competitor.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_frequency(self, frequency: str) -> list[Competitor]:
        stmt = select(Competitor).where(
            Competitor.enabled.is_(True),
            Competitor.collection_frequency == frequency,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_enabled(self) -> list[Competitor]:
        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists(self, competitor_id: int) -> bool:
        stmt = select(Competitor.id).where(Competitor.id == competitor_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Competitor)
        result = await self._session.execute(stmt)
        return result.scalar() or 0
