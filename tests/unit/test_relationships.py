"""Tests for the RelationshipEngine — entity-to-entity relationship detection."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from app.parsers.relationships import (
    ENT_FEATURE,
    ENT_OFFER,
    ENT_PLAN,
    ENT_PRICING,
    ENT_SERVICE,
    REL_HAS_FEATURE,
    REL_HAS_LOCATION,
    REL_HAS_OFFER,
    REL_HAS_PLAN,
    REL_HAS_PRICE,
    REL_HAS_REVIEW,
    REL_HAS_SERVICE,
    REL_IS_ABOUT,
    Relationship,
    RelationshipEngine,
    _best_substring_match,
    _find_container_for_text,
)
from app.parsers.strategy import ParsedResult

# ======================================================================
# Helpers
# ======================================================================


def _engine() -> RelationshipEngine:
    return RelationshipEngine()


def _make_result(**overrides: Any) -> ParsedResult:
    defaults: dict[str, Any] = {
        "services": [],
        "pricing": [],
        "plans": [],
        "offers": [],
        "reviews": [],
        "features": [],
        "locations": [],
        "content": [],
    }
    defaults.update(overrides)
    return ParsedResult(**defaults)


# ======================================================================
# Name matching: Service ↔ Pricing
# ======================================================================


class TestServicePricingMatch:
    def test_exact_name_match(self) -> None:
        result = _make_result(
            services=[{"name": "Website Design", "description": "Build a site"}],
            pricing=[{"service_name": "Website Design", "base_price": 1500.0}],
        )
        rels = _engine().run(result)
        matches = [r for r in rels if r.relation == REL_HAS_PRICE]
        assert len(matches) == 1
        m = matches[0]
        assert m.source_type == ENT_SERVICE
        assert m.source_value == "Website Design"
        assert m.target_type == ENT_PRICING
        assert m.target_value == "Website Design"
        assert m.confidence >= 0.90
        assert m.method == "name_match"

    def test_no_pricing(self) -> None:
        result = _make_result(
            services=[{"name": "Website Design"}],
            pricing=[],
        )
        rels = _engine().run(result)
        assert not any(r.relation == REL_HAS_PRICE for r in rels)

    def test_mismatched_names(self) -> None:
        result = _make_result(
            services=[{"name": "Service A"}],
            pricing=[{"service_name": "Service B", "base_price": 100.0}],
        )
        rels = _engine().run(result)
        assert not any(r.relation == REL_HAS_PRICE for r in rels)

    def test_multiple_services_and_prices(self) -> None:
        result = _make_result(
            services=[
                {"name": "Basic Plan"},
                {"name": "Premium Plan"},
                {"name": "Enterprise"},
            ],
            pricing=[
                {"service_name": "Basic Plan", "base_price": 10.0},
                {"service_name": "Premium Plan", "base_price": 25.0},
            ],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_PRICE]
        assert len(rels) == 2
        related_names = {r.source_value for r in rels}
        assert "Basic Plan" in related_names
        assert "Premium Plan" in related_names

    def test_partial_name_match(self) -> None:
        result = _make_result(
            services=[{"name": "Website Design & Development"}],
            pricing=[{"service_name": "Website Design", "base_price": 1000.0}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_PRICE]
        # Should match via substring
        assert len(rels) == 1
        assert rels[0].method == "text_overlap"

    def test_no_false_positive_short_names(self) -> None:
        """Short names like 'A' should not cause spurious matches."""
        result = _make_result(
            services=[{"name": "A"}],
            pricing=[{"service_name": "B", "base_price": 10.0}],
        )
        rels = _engine().run(result)
        assert not any(r.relation == REL_HAS_PRICE for r in rels)


# ======================================================================
# Name matching: Plan ↔ Features
# ======================================================================


class TestPlanFeaturesMatch:
    def test_exact_feature_name(self) -> None:
        result = _make_result(
            plans=[{"plan_name": "Pro", "features": ["SSL", "Backups", "Analytics"]}],
            features=[
                {"name": "SSL"},
                {"name": "Backups"},
                {"name": "Analytics"},
            ],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_FEATURE]
        assert len(rels) == 3
        for r in rels:
            assert r.source_type == ENT_PLAN
            assert r.source_value == "Pro"
            assert r.target_type == ENT_FEATURE
            assert r.confidence >= 0.90

    def test_plan_has_no_features_field(self) -> None:
        result = _make_result(
            plans=[{"plan_name": "Basic"}],
            features=[{"name": "Support"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_FEATURE]
        assert len(rels) == 0

    def test_feature_not_in_plan_list(self) -> None:
        result = _make_result(
            plans=[{"plan_name": "Pro", "features": ["SSL"]}],
            features=[{"name": "Something Else"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_FEATURE]
        assert len(rels) == 0

    def test_no_features_at_all(self) -> None:
        result = _make_result(
            plans=[{"plan_name": "Pro", "features": ["SSL"]}],
            features=[],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_FEATURE]
        assert len(rels) == 0


# ======================================================================
# Name matching: Plan ↔ Service
# ======================================================================


class TestPlanServiceMatch:
    def test_exact_plan_is_service(self) -> None:
        result = _make_result(
            plans=[{"plan_name": "Premium Plan", "price": 50.0}],
            services=[{"name": "Premium Plan"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_SERVICE]
        assert len(rels) == 1
        assert rels[0].source_value == "Premium Plan"
        assert rels[0].target_value == "Premium Plan"
        assert rels[0].confidence >= 0.85

    def test_plan_no_service_overlap(self) -> None:
        result = _make_result(
            plans=[{"plan_name": "Pro Tier"}],
            services=[{"name": "Consulting"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_SERVICE]
        assert len(rels) == 0


# ======================================================================
# Name matching: Offer ↔ Service
# ======================================================================


class TestOfferServiceMatch:
    def test_offer_mentions_service(self) -> None:
        result = _make_result(
            offers=[{"title": "Website Design — 20% Off This Month"}],
            services=[{"name": "Website Design"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_OFFER]
        assert len(rels) == 1
        assert rels[0].source_type == ENT_SERVICE
        assert rels[0].target_type == ENT_OFFER

    def test_offer_no_service_context(self) -> None:
        result = _make_result(
            offers=[{"title": "Summer Sale"}],
            services=[{"name": "Consulting"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_OFFER]
        assert len(rels) == 0

    def test_no_offers(self) -> None:
        result = _make_result(
            offers=[],
            services=[{"name": "Test"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_OFFER]
        assert len(rels) == 0


# ======================================================================
# Name matching: Review ↔ Service
# ======================================================================


class TestReviewServiceMatch:
    def test_review_mentions_service(self) -> None:
        result = _make_result(
            reviews=[{"title": "Great HVAC service!", "body": "HVAC Repair was excellent"}],
            services=[{"name": "HVAC Repair"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_REVIEW]
        assert len(rels) == 1

    def test_review_no_service_match(self) -> None:
        result = _make_result(
            reviews=[{"title": "Great experience"}],
            services=[{"name": "Consulting"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_REVIEW]
        assert len(rels) == 0


# ======================================================================
# Name matching: Location ↔ Service
# ======================================================================


class TestLocationServiceMatch:
    def test_location_in_service_name(self) -> None:
        result = _make_result(
            locations=[{"name": "Chicago", "type": "city"}],
            services=[{"name": "Chicago Plumbing Services"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_LOCATION]
        assert len(rels) == 1

    def test_location_in_service_description(self) -> None:
        result = _make_result(
            locations=[{"name": "Phoenix", "type": "city"}],
            services=[{"name": "AC Repair", "description": "Serving Phoenix area"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_LOCATION]
        assert len(rels) == 1

    def test_no_locations(self) -> None:
        result = _make_result(
            locations=[],
            services=[{"name": "Test"}],
        )
        rels = _engine().run(result)
        assert not any(r.relation == REL_HAS_LOCATION for r in rels)


# ======================================================================
# Name matching: FAQ ↔ Service
# ======================================================================


class TestFaqServiceMatch:
    def test_faq_mentions_service(self) -> None:
        result = _make_result(
            content=[
                {
                    "title": "How much does HVAC repair cost?",
                    "summary": "Our HVAC repair starts at $99",
                    "content_type": "faq",
                }
            ],
            services=[{"name": "HVAC Repair"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_IS_ABOUT]
        assert len(rels) == 1

    def test_non_faq_content_not_linked(self) -> None:
        result = _make_result(
            content=[
                {
                    "title": "How much does HVAC repair cost?",
                    "summary": "Our HVAC repair starts at $99",
                    "content_type": "article",
                }
            ],
            services=[{"name": "HVAC Repair"}],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_IS_ABOUT]
        assert len(rels) == 0


# ======================================================================
# Name matching: Pricing ↔ Plan (subscription_plans keys)
# ======================================================================


class TestPricingPlanMatch:
    def test_subscription_plan_matches(self) -> None:
        result = _make_result(
            pricing=[
                {
                    "service_name": "SaaS",
                    "subscription_plans": {"Pro": 99, "Enterprise": 499},
                }
            ],
            plans=[
                {"plan_name": "Pro"},
                {"plan_name": "Enterprise"},
            ],
        )
        rels = [r for r in _engine().run(result) if r.relation == REL_HAS_PLAN]
        assert len(rels) == 2
        plan_names = {r.target_value for r in rels}
        assert "Pro" in plan_names
        assert "Enterprise" in plan_names


# ======================================================================
# Deduplication
# ======================================================================


class TestDedup:
    def test_duplicate_relations_merged(self) -> None:
        """Same relation from name_match and dom_proximity — keep the highest."""
        result = _make_result(
            services=[{"name": "Web Design"}],
            pricing=[{"service_name": "Web Design", "base_price": 500}],
        )
        soup = BeautifulSoup(
            "<html><body><div><h1>Web Design</h1><p>$500</p></div></body></html>",
            "html.parser",
        )
        rels = _engine().run(result, soup)
        price_rels = [r for r in rels if r.relation == REL_HAS_PRICE]
        # Should be exactly 1 (deduped), with confidence 0.92 (name_match) not 0.55 (dom)
        assert len(price_rels) == 1
        assert price_rels[0].confidence == 0.92
        assert price_rels[0].method == "name_match"


# ======================================================================
# DOM proximity
# ======================================================================


class TestDomProximity:
    def test_same_container_linked(self) -> None:
        html = """
        <html><body>
            <section>
                <h2>Services</h2>
                <div class="card"><h3>Web Design</h3><p>Build sites</p><span>$500</span></div>
                <div class="card"><h3>SEO</h3><p>Optimize</p><span>$300</span></div>
            </section>
            <section>
                <h2>Reviews</h2>
                <p>Great Web Design service!</p>
            </section>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _make_result(
            services=[
                {"name": "Web Design"},
                {"name": "SEO"},
            ],
            pricing=[
                {"service_name": "Web Design", "base_price": 500.0},
                {"service_name": "SEO", "base_price": 300.0},
            ],
            reviews=[
                {"title": "Great Web Design service!"},
            ],
        )
        rels = _engine().run(result, soup)
        price_rels = [r for r in rels if r.relation == REL_HAS_PRICE]
        # Should have at least the 2 name-match relations
        assert len(price_rels) >= 2

    def test_no_soup_no_dom_relations(self) -> None:
        result = _make_result(
            services=[{"name": "A"}],
            pricing=[{"service_name": "B", "base_price": 10}],
        )
        rels = _engine().run(result)  # no soup
        dom_rels = [r for r in rels if r.method == "dom_proximity"]
        assert len(dom_rels) == 0


