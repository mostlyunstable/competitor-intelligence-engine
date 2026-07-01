import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.competitor_content_repository import CompetitorContentRepository
from app.database.repositories.competitor_repository import CompetitorRepository


@pytest.mark.integration
class TestCompetitorContentRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Content Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://contenttest.com",
        )

    async def test_create_content(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorContentRepository(self.session)
        content = await repo.create(
            competitor_id=competitor.id,
            title="Test Blog Post",
            author="John Doe",
            url="https://contenttest.com/blog/test",
            summary="A test blog post",
            raw_content="Full content here",
            content_type="blog",
        )
        assert content.id is not None
        assert content.title == "Test Blog Post"

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorContentRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, title="Post 1", url="https://contenttest.com/1"
        )
        await repo.create(
            competitor_id=competitor.id, title="Post 2", url="https://contenttest.com/2"
        )
        content = await repo.get_by_competitor(competitor.id)
        assert len(content) == 2

    async def test_get_by_type(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorContentRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            title="Blog",
            url="https://contenttest.com/blog",
            content_type="blog",
        )
        await repo.create(
            competitor_id=competitor.id,
            title="News",
            url="https://contenttest.com/news",
            content_type="news",
        )
        blogs = await repo.get_by_type(competitor.id, "blog")
        assert len(blogs) == 1
        assert blogs[0].title == "Blog"

    async def test_get_by_url(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorContentRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, title="Lookup", url="https://contenttest.com/lookup"
        )
        found = await repo.get_by_url(competitor.id, "https://contenttest.com/lookup")
        assert found is not None

    async def test_delete_by_competitor(self) -> None:
        competitor = await self._create_competitor(name="Delete Content Corp")
        repo = CompetitorContentRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, title="To Delete", url="https://deletecontent.com"
        )
        await repo.delete_by_competitor(competitor.id)
        content = await repo.get_by_competitor(competitor.id)
        assert len(content) == 0
