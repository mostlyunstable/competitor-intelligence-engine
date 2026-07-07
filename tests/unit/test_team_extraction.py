from bs4 import BeautifulSoup

from app.parsers.strategies.team_extraction import TeamExtractionStrategy


class TestTeamExtractionStrategy:
    def setup_method(self):
        self.strategy = TeamExtractionStrategy()

    def test_name(self):
        assert self.strategy.name == "team_extraction"

    def test_weight(self):
        assert self.strategy.weight == 0.15

    def test_jsonld_person(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Person","name":"John Smith","jobTitle":"CEO","description":"20 years experience"}
        </script>
        <script type="application/ld+json">
        {"@type":"Person","name":"Jane Doe","jobTitle":"CTO"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) == 2
        names = {t["name"] for t in result.team}
        assert "John Smith" in names
        assert "Jane Doe" in names
        assert any(t["title"] == "CEO" for t in result.team)

    def test_jsonld_in_array(self):
        html = """<html><body>
        <script type="application/ld+json">
        [{"@type":"Person","name":"Alice"},{"@type":"Person","name":"Bob"}]
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) == 2

    def test_jsonld_graph(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@graph":[{"@type":"Person","name":"Graph Person","jobTitle":"VP"}]}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) == 1
        assert result.team[0]["name"] == "Graph Person"
        assert result.team[0]["title"] == "VP"

    def test_microdata_person(self):
        html = """<html><body>
        <div itemscope itemtype="https://schema.org/Person">
            <span itemprop="name">Maria Garcia</span>
            <span itemprop="jobTitle">Director</span>
            <a itemprop="url" href="https://linkedin.com/in/maria">LinkedIn</a>
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) == 1
        assert result.team[0]["name"] == "Maria Garcia"
        assert result.team[0]["title"] == "Director"

    def test_team_section_heading(self):
        html = """<html><body>
        <section>
            <h2>Our Team</h2>
            <div class="team-card">
                <h3>Tom Builder</h3>
                <p>Founder with 30 years in construction.</p>
            </div>
            <div class="team-card">
                <h3>Sarah Director</h3>
                <p>Operations Manager specializing in logistics.</p>
            </div>
        </section>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) >= 2
        names = {t["name"] for t in result.team}
        assert "Tom Builder" in names
        assert "Sarah Director" in names

    def test_leadership_heading(self):
        html = """<html><body>
        <h2>Leadership</h2>
        <article>
            <strong>Chris Manager</strong> - <em>Regional Director</em>
            <p>Oversees the Midwest region for our operations.</p>
        </article>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) >= 1
        assert any("Chris Manager" in t["name"] for t in result.team)

    def test_card_grid_team(self):
        html = """<html><body>
        <div class="team-grid">
            <div class="card">
                <h4>Alice Engineer</h4>
                <p>Lead developer with 10 years experience in software.</p>
            </div>
            <div class="card">
                <h4>Bob Designer</h4>
                <p>Creative director focused on UX design.</p>
            </div>
            <div class="card">
                <h4>Carol Analyst</h4>
                <p>Data analyst specializing in business metrics.</p>
            </div>
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.team) >= 2

    def test_name_dedup(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Person","name":"Unique Name","jobTitle":"CEO"}
        </script>
        <div itemscope itemtype="https://schema.org/Person">
            <span itemprop="name">Unique Name</span>
            <span itemprop="jobTitle">CEO</span>
        </div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        team_names = [t["name"] for t in result.team]
        assert team_names.count("Unique Name") == 1

    def test_empty_html(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.team) == 0

    def test_segments_jsonld(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Person","name":"Segment Person","jobTitle":"Director"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="about",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        assert len(result.team) == 1
        assert result.team[0]["name"] == "Segment Person"

    def test_segments_navigation_type_section_skipped(self):
        from app.parsers.page_segmenter import PageSegment

        # Section/card extraction only runs on about/hero/unknown segments.
        # JSON-LD/microdata run on all segments.
        html = """<html><body>
        <section>
            <h2>Our Team</h2>
            <div class="team-card">
                <h3>Nav Person</h3>
                <p>Only found by section extraction if segment type matches.</p>
            </div>
        </section>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="navigation",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        # Navigation segments skip section/card extraction, only JSON-LD/microdata run
        assert len(result.team) == 0

    def test_invalid_jsonld_handled(self):
        html = """<html><body>
        <script type="application/ld+json">{invalid json</script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.team) == 0

    def test_jsonld_non_person_type_ignored(self):
        html = """<html><body>
        <script type="application/ld+json">
        {"@type":"Organization","name":"Acme Corp"}
        </script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.team) == 0
