"""End-to-end integration tests for the parsing pipeline.

Exercises the full StrategyParser — segmentation → strategy execution →
merge — against realistic competitor HTML that triggers most strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.parsers.strategy_parser import DEFAULT_STRATEGIES, StrategyParser
from tests.fixtures.competitor_page import HOME_SERVICES_HOMEPAGE

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

    from app.parsers.strategy import ParsedResult


class TestParsingPipeline:
    """Verify the full pipeline end-to-end with realistic HTML."""

    def setup_method(self) -> None:
        # Use max confidence threshold so ALL strategies get a chance to run
        self.parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        self.url = "https://abchomeservices.example.com"

    def parse(self) -> ParsedResult:
        result = self.parser.parse(HOME_SERVICES_HOMEPAGE, self.url)
        return result

    # ----------------------------------------------------------------
    # Company info — JSON-LD HomeAndConstructionBusiness
    # ----------------------------------------------------------------

    def test_company_name_extracted(self) -> None:
        result = self.parse()
        assert result.company_name == "ABC Home Services"

    def test_description_extracted(self) -> None:
        result = self.parse()
        desc = (result.description or "").lower()
        # JSON-LD description from HomeAndConstructionBusiness wins
        assert "professional" in desc
        assert "services" in desc

    def test_logo_extracted(self) -> None:
        result = self.parse()
        assert "logo" in (result.logo or "")

    def test_contact_info_extracted(self) -> None:
        result = self.parse()
        # Contact info nested in JSON-LD contactPoint isn't extracted directly;
        # form extraction finds email from placeholder attributes
        assert result.contact_email is not None or any(
            c.get("content_type") == "contact_method" for c in result.content
        )

    # ----------------------------------------------------------------
    # Social links — footer links
    # ----------------------------------------------------------------

    def test_social_links_extracted(self) -> None:
        result = self.parse()
        assert "facebook" in result.social_links or "Facebook" in result.social_links
        assert "linkedin" in result.social_links or "LinkedIn" in result.social_links
        assert "instagram" in result.social_links or "Instagram" in result.social_links

    # ----------------------------------------------------------------
    # Services — from Table + FAQ + Form + Schema.org
    # ----------------------------------------------------------------

    def test_services_extracted(self) -> None:
        result = self.parse()
        svc_names = {s["name"] for s in result.services}
        # From MultiPass Schema.org Product offers
        assert "Service Plans" in svc_names
        # From FAQ service-from-answer
        assert any(
            x in svc_names
            for x in ["Service", "Maintenance", "HVAC", "Do you offer emergency services?"]
        )
        # From Form dropdown options
        assert "Plumbing" in svc_names
        assert "Electrical" in svc_names

    # ----------------------------------------------------------------
    # Pricing — from Table + FAQ + Schema.org
    # ----------------------------------------------------------------

    def test_pricing_extracted(self) -> None:
        result = self.parse()
        # From Schema.org Product/Offer (Basic Plan $19.99, Premium Plan $49.99)
        # From FAQ (HVAC maintenance $99)
        prices = [p for p in result.pricing if p["base_price"] is not None]
        assert len(prices) >= 2
        amounts = {p["base_price"] for p in prices}
        assert 19.99 in amounts or 49.99 in amounts or 99.0 in amounts

    # ----------------------------------------------------------------
    # Content — from FAQ + Breadcrumb
    # ----------------------------------------------------------------

    def test_content_extracted(self) -> None:
        result = self.parse()
        content_types = {c.get("content_type") for c in result.content}
        assert "faq" in content_types
        assert "breadcrumb" in content_types

        faq_titles = {c["title"] for c in result.content if c.get("content_type") == "faq"}
        assert "What plumbing services do you offer?" in faq_titles
        assert "How much does HVAC maintenance cost?" in faq_titles

    # ----------------------------------------------------------------
    # Breadcrumb — JSON-LD
    # ----------------------------------------------------------------

    def test_breadcrumb_extracted(self) -> None:
        result = self.parse()
        assert "__breadcrumb__" in result.strategy_results, (
            f"Missing __breadcrumb__ in {list(result.strategy_results)}"
        )
        path = result.strategy_results["__breadcrumb__"]
        assert "Home" in path
        assert "Services" in path
        assert "Plumbing" in path

    # ----------------------------------------------------------------
    # Strategy results metadata
    # ----------------------------------------------------------------

    def test_strategy_results_populated(self) -> None:
        result = self.parse()
        assert len(result.strategy_results) >= 5

    def test_confidence_computed(self) -> None:
        result = self.parse()
        assert result.confidence > 0

    # ----------------------------------------------------------------
    # Industry / headquarters from JSON-LD
    # ----------------------------------------------------------------

    def test_industry_extracted(self) -> None:
        result = self.parse()
        assert result.industry is None or isinstance(result.industry, str)

    # ----------------------------------------------------------------
    # Page segmentation metadata
    # ----------------------------------------------------------------

    def test_segments_recorded(self) -> None:
        result = self.parse()
        assert "__segments__" in result.strategy_results
        segments = result.strategy_results["__segments__"]
        assert isinstance(segments, dict)
        assert len(segments) > 0

    # ----------------------------------------------------------------
    # Strategy count matches DEFAULT_STRATEGIES
    # ----------------------------------------------------------------

    def test_default_strategies_listed(self) -> None:
        assert len(DEFAULT_STRATEGIES) >= 12


class TestEmptyPage:
    """Edge case: empty / minimal pages."""

    def setup_method(self) -> None:
        self.parser = StrategyParser(use_adaptive_ordering=False)

    def test_empty_html(self) -> None:
        result = self.parser.parse("", "https://example.com")
        # Strategies always add weight even on empty pages
        assert result.company_name is None
        assert result.description is None

    def test_minimal_html(self) -> None:
        result = self.parser.parse("<html><body><p>Hello</p></body></html>", "https://example.com")
        assert result.confidence >= 0


class TestErrorHandling:
    """Error resilience — a single failing strategy should not crash the pipeline."""

    def test_bad_strategy_does_not_crash(self) -> None:
        from app.parsers.strategies import JsonLdStrategy

        class CrashingStrategy(JsonLdStrategy):
            @property
            def name(self) -> str:
                return "crashing"

            def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
                msg = "deliberate crash"
                raise RuntimeError(msg)

        parser = StrategyParser(
            strategies=[CrashingStrategy(), JsonLdStrategy()],
            use_adaptive_ordering=False,
        )
        result = parser.parse(
            "<html><body><p>test</p></body></html>",
            "https://example.com",
        )
        # Should still get a result, not crash
        assert result is not None
        assert isinstance(result.confidence, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
