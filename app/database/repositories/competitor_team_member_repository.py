from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
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
        """Native PostgreSQL upsert: single INSERT ... ON CONFLICT DO UPDATE query."""
        now = datetime.now(UTC)
        stmt = (
            insert(CompetitorTeamMember)
            .values(
                competitor_id=competitor_id,
                content_hash=content_hash,
                name=name,
                title=title,
                department=department,
                bio=bio,
                linkedin_url=linkedin_url,
                image_url=image_url,
                collected_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_competitor_team_member_hash",
                set_={"collected_at": now},
            )
            .returning(CompetitorTeamMember)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(CompetitorTeamMember).where(
            CompetitorTeamMember.competitor_id == competitor_id
        )
        await self._session.execute(stmt)
        await self._session.flush()
