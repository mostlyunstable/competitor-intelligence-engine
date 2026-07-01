import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CollectionStatus, Competitor
from app.database.repositories.competitor_page_repository import CompetitorPageRepository
from app.database.repositories.competitor_repository import CompetitorRepository


@pytest.mark.integration
class TestCompetitorPageRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Page Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://pagetest.com",
        )

    async def test_create_page(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorPageRepository(self.session)
        page = await repo.create(
            competitor_id=competitor.id,
            raw_html="<html><body>Hello</body></html>",
            raw_json={"title": "Hello"},
            collection_status=CollectionStatus.SUCCESS,
        )
        assert page.id is not None
        assert page.raw_html == "<html><body>Hello</body></html>"

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorPageRepository(self.session)
        await repo.create(competitor_id=competitor.id, raw_html="<html>Page 1</html>")
        await repo.create(competitor_id=competitor.id, raw_html="<html>Page 2</html>")
        pages = await repo.get_by_competitor(competitor.id)
        assert len(pages) == 2

    async def test_get_latest(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorPageRepository(self.session)
        _first = await repo.create(competitor_id=competitor.id, raw_html="<html>First</html>")
        second = await repo.create(competitor_id=competitor.id, raw_html="<html>Latest</html>")
        latest = await repo.get_latest_by_competitor(competitor.id)
        assert latest is not None
        assert latest.id == second.id

    async def test_cascade_delete(self) -> None:
        competitor = await self._create_competitor(name="Cascade Page Corp")
        repo = CompetitorPageRepository(self.session)
        await repo.create(competitor_id=competitor.id, raw_html="<html>Page</html>")
        comp_repo = CompetitorRepository(self.session)
        await comp_repo.delete(competitor.id)
        pages = await repo.get_by_competitor(competitor.id)
        assert len(pages) == 0
