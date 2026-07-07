from bs4 import BeautifulSoup

from app.parsers.strategies.location_extraction import LocationExtractionStrategy


class TestLocationExtractionStrategy:
    def setup_method(self):
        self.strategy = LocationExtractionStrategy()

    def test_name(self):
        assert self.strategy.name == "location_extraction"

    def test_weight(self):
        assert self.strategy.weight == 0.15

    def test_jsonld_local_business_address(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"LocalBusiness","name":"Acme","address":{"@type":"PostalAddress","streetAddress":"123 Main St","addressLocality":"Austin","addressRegion":"TX","postalCode":"78701","addressCountry":"US"}}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 1
        loc = result.locations[0]
        assert "Austin" in loc["name"]
        assert loc["type"] == "physical"

    def test_jsonld_service_area(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Service","serviceArea":[{"@type":"City","name":"Houston"},{"@type":"State","name":"Texas"}]}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 2

    def test_jsonld_address_string(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","address":"456 Oak Avenue, Dallas, TX 75201"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 1

    def test_microdata_postal_address(self):
        html = """<html><body>
        <div itemscope itemtype="https://schema.org/PostalAddress">
            <span itemprop="streetAddress">456 Oak Ave</span>
            <span itemprop="addressLocality">Dallas</span>
            <span itemprop="addressRegion">TX</span>
            <span itemprop="postalCode">75201</span>
            <span itemprop="addressCountry">US</span>
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 1
        loc = result.locations[0]
        assert "Dallas" in loc["name"]
        assert loc["type"] == "physical"

    def test_address_element(self):
        html = """<html><body>
        <address>789 Elm Street, San Antonio, TX 78205</address>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 1

    def test_address_element_too_short(self):
        html = """<html><body>
        <address>Short</address>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 0

    def test_location_section_heading_list(self):
        html = """<html><body>
        <section>
            <h2>Service Areas</h2>
            <ul>
                <li>Austin</li>
                <li>Round Rock</li>
                <li>Cedar Park</li>
            </ul>
        </section>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 3
        names = {loc["name"] for loc in result.locations}
        assert "Austin" in names
        assert "Round Rock" in names
        assert "Cedar Park" in names

    def test_cities_served_comma_separated(self):
        html = """<html><body>
        <h3>Cities We Serve</h3>
        <p>Phoenix, Scottsdale, Tempe, Mesa</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 4

    def test_coverage_heading(self):
        html = """<html><body>
        <div class="coverage">
            <h2>Areas Served</h2>
            <p>Miami, Fort Lauderdale, West Palm Beach</p>
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) >= 3
        names = {loc["name"] for loc in result.locations}
        assert "Miami" in names

    def test_location_dedup(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"LocalBusiness","address":{"@type":"PostalAddress","addressLocality":"Austin","addressRegion":"TX"}}
        </script>
        <div itemscope itemtype="https://schema.org/PostalAddress">
            <span itemprop="addressLocality">Austin</span>
            <span itemprop="addressRegion">TX</span>
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        # Both produce the same name "Austin, TX" so dedup keeps one
        assert len(result.locations) == 1

    def test_empty_html(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.locations) == 0

    def test_invalid_jsonld_handled(self):
        html = """<html><body>
        <script type="application/ld+json">{bad json</script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.locations) == 0

    def test_segments_about_type(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"LocalBusiness","address":{"@type":"PostalAddress","addressLocality":"Segment City","addressRegion":"TX"}}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="about",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        # JSON-LD extraction runs on all segments
        assert len(result.locations) == 1

    def test_segments_navigation_type(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"LocalBusiness","address":{"@type":"PostalAddress","addressLocality":"Nav City","addressRegion":"TX"}}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="navigation",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        # JSON-LD extraction runs on all segments
        assert len(result.locations) == 1

    def test_jsonld_radius_served(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Service","serviceArea":{"@type":"GeoCircle","description":"50 mile radius from Portland"}}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 1
        assert result.locations[0]["type"] == "radius"

    def test_jsonld_has_part(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","hasPart":[{"@type":"LocalBusiness","address":{"@type":"PostalAddress","addressLocality":"Office 1"}}]}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.locations) == 1
