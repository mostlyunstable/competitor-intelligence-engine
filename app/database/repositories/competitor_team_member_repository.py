from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CompetitorTeamMember
from app.database.repositories.base import BaseRepository


class CompetitorTeamMemberRepository(BaseRepository[CompetitorTeamMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorTeamMember)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorTeamMember]:
        stmt = (
            select(CompetitorTeamMember)
            .where(CompetitorTeamMember.competitor_id == competitor_id)
            .order_by(CompetitorTeamMember.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_hash(self, competitor_id: int, content_hash: str) -> CompetitorTeamMember | None:
        stmt = select(CompetitorTeamMember).where(
            CompetitorTeamMember.competitor_id == competitor_id,
            CompetitorTeamMember.content_hash == content_hash,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        content_hash: str,
        name: str,
        title: str | None = None,
        department: str | None = None,
        bio: str | None = None,
        linkedin_url: str | None = None,
        image_url: str | None = None,
    ) -> CompetitorTeamMember:
        existing = await self.get_by_hash(competitor_id, content_hash)
        if existing:
            existing.collected_at = datetime.now(UTC)
            await self._session.flush()
            return existing
        return await self.create(
            competitor_id=competitor_id,
            content_hash=content_hash,
            name=name,
            title=title,
            department=department,
            bio=bio,
            linkedin_url=linkedin_url,
            image_url=image_url,
        )

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorTeamMember).where(CompetitorTeamMember.competitor_id == competitor_id)
        await self._session.execute(stmt)
        await self._session.flush()
