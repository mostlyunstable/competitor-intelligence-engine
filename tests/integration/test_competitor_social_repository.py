import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor, SocialPlatform
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.competitor_social_repository import CompetitorSocialRepository


@pytest.mark.integration
class TestCompetitorSocialRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Social Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://socialtest.com",
        )

    async def test_create_social(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSocialRepository(self.session)
        social = await repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/test",
            username="testcompany",
        )
        assert social.id is not None
        assert social.platform == SocialPlatform.LINKEDIN

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSocialRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/test",
        )
        await repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.FACEBOOK,
            profile_url="https://facebook.com/test",
        )
        profiles = await repo.get_by_competitor(competitor.id)
        assert len(profiles) == 2

    async def test_get_by_platform(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSocialRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/test",
        )
        found = await repo.get_by_platform(competitor.id, SocialPlatform.LINKEDIN)
        assert found is not None

    async def test_upsert_creates(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSocialRepository(self.session)
        social = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.TWITTER,
            profile_url="https://twitter.com/test",
            username="testcompany",
        )
        assert social.id is not None
        assert social.username == "testcompany"

    async def test_upsert_updates(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorSocialRepository(self.session)
        await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.YOUTUBE,
            profile_url="https://youtube.com/old",
            username="oldchannel",
        )
        updated = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.YOUTUBE,
            profile_url="https://youtube.com/new",
            username="newchannel",
        )
        assert updated.profile_url == "https://youtube.com/new"
        assert updated.username == "newchannel"

    async def test_unique_platform_constraint(self) -> None:
        from sqlalchemy.exc import IntegrityError

        competitor = await self._create_competitor()
        repo = CompetitorSocialRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.INSTAGRAM,
            profile_url="https://instagram.com/test",
        )
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=competitor.id,
                platform=SocialPlatform.INSTAGRAM,
                profile_url="https://instagram.com/test2",
            )
            await self.session.flush()

    async def test_cascade_delete(self) -> None:
        competitor = await self._create_competitor(name="Cascade Social Corp")
        repo = CompetitorSocialRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/cascade",
        )
        comp_repo = CompetitorRepository(self.session)
        await comp_repo.delete(competitor.id)
        profiles = await repo.get_by_competitor(competitor.id)
        assert len(profiles) == 0
