"""Tests for the Entity Resolution Engine — deduplication and canonicalization."""

from __future__ import annotations

from typing import Any

from app.parsers.resolution import (
    EntityResolver,
    _first_value,
    _pick_canonical,
    levenshtein,
    name_similarity,
    normalize,
)
from app.parsers.strategy import ParsedResult

# ======================================================================
# Helpers
# ======================================================================


def _resolver() -> EntityResolver:
    return EntityResolver()


def _make_result(**overrides: Any) -> ParsedResult:
    defaults: dict[str, Any] = {
        "services": [],
        "pricing": [],
        "plans": [],
        "offers": [],
        "reviews": [],
        "features": [],
        "media": [],
        "locations": [],
        "content": [],
    }
    defaults.update(overrides)
    return ParsedResult(**defaults)


# ======================================================================
# Normalization
# ======================================================================


class TestNormalize:
    def test_lowercase(self) -> None:
        assert normalize("Kitchen Cleaning") == "kitchen cleaning"

    def test_punctuation_removed(self) -> None:
        assert normalize("Heating, Ventilation & A/C!") == "heating ventilation c"

    def test_whitespace_collapsed(self) -> None:
        assert normalize("  Kitchen   Cleaning  ") == "kitchen cleaning"

    def test_stop_words_removed(self) -> None:
        assert normalize("The Best Kitchen Cleaning") == "best kitchen cleaning"

    def test_removable_words_removed(self) -> None:
        assert normalize("Kitchen Cleaning Service") == "kitchen cleaning"
        assert normalize("Premium Plan Package") == "premium"

    def test_abbreviation_expansion_hvac(self) -> None:
        result = normalize("HVAC Repair")
        assert "heating" in result
        assert "ventilation" in result

    def test_abbreviation_expansion_seo(self) -> None:
        result = normalize("SEO Services")
        assert "search" in result
        assert "engine" in result
        assert "optimization" in result
        assert "service" not in result  # removable word removed

    def test_empty_string(self) -> None:
        assert normalize("") == ""
        assert normalize(None) == ""  # type: ignore[arg-type]

    def test_already_normalized(self) -> None:
        assert normalize("deep cleaning") == "deep cleaning"

    def test_and_to_ampersand(self) -> None:
        assert normalize("Heating & Cooling") == "heating cooling"

    def test_hvac_produces_same_as_full_form(self) -> None:
        a = normalize("HVAC Service")
        b = normalize("Heating Ventilation Air Conditioning")
        assert a == b


# ======================================================================
# Levenshtein distance
# ======================================================================


class TestLevenshtein:
    def test_identical(self) -> None:
        assert levenshtein("abc", "abc") == 0

    def test_completely_different(self) -> None:
        assert levenshtein("abc", "xyz") == 3

    def test_one_insertion(self) -> None:
        assert levenshtein("cat", "cats") == 1

    def test_one_deletion(self) -> None:
        assert levenshtein("cats", "cat") == 1

    def test_one_substitution(self) -> None:
        assert levenshtein("cat", "car") == 1

    def test_empty_strings(self) -> None:
        assert levenshtein("", "") == 0
        assert levenshtein("a", "") == 1
        assert levenshtein("", "a") == 1


# ======================================================================
# Name similarity
# ======================================================================


class TestNameSimilarity:
    def test_identical_names(self) -> None:
        assert name_similarity("Kitchen Cleaning", "Kitchen Cleaning") == 1.0

    def test_identical_after_normalization(self) -> None:
        sim = name_similarity("Kitchen Cleaning Service", "Kitchen Cleaning")
        assert sim >= 0.80

    def test_hvac_vs_full_form(self) -> None:
        sim = name_similarity("HVAC Repair", "Heating Ventilation Air Conditioning Repair")
        assert sim >= 0.50

    def test_different_entities(self) -> None:
        sim = name_similarity("Kitchen Cleaning", "Plumbing Repair")
        assert sim == 0.0

    def test_substring_variant(self) -> None:
        sim = name_similarity("Deep Cleaning", "Kitchen Deep Cleaning")
        assert sim >= 0.50

    def test_empty(self) -> None:
        assert name_similarity("", "test") == 0.0
        assert name_similarity("test", "") == 0.0
        assert name_similarity("", "") == 0.0

    def test_basic_plan_vs_basic(self) -> None:
        sim = name_similarity("Basic Plan", "Basic")
        assert sim >= 0.50

    def test_plumbing_vs_plumbing_repair(self) -> None:
        sim = name_similarity("Plumbing", "Plumbing Repair Service")
        assert sim >= 0.50

    def test_prefix_preserves(self) -> None:
        # "Kitchen Cleaning" and "Kitchen Cleaning Plus" should match well
        sim = name_similarity("Kitchen Cleaning", "Kitchen Cleaning Plus")
        assert sim >= 0.50

    def test_ac_expansion(self) -> None:
        sim = name_similarity("AC Repair", "Air Conditioning Repair")
        # After expansion: "air conditioning repair" vs "air conditioning repair" = identical
        assert sim == 1.0


