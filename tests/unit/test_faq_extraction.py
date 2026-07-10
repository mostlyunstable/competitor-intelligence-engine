"""Unit tests for the FaqExtractionStrategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from app.parsers.strategies.faq_extraction import FaqExtractionStrategy

if TYPE_CHECKING:
    from app.parsers.strategy import ParsedResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestFaqExtraction:
    def setup_method(self) -> None:
        self.strat = FaqExtractionStrategy()

    def _parse(self, html: str) -> ParsedResult:
        soup = _soup(html)
        return self.strat.parse(soup, "https://example.com/faq")

    # ------------------------------------------------------------------
    # <details> / <summary>
    # ------------------------------------------------------------------

    def test_details_summary(self) -> None:
        html = """
        <section>
            <h2>Frequently Asked Questions</h2>
            <details>
                <summary>How do I sign up?</summary>
                <p>Click the sign-up button on the top right corner and fill in your details.</p>
            </details>
            <details>
                <summary>What payment methods do you accept?</summary>
                <p>We accept Visa, Mastercard, and PayPal.</p>
            </details>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 2
        titles = {c["title"] for c in faqs}
        assert "How do I sign up?" in titles
        assert "What payment methods do you accept?" in titles

    def test_details_empty_summary(self) -> None:
        html = """
        <section>
            <details>
                <summary></summary>
                <p>Some answer without a question.</p>
            </details>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) == 0

    # ------------------------------------------------------------------
    # Definition list <dl> / <dt> / <dd>
    # ------------------------------------------------------------------

    def test_definition_list(self) -> None:
        html = """
        <section>
            <h2>FAQs</h2>
            <dl>
                <dt>What is your return policy?</dt>
                <dd>You can return any item within 30 days.</dd>
                <dt>How long does shipping take?</dt>
                <dd>Standard shipping takes 5-7 business days.</dd>
            </dl>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 2
        titles = {c["title"] for c in faqs}
        assert "What is your return policy?" in titles

    # ------------------------------------------------------------------
    # Accordion pattern (heading + content, repeated)
    # ------------------------------------------------------------------

    def test_accordion_pattern(self) -> None:
        html = """
        <section>
            <h2>Frequently Asked Questions</h2>
            <div>
                <h3>How do I book a service?</h3>
                <div>Visit our website and select the service you need.</div>
            </div>
            <div>
                <h3>Can I cancel my appointment?</h3>
                <div>Yes, you can cancel up to 24 hours before.</div>
            </div>
            <div>
                <h3>What areas do you cover?</h3>
                <div>We cover all major cities in California.</div>
            </div>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 2
        titles = {c["title"] for c in faqs}
        assert "How do I book a service?" in titles
        assert "Can I cancel my appointment?" in titles

    def test_non_faq_section_accordion(self) -> None:
        """Accordion without FAQ heading should still be detected if heading+content pattern."""
        html = """
        <section>
            <h2>Common Questions</h2>
            <div>
                <h3>Question one?</h3>
                <div>Answer one here.</div>
            </div>
            <div>
                <h3>Question two?</h3>
                <div>Answer two here.</div>
            </div>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 2

    # ------------------------------------------------------------------
    # FAQPage microdata
    # ------------------------------------------------------------------

    def test_microdata_faqpage(self) -> None:
        html = """
        <div itemscope itemtype="https://schema.org/FAQPage">
            <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
                <h3 itemprop="name">What is the cost?</h3>
                <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
                    <p itemprop="text">Our basic plan costs $29/month.</p>
                </div>
            </div>
            <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
                <h3 itemprop="name">Do you offer support?</h3>
                <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
                    <p itemprop="text">Yes, 24/7 support is available.</p>
                </div>
            </div>
        </div>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 2
        titles = {c["title"] for c in faqs}
        assert "What is the cost?" in titles

    # ------------------------------------------------------------------
    # Pricing extraction from FAQ answers
    # ------------------------------------------------------------------

    def test_pricing_extracted_from_answer(self) -> None:
        html = """
        <section>
            <h2>FAQ</h2>
            <details>
                <summary>How much does it cost?</summary>
                <p>Our basic plan is $29/month and the pro plan is $99/month.</p>
            </details>
        </section>
        """
        result = self._parse(html)
        assert len(result.pricing) >= 1
        prices = [p["base_price"] for p in result.pricing if p["base_price"] is not None]
        assert 29.0 in prices or 99.0 in prices

    # ------------------------------------------------------------------
    # Service description extraction from FAQ answers
    # ------------------------------------------------------------------

    def test_service_extracted_from_answer(self) -> None:
        html = """
        <section>
            <h2>FAQ</h2>
            <details>
                <summary>What cleaning services do you offer?</summary>
                <p>We offer comprehensive home cleaning services including kitchen and bathroom cleaning.</p>
            </details>
        </section>
        """
        result = self._parse(html)
        svc_names = {s["name"] for s in result.services}
        assert "What cleaning services do you offer?" in svc_names

    # ------------------------------------------------------------------
    # Coverage area extraction from FAQ answers
    # ------------------------------------------------------------------

    def test_coverage_extracted_from_answer(self) -> None:
        html = """
        <section>
            <h2>FAQ</h2>
            <details>
                <summary>What areas do you serve?</summary>
                <p>We serve New York, Los Angeles, and Chicago.</p>
            </details>
        </section>
        """
        result = self._parse(html)
        areas = {loc["name"] for loc in result.locations if loc.get("source") == "faq_coverage"}
        assert "New York" in areas
        assert "Los Angeles" in areas

    # ------------------------------------------------------------------
    # Multiple FAQ sources combined
    # ------------------------------------------------------------------

    def test_multiple_sources(self) -> None:
        html = """
        <section>
            <h2>FAQs</h2>
            <details>
                <summary>Q1?</summary>
                <p>A1.</p>
            </details>
            <dl>
                <dt>Q2?</dt>
                <dd>A2.</dd>
            </dl>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 2

    # ------------------------------------------------------------------
    # Duplicate question deduplication
    # ------------------------------------------------------------------

    def test_dedup_questions(self) -> None:
        html = """
        <section>
            <h2>FAQ</h2>
            <details>
                <summary>Same Question?</summary>
                <p>First answer.</p>
            </details>
            <details>
                <summary>Same Question?</summary>
                <p>Second answer.</p>
            </details>
        </section>
        """
        result = self._parse(html)
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) == 1

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_no_faq_content(self) -> None:
        result = self._parse("<html><body><p>Just a paragraph.</p></body></html>")
        assert len(result.content) == 0

    def test_empty_html(self) -> None:
        result = self._parse("")
        assert len(result.content) == 0

    # ------------------------------------------------------------------
    # Integration with StrategyParser
    # ------------------------------------------------------------------

    def test_strategy_parser_includes_faq_extraction(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <section>
            <h2>FAQ</h2>
            <details>
                <summary>How do I start?</summary>
                <p>Sign up online to get started.</p>
            </details>
        </section>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        assert "faq_extraction" in result.strategy_results

    def test_segment_aware_parsing(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <section>
            <h2>FAQ</h2>
            <details>
                <summary>What do you charge?</summary>
                <p>We charge $50 for a standard visit.</p>
            </details>
        </section>
        <footer><p>© 2024</p></footer>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        faqs = [c for c in result.content if c.get("content_type") == "faq"]
        assert len(faqs) >= 1