# ======================================================================
# Relationship.to_dict()
# ======================================================================


class TestRelationshipToDict:
    def test_basic_serialization(self) -> None:
        r = Relationship(
            source_type="service",
            source_value="Web Design",
            target_type="pricing",
            target_value="Web Design",
            relation="has_price",
            confidence=0.92,
            method="name_match",
        )
        d = r.to_dict()
        assert d["source_type"] == "service"
        assert d["source_value"] == "Web Design"
        assert d["relation"] == "has_price"
        assert d["confidence"] == 0.92
        assert "metadata" not in d

    def test_serialization_with_metadata(self) -> None:
        r = Relationship(
            source_type="service",
            source_value="A",
            target_type="pricing",
            target_value="B",
            relation="has_price",
            confidence=0.55,
            method="dom_proximity",
            metadata={"container_id": 123},
        )
        d = r.to_dict()
        assert d["metadata"] == {"container_id": 123}

    def test_confidence_rounded(self) -> None:
        r = Relationship(
            source_type="a",
            source_value="x",
            target_type="b",
            target_value="y",
            relation="r",
            confidence=0.923456,
            method="name_match",
        )
        assert r.to_dict()["confidence"] == 0.9235


# ======================================================================
# Helper: _best_substring_match
# ======================================================================


class TestBestSubstringMatch:
    def test_exact(self) -> None:
        assert _best_substring_match("Web Design", {"Web Design", "SEO"}) == "Web Design"

    def test_substring(self) -> None:
        assert (
            _best_substring_match("Web Design", {"Web Design Services", "SEO"})
            == "Web Design Services"
        )

    def test_superstring(self) -> None:
        assert _best_substring_match("Full Web Design Package", {"Web Design"}) == "Web Design"

    def test_word_overlap(self) -> None:
        result = _best_substring_match("HVAC Repair", {"HVAC Repair Service", "Plumbing"})
        assert result == "HVAC Repair Service"

    def test_no_match(self) -> None:
        assert _best_substring_match("XYZ", {"ABC", "DEF"}) is None

    def test_empty_candidates(self) -> None:
        assert _best_substring_match("Test", set()) is None


