from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CollectionLog
from app.database.repositories.base import BaseRepository


class CollectionLogRepository(BaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CollectionLog)

    async def get_by_competitor(self, competitor_id: int, limit: int = 50) -> list[CollectionLog]:
        stmt = (
            select(CollectionLog)
            .where(CollectionLog.competitor_id == competitor_id)
            .order_by(CollectionLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 100) -> list[CollectionLog]:
        stmt = select(CollectionLog).order_by(CollectionLog.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_date_range(self, start: datetime, end: datetime) -> list[CollectionLog]:
        stmt = (
            select(CollectionLog)
            .where(CollectionLog.start_time >= start, CollectionLog.start_time <= end)
            .order_by(CollectionLog.start_time.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_competitor(self, competitor_id: int) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(CollectionLog)
            .where(CollectionLog.competitor_id == competitor_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
