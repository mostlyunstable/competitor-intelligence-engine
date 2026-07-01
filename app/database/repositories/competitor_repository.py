from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.base import BaseRepository


class CompetitorRepository(BaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Competitor)

    async def get_by_name(self, name: str) -> Competitor | None:
        stmt = select(Competitor).where(Competitor.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_enabled(self) -> list[Competitor]:
        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_frequency(self, frequency: str) -> list[Competitor]:
        stmt = select(Competitor).where(
            Competitor.enabled.is_(True),
            Competitor.collection_frequency == frequency,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def enable(self, competitor_id: int) -> Competitor | None:
        return await self.update(competitor_id, enabled=True)

    async def disable(self, competitor_id: int) -> Competitor | None:
        return await self.update(competitor_id, enabled=False)
