from bs4 import BeautifulSoup

from app.parsers.strategies.asset_extraction import AssetExtractionStrategy


class TestAssetExtractionStrategy:
    def setup_method(self):
        self.strategy = AssetExtractionStrategy()

    def test_name(self):
        assert self.strategy.name == "asset_extraction"

    def test_weight(self):
        assert self.strategy.weight == 0.15

    def test_pdf_download(self):
        html = """<html><body>
        <a href="/files/brochure.pdf">Download Brochure</a>
        <a href="/docs/pricing-guide.pdf">Pricing Guide (PDF)</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 2
        assert all(a["category"] == "document" for a in result.assets)

    def test_docx_download(self):
        html = """<html><body>
        <a href="/files/contract.docx">Contract Template</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1

    def test_xlsx_download(self):
        html = """<html><body>
        <a href="/files/pricing.xlsx">Pricing Spreadsheet</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1

    def test_google_analytics(self):
        html = """<html><body>
        <script src="https://www.googletagmanager.com/gtag/js?id=GA-123"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "analytics"
        assert result.assets[0]["type"] == "technology"

    def test_hubspot(self):
        html = """<html><body>
        <script src="https://track.hubspot.com/hubspot.js"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "crm"

    def test_stripe(self):
        html = """<html><body>
        <script src="https://js.stripe.com/v3/"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "payment"

    def test_intercom(self):
        html = """<html><body>
        <script src="https://widget.intercom.io/widget/abc123"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "chat"

    def test_facebook_pixel(self):
        html = """<html><body>
        <script src="https://connect.facebook.net/en_US/fbevents.js"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "analytics"

    def test_meta_generator_wordpress(self):
        html = """<html><head>
        <meta name="generator" content="WordPress 6.4">
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "cms"

    def test_meta_generator_shopify(self):
        html = """<html><head>
        <meta name="generator" content="Shopify">
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "cms"

    def test_powered_by_badge(self):
        html = """<html><body>
        <img src="powered-by-shopify.png" alt="Powered by Shopify">
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "cms"

    def test_unknown_script_ignored(self):
        html = """<html><body>
        <script src="https://cdn.example.com/custom.js"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 0

    def test_name_dedup(self):
        html = """<html><body>
        <script src="https://www.googletagmanager.com/gtag/js?id=GA-1"></script>
        <script src="https://www.googletagmanager.com/gtag/js?id=GA-2"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1

    def test_empty_html(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        result = self.strategy.parse(soup, "https://example.com")
        assert len(result.assets) == 0

    def test_segments_about_type(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <a href="/files/report.pdf">Annual Report</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="about",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        assert len(result.assets) == 1

    def test_segments_navigation_type_document(self):
        from app.parsers.page_segmenter import PageSegment

        html = """<html><body>
        <a href="/files/report.pdf">Annual Report</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        seg = PageSegment(
            segment_type="navigation",
            confidence=0.8,
            element=soup.body,  # type: ignore[arg-type]
        )
        result = self.strategy.parse_segments([seg], "https://example.com")
        # Document extraction runs on all segments
        assert len(result.assets) == 1

    def test_download_attribute(self):
        html = """<html><body>
        <a href="/files/data.csv" download>Download Data</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1

    def test_keyword_in_text(self):
        html = """<html><body>
        <a href="/files/spec.pdf">View Spec Sheet</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1

    def test_pdf_dedup_by_url(self):
        html = """<html><body>
        <a href="/files/report.pdf">Report v1</a>
        <a href="/files/report.pdf">Report v2</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1

    def test_meta_generator_drupal(self):
        html = """<html><head>
        <meta name="generator" content="Drupal 10">
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["name"] == "Drupal"

    def test_hotjar(self):
        html = """<html><body>
        <script src="https://static.hotjar.com/c/hotjar.js"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "analytics"

    def test_mixpanel(self):
        html = """<html><body>
        <script src="https://cdn.mixpanel.com/mixpanel.js"></script>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = self.strategy.parse(soup, "https://example.com")

        assert len(result.assets) == 1
        assert result.assets[0]["category"] == "analytics"
