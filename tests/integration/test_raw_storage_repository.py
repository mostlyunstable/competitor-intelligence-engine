import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.raw_storage_repository import RawStorageRepository


@pytest.mark.integration
class TestRawStorageRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Raw Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://rawtest.com",
        )

    async def test_create_raw_storage(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        raw = await repo.create(
            competitor_id=competitor.id,
            source_url="https://rawtest.com/page",
            raw_html="<html><body>Raw</body></html>",
            raw_json={"status": "ok"},
            collection_status="success",
        )
        assert raw.id is not None
        assert raw.raw_html == "<html><body>Raw</body></html>"

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/1", raw_html="HTML1"
        )
        await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/2", raw_html="HTML2"
        )
        items = await repo.get_by_competitor(competitor.id)
        assert len(items) == 2

    async def test_get_by_url(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/lookup", raw_html="Lookup"
        )
        found = await repo.get_by_url(competitor.id, "https://rawtest.com/lookup")
        assert found is not None

    async def test_get_latest(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        _old = await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/old", raw_html="Old"
        )
        new = await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/new", raw_html="New"
        )
        latest = await repo.get_latest(competitor.id)
        assert latest is not None
        assert latest.id == new.id

    async def test_delete_by_competitor(self) -> None:
        competitor = await self._create_competitor(name="Delete Raw Corp")
        repo = RawStorageRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, source_url="https://deleteraw.com", raw_html="Delete"
        )
        await repo.delete_by_competitor(competitor.id)
        items = await repo.get_by_competitor(competitor.id)
        assert len(items) == 0
