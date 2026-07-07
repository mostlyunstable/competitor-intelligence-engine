"""Unit tests for the TableExtractionStrategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from app.parsers.strategies.table_extraction import TableExtractionStrategy

if TYPE_CHECKING:
    from app.parsers.strategy import ParsedResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestTableExtraction:
    def setup_method(self) -> None:
        self.strat = TableExtractionStrategy()

    def _parse(self, html: str) -> ParsedResult:
        soup = _soup(html)
        result = self.strat.parse(soup, "https://example.com")
        return result

    # ------------------------------------------------------------------
    # Pricing tables
    # ------------------------------------------------------------------

    def test_pricing_table_basic(self) -> None:
        html = """
        <h2>Pricing Plans</h2>
        <table>
            <tr><th>Plan</th><th>Price</th><th>Features</th></tr>
            <tr><td>Basic</td><td>$9/month</td><td>5 users, email support</td></tr>
            <tr><td>Pro</td><td>$29/month</td><td>Unlimited users, priority support</td></tr>
            <tr><td>Enterprise</td><td>$99/month</td><td>All features, dedicated support</td></tr>
        </table>
        """
        result = self._parse(html)
        assert len(result.pricing) >= 1
        assert result.pricing[0]["service_name"] in ("Basic", "Pro", "Enterprise")
        prices = {p["service_name"]: p["base_price"] for p in result.pricing}
        assert prices.get("Basic") == 9.0
        assert prices.get("Pro") == 29.0
        assert prices.get("Enterprise") == 99.0

    def test_pricing_table_currency(self) -> None:
        html = """
        <h2>Subscription</h2>
        <table>
            <tr><th>Plan</th><th>Price</th></tr>
            <tr><td>Starter</td><td>€19/mo</td></tr>
            <tr><td>Business</td><td>€49/mo</td></tr>
        </table>
        """
        result = self._parse(html)
        for p in result.pricing:
            assert p["currency"] == "EUR"

    def test_pricing_table_no_currency_symbol(self) -> None:
        html = """
        <h2>Pricing</h2>
        <table>
            <tr><th>Plan</th><th>Price</th></tr>
            <tr><td>Free</td><td>$0</td></tr>
            <tr><td>Premium</td><td>$15</td></tr>
        </table>
        """
        result = self._parse(html)
        assert len(result.pricing) >= 1
        for p in result.pricing:
            assert p["currency"] == "USD"

    def test_pricing_table_with_thead_and_tbody(self) -> None:
        html = """
        <h2>Our Plans</h2>
        <table>
            <thead>
                <tr><th>Plan Name</th><th>Monthly Cost</th><th>What's Included</th></tr>
            </thead>
            <tbody>
                <tr><td>Starter</td><td>$10</td><td>Basic features</td></tr>
                <tr><td>Growth</td><td>$25</td><td>Advanced features</td></tr>
            </tbody>
        </table>
        """
        result = self._parse(html)
        assert len(result.pricing) == 2
        names = {p["service_name"] for p in result.pricing}
        assert names == {"Starter", "Growth"}

    def test_pricing_table_with_caption(self) -> None:
        html = """
        <table>
            <caption>Pricing Packages</caption>
            <tr><th>Tier</th><th>Price</th></tr>
            <tr><td>Basic</td><td>$5</td></tr>
        </table>
        """
        result = self._parse(html)
        assert len(result.pricing) >= 1

    # ------------------------------------------------------------------
    # Service tables
    # ------------------------------------------------------------------

    def test_service_table(self) -> None:
        html = """
        <h2>Our Services</h2>
        <table>
            <tr><th>Service</th><th>Description</th><th>Price</th></tr>
            <tr><td>Web Design</td><td>Custom website design</td><td>$500</td></tr>
            <tr><td>SEO</td><td>Search engine optimization</td><td>$200/mo</td></tr>
        </table>
        """
        result = self._parse(html)
        assert len(result.services) >= 1
        names = {s["name"] for s in result.services}
        assert "Web Design" in names
        assert "SEO" in names
        assert result.services[0]["starting_price"] == 500.0

    def test_service_table_heading_proximity(self) -> None:
        html = """
        <h2>What We Offer</h2>
        <table>
            <tr><th>Service</th><th>Details</th></tr>
            <tr><td>Consulting</td><td>Expert advice</td></tr>
            <tr><td>Development</td><td>Custom software</td></tr>
        </table>
        """
        result = self._parse(html)
        names = {s["name"] for s in result.services}
        assert "Consulting" in names or "Development" in names

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def test_feature_extraction_from_bullets(self) -> None:
        html = """
        <h2>Plans</h2>
        <table>
            <tr><th>Plan</th><th>Features</th><th>Price</th></tr>
            <tr><td>Basic</td><td>• 5GB storage • Email support • 1 user</td><td>$10</td></tr>
        </table>
        """
        result = self._parse(html)
        svc = result.services[0] if result.services else result.pricing[0]
        assert svc.get("features") is not None

    # ------------------------------------------------------------------
    # Duration parsing
    # ------------------------------------------------------------------

    def test_duration_monthly_detected(self) -> None:
        html = """
        <h2>Pricing</h2>
        <table>
            <tr><th>Plan</th><th>Price</th></tr>
            <tr><td>Monthly</td><td>$15/month</td></tr>
        </table>
        """
        result = self._parse(html)
        assert len(result.pricing) >= 1
        assert result.pricing[0]["base_price"] == 15.0

    # ------------------------------------------------------------------
    # Discount / promo price
    # ------------------------------------------------------------------

    def test_discount_column(self) -> None:
        html = """
        <h2>Special Offers</h2>
        <table>
            <tr><th>Plan</th><th>Price</th><th>Discount</th></tr>
            <tr><td>Annual</td><td>$100</td><td>Save 20%</td></tr>
        </table>
        """
        result = self._parse(html)
        assert len(result.pricing) >= 1

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_html(self) -> None:
        result = self._parse("<html><body></body></html>")
        assert len(result.pricing) == 0
        assert len(result.services) == 0

    def test_no_tables(self) -> None:
        result = self._parse("<h2>No tables here</h2><p>Just paragraphs.</p>")
        assert len(result.pricing) == 0
        assert len(result.services) == 0

    def test_single_row_table(self) -> None:
        result = self._parse("<table><tr><td>Only one row</td></tr></table>")
        assert len(result.pricing) == 0
        assert len(result.services) == 0

    def test_invalid_html(self) -> None:
        result = self._parse("not html at all <<< >>>")
        assert len(result.pricing) == 0
        assert len(result.services) == 0

    def test_nested_tables(self) -> None:
        html = """
        <h2>Pricing</h2>
        <table>
            <tr><th>Plan</th><th>Price</th></tr>
            <tr><td>Outer</td><td>$10</td>
                <td><table><tr><td>Inner</td><td>$5</td></tr></table></td>
            </tr>
        </table>
        """
        result = self._parse(html)
        names = {p["service_name"] for p in result.pricing}
        assert "Outer" in names

    # ------------------------------------------------------------------
    # Integration with StrategyParser
    # ------------------------------------------------------------------

    def test_strategy_parser_includes_table_extraction(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <h2>Pricing Plans</h2>
        <table>
            <tr><th>Plan</th><th>Price</th></tr>
            <tr><td>Basic</td><td>$9</td></tr>
            <tr><td>Pro</td><td>$29</td></tr>
        </table>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        assert len(result.pricing) >= 1
        assert "table_extraction" in result.strategy_results

    def test_segment_aware_parsing(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <section>
            <h2>Pricing</h2>
            <table>
                <tr><th>Plan</th><th>Price</th></tr>
                <tr><td>Basic</td><td>$9</td></tr>
            </table>
        </section>
        <footer><p>© 2024 Corp</p></footer>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        assert len(result.pricing) >= 1
