"""Unit tests for the BreadcrumbExtractionStrategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from app.parsers.strategies.breadcrumb_extraction import (
    BreadcrumbExtractionStrategy,
)

if TYPE_CHECKING:
    from app.parsers.strategy import ParsedResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestBreadcrumbExtraction:
    def setup_method(self) -> None:
        self.strat = BreadcrumbExtractionStrategy()

    def _parse(self, html: str) -> ParsedResult:
        soup = _soup(html)
        return self.strat.parse(soup, "https://example.com/services/cleaning")

    # ------------------------------------------------------------------
    # JSON-LD BreadcrumbList
    # ------------------------------------------------------------------

    def test_jsonld_breadcrumb(self) -> None:
        html = """
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "item": {"@id": "https://example.com", "name": "Home"}},
                {"@type": "ListItem", "position": 2, "item": {"@id": "https://example.com/services", "name": "Services"}},
                {"@type": "ListItem", "position": 3, "item": {"@id": "https://example.com/cleaning", "name": "Cleaning"}}
            ]
        }
        </script>
        """
        result = self._parse(html)
        assert "__breadcrumb__" in result.strategy_results
        assert result.strategy_results["__breadcrumb__"] == ["Home", "Services", "Cleaning"]

    def test_jsonld_breadcrumb_content_entry(self) -> None:
        html = """
        <script type="application/ld+json">
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home"},
                {"@type": "ListItem", "position": 2, "name": "Products"},
                {"@type": "ListItem", "position": 3, "name": "Widgets"}
            ]
        }
        </script>
        """
        result = self._parse(html)
        breadcrumbs = [c for c in result.content if c.get("content_type") == "breadcrumb"]
        assert len(breadcrumbs) == 1
        assert "Products" in breadcrumbs[0]["summary"]

    # ------------------------------------------------------------------
    # Microdata BreadcrumbList
    # ------------------------------------------------------------------

    def test_microdata_breadcrumb(self) -> None:
        html = """
        <ol itemscope itemtype="https://schema.org/BreadcrumbList">
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <a itemprop="item" href="/"><span itemprop="name">Home</span></a>
            </li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <a itemprop="item" href="/services"><span itemprop="name">Services</span></a>
            </li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <span itemprop="name">Deep Cleaning</span>
            </li>
        </ol>
        """
        result = self._parse(html)
        assert "__breadcrumb__" in result.strategy_results
        path = result.strategy_results["__breadcrumb__"]
        assert "Home" in path
        assert "Services" in path
        assert "Deep Cleaning" in path

    # ------------------------------------------------------------------
    # <nav aria-label="breadcrumb">
    # ------------------------------------------------------------------

    def test_nav_breadcrumb(self) -> None:
        html = """
        <nav aria-label="breadcrumb">
            <ol>
                <li><a href="/">Home</a></li>
                <li><a href="/services">Services</a></li>
                <li aria-current="page">Kitchen Cleaning</li>
            </ol>
        </nav>
        """
        result = self._parse(html)
        assert "__breadcrumb__" in result.strategy_results
        path = result.strategy_results["__breadcrumb__"]
        assert "Home" in path
        assert "Services" in path
        assert "Kitchen Cleaning" in path

    def test_nav_aria_label_breadcrumb_trail(self) -> None:
        html = """
        <nav aria-label="Breadcrumb trail">
            <ol>
                <li><a href="/">Home</a></li>
                <li><a href="/category">Category</a></li>
                <li>Sub Category</li>
            </ol>
        </nav>
        """
        result = self._parse(html)
        assert "__breadcrumb__" in result.strategy_results

    # ------------------------------------------------------------------
    # Ordered list breadcrumb
    # ------------------------------------------------------------------

    def test_ordered_list_breadcrumb(self) -> None:
        html = """
        <ol>
            <li><a href="/">Home</a></li>
            <li><a href="/products">Products</a></li>
            <li><a href="/products/gadgets">Gadgets</a></li>
            <li>Smart Widget</li>
        </ol>
        """
        result = self._parse(html)
        assert "__breadcrumb__" in result.strategy_results
        path = result.strategy_results["__breadcrumb__"]
        assert len(path) >= 3

    # ------------------------------------------------------------------
    # Separator pattern (>)
    # ------------------------------------------------------------------

    def test_separator_pattern(self) -> None:
        html = """
        <div>
            <a href="/">Home</a> &gt;
            <a href="/services">Services</a> &gt;
            <span>Cleaning</span>
        </div>
        """
        result = self._parse(html)
        assert "__breadcrumb__" in result.strategy_results

    # ------------------------------------------------------------------
    # Service categorization from breadcrumb
    # ------------------------------------------------------------------

    def test_service_categorization(self) -> None:
        html = """
        <nav aria-label="breadcrumb">
            <ol>
                <li><a href="/">Home</a></li>
                <li><a href="/services">Services</a></li>
                <li><a href="/cleaning">Cleaning</a></li>
                <li>Kitchen Deep Clean</li>
            </ol>
        </nav>
        """
        result = self._parse(html)
        services = [s for s in result.services if s.get("source") == "breadcrumb"]
        assert len(services) >= 1
        assert services[0]["name"] == "Kitchen Deep Clean"
        assert services[0]["category"] == "Cleaning"

    # ------------------------------------------------------------------
    # Skip non-breadcrumb lists
    # ------------------------------------------------------------------

    def test_non_breadcrumb_list_ignored(self) -> None:
        html = """
        <ol>
            <li>First step in tutorial</li>
            <li>Second step</li>
            <li>Third step</li>
        </ol>
        """
        result = self._parse(html)
        assert "__breadcrumb__" not in result.strategy_results

    # ------------------------------------------------------------------
    # No breadcrumb content
    # ------------------------------------------------------------------

    def test_no_breadcrumb(self) -> None:
        result = self._parse("<html><body><p>No breadcrumb here.</p></body></html>")
        assert "__breadcrumb__" not in result.strategy_results

    def test_empty_html(self) -> None:
        result = self._parse("")
        assert "__breadcrumb__" not in result.strategy_results

    # ------------------------------------------------------------------
    # Priority order: JSON-LD > microdata > nav > ol > separator
    # ------------------------------------------------------------------

    def test_jsonld_takes_priority(self) -> None:
        html = """
        <script type="application/ld+json">
        {"@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"JSON-LD Home"},
            {"@type":"ListItem","position":2,"name":"JSON-LD Page"}
        ]}
        </script>
        <nav aria-label="breadcrumb">
            <ol><li>Nav Home</li><li>Nav Page</li></ol>
        </nav>
        """
        result = self._parse(html)
        path = result.strategy_results["__breadcrumb__"]
        assert "JSON-LD Home" in path
        assert "Nav Home" not in path

    # ------------------------------------------------------------------
    # Integration with StrategyParser
    # ------------------------------------------------------------------

    def test_strategy_parser_includes_breadcrumb(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <nav aria-label="breadcrumb">
            <ol>
                <li><a href="/">Home</a></li>
                <li><a href="/services">Services</a></li>
                <li>Pricing</li>
            </ol>
        </nav>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        assert "breadcrumb_extraction" in result.strategy_results
