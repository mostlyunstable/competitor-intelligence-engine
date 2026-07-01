import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.competitor_source_repository import CompetitorSourceRepository


@pytest.mark.integration
class TestCompetitorSourceRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Source Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://sourcetest.com",
        )

    async def test_create_source(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSourceRepository(self.session)
        source = await repo.create(
            competitor_id=competitor.id,
            url="https://sourcetest.com/about",
            page_type="about",
        )
        assert source.id is not None
        assert source.url == "https://sourcetest.com/about"

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSourceRepository(self.session)
        await repo.create(competitor_id=competitor.id, url="https://sourcetest.com/page1")
        await repo.create(competitor_id=competitor.id, url="https://sourcetest.com/page2")
        sources = await repo.get_by_competitor(competitor.id)
        assert len(sources) == 2

    async def test_get_by_url(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSourceRepository(self.session)
        await repo.create(competitor_id=competitor.id, url="https://sourcetest.com/lookup")
        found = await repo.get_by_url(competitor.id, "https://sourcetest.com/lookup")
        assert found is not None

    async def test_deactivate(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSourceRepository(self.session)
        source = await repo.create(
            competitor_id=competitor.id,
            url="https://sourcetest.com/deactivate",
        )
        deactivated = await repo.deactivate(source.id)
        assert deactivated is not None
        assert deactivated.is_active is False

    async def test_unique_url_constraint(self) -> None:
        from sqlalchemy.exc import IntegrityError

        competitor = await self._create_competitor()
        repo = CompetitorSourceRepository(self.session)
        await repo.create(competitor_id=competitor.id, url="https://sourcetest.com/unique")
        with pytest.raises(IntegrityError):
            await repo.create(competitor_id=competitor.id, url="https://sourcetest.com/unique")
            await self.session.flush()

    async def test_cascade_delete(self) -> None:
        competitor = await self._create_competitor(name="Cascade Source Corp")
        repo = CompetitorSourceRepository(self.session)
        await repo.create(competitor_id=competitor.id, url="https://cascadesource.com/page1")
        comp_repo = CompetitorRepository(self.session)
        await comp_repo.delete(competitor.id)
        sources = await repo.get_by_competitor(competitor.id)
        assert len(sources) == 0
