from bs4 import BeautifulSoup

from app.parsers.strategies.trust_signal_extraction import TrustSignalExtractionStrategy


class TestTrustSignalExtractionStrategy:
    def setup_method(self):
        self.strategy = TrustSignalExtractionStrategy()

    def test_name(self):
        assert self.strategy.name == "trust_signal_extraction"

    def test_weight(self):
        assert self.strategy.weight == 0.10

    def test_jsonld_award_on_organization(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","name":"Acme","award":"Best Contractor 2024"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1
        assert result.trust_signals[0]["type"] == "award"
        assert "Best Contractor 2024" in result.trust_signals[0]["name"]

    def test_jsonld_award_list(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","award":["Top Rated 2024","Best Service Award"]}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 2

    def test_jsonld_has_credential_dict(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","hasCredential":{"name":"Licensed Electrician"}}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1
        assert result.trust_signals[0]["type"] == "certification"

    def test_jsonld_has_credential_string(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","hasCredential":"ISO 9001 Certified"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1

    def test_microdata_award(self):
        html = """<html><body>
        <div itemprop="award">Top Rated Service Provider</div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1
        assert "Top Rated Service" in result.trust_signals[0]["name"]

    def test_microdata_credential(self):
        html = """<html><body>
        <div itemprop="hasCredential">ISO 9001 Certified Provider</div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1
        assert result.trust_signals[0]["type"] == "certification"

    def test_badge_image(self):
        html = """<html><body>
        <div class="trust-badges">
            <img src="badge1.png" alt="BBB A+ Rated badge">
            <img src="badge2.png" alt="EPA Certified Contractor badge">
            <img src="logo.png" alt="Company Logo">
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 2
        names = {t["name"] for t in result.trust_signals}
        assert "BBB A+ Rated badge" in names
        assert "EPA Certified Contractor badge" in names

    def test_trust_section_heading_li(self):
        html = """<html><body>
        <section>
            <h2>Awards & Certifications</h2>
            <ul>
                <li>EPA Lead-Safe Certified for residential work since 2015</li>
                <li>NARI Member Since 2010 for professional standards compliance</li>
            </ul>
        </section>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) >= 2

    def test_our_guarantee_heading(self):
        html = """<html><body>
        <h2>Our Guarantees</h2>
        <p>We provide a 100% satisfaction guarantee on all our work performed for customers.</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) >= 1
        assert any(t["type"] == "guarantee" for t in result.trust_signals)

    def test_text_pattern_licensed(self):
        html = """<html><body>
        <p>We are a fully licensed contractor serving residential customers.</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        types = {t["type"] for t in result.trust_signals}
        assert "license" in types

    def test_text_pattern_insured(self):
        html = """<html><body>
        <p>Our team is fully insured for your complete protection.</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        types = {t["type"] for t in result.trust_signals}
        assert "insurance" in types

    def test_text_pattern_bonded(self):
        html = """<html><body>
        <p>We are bonded for your complete peace of mind.</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        types = {t["type"] for t in result.trust_signals}
        assert "bonded" in types

    def test_text_pattern_guarantee(self):
        html = """<html><body>
        <p>We offer a full satisfaction guarantee on every project.</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert any(t["type"] == "guarantee" for t in result.trust_signals)

    def test_dedup(self):
        html = """<html><body>
        <div itemprop="award">Best Service Award</div>
        <script type="application/ld+json">
        {"@type":"Organization","award":"Best Service Award"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1

    def test_empty_html(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.trust_signals) == 0

    def test_invalid_jsonld_handled(self):
        html = """<html><body>
        <script type="application/ld+json">{bad json</script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.trust_signals) == 0

    def test_non_trust_jsonld_type_ignored(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Person","name":"John"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.trust_signals) == 0

    def test_segments_about_type(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <div class="trust-badges">
            <img src="epa.png" alt="EPA Certified for all work">
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="about",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        assert len(result.trust_signals) == 1

    def test_segments_hero_type(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <div class="trust-badges">
            <img src="epa.png" alt="ISO 9001 Certified provider">
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="hero",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        # Badge extraction runs on all segments
        assert len(result.trust_signals) == 1

    def test_jsonld_graph(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@graph":[{"@type":"Organization","award":"Graph Award"}]}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.trust_signals) == 1
