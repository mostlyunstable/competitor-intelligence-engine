from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CompetitorCertification
from app.database.repositories.base import BaseRepository


class CompetitorCertificationRepository(BaseRepository[CompetitorCertification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorCertification)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorCertification]:
        stmt = (
            select(CompetitorCertification)
            .where(CompetitorCertification.competitor_id == competitor_id)
            .order_by(CompetitorCertification.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(
        self, competitor_id: int, category: str
    ) -> list[CompetitorCertification]:
        stmt = (
            select(CompetitorCertification)
            .where(
                CompetitorCertification.competitor_id == competitor_id,
                CompetitorCertification.category == category,
            )
            .order_by(CompetitorCertification.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        competitor_id: int,
        content_hash: str,
        name: str,
        category: str = "certification",
        issuing_body: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
    ) -> CompetitorCertification:
        """Native PostgreSQL upsert: single INSERT ... ON CONFLICT DO UPDATE query."""
        now = datetime.now(UTC)
        stmt = (
            insert(CompetitorCertification)
            .values(
                competitor_id=competitor_id,
                content_hash=content_hash,
                name=name,
                category=category,
                issuing_body=issuing_body,
                description=description,
                image_url=image_url,
                collected_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_competitor_certification_hash",
                set_={"collected_at": now},
            )
            .returning(CompetitorCertification)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorCertification).where(
            CompetitorCertification.competitor_id == competitor_id
        )
        await self._session.execute(stmt)
        await self._session.flush()
