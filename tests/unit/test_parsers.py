from app.parsers.discovery import DiscoveryParser


class TestDiscoveryParser:
    def setup_method(self) -> None:
        self.parser = DiscoveryParser()

    def test_parse_links(self) -> None:
        html = """
        <html>
        <body>
            <a href="/about">About</a>
            <a href="/services">Services</a>
            <a href="https://example.com/pricing">Pricing</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["url"] == "https://example.com"
        assert result["link_count"] >= 3
        assert "https://example.com/about" in result["links"]
        assert "https://example.com/services" in result["links"]
        assert "https://example.com/pricing" in result["links"]

    def test_parse_sitemap(self) -> None:
        html = """
        <?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>
        """
        result = self.parser.parse(html, "https://example.com/sitemap.xml")
        assert "https://example.com/page1" in result["links"]
        assert "https://example.com/page2" in result["links"]

    def test_parse_sitemap_index(self) -> None:
        html = """
        <?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
        </sitemapindex>
        """
        result = self.parser.parse(html, "https://example.com/sitemap-index.xml")
        assert "https://example.com/sitemap1.xml" in result["links"]

    def test_parse_canonical(self) -> None:
        html = """
        <html>
        <head>
            <link rel="canonical" href="/canonical-page" />
        </head>
        <body></body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert "https://example.com/canonical-page" in result["links"]

    def test_parse_empty_html(self) -> None:
        result = self.parser.parse("", "https://example.com")
        assert result["link_count"] == 0
        assert result["links"] == []

    def test_deduplicates_links(self) -> None:
        html = """
        <html>
        <body>
            <a href="/page">Link 1</a>
            <a href="/page">Link 2</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["links"].count("https://example.com/page") == 1
