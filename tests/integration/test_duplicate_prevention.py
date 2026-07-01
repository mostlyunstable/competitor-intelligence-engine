"""Integration tests for duplicate prevention across collection runs.

Tests verify that pages, services, pricing, content, and social links
are properly deduplicated using content hashing and canonical URL normalization.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    CollectionFrequency,
    CollectionStatus,
    Competitor,
    SocialPlatform,
)
from app.database.repositories.competitor_content_repository import CompetitorContentRepository
from app.database.repositories.competitor_pricing_repository import CompetitorPricingRepository
from app.database.repositories.competitor_service_repository import CompetitorServiceRepository
from app.database.repositories.competitor_social_repository import CompetitorSocialRepository
from app.utilities.content_hasher import (
    compute_content_hash,
    compute_content_item_hash,
    compute_pricing_hash,
    compute_service_hash,
)
from app.utilities.url_normalizer import normalize_content_url, normalize_url

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_competitor(session: AsyncSession, name: str = "Test Corp") -> Competitor:
    competitor = Competitor(
        name=name,
        website_url=f"https://{name.lower().replace(' ', '')}.com",
        enabled=True,
        collection_frequency=CollectionFrequency.DAILY,
        modules=["services", "pricing", "content", "social"],
        tags=["test"],
    )
    session.add(competitor)
    await session.flush()
    return competitor


# ===========================================================================
# URL Normalization Tests
# ===========================================================================


@pytest.mark.integration
class TestURLNormalization:
    def test_trailing_slash_stripped(self) -> None:
        assert normalize_url("https://example.com/path/") == "https://example.com/path"
        assert normalize_url("https://example.com/") == "https://example.com/"

    def test_protocol_lowered(self) -> None:
        assert normalize_url("HTTP://EXAMPLE.COM") == "http://example.com"

    def test_www_stripped(self) -> None:
        assert normalize_url("https://www.example.com") == "https://example.com"

    def test_default_port_stripped(self) -> None:
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_fragment_removed(self) -> None:
        assert normalize_url("https://example.com/path#section") == "https://example.com/path"

    def test_query_params_sorted(self) -> None:
        result = normalize_url("https://example.com?z=1&a=2&m=3")
        assert result == "https://example.com?a=2&m=3&z=1"

    def test_tracking_params_stripped(self) -> None:
        url = "https://example.com/page?utm_source=google&utm_medium=cpc&id=42"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=42" in result

    def test_relative_url_resolved(self) -> None:
        result = normalize_url("/about", base_url="https://example.com")
        assert result == "https://example.com/about"

    def test_empty_url_passthrough(self) -> None:
        assert normalize_url("") == ""

    def test_content_url_normalization(self) -> None:
        assert normalize_content_url("https://example.com/blog/") == "https://example.com/blog"
        assert normalize_content_url("https://example.com/blog") == "https://example.com/blog"


# ===========================================================================
# Content Hashing Tests
# ===========================================================================


@pytest.mark.integration
class TestContentHashing:
    def test_deterministic_hash(self) -> None:
        h1 = compute_service_hash("AC Repair", "home", "Fix AC", 99.99, "USD")
        h2 = compute_service_hash("AC Repair", "home", "Fix AC", 99.99, "USD")
        assert h1 == h2

    def test_different_content_different_hash(self) -> None:
        h1 = compute_service_hash("AC Repair", "home", "Fix AC", 99.99, "USD")
        h2 = compute_service_hash("Heating Repair", "home", "Fix Heat", 149.99, "USD")
        assert h1 != h2

    def test_case_insensitive_hash(self) -> None:
        h1 = compute_service_hash("AC Repair", None, None, None, "USD")
        h2 = compute_service_hash("ac repair", None, None, None, "USD")
        assert h1 == h2

    def test_whitespace_insensitive_hash(self) -> None:
        h1 = compute_service_hash("AC Repair", None, None, None, "USD")
        h2 = compute_service_hash("  AC  Repair  ", None, None, None, "USD")
        assert h1 == h2

    def test_pricing_hash(self) -> None:
        h1 = compute_pricing_hash("Basic Plan", "monthly", 29.99, None, "USD")
        h2 = compute_pricing_hash("Basic Plan", "monthly", 29.99, None, "USD")
        assert h1 == h2

    def test_content_item_hash(self) -> None:
        h1 = compute_content_item_hash(
            "How to Fix AC", "https://example.com/blog/fix-ac", "John", "2024-01-01", "article"
        )
        h2 = compute_content_item_hash(
            "How to Fix AC", "https://example.com/blog/fix-ac", "John", "2024-01-01", "article"
        )
        assert h1 == h2

    def test_hash_is_sha256(self) -> None:
        h = compute_content_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ===========================================================================
# Page Duplicate Prevention
# ===========================================================================


@pytest.mark.integration
class TestPageDuplicatePrevention:
    async def test_same_content_not_duplicated(self, session: AsyncSession) -> None:
        """Two pages with same source_id and content_hash should not both be inserted."""
        competitor = await _create_competitor(session)
        content_hash = compute_content_hash("<html>same content</html>", "https://example.com")

        # Insert first page
        from app.database.repositories.competitor_page_repository import CompetitorPageRepository

        repo = CompetitorPageRepository(session)
        page1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            source_id=None,
            raw_html="<html>same content</html>",
            collection_status=CollectionStatus.SUCCESS,
        )
        assert page1.id is not None

        # Upsert with same hash should update, not create new
        page2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            source_id=None,
            raw_html="<html>same content</html>",
            collection_status=CollectionStatus.SUCCESS,
        )
        assert page2.id == page1.id

        # Verify only one page exists
        all_pages = await repo.get_by_competitor(competitor.id)
        assert len(all_pages) == 1

    async def test_different_content_creates_separate_pages(self, session: AsyncSession) -> None:
        """Pages with different content hashes should both be inserted."""
        competitor = await _create_competitor(session, name="MultiPage Corp")

        from app.database.repositories.competitor_page_repository import CompetitorPageRepository

        repo = CompetitorPageRepository(session)
        hash1 = compute_content_hash("<html>page one</html>", "https://example.com/page1")
        hash2 = compute_content_hash("<html>page two</html>", "https://example.com/page2")

        page1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash1,
            raw_html="<html>page one</html>",
        )
        page2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash2,
            raw_html="<html>page two</html>",
        )

        assert page1.id != page2.id
        all_pages = await repo.get_by_competitor(competitor.id)
        assert len(all_pages) == 2


# ===========================================================================
# Service Duplicate Prevention
# ===========================================================================


@pytest.mark.integration
class TestServiceDuplicatePrevention:
    async def test_same_service_not_duplicated(self, session: AsyncSession) -> None:
        """Two identical services should not both be inserted."""
        competitor = await _create_competitor(session)
        content_hash = compute_service_hash("AC Repair", "home", "Fix AC", 99.99, "USD")

        repo = CompetitorServiceRepository(session)
        svc1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            service_name="AC Repair",
            service_category="home",
            description="Fix AC",
            starting_price=99.99,
            currency="USD",
        )
        assert svc1.id is not None

        # Upsert with same hash should update timestamp, not create new
        svc2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            service_name="AC Repair",
            service_category="home",
            description="Fix AC",
            starting_price=99.99,
            currency="USD",
        )
        assert svc2.id == svc1.id

        all_services = await repo.get_by_competitor(competitor.id)
        assert len(all_services) == 1

    async def test_different_services_create_separate_records(self, session: AsyncSession) -> None:
        """Different services (different hashes) should create separate records."""
        competitor = await _create_competitor(session, name="MultiService Corp")
        repo = CompetitorServiceRepository(session)

        hash1 = compute_service_hash("AC Repair", "home", "Fix AC", 99.99, "USD")
        hash2 = compute_service_hash("Heating Repair", "home", "Fix Heat", 149.99, "USD")

        svc1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash1,
            service_name="AC Repair",
            service_category="home",
            description="Fix AC",
            starting_price=99.99,
        )
        svc2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash2,
            service_name="Heating Repair",
            service_category="home",
            description="Fix Heat",
            starting_price=149.99,
        )

        assert svc1.id != svc2.id
        all_services = await repo.get_by_competitor(competitor.id)
        assert len(all_services) == 2

    async def test_same_service_different_competitors_allowed(self, session: AsyncSession) -> None:
        """The same service can exist for different competitors."""
        comp1 = await _create_competitor(session, name="Corp A")
        comp2 = await _create_competitor(session, name="Corp B")

        content_hash = compute_service_hash("AC Repair", None, None, None, "USD")
        repo = CompetitorServiceRepository(session)

        svc1 = await repo.upsert(
            competitor_id=comp1.id,
            content_hash=content_hash,
            service_name="AC Repair",
        )
        svc2 = await repo.upsert(
            competitor_id=comp2.id,
            content_hash=content_hash,
            service_name="AC Repair",
        )

        assert svc1.id != svc2.id
        assert len(await repo.get_by_competitor(comp1.id)) == 1
        assert len(await repo.get_by_competitor(comp2.id)) == 1


# ===========================================================================
# Pricing Duplicate Prevention
# ===========================================================================


@pytest.mark.integration
class TestPricingDuplicatePrevention:
    async def test_same_pricing_not_duplicated(self, session: AsyncSession) -> None:
        """Two identical pricing entries should not both be inserted."""
        competitor = await _create_competitor(session)
        content_hash = compute_pricing_hash("Basic Plan", "monthly", 29.99, None, "USD")

        repo = CompetitorPricingRepository(session)
        price1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            service_name="Basic Plan",
            category="monthly",
            base_price=29.99,
            currency="USD",
        )
        assert price1.id is not None

        # Upsert with same hash should update, not create new
        price2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            service_name="Basic Plan",
            category="monthly",
            base_price=29.99,
            currency="USD",
        )
        assert price2.id == price1.id

        all_pricing = await repo.get_by_competitor(competitor.id)
        assert len(all_pricing) == 1

    async def test_different_pricing_create_separate_records(self, session: AsyncSession) -> None:
        """Different pricing entries (different hashes) should create separate records."""
        competitor = await _create_competitor(session, name="MultiPrice Corp")
        repo = CompetitorPricingRepository(session)

        hash1 = compute_pricing_hash("Basic Plan", "monthly", 29.99, None, "USD")
        hash2 = compute_pricing_hash("Premium Plan", "monthly", 99.99, 79.99, "USD")

        p1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash1,
            service_name="Basic Plan",
            category="monthly",
            base_price=29.99,
        )
        p2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash2,
            service_name="Premium Plan",
            category="monthly",
            base_price=99.99,
            promotional_price=79.99,
        )

        assert p1.id != p2.id
        all_pricing = await repo.get_by_competitor(competitor.id)
        assert len(all_pricing) == 2


# ===========================================================================
# Content Duplicate Prevention
# ===========================================================================


@pytest.mark.integration
class TestContentDuplicatePrevention:
    async def test_same_url_not_duplicated(self, session: AsyncSession) -> None:
        """Two content items with the same URL should not both be inserted."""
        competitor = await _create_competitor(session)
        content_url = normalize_content_url("https://example.com/blog/fix-ac")
        content_hash = compute_content_item_hash(
            "How to Fix AC", content_url, "John", content_type="article"
        )

        repo = CompetitorContentRepository(session)
        item1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            title="How to Fix AC",
            url=content_url,
            author="John",
            content_type="article",
        )
        assert item1.id is not None

        # Upsert with same URL should update, not create new
        item2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            title="How to Fix AC",
            url=content_url,
            author="John",
            content_type="article",
        )
        assert item2.id == item1.id

        all_content = await repo.get_by_competitor(competitor.id)
        assert len(all_content) == 1

    async def test_different_url_creates_separate_content(self, session: AsyncSession) -> None:
        """Different content URLs should create separate records."""
        competitor = await _create_competitor(session, name="MultiContent Corp")
        repo = CompetitorContentRepository(session)

        url1 = normalize_content_url("https://example.com/blog/fix-ac")
        url2 = normalize_content_url("https://example.com/blog/fix-heat")

        item1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=compute_content_item_hash("Fix AC", url1),
            title="Fix AC",
            url=url1,
        )
        item2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=compute_content_item_hash("Fix Heat", url2),
            title="Fix Heat",
            url=url2,
        )

        assert item1.id != item2.id
        all_content = await repo.get_by_competitor(competitor.id)
        assert len(all_content) == 2

    async def test_url_variants_deduplicated(self, session: AsyncSession) -> None:
        """URLs that normalize to the same canonical form should not be duplicated."""
        competitor = await _create_competitor(session, name="URLVariant Corp")
        repo = CompetitorContentRepository(session)

        # These normalize to the same URL
        url1 = normalize_content_url("https://example.com/blog/fix-ac")
        url2 = normalize_content_url("https://example.com/blog/fix-ac/")
        url3 = normalize_content_url("https://www.example.com/blog/fix-ac")
        assert url1 == url2 == url3, f"URL normalization failed: {url1!r} != {url2!r} != {url3!r}"

        content_hash = compute_content_item_hash("Fix AC", url1)

        item1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            title="Fix AC",
            url=url1,
        )
        # Upsert with normalized URL should find existing
        item2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=compute_content_item_hash("Fix AC", url2),
            title="Fix AC",
            url=url2,
        )

        assert item2.id == item1.id

    async def test_same_content_different_url_deduplicated_by_hash(
        self, session: AsyncSession
    ) -> None:
        """Same content at different URLs should be deduplicated by content hash."""
        competitor = await _create_competitor(session, name="HashDedup Corp")
        repo = CompetitorContentRepository(session)

        content_hash = compute_content_item_hash(
            "How to Fix AC", "https://example.com/blog/fix-ac-v1"
        )

        item1 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            title="How to Fix AC",
            url="https://example.com/blog/fix-ac-v1",
        )
        # Upsert with same hash but different URL should find existing by hash
        item2 = await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            title="How to Fix AC",
            url="https://example.com/blog/fix-ac-v2",
        )

        assert item2.id == item1.id

    async def test_unique_constraint_enforced(self, session: AsyncSession) -> None:
        """Database unique constraint on (competitor_id, url) prevents duplicates."""
        from sqlalchemy.exc import IntegrityError

        competitor = await _create_competitor(session, name="Constraint Corp")
        repo = CompetitorContentRepository(session)

        content_url = "https://example.com/blog/test"
        content_hash = compute_content_item_hash("Test", content_url)

        await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            title="Test",
            url=content_url,
        )

        # Direct create with same URL should fail at DB level
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=competitor.id,
                content_hash=content_hash,
                title="Test Duplicate",
                url=content_url,
            )
            await session.flush()


# ===========================================================================
# Social Duplicate Prevention
# ===========================================================================


@pytest.mark.integration
class TestSocialDuplicatePrevention:
    async def test_same_platform_upserts(self, session: AsyncSession) -> None:
        """Two social profiles for the same platform should upsert (not duplicate)."""
        competitor = await _create_competitor(session)
        repo = CompetitorSocialRepository(session)

        profile1 = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/test",
            username="testcompany",
        )
        assert profile1.id is not None

        # Upsert with same platform should update, not create new
        profile2 = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/test-updated",
            username="testcompanyupdated",
        )
        assert profile2.id == profile1.id
        assert profile2.profile_url == "https://linkedin.com/company/test-updated"

        all_profiles = await repo.get_by_competitor(competitor.id)
        assert len(all_profiles) == 1

    async def test_different_platforms_create_separate_profiles(
        self, session: AsyncSession
    ) -> None:
        """Different platforms should create separate social profile records."""
        competitor = await _create_competitor(session, name="MultiSocial Corp")
        repo = CompetitorSocialRepository(session)

        p1 = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.LINKEDIN,
            profile_url="https://linkedin.com/company/test",
        )
        p2 = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.TWITTER,
            profile_url="https://twitter.com/test",
        )

        assert p1.id != p2.id
        all_profiles = await repo.get_by_competitor(competitor.id)
        assert len(all_profiles) == 2

    async def test_social_url_normalized(self, session: AsyncSession) -> None:
        """Social URLs should be normalized before storage."""
        competitor = await _create_competitor(session, name="SocialNorm Corp")
        repo = CompetitorSocialRepository(session)

        profile = await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.FACEBOOK,
            profile_url="https://www.facebook.com/TestCompany/",
            username="TestCompany",
        )

        assert profile.profile_url == "https://www.facebook.com/TestCompany/"

    async def test_unique_constraint_enforced(self, session: AsyncSession) -> None:
        """Database unique constraint on (competitor_id, platform) prevents duplicates."""
        from sqlalchemy.exc import IntegrityError

        competitor = await _create_competitor(session, name="SocialConstraint Corp")
        repo = CompetitorSocialRepository(session)

        await repo.upsert(
            competitor_id=competitor.id,
            platform=SocialPlatform.YOUTUBE,
            profile_url="https://youtube.com/@test",
            username="test",
        )

        # Direct create with same platform should fail at DB level
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=competitor.id,
                platform=SocialPlatform.YOUTUBE,
                profile_url="https://youtube.com/@test2",
                username="test2",
            )
            await session.flush()


# ===========================================================================
# Cross-Run Deduplication Simulation
# ===========================================================================


@pytest.mark.integration
class TestCrossRunDeduplication:
    """Simulates multiple collection runs and verifies deduplication."""

    async def test_service_collection_run_idempotent(self, session: AsyncSession) -> None:
        """Running service collection twice with same data produces same count."""
        competitor = await _create_competitor(session, name="Idempotent Corp")
        repo = CompetitorServiceRepository(session)

        services = [
            ("AC Repair", "home", "Fix AC", 99.99),
            ("Heating Repair", "home", "Fix Heat", 149.99),
            ("Plumbing", "home", "Fix Pipes", 129.99),
        ]

        # Simulate first collection run
        for name, cat, desc, price in services:
            content_hash = compute_service_hash(name, cat, desc, price, "USD")
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name=name,
                service_category=cat,
                description=desc,
                starting_price=price,
            )

        # Simulate second collection run (same data)
        for name, cat, desc, price in services:
            content_hash = compute_service_hash(name, cat, desc, price, "USD")
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name=name,
                service_category=cat,
                description=desc,
                starting_price=price,
            )

        all_services = await repo.get_by_competitor(competitor.id)
        assert len(all_services) == 3

    async def test_pricing_collection_run_idempotent(self, session: AsyncSession) -> None:
        """Running pricing collection twice with same data produces same count."""
        competitor = await _create_competitor(session, name="PricingIdem Corp")
        repo = CompetitorPricingRepository(session)

        pricing_data = [
            ("Basic", "monthly", 29.99, None),
            ("Premium", "monthly", 99.99, 79.99),
        ]

        # First run
        for name, cat, base, promo in pricing_data:
            content_hash = compute_pricing_hash(name, cat, base, promo, "USD")
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name=name,
                category=cat,
                base_price=base,
                promotional_price=promo,
            )

        # Second run (same data)
        for name, cat, base, promo in pricing_data:
            content_hash = compute_pricing_hash(name, cat, base, promo, "USD")
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name=name,
                category=cat,
                base_price=base,
                promotional_price=promo,
            )

        all_pricing = await repo.get_by_competitor(competitor.id)
        assert len(all_pricing) == 2

    async def test_content_collection_run_idempotent(self, session: AsyncSession) -> None:
        """Running content collection twice with same data produces same count."""
        competitor = await _create_competitor(session, name="ContentIdem Corp")
        repo = CompetitorContentRepository(session)

        articles = [
            ("How to Fix AC", "https://example.com/blog/fix-ac", "John"),
            ("Heating Tips", "https://example.com/blog/heating-tips", "Jane"),
        ]

        # First run
        for title, url, author in articles:
            norm_url = normalize_content_url(url)
            content_hash = compute_content_item_hash(title, norm_url, author)
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                title=title,
                url=norm_url,
                author=author,
            )

        # Second run (same data)
        for title, url, author in articles:
            norm_url = normalize_content_url(url)
            content_hash = compute_content_item_hash(title, norm_url, author)
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                title=title,
                url=norm_url,
                author=author,
            )

        all_content = await repo.get_by_competitor(competitor.id)
        assert len(all_content) == 2

    async def test_social_collection_run_idempotent(self, session: AsyncSession) -> None:
        """Running social collection twice with same data produces same count."""
        competitor = await _create_competitor(session, name="SocialIdem Corp")
        repo = CompetitorSocialRepository(session)

        profiles = [
            (SocialPlatform.LINKEDIN, "https://linkedin.com/company/test"),
            (SocialPlatform.TWITTER, "https://twitter.com/test"),
        ]

        # First run
        for platform, url in profiles:
            await repo.upsert(
                competitor_id=competitor.id,
                platform=platform,
                profile_url=url,
            )

        # Second run (same data)
        for platform, url in profiles:
            await repo.upsert(
                competitor_id=competitor.id,
                platform=platform,
                profile_url=url,
            )

        all_profiles = await repo.get_by_competitor(competitor.id)
        assert len(all_profiles) == 2

    async def test_new_data_adds_without_removing_existing(self, session: AsyncSession) -> None:
        """New services are added while existing ones are preserved across runs."""
        competitor = await _create_competitor(session, name="Incremental Corp")
        repo = CompetitorServiceRepository(session)

        # First run: 2 services
        first_run = [("AC Repair", 99.99), ("Heating", 149.99)]
        for name, price in first_run:
            content_hash = compute_service_hash(name, None, None, price, "USD")
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name=name,
                starting_price=price,
            )

        # Second run: 1 existing + 1 new
        second_run = [("AC Repair", 99.99), ("Plumbing", 129.99)]
        for name, price in second_run:
            content_hash = compute_service_hash(name, None, None, price, "USD")
            await repo.upsert(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name=name,
                starting_price=price,
            )

        all_services = await repo.get_by_competitor(competitor.id)
        service_names = {s.service_name for s in all_services}
        assert len(all_services) == 3
        assert service_names == {"AC Repair", "Heating", "Plumbing"}

    async def test_price_change_creates_new_record(self, session: AsyncSession) -> None:
        """A changed price creates a new pricing record (different hash)."""
        competitor = await _create_competitor(session, name="PriceChange Corp")
        repo = CompetitorPricingRepository(session)

        # First run
        hash1 = compute_pricing_hash("Basic Plan", "monthly", 29.99, None, "USD")
        await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash1,
            service_name="Basic Plan",
            category="monthly",
            base_price=29.99,
        )

        # Second run: price changed
        hash2 = compute_pricing_hash("Basic Plan", "monthly", 39.99, None, "USD")
        await repo.upsert(
            competitor_id=competitor.id,
            content_hash=hash2,
            service_name="Basic Plan",
            category="monthly",
            base_price=39.99,
        )

        all_pricing = await repo.get_by_competitor(competitor.id)
        assert len(all_pricing) == 2

    async def test_service_content_hash_unique_constraint(self, session: AsyncSession) -> None:
        """Database unique constraint on (competitor_id, content_hash) prevents duplicates."""
        from sqlalchemy.exc import IntegrityError

        competitor = await _create_competitor(session, name="ServiceConstraint Corp")
        repo = CompetitorServiceRepository(session)

        content_hash = compute_service_hash("AC Repair", None, None, None, "USD")
        await repo.upsert(
            competitor_id=competitor.id,
            content_hash=content_hash,
            service_name="AC Repair",
        )

        # Direct create with same hash should fail at DB level
        with pytest.raises(IntegrityError):
            await repo.create(
                competitor_id=competitor.id,
                content_hash=content_hash,
                service_name="AC Repair Duplicate",
            )
            await session.flush()