# ======================================================================
# Helper: _find_container_for_text
# ======================================================================


class TestFindContainerForText:
    def test_finds_parent_div(self) -> None:
        html = "<div><p>Web Design</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        container = _find_container_for_text(soup, "Web Design")
        assert container is not None
        assert container.name == "div"

    def test_finds_parent_section(self) -> None:
        html = "<section><h2>Services</h2><p>Web Design</p></section>"
        soup = BeautifulSoup(html, "html.parser")
        container = _find_container_for_text(soup, "Web Design")
        assert container is not None
        assert container.name == "section"

    def test_no_match_returns_none(self) -> None:
        html = "<div><p>Something</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        container = _find_container_for_text(soup, "Nonexistent")
        assert container is None

    def test_short_text_ignored(self) -> None:
        html = "<div><p>AB</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        container = _find_container_for_text(soup, "AB")
        assert container is None  # too short (< 3 chars)


# ======================================================================
# Integration-like: full ParsedResult with all entity types
# ======================================================================


class TestFullPipeline:
    def test_all_relationship_types(self) -> None:
        result = _make_result(
            services=[{"name": "HVAC Repair"}, {"name": "Plumbing"}],
            pricing=[
                {"service_name": "HVAC Repair", "base_price": 99.0},
                {"service_name": "Plumbing", "base_price": 150.0},
            ],
            plans=[
                {
                    "plan_name": "HVAC Repair",
                    "features": ["Inspection", "Filter Change"],
                }
            ],
            features=[
                {"name": "Inspection"},
                {"name": "Filter Change"},
            ],
            offers=[{"title": "HVAC Repair Discount"}],
            reviews=[
                {"title": "Great HVAC Repair service"},
            ],
            locations=[{"name": "Chicago", "type": "city"}],
        )
        # Add location context via service description
        result.services[0]["description"] = "Serving Chicago area"

        rels = _engine().run(result)
        rel_types = {r.relation for r in rels}

        assert REL_HAS_PRICE in rel_types
        assert REL_HAS_FEATURE in rel_types
        assert REL_HAS_SERVICE in rel_types
        assert REL_HAS_OFFER in rel_types
        assert REL_HAS_REVIEW in rel_types
        assert REL_HAS_LOCATION in rel_types
