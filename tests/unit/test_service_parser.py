from app.parsers.service import ServiceParser


class TestServiceParser:
    def setup_method(self) -> None:
        self.parser = ServiceParser()

    def test_parse_service_cards(self) -> None:
        html = """
        <html>
        <body>
            <div class="service-card">
                <h3>HVAC Repair</h3>
                <p>Professional heating and cooling repair</p>
                <span class="price">$150</span>
                <span class="duration">2-3 hours</span>
                <span class="category">Heating</span>
            </div>
            <div class="service-card">
                <h3>Plumbing</h3>
                <p>Emergency plumbing services</p>
                <span class="price">$100</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/services")
        assert len(result["services"]) == 2
        assert result["services"][0]["name"] == "HVAC Repair"
        assert result["services"][0]["starting_price"] == 150.0
        assert result["services"][0]["currency"] == "USD"
        assert result["services"][0]["estimated_duration"] == "2-3 hours"

    def test_parse_product_cards(self) -> None:
        html = """
        <html>
        <body>
            <div class="product-card">
                <h3>Basic Plan</h3>
                <span class="price">$49.99/mo</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/products")
        assert len(result["services"]) == 1
        assert result["services"][0]["name"] == "Basic Plan"

    def test_parse_empty_page(self) -> None:
        html = "<html><body></body></html>"
        result = self.parser.parse(html, "https://example.com")
        assert result["services"] == []

    def test_parse_price_with_comma(self) -> None:
        html = """
        <html>
        <body>
            <div class="service-card">
                <h3>Premium Service</h3>
                <span class="price">$1,250.00</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["services"][0]["starting_price"] == 1250.0

    def test_parse_euro_price(self) -> None:
        html = """
        <html>
        <body>
            <div class="service-card">
                <h3>European Service</h3>
                <span class="price">€200</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["services"][0]["currency"] == "EUR"

    def test_parse_from_headings(self) -> None:
        html = """
        <html>
        <body>
            <h2>HVAC Installation</h2>
            <p>Complete HVAC system installation</p>
            <h2>AC Repair</h2>
            <p>Fast air conditioning repair</p>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert len(result["services"]) == 2
