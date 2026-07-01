import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CollectionFrequency
from app.database.repositories.competitor_repository import CompetitorRepository


@pytest.mark.integration
class TestCompetitorRepository:
    async def test_create_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Test Corp",
            website_url="https://test.com",
            enabled=True,
            collection_frequency=CollectionFrequency.DAILY,
            modules=["company", "services"],
            tags=["test"],
        )
        assert competitor.id is not None
        assert competitor.name == "Test Corp"
        assert competitor.website_url == "https://test.com"
        assert competitor.enabled is True

    async def test_get_by_id(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="GetById Corp",
            website_url="https://getbyid.com",
        )
        fetched = await repo.get_by_id(competitor.id)
        assert fetched is not None
        assert fetched.name == "GetById Corp"

    async def test_get_by_name(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        await repo.create(
            name="ByName Corp",
            website_url="https://byname.com",
        )
        found = await repo.get_by_name("ByName Corp")
        assert found is not None
        assert found.website_url == "https://byname.com"

    async def test_get_by_name_not_found(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        found = await repo.get_by_name("Nonexistent Corp")
        assert found is None

    async def test_get_all(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        await repo.create(name="All1 Corp", website_url="https://all1.com")
        await repo.create(name="All2 Corp", website_url="https://all2.com")
        all_competitors = await repo.get_all()
        assert len(all_competitors) >= 2

    async def test_get_enabled(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        await repo.create(name="Enabled Corp", website_url="https://enabled.com", enabled=True)
        await repo.create(name="Disabled Corp", website_url="https://disabled.com", enabled=False)
        enabled = await repo.get_enabled()
        assert any(c.name == "Enabled Corp" for c in enabled)
        assert not any(c.name == "Disabled Corp" for c in enabled)

    async def test_update_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Update Corp",
            website_url="https://update.com",
        )
        updated = await repo.update(competitor.id, name="Updated Corp")
        assert updated is not None
        assert updated.name == "Updated Corp"

    async def test_delete_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Delete Corp",
            website_url="https://delete.com",
        )
        deleted = await repo.delete(competitor.id)
        assert deleted is True
        assert await repo.get_by_id(competitor.id) is None

    async def test_delete_nonexistent(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        deleted = await repo.delete(99999)
        assert deleted is False

    async def test_exists(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Exists Corp",
            website_url="https://exists.com",
        )
        assert await repo.exists(competitor.id) is True
        assert await repo.exists(99999) is False

    async def test_count(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        initial_count = await repo.count()
        await repo.create(name="Count Corp", website_url="https://count.com")
        assert await repo.count() == initial_count + 1

    async def test_unique_name_constraint(self, session: AsyncSession) -> None:
        from sqlalchemy.exc import IntegrityError

        repo = CompetitorRepository(session)
        await repo.create(name="Unique Corp", website_url="https://unique1.com")
        with pytest.raises(IntegrityError):
            await repo.create(name="Unique Corp", website_url="https://unique2.com")
            await session.flush()
