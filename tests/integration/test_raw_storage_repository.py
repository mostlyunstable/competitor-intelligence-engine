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
            storage_uri="file:///path/to/blob.html",
            file_size_bytes=100,
            mime_type="text/html",
            collection_status="success",
        )
        assert raw.id is not None
        assert raw.storage_uri == "file:///path/to/blob.html"

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/1", storage_uri="HTML1"
        )
        await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/2", storage_uri="HTML2"
        )
        items = await repo.get_by_competitor(competitor.id)
        assert len(items) == 2

    async def test_get_by_url(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            source_url="https://rawtest.com/lookup",
            storage_uri="Lookup",
        )
        found = await repo.get_by_url(competitor.id, "https://rawtest.com/lookup")
        assert found is not None

    async def test_get_latest(self) -> None:
        competitor = await self._create_competitor()
        repo = RawStorageRepository(self.session)
        _old = await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/old", storage_uri="Old"
        )
        new = await repo.create(
            competitor_id=competitor.id, source_url="https://rawtest.com/new", storage_uri="New"
        )
        latest = await repo.get_latest(competitor.id)
        assert latest is not None
        assert latest.id == new.id

    async def test_delete_by_competitor(self) -> None:
        competitor = await self._create_competitor(name="Delete Raw Corp")
        repo = RawStorageRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, source_url="https://deleteraw.com", storage_uri="Delete"
        )
        await repo.delete_by_competitor(competitor.id)
        items = await repo.get_by_competitor(competitor.id)
        assert len(items) == 0
