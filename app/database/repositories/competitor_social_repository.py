from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CompetitorSocial, SocialPlatform
from app.database.repositories.base import BaseRepository


class CompetitorSocialRepository(BaseRepository[CompetitorSocial]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CompetitorSocial)

    async def get_by_competitor(self, competitor_id: int) -> list[CompetitorSocial]:
        stmt = (
            select(CompetitorSocial)
            .where(CompetitorSocial.competitor_id == competitor_id)
            .order_by(CompetitorSocial.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_platform(
        self, competitor_id: int, platform: SocialPlatform
    ) -> CompetitorSocial | None:
        stmt = select(CompetitorSocial).where(
            CompetitorSocial.competitor_id == competitor_id,
            CompetitorSocial.platform == platform,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        platform: SocialPlatform,
        profile_url: str,
        username: str | None = None,
        content_hash: str | None = None,
    ) -> CompetitorSocial:
        existing = await self.get_by_platform(competitor_id, platform)
        if existing:
            existing.profile_url = profile_url
            existing.username = username
            existing.content_hash = content_hash
            await self._session.flush()
            return existing
        return await self.create(
            competitor_id=competitor_id,
            platform=platform,
            profile_url=profile_url,
            username=username,
            content_hash=content_hash,
        )

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorSocial).where(CompetitorSocial.competitor_id == competitor_id)
        await self._session.execute(stmt)
        await self._session.flush()
