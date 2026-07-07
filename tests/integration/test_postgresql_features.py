from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.database.models import (
    CollectionLog,
    Competitor,
    CompetitorPricing,
    CompetitorService,
    RawStorage,
    SocialPlatform,
)
from app.database.repositories.collection_log_repository import CollectionLogRepository
from app.database.repositories.competitor_content_repository import CompetitorContentRepository
from app.database.repositories.competitor_page_repository import CompetitorPageRepository
from app.database.repositories.competitor_pricing_repository import CompetitorPricingRepository
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.competitor_service_repository import CompetitorServiceRepository
from app.database.repositories.competitor_social_repository import CompetitorSocialRepository
from app.database.repositories.competitor_source_repository import CompetitorSourceRepository
from app.database.repositories.raw_storage_repository import RawStorageRepository


@pytest.mark.integration
class TestTransactionLifecycle:
    async def test_commit_persists_data(self, session: AsyncSession, engine: AsyncEngine) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Commit Test Corp",
            website_url="https://committest.com",
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(Competitor, competitor.id)
            assert fetched is not None
            assert fetched.name == "Commit Test Corp"

    async def test_rollback_discards_data(self, session: AsyncSession, engine: AsyncEngine) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Rollback Test Corp",
            website_url="https://rollbacktest.com",
        )
        await session.flush()
        await session.rollback()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(Competitor, competitor.id)
            assert fetched is None

    async def test_nested_transaction_savepoint(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="Savepoint Test Corp",
            website_url="https://savepointtest.com",
        )
        await session.flush()

        async with session.begin_nested():
            inner_repo = CompetitorRepository(session)
            await inner_repo.create(
                name="Inner Corp",
                website_url="https://innertest.com",
            )

        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(Competitor, competitor.id)
            assert fetched is not None

    async def test_concurrent_writes_different_competitors(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        async with async_sessionmaker(engine)() as fresh_session:
            repo = CompetitorRepository(fresh_session)

            for i in range(10):
                await repo.create(
                    name=f"Concurrent Corp {i}",
                    website_url=f"https://concurrentcorp{i}.com",
                )

            all_competitors = await repo.get_all()
            concurrent = [c for c in all_competitors if c.name.startswith("Concurrent Corp")]
            assert len(concurrent) == 10

    async def test_concurrent_writes_same_table(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        async with async_sessionmaker(engine)() as fresh_session:
            repo = CompetitorRepository(fresh_session)
            competitor = await repo.create(
                name="Concurrent Write Corp",
                website_url="https://concurrentwrite.com",
            )

            source_repo = CompetitorSourceRepository(fresh_session)

            for i in range(20):
                await source_repo.create(
                    competitor_id=competitor.id,
                    url=f"https://concurrentwrite.com/page{i}",
                    page_type="general",
                )

            sources = await source_repo.get_by_competitor(competitor.id)
            assert len(sources) == 20


@pytest.mark.integration
class TestForeignKeyConstraints:
    async def test_source_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorSourceRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                url="https://invalid.com",
            )
            await session.flush()

    async def test_page_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorPageRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                raw_html="<html></html>",
            )
            await session.flush()

    async def test_service_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorServiceRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                service_name="Invalid Service",
            )
            await session.flush()

    async def test_pricing_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorPricingRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                service_name="Invalid Pricing",
            )
            await session.flush()

    async def test_content_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorContentRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                title="Invalid Content",
                url="https://invalid.com",
            )
            await session.flush()

    async def test_social_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CompetitorSocialRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                platform=SocialPlatform.LINKEDIN,
                profile_url="https://linkedin.com/invalid",
            )
            await session.flush()

    async def test_log_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = CollectionLogRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                start_time=datetime.now(UTC),
            )
            await session.flush()

    async def test_raw_storage_requires_valid_competitor(self, session: AsyncSession) -> None:
        repo = RawStorageRepository(session)
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=999999,
                source_url="https://invalid.com",
            )
            await session.flush()


