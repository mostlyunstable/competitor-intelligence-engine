from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CollectionStatus, RawStorage
from app.database.repositories.base import BaseRepository


class RawStorageRepository(BaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RawStorage)

    async def get_by_competitor(self, competitor_id: int) -> list[RawStorage]:
        stmt = (
            select(RawStorage)
            .where(RawStorage.competitor_id == competitor_id)
            .order_by(RawStorage.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_url(self, competitor_id: int, source_url: str) -> RawStorage | None:
        stmt = select(RawStorage).where(
            RawStorage.competitor_id == competitor_id,
            RawStorage.source_url == source_url,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest(self, competitor_id: int) -> RawStorage | None:
        stmt = (
            select(RawStorage)
            .where(RawStorage.competitor_id == competitor_id)
            .order_by(RawStorage.id.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def upsert(
        self,
        competitor_id: int,
        source_url: str,
        content_hash: str,
        raw_html: str | None = None,
        raw_json: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        collection_status: CollectionStatus = CollectionStatus.SUCCESS,
    ) -> RawStorage:
        """Insert or update raw storage based on URL.

        If an entry with the same URL exists, update its HTML and metadata.
        Otherwise, create a new record.
        """
        existing = await self.get_by_url(competitor_id, source_url)
        if existing:
            existing.raw_html = raw_html
            existing.raw_json = raw_json
            existing.metadata_ = metadata
            existing.content_hash = content_hash
            existing.collection_status = collection_status
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing
        return await self.create(  # type: ignore[no-any-return]
            competitor_id=competitor_id,
            source_url=source_url,
            content_hash=content_hash,
            raw_html=raw_html,
            raw_json=raw_json,
            metadata_=metadata,
            collection_status=collection_status,
        )

    async def delete_by_competitor(self, competitor_id: int) -> None:
        items = await self.get_by_competitor(competitor_id)
        for item in items:
            await self._session.delete(item)
        await self._session.flush()