# ======================================================================
# First value helper
# ======================================================================


class TestFirstValue:
    def test_first_key_found(self) -> None:
        assert _first_value({"name": "Test", "title": "Other"}, ("name", "title")) == "Test"

    def test_fallback_key(self) -> None:
        assert _first_value({"title": "Test"}, ("name", "title")) == "Test"

    def test_no_match(self) -> None:
        assert _first_value({"other": "Test"}, ("name", "title")) is None

    def test_empty_values_skipped(self) -> None:
        assert _first_value({"name": "", "title": "Test"}, ("name", "title")) == "Test"


# ======================================================================
# Pick canonical
# ======================================================================


class TestPickCanonical:
    def test_picks_most_complete(self) -> None:
        items: list[dict[str, Any]] = [
            {"name": "Basic", "price": None},  # 1 field filled
            {"name": "Basic Plan", "price": 29.0, "description": "Starter"},  # 3 fields
            {"name": "Basic Service", "price": None},  # 1 field filled
        ]
        idx, name = _pick_canonical(items, [0, 1, 2], ["Basic", "Basic Plan", "Basic Service"])
        assert idx == 1
        assert name == "Basic Plan"


# ======================================================================
# Entity resolution — service deduplication
# ======================================================================


class TestResolveServices:
    def test_exact_duplicates(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "Kitchen Cleaning"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1
        assert result.services[0]["name"] == "Kitchen Cleaning"

    def test_substring_variants(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning", "starting_price": 100.0},
                {"name": "Kitchen Deep Cleaning", "description": "Deep scrub"},
                {"name": "Kitchen Cleaning Service"},
            ],
        )
        _resolver().resolve(result)
        # Should merge into 1 entity (most descriptive)
        assert len(result.services) == 1
        merged = result.services[0]
        assert merged["name"] == "Kitchen Deep Cleaning"  # longest, most descriptive
        # Fields should be enriched from all variants
        assert merged["starting_price"] == 100.0
        assert merged["description"] == "Deep scrub"

    def test_service_plus_plan_resolution(self) -> None:
        result = _make_result(
            services=[
                {"name": "Basic Cleaning", "starting_price": 50.0},
                {"name": "Basic Cleaning"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1
        assert result.services[0]["starting_price"] == 50.0

    def test_no_false_merge(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "Plumbing Repair"},
                {"name": "Electrical"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 3

    def test_empty_list(self) -> None:
        result = _make_result(services=[])
        _resolver().resolve(result)
        assert len(result.services) == 0


# ======================================================================
# Entity resolution — plans
# ======================================================================


class TestResolvePlans:
    def test_plan_variants_merged(self) -> None:
        result = _make_result(
            plans=[
                {"plan_name": "Basic Plan", "price": 29.0},
                {"plan_name": "Basic", "description": "Starter"},
                {"plan_name": "Basic Plan Package"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.plans) == 1
        merged = result.plans[0]
        assert merged["price"] == 29.0
        assert merged["description"] == "Starter"

    def test_separate_plans_not_merged(self) -> None:
        result = _make_result(
            plans=[
                {"plan_name": "Basic Plan"},
                {"plan_name": "Premium Plan"},
                {"plan_name": "Enterprise"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.plans) == 3


# ======================================================================
# Entity resolution — features
# ======================================================================


class TestResolveFeatures:
    def test_feature_variants(self) -> None:
        result = _make_result(
            features=[
                {"name": "Email Support"},
                {"name": "Email Support Service"},
                {"name": "Email Support 24/7"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.features) >= 1  # "24/7" is enough difference
        # At least the first two should merge
        assert len(result.features) <= 2


# ======================================================================
# Entity resolution — locations
# ======================================================================


class TestResolveLocations:
    def test_city_duplicates(self) -> None:
        result = _make_result(
            locations=[
                {"name": "Chicago", "type": "city"},
                {"name": "Chicago", "type": "city"},
                {"name": "New York", "type": "city"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.locations) == 2
        city_names = {loc["name"] for loc in result.locations}
        assert city_names == {"Chicago", "New York"}


# ======================================================================
# Cross-reference updates
# ======================================================================


class TestCrossReferenceUpdates:
    def test_pricing_service_name_updated(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "Kitchen Deep Cleaning"},
            ],
            pricing=[
                {"service_name": "Kitchen Cleaning", "base_price": 100.0},
                {"service_name": "Kitchen Deep Cleaning", "base_price": 150.0},
            ],
        )
        _resolver().resolve(result)
        # Services should be merged
        assert len(result.services) == 1
        canonical = result.services[0]["name"]
        # Pricing entries should reference the canonical name
        for price in result.pricing:
            assert price["service_name"] == canonical

    def test_pricing_multiple_services(self) -> None:
        result = _make_result(
            services=[
                {"name": "Basic Cleaning"},
                {"name": "Deep Cleaning"},
            ],
            pricing=[
                {"service_name": "Basic Cleaning", "base_price": 50.0},
                {"service_name": "Deep Cleaning", "base_price": 100.0},
            ],
        )
        _resolver().resolve(result)
        # Distinct services should NOT be merged
        assert len(result.services) == 2
        assert len(result.pricing) == 2


# ======================================================================
# Full pipeline integration
# ======================================================================


class TestFullPipeline:
    def test_all_entity_types_resolved(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning", "starting_price": 100.0},
                {"name": "Kitchen Deep Cleaning", "description": "Deep scrub"},
                {"name": "Plumbing Repair", "starting_price": 150.0},
            ],
            pricing=[
                {"service_name": "Kitchen Cleaning", "base_price": 100.0},
                {"service_name": "Plumbing Repair", "base_price": 150.0},
            ],
            plans=[
                {"plan_name": "Basic Plan", "price": 29.0},
                {"plan_name": "Basic", "description": "Starter"},
            ],
            features=[
                {"name": "Email Support"},
                {"name": "Email Support 24/7"},
            ],
            locations=[
                {"name": "Chicago"},
                {"name": "Chicago"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 2  # Kitchen variants merged, Plumbing separate
        assert len(result.plans) == 1  # Basic variants merged
        assert len(result.locations) == 1  # Chicago deduplicated
        # Pricing references should be updated
        for price in result.pricing:
            assert price["service_name"] in {s["name"] for s in result.services}

    def test_no_cross_contamination(self) -> None:
        """Different entity types should never merge with each other."""
        result = _make_result(
            services=[{"name": "Plumbing"}, {"name": "Plumbing Repair"}],
            features=[{"name": "Plumbing"}, {"name": "Plumbing Upgrade"}],
        )
        _resolver().resolve(result)
        # Services and features are separate lists - resolution is per-list
        assert len(result.services) == 1
        assert len(result.features) == 1


# ======================================================================
# Edge cases
# ======================================================================


class TestEdgeCases:
    def test_single_item_no_change(self) -> None:
        result = _make_result(
            services=[{"name": "Kitchen Cleaning"}],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1

    def test_abbreviation_hvac_matches(self) -> None:
        result = _make_result(
            services=[
                {"name": "HVAC Repair", "starting_price": 200.0},
                {"name": "Heating Ventilation Air Conditioning Repair"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1
        assert result.services[0]["starting_price"] == 200.0

    def test_punctuation_variants(self) -> None:
        result = _make_result(
            services=[
                {"name": "Heating & Cooling"},
                {"name": "Heating and Cooling"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1

    def test_very_short_names_not_merged(self) -> None:
        result = _make_result(
            services=[
                {"name": "A"},
                {"name": "B"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 2

    def test_media_not_affected(self) -> None:
        """Media uses URL as dedup key, not name — should not change."""
        result = _make_result(
            media=[
                {"type": "card", "title": "Logo", "image_url": "https://example.com/logo.png"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.media) == 1

    def test_content_preserved(self) -> None:
        result = _make_result(
            content=[
                {"title": "Blog Post 1"},
                {"title": "Blog Post 2"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.content) == 2

    def test_resolve_does_not_create_duplicates(self) -> None:
        """After resolution, no two items should share a dedup key."""
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "Kitchen Cleaning Service"},
                {"name": "Kitchen Deep Cleaning"},
            ],
        )
        _resolver().resolve(result)
        names = {s["name"] for s in result.services}
        assert len(names) == len(result.services)


# ======================================================================
# Resolution via normalize only (exact normalization match)
# ======================================================================


class TestNormalizeBasedResolution:
    def test_case_difference(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "KITCHEN CLEANING"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1

    def test_whitespace_difference(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "  Kitchen   Cleaning  "},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1

    def test_removable_word_suffix(self) -> None:
        result = _make_result(
            services=[
                {"name": "Kitchen Cleaning"},
                {"name": "Kitchen Cleaning Services"},
            ],
        )
        _resolver().resolve(result)
        assert len(result.services) == 1


# ======================================================================
# Pricing deduplication
# ======================================================================


class TestPricingDedup:
    def test_pricing_dedup_by_service_name(self) -> None:
        result = _make_result(
            pricing=[
                {"service_name": "Kitchen Cleaning", "base_price": 100.0},
                {"service_name": "Kitchen Cleaning", "base_price": 100.0},
            ],
        )
        _resolver().resolve(result)
        assert len(result.pricing) == 1