@pytest.mark.integration
class TestUniqueConstraints:
    async def test_competitor_name_unique(self, session: AsyncSession) -> None:
        repo = CompetitorRepository(session)
        await repo.create(name="Unique Name Corp", website_url="https://unique1.com")
        with pytest.raises(IntegrityError):
            await repo.create(name="Unique Name Corp", website_url="https://unique2.com")
            await session.flush()

    async def test_source_url_per_competitor_unique(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Source Unique Corp",
            website_url="https://sourceunique.com",
        )

        source_repo = CompetitorSourceRepository(session)
        await source_repo.create(
            competitor_id=competitor.id,
            url="https://sourceunique.com/page",
        )
        with pytest.raises(IntegrityError):
            await source_repo.create(
                competitor_id=competitor.id,
                url="https://sourceunique.com/page",
            )
            await session.flush()

    async def test_social_platform_per_competitor_unique(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Social Unique Corp",
            website_url="https://socialunique.com",
        )

        social_repo = CompetitorSocialRepository(session)
        await social_repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/socialunique",
        )
        with pytest.raises(IntegrityError):
            await social_repo.create(
                competitor_id=competitor.id,
                platform=SocialPlatform.LINKEDIN,
                profile_url="https://linkedin.com/company/socialunique2",
            )
            await session.flush()

    async def test_different_competitors_same_url_allowed(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        comp1 = await comp_repo.create(
            name="URL Allowed Corp 1",
            website_url="https://urlallowed1.com",
        )
        comp2 = await comp_repo.create(
            name="URL Allowed Corp 2",
            website_url="https://urlallowed2.com",
        )

        source_repo = CompetitorSourceRepository(session)
        await source_repo.create(
            competitor_id=comp1.id,
            url="https://shared.com/page",
        )
        await source_repo.create(
            competitor_id=comp2.id,
            url="https://shared.com/page",
        )

        sources1 = await source_repo.get_by_competitor(comp1.id)
        sources2 = await source_repo.get_by_competitor(comp2.id)
        assert len(sources1) == 1
        assert len(sources2) == 1


@pytest.mark.integration
class TestCascadeDeletes:
    async def test_delete_competitor_cascades_sources(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Source Corp",
            website_url="https://cascadesource.com",
        )

        source_repo = CompetitorSourceRepository(session)
        await source_repo.create(competitor_id=competitor.id, url="https://cascadesource.com/p1")
        await source_repo.create(competitor_id=competitor.id, url="https://cascadesource.com/p2")

        await comp_repo.delete(competitor.id)
        sources = await source_repo.get_by_competitor(competitor.id)
        assert len(sources) == 0

    async def test_delete_competitor_cascades_pages(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Page Corp",
            website_url="https://cascadepage.com",
        )

        page_repo = CompetitorPageRepository(session)
        await page_repo.create(competitor_id=competitor.id, raw_html="<html>p1</html>")
        await page_repo.create(competitor_id=competitor.id, raw_html="<html>p2</html>")

        await comp_repo.delete(competitor.id)
        pages = await page_repo.get_by_competitor(competitor.id)
        assert len(pages) == 0

    async def test_delete_competitor_cascades_services(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Service Corp",
            website_url="https://cascadeservice.com",
        )

        service_repo = CompetitorServiceRepository(session)
        await service_repo.create(competitor_id=competitor.id, service_name="Service 1")
        await service_repo.create(competitor_id=competitor.id, service_name="Service 2")

        await comp_repo.delete(competitor.id)
        services = await service_repo.get_by_competitor(competitor.id)
        assert len(services) == 0

    async def test_delete_competitor_cascades_pricing(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Pricing Corp",
            website_url="https://cascadepricing.com",
        )

        pricing_repo = CompetitorPricingRepository(session)
        await pricing_repo.create(
            competitor_id=competitor.id, service_name="Pricing 1", base_price=100
        )
        await pricing_repo.create(
            competitor_id=competitor.id, service_name="Pricing 2", base_price=200
        )

        await comp_repo.delete(competitor.id)
        pricing = await pricing_repo.get_by_competitor(competitor.id)
        assert len(pricing) == 0

    async def test_delete_competitor_cascades_content(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Content Corp",
            website_url="https://cascadecontent.com",
        )

        content_repo = CompetitorContentRepository(session)
        await content_repo.create(
            competitor_id=competitor.id, title="Content 1", url="https://cascadecontent.com/1"
        )
        await content_repo.create(
            competitor_id=competitor.id, title="Content 2", url="https://cascadecontent.com/2"
        )

        await comp_repo.delete(competitor.id)
        content = await content_repo.get_by_competitor(competitor.id)
        assert len(content) == 0

    async def test_delete_competitor_cascades_social(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Social Corp",
            website_url="https://cascadesocial.com",
        )

        social_repo = CompetitorSocialRepository(session)
        await social_repo.create(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/cascadesocial",
        )

        await comp_repo.delete(competitor.id)
        socials = await social_repo.get_by_competitor(competitor.id)
        assert len(socials) == 0

    async def test_delete_competitor_cascades_logs(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Log Corp",
            website_url="https://cascadelog.com",
        )

        log_repo = CollectionLogRepository(session)
        await log_repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=True,
        )

        await comp_repo.delete(competitor.id)
        logs = await log_repo.get_by_competitor(competitor.id)
        assert len(logs) == 0

    async def test_delete_competitor_cascades_raw_storage(self, session: AsyncSession) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="Cascade Raw Corp",
            website_url="https://cascaderaw.com",
        )

        raw_repo = RawStorageRepository(session)
        await raw_repo.create(
            competitor_id=competitor.id,
            source_url="https://cascaderaw.com/page",
            raw_html="<html>raw</html>",
        )

        await comp_repo.delete(competitor.id)
        raw_items = await raw_repo.get_by_competitor(competitor.id)
        assert len(raw_items) == 0


