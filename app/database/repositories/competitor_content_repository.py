from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CompetitorContent
from app.database.repositories.base import BaseRepository


class CompetitorContentRepository(BaseRepository[CompetitorContent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorContent)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorContent]:
        stmt = (
            select(CompetitorContent)
            .where(CompetitorContent.competitor_id == competitor_id)
            .order_by(CompetitorContent.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(self, competitor_id: int, content_type: str) -> list[CompetitorContent]:
        stmt = (
            select(CompetitorContent)
            .where(
                CompetitorContent.competitor_id == competitor_id,
                CompetitorContent.content_type == content_type,
            )
            .order_by(CompetitorContent.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_url(self, competitor_id: int, url: str) -> CompetitorContent | None:
        stmt = select(CompetitorContent).where(
            CompetitorContent.competitor_id == competitor_id,
            CompetitorContent.url == url,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(self, competitor_id: int, content_hash: str) -> CompetitorContent | None:
        """Find a content item by its content hash within a competitor scope."""
        stmt = select(CompetitorContent).where(
            CompetitorContent.competitor_id == competitor_id,
            CompetitorContent.content_hash == content_hash,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        content_hash: str,
        title: str,
        url: str,
        author: str | None = None,
        publish_date: "date | None" = None,
        summary: str | None = None,
        raw_content: str | None = None,
        content_type: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> CompetitorContent:
        """Insert or update a content item based on URL or content hash.

        First checks by URL (primary dedup key), then by content hash
        (catches same content at different URLs). If found, updates the
        collected_at timestamp. Otherwise, creates a new record.
        """
        # Primary: check by URL
        existing = await self.get_by_url(competitor_id, url)
        if existing:
            existing.provenance = provenance
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        # Secondary: check by content hash (same content, different URL)
        existing = await self.get_by_hash(competitor_id, content_hash)
        if existing:
            existing.provenance = provenance
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        return await self.create(
            competitor_id=competitor_id,
            content_hash=content_hash,
            title=title,
            url=url,
            author=author,
            publish_date=publish_date,
            summary=summary,
            raw_content=raw_content,
            content_type=content_type,
            provenance=provenance,
        )

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorContent).where(CompetitorContent.competitor_id == competitor_id)
        await self._session.execute(stmt)
        await self._session.flush()
