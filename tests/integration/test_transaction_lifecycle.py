import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.competitor_repository import CompetitorRepository


@pytest.mark.integration
class TestTransactionLifecycle:
    async def test_commit_on_success(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Commit Test Corp",
            website_url="https://committest.com",
        )
        await session.commit()
        assert competitor.id is not None

    async def test_flush_persists_to_db(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        await repo.create(
            name="Flush Persist Corp",
            website_url="https://flushpersist.com",
        )
        await session.flush()
        result = await session.execute(text("SELECT count(*) FROM competitors"))
        count = result.scalar_one()
        assert count >= 1

    async def test_rollback_removes_uncommitted(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        await repo.create(
            name="Rollback Uncommitted Corp",
            website_url="https://rollbackuncommitted.com",
        )
        await session.flush()
        await session.rollback()
        result = await session.execute(
            text("SELECT count(*) FROM competitors WHERE name = 'Rollback Uncommitted Corp'")
        )
        count = result.scalar_one()
        assert count == 0

    async def test_multiple_operations_same_session(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        c1 = await repo.create(name="Multi1 Corp", website_url="https://multi1.com")
        c2 = await repo.create(name="Multi2 Corp", website_url="https://multi2.com")
        assert c1.id is not None
        assert c2.id is not None
        assert c1.id != c2.id