@pytest.mark.integration
class TestJsonFields:
    async def test_competitor_modules_json(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="JSON Modules Corp",
            website_url="https://jsonmodules.com",
            modules=["discovery", "company", "services"],
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(Competitor, competitor.id)
            assert fetched is not None
            assert fetched.modules == ["discovery", "company", "services"]

    async def test_competitor_tags_json(self, session: AsyncSession, engine: AsyncEngine) -> None:
        repo = CompetitorRepository(session)
        competitor = await repo.create(
            name="JSON Tags Corp",
            website_url="https://jsontags.com",
            tags=["home-services", "warranty"],
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(Competitor, competitor.id)
            assert fetched is not None
            assert fetched.tags == ["home-services", "warranty"]

    async def test_service_add_ons_json(self, session: AsyncSession, engine: AsyncEngine) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="JSON Service Corp",
            website_url="https://jsonservice.com",
        )

        service_repo = CompetitorServiceRepository(session)
        service = await service_repo.create(
            competitor_id=competitor.id,
            service_name="HVAC Repair",
            available_add_ons=["filter_replacement", "duct_cleaning"],
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(CompetitorService, service.id)
            assert fetched is not None
            assert fetched.available_add_ons == ["filter_replacement", "duct_cleaning"]

    async def test_pricing_subscription_plans_json(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        from typing import cast
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="JSON Pricing Corp",
            website_url="https://jsonpricing.com",
        )

        pricing_repo = CompetitorPricingRepository(session)
        pricing = await pricing_repo.create(
            competitor_id=competitor.id,
            service_name="Basic Plan",
            subscription_plans={"monthly": 29.99, "annual": 299.99},
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(CompetitorPricing, pricing.id)
            assert fetched is not None
            plans = cast("dict[str, Any]", fetched.subscription_plans)
            assert plans["monthly"] == 29.99
            assert plans["annual"] == 299.99

    async def test_collection_log_errors_json(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="JSON Log Corp",
            website_url="https://jsonlog.com",
        )

        log_repo = CollectionLogRepository(session)
        log = await log_repo.create(
            competitor_id=competitor.id,
            start_time=datetime.now(UTC),
            success=False,
            errors=["Connection timeout", "HTTP 500 error"],
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(CollectionLog, log.id)
            assert fetched is not None
            assert fetched.errors == ["Connection timeout", "HTTP 500 error"]

    async def test_raw_storage_json_fields(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        comp_repo = CompetitorRepository(session)
        competitor = await comp_repo.create(
            name="JSON Raw Corp",
            website_url="https://jsonraw.com",
        )

        raw_repo = RawStorageRepository(session)
        raw = await raw_repo.create(
            competitor_id=competitor.id,
            source_url="https://jsonraw.com/page",
            raw_html="<html></html>",
            raw_json={"title": "Test", "status": "ok"},
            metadata_={"collector": "discovery", "version": "1.0"},
        )
        await session.commit()

        async with async_sessionmaker(engine)() as new_session:
            fetched = await new_session.get(RawStorage, raw.id)
            assert fetched is not None
            assert fetched.raw_json is not None
            assert fetched.raw_json["title"] == "Test"
            assert fetched.metadata_ is not None
            assert fetched.metadata_["collector"] == "discovery"


@pytest.mark.integration
class TestConcurrentWrites:
    async def test_concurrent_competitor_creation(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        async with async_sessionmaker(engine)() as fresh_session:
            repo = CompetitorRepository(fresh_session)

            for i in range(50):
                await repo.create(
                    name=f"Concurrent Corp {i}",
                    website_url=f"https://concurrent{i}.com",
                )

            all_competitors = await repo.get_all()
            concurrent = [c for c in all_competitors if c.name.startswith("Concurrent Corp")]
            assert len(concurrent) == 50

    async def test_concurrent_source_creation(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        async with async_sessionmaker(engine)() as fresh_session:
            comp_repo = CompetitorRepository(fresh_session)
            competitor = await comp_repo.create(
                name="Concurrent Source Corp",
                website_url="https://concurrentsource.com",
            )

            source_repo = CompetitorSourceRepository(fresh_session)

            for i in range(50):
                await source_repo.create(
                    competitor_id=competitor.id,
                    url=f"https://concurrentsource.com/page{i}",
                    page_type="general",
                )

            sources = await source_repo.get_by_competitor(competitor.id)
            assert len(sources) == 50

    async def test_concurrent_social_creation(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        async with async_sessionmaker(engine)() as fresh_session:
            comp_repo = CompetitorRepository(fresh_session)
            competitor = await comp_repo.create(
                name="Concurrent Social Corp",
                website_url="https://concurrentsocial.com",
            )

            social_repo = CompetitorSocialRepository(fresh_session)
            platforms = list(SocialPlatform)

            for p in platforms:
                await social_repo.create(
                    competitor_id=competitor.id,
                    platform=p,
                    profile_url=f"https://{p.value}.com/concurrentsocial",
                )

            socials = await social_repo.get_by_competitor(competitor.id)
            assert len(socials) == len(platforms)

    async def test_concurrent_different_tables(
        self, session: AsyncSession, engine: AsyncEngine
    ) -> None:
        async with async_sessionmaker(engine)() as fresh_session:
            comp_repo = CompetitorRepository(fresh_session)
            competitor = await comp_repo.create(
                name="Concurrent Multi Corp",
                website_url="https://concurrentmulti.com",
            )

            source_repo = CompetitorSourceRepository(fresh_session)
            service_repo = CompetitorServiceRepository(fresh_session)
            content_repo = CompetitorContentRepository(fresh_session)

            await source_repo.create(
                competitor_id=competitor.id,
                url="https://concurrentmulti.com/source",
            )

            await service_repo.create(
                competitor_id=competitor.id,
                service_name="Concurrent Service",
            )

            await content_repo.create(
                competitor_id=competitor.id,
                title="Concurrent Content",
                url="https://concurrentmulti.com/content",
            )

            sources = await source_repo.get_by_competitor(competitor.id)
            services = await service_repo.get_by_competitor(competitor.id)
            content = await content_repo.get_by_competitor(competitor.id)
            assert len(sources) == 1
            assert len(services) == 1
            assert len(content) == 1
