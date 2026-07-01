from app.parsers.pricing import PricingParser


class TestPricingParser:
    def setup_method(self) -> None:
        self.parser = PricingParser()

    def test_parse_pricing_cards(self) -> None:
        html = """
        <html>
        <body>
            <div class="pricing-card">
                <h3>Basic Plan</h3>
                <span class="price">$29/mo</span>
            </div>
            <div class="pricing-card">
                <h3>Pro Plan</h3>
                <span class="price">$99/mo</span>
                <span class="promo-price">$79/mo</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/pricing")
        assert len(result["pricing"]) == 2
        assert result["pricing"][0]["service_name"] == "Basic Plan"
        assert result["pricing"][0]["base_price"] == 29.0
        assert result["pricing"][1]["base_price"] == 99.0
        assert result["pricing"][1]["promotional_price"] == 79.0

    def test_parse_plan_cards(self) -> None:
        html = """
        <html>
        <body>
            <div class="plan-card">
                <h3>Enterprise</h3>
                <span class="base-price">$499</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/pricing")
        assert len(result["pricing"]) == 1
        assert result["pricing"][0]["base_price"] == 499.0

    def test_parse_table_pricing(self) -> None:
        html = """
        <html>
        <body>
            <table>
                <tr><th>Service</th><th>Price</th><th>Category</th></tr>
                <tr><td>HVAC Repair</td><td>$150</td><td>Heating</td></tr>
                <tr><td>Plumbing</td><td>$100</td><td>Water</td></tr>
            </table>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/pricing")
        assert len(result["pricing"]) == 2
        assert result["pricing"][0]["service_name"] == "HVAC Repair"
        assert result["pricing"][0]["base_price"] == 150.0

    def test_parse_empty_page(self) -> None:
        html = "<html><body></body></html>"
        result = self.parser.parse(html, "https://example.com")
        assert result["pricing"] == []

    def test_parse_discount(self) -> None:
        html = """
        <html>
        <body>
            <div class="pricing-card">
                <h3>Annual Plan</h3>
                <span class="price">$1200</span>
                <span class="discount">$200 off</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["pricing"][0]["discount"] == 200.0

    def test_parse_membership(self) -> None:
        html = """
        <html>
        <body>
            <div class="pricing-card">
                <h3>Premium</h3>
                <span class="price">$99</span>
                <span class="membership">$49/mo membership</span>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["pricing"][0]["membership_pricing"] is not None
