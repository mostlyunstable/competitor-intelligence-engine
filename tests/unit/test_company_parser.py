from app.parsers.company import CompanyParser


class TestCompanyParser:
    def setup_method(self) -> None:
        self.parser = CompanyParser()

    def test_parse_basic(self) -> None:
        html = """
        <html>
        <head>
            <meta property="og:site_name" content="Acme Corp" />
            <meta property="og:description" content="Leading provider of home services" />
            <meta property="og:image" content="/logo.png" />
            <meta name="description" content="Acme Corp - Home services" />
        </head>
        <body>
            <h1>Acme Corp</h1>
            <p class="company-description">We provide home services</p>
            <a href="mailto:info@acme.com">Email</a>
            <a href="tel:+1234567890">Call</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        assert result["url"] == "https://acme.com"
        assert result["name"] == "Acme Corp"
        assert result["contact_email"] == "info@acme.com"
        assert result["contact_phone"] == "+1234567890"

    def test_parse_social_links(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://linkedin.com/company/acme">LinkedIn</a>
            <a href="https://facebook.com/acme">Facebook</a>
            <a href="https://twitter.com/acme">Twitter</a>
            <a href="https://instagram.com/acme">Instagram</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        social = result["social_links"]
        assert "linkedin" in social
        assert "facebook" in social
        assert "twitter" in social
        assert "instagram" in social

    def test_parse_minimal_page(self) -> None:
        html = "<html><body></body></html>"
        result = self.parser.parse(html, "https://minimal.com")
        assert result["name"] is None
        assert result["contact_email"] is None
        assert result["contact_phone"] is None
        assert result["social_links"] == {}

    def test_parse_logo_from_meta(self) -> None:
        html = """
        <html>
        <head>
            <meta property="og:image" content="https://example.com/logo.png" />
        </head>
        <body></body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["logo"] == "https://example.com/logo.png"

    def test_parse_logo_from_img(self) -> None:
        html = """
        <html>
        <body>
            <div class="logo"><img src="/images/logo.png" /></div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["logo"] == "https://example.com/images/logo.png"

    def test_parse_description_from_meta(self) -> None:
        html = """
        <html>
        <head>
            <meta property="og:description" content="Best services ever" />
        </head>
        <body></body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["description"] == "Best services ever"

    def test_parse_x_as_twitter(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://x.com/acme">X</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        assert "twitter" in result["social_links"]
