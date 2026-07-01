from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.collection_log_repository import CollectionLogRepository
from app.database.repositories.competitor_repository import CompetitorRepository


@pytest.mark.integration
class TestCollectionLogRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Log Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://logtest.com",
        )

    async def test_create_log(self) -> None:
        competitor = await self._create_competitor()
        repo = CollectionLogRepository(self.session)
        log = await repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=True,
            duration_seconds=5.5,
            records_collected=10,
            errors=[],
            retry_count=0,
        )
        assert log.id is not None
        assert log.success is True

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CollectionLogRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=True,
        )
        await repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=False,
        )
        logs = await repo.get_by_competitor(competitor.id)
        assert len(logs) == 2

    async def test_get_recent(self) -> None:
        competitor = await self._create_competitor()
        repo = CollectionLogRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=True,
        )
        recent = await repo.get_recent(limit=10)
        assert len(recent) >= 1

    async def test_count_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CollectionLogRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=True,
        )
        count = await repo.count_by_competitor(competitor.id)
        assert count >= 1

    async def test_cascade_delete(self) -> None:
        competitor = await self._create_competitor(name="Cascade Log Corp")
        repo = CollectionLogRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=True,
        )
        comp_repo = CompetitorRepository(self.session)
        await comp_repo.delete(competitor.id)
        logs = await repo.get_by_competitor(competitor.id)
        assert len(logs) == 0
