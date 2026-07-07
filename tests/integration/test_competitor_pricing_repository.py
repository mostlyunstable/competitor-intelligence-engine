import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Competitor
from app.database.repositories.competitor_pricing_repository import CompetitorPricingRepository
from app.database.repositories.competitor_repository import CompetitorRepository


@pytest.mark.integration
class TestCompetitorPricingRepository:
    @pytest.fixture(autouse=True)
    def setup(self, session: AsyncSession) -> None:
        self.session = session

    async def _create_competitor(self, name: str = "Pricing Test Corp") -> Competitor:
        repo = CompetitorRepository(self.session)
        return await repo.create(
            name=name,
            website_url="https://pricingtest.com",
        )

    async def test_create_pricing(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorPricingRepository(self.session)
        pricing = await repo.create(
            competitor_id=competitor.id,
            service_name="HVAC Repair",
            category="Heating",
            base_price=200.00,
            promotional_price=150.00,
            currency="USD",
            discount=50.00,
        )
        assert pricing.id is not None
        assert pricing.base_price is not None
        assert float(pricing.base_price) == 200.00

    async def test_get_by_competitor(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorPricingRepository(self.session)
        await repo.create(competitor_id=competitor.id, service_name="Service 1", base_price=100)
        await repo.create(competitor_id=competitor.id, service_name="Service 2", base_price=200)
        pricing = await repo.get_by_competitor(competitor.id)
        assert len(pricing) == 2

    async def test_get_by_category(self) -> None:
        competitor = await self._create_competitor()
        repo = CompetitorPricingRepository(self.session)
        await repo.create(
            competitor_id=competitor.id, service_name="HVAC", category="Heating", base_price=100
        )
        await repo.create(
            competitor_id=competitor.id, service_name="Plumbing", category="Water", base_price=200
        )
        heating = await repo.get_by_category(competitor.id, "Heating")
        assert len(heating) == 1

    async def test_delete_by_competitor(self) -> None:
        competitor = await self._create_competitor(name="Delete Pricing Corp")
        repo = CompetitorPricingRepository(self.session)
        await repo.create(competitor_id=competitor.id, service_name="To Delete", base_price=100)
        await repo.delete_by_competitor(competitor.id)
        pricing = await repo.get_by_competitor(competitor.id)
        assert len(pricing) == 0
