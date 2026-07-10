import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.competitor_service_repository import CompetitorServiceRepository


@pytest.mark.integration
class TestCompetitorServiceRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Service Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://servicetest.com",
        )

    async def test_create_service(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorServiceRepository(self.session)
        service = await repo.create(
            competitor_id=competitor.id,
            service_name="HVAC Repair",
            service_category="Heating",
            description="Professional HVAC repair",
            starting_price=150.00,
            currency="USD",
        )
        assert service.id is not None
        assert service.service_name == "HVAC Repair"

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorServiceRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, service_name="Service 1", content_hash="hash1"
        )
        await repo.create(
            competitor_id=competitor.id, service_name="Service 2", content_hash="hash2"
        )
        services = await repo.get_by_competitor(competitor.id)
        assert len(services) == 2

    async def test_get_by_category(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorServiceRepository(self.session)
        await repo.create(
            competitor_id=competitor.id,
            service_name="HVAC",
            service_category="Heating",
            content_hash="hash1",
        )
        await repo.create(
            competitor_id=competitor.id,
            service_name="Plumbing",
            service_category="Water",
            content_hash="hash2",
        )
        heating = await repo.get_by_category(competitor.id, "Heating")
        assert len(heating) == 1
        assert heating[0].service_name == "HVAC"

    async def test_delete_by_competitor(self) -> None:
        competitor = await self._create_competitor(name="Delete Service Corp")
        repo = CompetitorServiceRepository(self.session)
        await repo.create(competitor_id=competitor.id, service_name="To Delete")
        await repo.delete_by_competitor(competitor.id)
        services = await repo.get_by_competitor(competitor.id)
        assert len(services) == 0
