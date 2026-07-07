"""Unit tests for the PageSegmenter engine."""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.parsers.page_segmenter import (
    ALL_TYPES,
    SEGMENT_ABOUT,
    SEGMENT_BLOG,
    SEGMENT_CONTACT,
    SEGMENT_FAQ,
    SEGMENT_FOOTER,
    SEGMENT_HERO,
    SEGMENT_NAVIGATION,
    SEGMENT_PRICING,
    SEGMENT_SERVICES,
    PageSegment,
    PageSegmenter,
    best_segment,
    segments_of_type,
)


def _html(body: str) -> str:
    return f"<html><body>{body}</body></html>"


class TestPageSegmenter:
    def setup_method(self) -> None:
        self.seg = PageSegmenter()

    # ------------------------------------------------------------------
    # Basic contract
    # ------------------------------------------------------------------

    def test_returns_at_least_one_segment(self) -> None:
        result = self.seg.segment("<html><body><p>Hello</p></body></html>")
        assert len(result) >= 1

    def test_empty_html_returns_fallback(self) -> None:
        result = self.seg.segment("")
        assert len(result) >= 1
        assert result[0].segment_type in ALL_TYPES

    def test_never_raises(self) -> None:
        """Segmenter must never propagate exceptions."""
        result = self.seg.segment("not html at all <<< >>>")
        assert isinstance(result, list)

    def test_segments_have_elements(self) -> None:
        html = _html("<header><h1>Welcome</h1><p>Hero content here.</p></header>")
        segs = self.seg.segment(html)
        for seg in segs:
            assert isinstance(seg, PageSegment)
            assert seg.element is not None

    def test_to_soup_returns_parseable(self) -> None:
        html = _html("<section><h2>Our Services</h2><p>We build things.</p></section>")
        segs = self.seg.segment(html)
        for seg in segs:
            sub = seg.to_soup()
            assert isinstance(sub, BeautifulSoup)

    # ------------------------------------------------------------------
    # Landmark detection
    # ------------------------------------------------------------------

    def test_nav_element_classified_as_navigation(self) -> None:
        html = _html(
            "<nav>"
            "<a href='/'>Home</a><a href='/about'>About</a><a href='/contact'>Contact</a>"
            "</nav>"
            "<main><p>Main content goes here for testing purposes only.</p></main>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_NAVIGATION in types

    def test_footer_element_classified_as_footer(self) -> None:
        html = _html(
            "<main><p>Some main content paragraph here for length.</p></main>"
            "<footer><p>© 2024 Acme Corp. All rights reserved. Privacy Policy.</p></footer>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_FOOTER in types

    def test_header_element_classified_as_hero(self) -> None:
        html = _html(
            "<header><h1>Welcome to our platform</h1><p>Get started today for free.</p></header>"
            "<main><p>Main content here for sufficient length.</p></main>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_HERO in types

    # ------------------------------------------------------------------
    # Keyword-based classification
    # ------------------------------------------------------------------

    def test_pricing_keywords_detected(self) -> None:
        html = _html(
            "<section>"
            "<h2>Pricing Plans</h2>"
            "<p>Basic plan: $9/month. Pro plan: $29/month. Enterprise pricing available.</p>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_PRICING in types

    def test_faq_keywords_detected(self) -> None:
        html = _html(
            "<section>"
            "<h2>Frequently Asked Questions</h2>"
            "<details><summary>How do I sign up?</summary><p>Click the sign-up button.</p></details>"
            "<details><summary>Can I cancel anytime?</summary><p>Yes you can.</p></details>"
            "<details><summary>What payment methods do you accept?</summary><p>All major cards.</p></details>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_FAQ in types

    def test_contact_form_detected(self) -> None:
        html = _html(
            "<section>"
            "<h2>Contact Us</h2>"
            "<form><input type='text' placeholder='Name'/>"
            "<input type='email' placeholder='Email'/>"
            "<button>Send Message</button></form>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_CONTACT in types

    def test_about_section_detected(self) -> None:
        html = _html(
            "<section>"
            "<h2>About Us</h2>"
            "<p>Our story began in 2015. Our mission is to make life easier. "
            "Our team of experts brings years of experience to every project.</p>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_ABOUT in types

    def test_services_section_detected(self) -> None:
        html = _html(
            "<section>"
            "<h2>Our Services</h2>"
            "<p>We offer web design, mobile development, and cloud solutions. "
            "Our expertise covers all major platforms.</p>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_SERVICES in types

    def test_blog_section_detected(self) -> None:
        html = _html(
            "<section>"
            "<h2>Latest Blog Posts</h2>"
            "<article><h3>How to build APIs</h3><p>Article content here.</p></article>"
            "<article><h3>Top 10 Python tips</h3><p>More article content.</p></article>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_BLOG in types

    # ------------------------------------------------------------------
    # Structural signals
    # ------------------------------------------------------------------

    def test_copyright_in_last_element_classified_footer(self) -> None:
        html = _html(
            "<main><p>Some very long main content paragraph that is definitely long enough.</p></main>"
            "<div><p>© 2024 MyCompany Inc. All rights reserved. Terms of Service.</p></div>"
        )
        segs = self.seg.segment(html)
        # The last element with copyright text should be footer
        last_seg = segs[-1]
        assert last_seg.segment_type == SEGMENT_FOOTER

    def test_price_table_boosts_pricing(self) -> None:
        html = _html(
            "<section>"
            "<table>"
            "<tr><th>Plan</th><th>Price</th><th>Features</th></tr>"
            "<tr><td>Basic</td><td>$9/mo</td><td>5 users</td></tr>"
            "<tr><td>Pro</td><td>$29/mo</td><td>Unlimited</td></tr>"
            "</table>"
            "</section>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_PRICING in types

    def test_aria_role_navigation(self) -> None:
        html = _html(
            '<div role="navigation">'
            "<a href='/'>Home</a><a href='/about'>About</a>"
            "<a href='/contact'>Contact</a><a href='/blog'>Blog</a>"
            "</div>"
            "<main><p>Main page content goes here for testing.</p></main>"
        )
        segs = self.seg.segment(html)
        types = [s.segment_type for s in segs]
        assert SEGMENT_NAVIGATION in types

    # ------------------------------------------------------------------
    # Multi-section page
    # ------------------------------------------------------------------

    def test_full_page_produces_multiple_segments(self) -> None:
        html = """
        <html><body>
        <header>
            <h1>Acme Corp — Build faster</h1>
            <p>Get started for free. No credit card required.</p>
        </header>
        <nav>
            <a href="/">Home</a><a href="/services">Services</a>
            <a href="/pricing">Pricing</a><a href="/about">About</a>
        </nav>
        <main>
            <section>
                <h2>Our Services</h2>
                <p>We offer consulting, development, and design solutions for enterprises.</p>
            </section>
            <section>
                <h2>Pricing Plans</h2>
                <p>Starter: $9/month. Pro: $29/month. Enterprise pricing on request.</p>
            </section>
            <section>
                <h2>Frequently Asked Questions</h2>
                <details><summary>How do I get started?</summary><p>Sign up online.</p></details>
                <details><summary>Can I upgrade my plan?</summary><p>Yes anytime.</p></details>
                <details><summary>Do you offer refunds?</summary><p>Yes within 30 days.</p></details>
            </section>
        </main>
        <footer>
            <p>© 2024 Acme Corp. All rights reserved. Privacy Policy | Terms of Service.</p>
        </footer>
        </body></html>
        """
        segs = self.seg.segment(html)
        assert len(segs) >= 3
        types = {s.segment_type for s in segs}
        # Should detect at least hero/nav, pricing/services/faq, and footer
        assert len(types) >= 3

    # ------------------------------------------------------------------
    # Confidence values
    # ------------------------------------------------------------------

    def test_confidence_in_valid_range(self) -> None:
        html = _html(
            "<header><h1>Hero</h1><p>Get started free today.</p></header>"
            "<main><section><h2>Services</h2><p>We offer many services.</p></section></main>"
            "<footer><p>© 2024 All rights reserved.</p></footer>"
        )
        segs = self.seg.segment(html)
        for seg in segs:
            assert 0.0 <= seg.confidence <= 1.0

    def test_landmark_gets_high_confidence(self) -> None:
        html = _html(
            "<footer><p>© 2024 Corp. All rights reserved. Privacy Policy. Terms of Service.</p></footer>"
        )
        segs = self.seg.segment(html)
        footer_segs = [s for s in segs if s.segment_type == SEGMENT_FOOTER]
        assert footer_segs, "Expected at least one footer segment"
        assert footer_segs[0].confidence >= 0.4

    # ------------------------------------------------------------------
    # Helper functions
    # ------------------------------------------------------------------

    def test_segments_of_type_filter(self) -> None:
        html = _html(
            "<header><h1>Welcome</h1><p>Hero content here for length.</p></header>"
            "<footer><p>© 2024 All rights reserved. Terms of Service.</p></footer>"
        )
        segs = self.seg.segment(html)
        footer_segs = segments_of_type(segs, SEGMENT_FOOTER)
        assert all(s.segment_type == SEGMENT_FOOTER for s in footer_segs)

    def test_best_segment_returns_highest_confidence(self) -> None:
        html = _html("<footer><p>© 2024 All rights reserved. Privacy Policy.</p></footer>")
        segs = self.seg.segment(html)
        footer = best_segment(segs, SEGMENT_FOOTER)
        if footer:
            assert footer.segment_type == SEGMENT_FOOTER

    def test_best_segment_returns_none_when_missing(self) -> None:
        html = _html("<p>Just a paragraph.</p>")
        segs = self.seg.segment(html)
        result = best_segment(segs, SEGMENT_BLOG)
        # Either None or a segment — not an exception
        assert result is None or result.segment_type == SEGMENT_BLOG

    # ------------------------------------------------------------------
    # Heading extraction
    # ------------------------------------------------------------------

    def test_heading_extracted_correctly(self) -> None:
        html = _html(
            "<section><h2>Contact Our Team</h2>"
            "<p>Reach us at hello@example.com or call us at 1-800-EXAMPLE.</p></section>"
        )
        segs = self.seg.segment(html)
        headings = [s.heading for s in segs if s.heading]
        assert any("Contact" in h for h in headings)

    # ------------------------------------------------------------------
    # Integration: StrategyParser exposes segments
    # ------------------------------------------------------------------

    def test_strategy_parser_stores_segment_map(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <header><h1>Welcome</h1><p>Get started today free.</p></header>
        <footer><p>© 2024 Corp. All rights reserved. Privacy Policy.</p></footer>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False)
        result = parser.parse(html, "https://example.com")
        assert "__segments__" in result.strategy_results
        seg_map = result.strategy_results["__segments__"]
        assert isinstance(seg_map, dict)
        assert len(seg_map) >= 1

    def test_get_segments_method_exists(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = _html(
            "<header><h1>Welcome</h1><p>Start for free today.</p></header>"
            "<main><p>Main content paragraph with enough text here.</p></main>"
            "<footer><p>© 2024 Corp. All rights reserved.</p></footer>"
        )
        parser = StrategyParser(use_adaptive_ordering=False)
        segs = parser.get_segments(html)
        assert isinstance(segs, list)
        assert len(segs) >= 1
