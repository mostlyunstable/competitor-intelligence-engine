from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CollectionStatus, CompetitorPage
from app.database.repositories.base import BaseRepository


class CompetitorPageRepository(BaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorPage)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorPage]:
        stmt = (
            select(CompetitorPage)
            .where(CompetitorPage.competitor_id == competitor_id)
            .order_by(CompetitorPage.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_source(self, source_id: int) -> CompetitorPage | None:
        stmt = (
            select(CompetitorPage)
            .where(CompetitorPage.source_id == source_id)
            .order_by(CompetitorPage.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_latest_by_competitor(self, competitor_id: int) -> CompetitorPage | None:
        stmt = (
            select(CompetitorPage)
            .where(CompetitorPage.competitor_id == competitor_id)
            .order_by(CompetitorPage.id.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_hash(
        self, competitor_id: int, source_id: int | None, content_hash: str
    ) -> CompetitorPage | None:
        """Find a page by its content hash within a competitor and source scope."""
        stmt = select(CompetitorPage).where(
            CompetitorPage.competitor_id == competitor_id,
            CompetitorPage.source_id == source_id,
            CompetitorPage.content_hash == content_hash,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        content_hash: str,
        source_id: int | None = None,
        raw_html: str | None = None,
        raw_json: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        collection_status: CollectionStatus = CollectionStatus.SUCCESS,
    ) -> CompetitorPage:
        """Insert or update a page based on content hash.

        If an identical page (same competitor, source, and content hash) exists,
        update its collected_at timestamp. Otherwise, create a new record.
        """
        existing = await self.get_by_hash(competitor_id, source_id, content_hash)
        if existing:
            existing.raw_html = raw_html
            existing.raw_json = raw_json
            existing.metadata_ = metadata
            existing.collection_status = collection_status
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing
        return await self.create(  # type: ignore[no-any-return]
            competitor_id=competitor_id,
            source_id=source_id,
            content_hash=content_hash,
            raw_html=raw_html,
            raw_json=raw_json,
            metadata_=metadata,
            collection_status=collection_status,
        )
