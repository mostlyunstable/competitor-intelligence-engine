"""Unit tests for the FormExtractionStrategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from app.parsers.strategies.form_extraction import FormExtractionStrategy

if TYPE_CHECKING:
    from app.parsers.strategy import ParsedResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestFormExtraction:
    def setup_method(self) -> None:
        self.strat = FormExtractionStrategy()

    def _parse(self, html: str) -> ParsedResult:
        soup = _soup(html)
        return self.strat.parse(soup, "https://example.com")

    # ------------------------------------------------------------------
    # Contact form — email extraction
    # ------------------------------------------------------------------

    def test_contact_form_email(self) -> None:
        html = """
        <form>
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email" value="test@example.com">
            <button type="submit">Send</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "test@example.com"

    def test_contact_form_email_from_type(self) -> None:
        html = """
        <form>
            <label>Your Email <input type="email" name="email" value="hello@company.com"></label>
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "hello@company.com"

    def test_contact_form_email_from_placeholder(self) -> None:
        html = """
        <form>
            <input type="email" name="email" placeholder="Enter your email" value="user@domain.com">
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "user@domain.com"

    def test_contact_form_email_from_aria_label(self) -> None:
        html = """
        <form>
            <input type="email" name="email" aria-label="Email address" value="contact@site.com">
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "contact@site.com"

    # ------------------------------------------------------------------
    # Contact form — phone extraction
    # ------------------------------------------------------------------

    def test_contact_form_phone(self) -> None:
        html = """
        <form>
            <label for="phone">Phone Number</label>
            <input type="tel" id="phone" name="phone" value="+1-555-123-4567">
            <button type="submit">Send</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_phone is not None
        assert "+1-555-123-4567" in result.contact_phone

    def test_contact_form_phone_input_text(self) -> None:
        html = """
        <form>
            <label for="mobile">Mobile</label>
            <input type="text" id="mobile" name="mobile" value="+91 98765 43210">
            <button type="submit">Send</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_phone is not None

    # ------------------------------------------------------------------
    # Service category dropdown
    # ------------------------------------------------------------------

    def test_service_category_dropdown(self) -> None:
        html = """
        <form>
            <label for="service">What service do you need?</label>
            <select id="service" name="service">
                <option value="">Select</option>
                <option value="cleaning">Home Cleaning</option>
                <option value="plumbing">Plumbing Repair</option>
                <option value="electrical">Electrical Work</option>
            </select>
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        categories = {s["name"] for s in result.services if s.get("source") == "form_category"}
        assert "Home Cleaning" in categories
        assert "Plumbing Repair" in categories
        assert "Electrical Work" in categories

    # ------------------------------------------------------------------
    # City / location dropdown
    # ------------------------------------------------------------------

    def test_city_dropdown(self) -> None:
        html = """
        <form>
            <label for="city">Your City</label>
            <select id="city" name="city">
                <option value="">Choose</option>
                <option value="nyc">New York</option>
                <option value="la">Los Angeles</option>
                <option value="chi">Chicago</option>
            </select>
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        cities = {s["name"] for s in result.services if s.get("source") == "form_city"}
        assert "New York" in cities
        assert "Los Angeles" in cities
        assert "Chicago" in cities

    # ------------------------------------------------------------------
    # Login forms skipped
    # ------------------------------------------------------------------

    def test_login_form_skipped(self) -> None:
        html = """
        <form>
            <label for="username">Username</label>
            <input type="text" id="username" name="username">
            <label for="password">Password</label>
            <input type="password" id="password" name="password">
            <button type="submit">Login</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email is None
        assert len(result.services) == 0

    def test_signup_form_skipped_by_action(self) -> None:
        html = """
        <form action="/signup">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="test@test.com">
            <button type="submit">Create Account</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email is None

    # ------------------------------------------------------------------
    # Contact method radio buttons
    # ------------------------------------------------------------------

    def test_contact_method_radios(self) -> None:
        html = """
        <form>
            <label>Preferred contact method</label>
            <label><input type="radio" name="contact" value="email"> Email</label>
            <label><input type="radio" name="contact" value="phone"> Phone</label>
            <label><input type="radio" name="contact" value="sms"> SMS</label>
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        methods = {c["title"] for c in result.content if c.get("content_type") == "contact_method"}
        assert "Email" in methods
        assert "Phone" in methods
        assert "SMS" in methods

    def test_contact_method_dropdown(self) -> None:
        html = """
        <form>
            <label for="contact">How did you hear about us?</label>
            <select id="contact" name="referral">
                <option>Google</option>
                <option>Friend</option>
                <option>Social Media</option>
            </select>
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        methods = {c["title"] for c in result.content if c.get("content_type") == "contact_method"}
        assert "Google" in methods
        assert "Friend" in methods
        assert "Social Media" in methods

    # ------------------------------------------------------------------
    # Multiple forms
    # ------------------------------------------------------------------

    def test_multiple_forms_combined(self) -> None:
        html = """
        <form id="form1">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="a@example.com">
        </form>
        <form id="form2">
            <label for="phone">Phone</label>
            <input type="tel" id="phone" name="phone" value="+1-555-0000">
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "a@example.com"
        assert result.contact_phone is not None

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_no_forms(self) -> None:
        result = self._parse("<html><body><p>No forms here.</p></body></html>")
        assert result.contact_email is None
        assert len(result.services) == 0

    def test_empty_form(self) -> None:
        result = self._parse("<form></form>")
        assert result.contact_email is None

    def test_hidden_inputs_ignored(self) -> None:
        html = """
        <form>
            <input type="hidden" name="token" value="secret123">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="user@example.com">
            <button type="submit">Submit</button>
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "user@example.com"

    def test_email_in_text_input(self) -> None:
        html = """
        <form>
            <label for="contact">Email Address</label>
            <input type="text" id="contact" name="contact" value="support@company.com">
        </form>
        """
        result = self._parse(html)
        assert result.contact_email == "support@company.com"

    # ------------------------------------------------------------------
    # Integration with StrategyParser
    # ------------------------------------------------------------------

    def test_strategy_parser_includes_form_extraction(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <form>
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email" value="info@example.com">
            <button type="submit">Send</button>
        </form>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        assert "form_extraction" in result.strategy_results

    def test_segment_aware_parsing(self) -> None:
        from app.parsers.strategy_parser import StrategyParser

        html = """
        <html><body>
        <section>
            <h2>Contact Us</h2>
            <form>
                <label for="service">Service Needed</label>
                <select id="service" name="service">
                    <option>Painting</option>
                    <option>Plumbing</option>
                </select>
                <button type="submit">Submit</button>
            </form>
        </section>
        </body></html>
        """
        parser = StrategyParser(use_adaptive_ordering=False, confidence_threshold=1.1)
        result = parser.parse(html, "https://example.com")
        categories = {s["name"] for s in result.services if s.get("source") == "form_category"}
        assert "Painting" in categories
        assert "Plumbing" in categories
