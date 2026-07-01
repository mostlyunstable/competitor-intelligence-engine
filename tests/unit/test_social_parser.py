from app.parsers.social import SocialParser


class TestSocialParser:
    def setup_method(self) -> None:
        self.parser = SocialParser()

    def test_parse_social_links(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://linkedin.com/company/acme-corp">LinkedIn</a>
            <a href="https://facebook.com/acme-corp">Facebook</a>
            <a href="https://twitter.com/acme-corp">Twitter</a>
            <a href="https://instagram.com/acme-corp">Instagram</a>
            <a href="https://youtube.com/channel/acme-corp">YouTube</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        profiles = result["social_profiles"]
        assert len(profiles) == 5
        platforms = {p["platform"] for p in profiles}
        assert "linkedin" in platforms
        assert "facebook" in platforms
        assert "twitter" in platforms
        assert "instagram" in platforms
        assert "youtube" in platforms

    def test_parse_x_as_twitter(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://x.com/acme">Follow us</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        assert any(p["platform"] == "twitter" for p in result["social_profiles"])

    def test_parse_threads(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://threads.net/@acme">Threads</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        assert any(p["platform"] == "threads" for p in result["social_profiles"])

    def test_extract_username_linkedin(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://www.linkedin.com/company/acme-corp">LinkedIn</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        linkedin = [p for p in result["social_profiles"] if p["platform"] == "linkedin"]
        assert len(linkedin) == 1
        assert linkedin[0]["username"] == "acme-corp"

    def test_extract_username_twitter(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://twitter.com/acme">Twitter</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        twitter = [p for p in result["social_profiles"] if p["platform"] == "twitter"]
        assert len(twitter) == 1
        assert twitter[0]["username"] == "acme"

    def test_parse_empty_page(self) -> None:
        html = "<html><body></body></html>"
        result = self.parser.parse(html, "https://acme.com")
        assert result["social_profiles"] == []

    def test_deduplicates_platforms(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://linkedin.com/company/acme">Link 1</a>
            <a href="https://linkedin.com/company/acme-page">Link 2</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        linkedin = [p for p in result["social_profiles"] if p["platform"] == "linkedin"]
        assert len(linkedin) == 1

    def test_parse_pinterest(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://pinterest.com/acme">Pinterest</a>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://acme.com")
        assert any(p["platform"] == "pinterest" for p in result["social_profiles"])
