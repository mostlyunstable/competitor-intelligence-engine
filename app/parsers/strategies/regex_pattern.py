from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

    from app.parsers.page_segmenter import PageSegment
from app.parsers.strategy import ParsedResult, ParsingStrategy


class RegexPatternStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "regex_pattern"

    @property
    def weight(self) -> float:
        return 0.05

    EMAIL_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    )
    PHONE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    )
    PRICE_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"[\$€£₹]\s*[\d,]+(?:\.\d{2})?"),
        re.compile(r"[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR)"),
    ]
    SOCIAL_PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9\-]+"),
        "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9.\-]+"),
        "twitter": re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+"),
        "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+"),
        "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)[a-zA-Z0-9\-_]+"),
    }

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        text = soup.get_text()
        html = str(soup)
        self._extract_emails(text, result)
        self._extract_phones(text, result)
        self._extract_prices(text, result)
        self._extract_social_links(html, result)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        """Regex is text-based — extract from all segment text combined."""
        result = ParsedResult()
        all_text = " ".join(seg.text_content() for seg in segments)
        all_html = "".join(str(seg.element) for seg in segments)
        self._extract_emails(all_text, result)
        self._extract_phones(all_text, result)
        self._extract_prices(all_text, result)
        self._extract_social_links(all_html, result)
        return result

    def _extract_emails(self, text: str, result: ParsedResult) -> None:
        if result.contact_email:
            return
        match = self.EMAIL_PATTERN.search(text)
        if match:
            email = match.group(0)
            if not email.endswith((".png", ".jpg", ".gif", ".svg", ".css", ".js")):
                result.contact_email = email

    def _extract_phones(self, text: str, result: ParsedResult) -> None:
        if result.contact_phone:
            return
        match = self.PHONE_PATTERN.search(text)
        if match:
            result.contact_phone = match.group(0).strip()

    def _extract_prices(self, text: str, result: ParsedResult) -> None:
        if result.pricing:
            return
        for pattern in self.PRICE_PATTERNS:
            matches = pattern.findall(text)
            for match in matches[:5]:
                price = self._parse_price(match)
                if price is not None and price > 0:
                    result.pricing.append(
                        {
                            "service_name": f"Detected Price ({self._detect_currency(match)}{price})",
                            "category": None,
                            "base_price": price,
                            "promotional_price": None,
                            "currency": self._detect_currency(match),
                            "discount": None,
                            "subscription_plans": {},
                            "membership_pricing": None,
                        }
                    )
            if result.pricing:
                break

    def _extract_social_links(self, html: str, result: ParsedResult) -> None:
        for platform, pattern in self.SOCIAL_PATTERNS.items():
            if platform in result.social_links:
                continue
            match = pattern.search(html)
            if match:
                result.social_links[platform] = match.group(0)

    def _parse_price(self, price_text: str | None) -> float | None:
        if not price_text:
            return None
        numbers = re.findall(r"[\d,]+\.?\d*", price_text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None

    def _detect_currency(self, price_text: str | None) -> str:
        if not price_text:
            return "USD"
        if "$" in price_text:
            return "USD"
        if "€" in price_text:
            return "EUR"
        if "£" in price_text:
            return "GBP"
        if "₹" in price_text:
            return "INR"
        return "USD"
