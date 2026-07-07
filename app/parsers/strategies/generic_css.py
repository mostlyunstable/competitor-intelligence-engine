import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.parsers.page_segmenter import PageSegment
from app.parsers.strategy import ParsedResult, ParsingStrategy


class GenericCssPatternStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "generic_css_pattern"

    @property
    def weight(self) -> float:
        return 0.10

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_services(soup, result)
        self._extract_pricing(soup, result)
        self._extract_content(soup, result, url)
        self._extract_company(soup, result, url)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        """Only process service/pricing/content segments."""
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            if seg.segment_type in ("services", "pricing"):
                self._extract_services(soup, result)
                self._extract_pricing(soup, result)
            elif seg.segment_type in ("content", "blog"):
                self._extract_content(soup, result, url)
            elif seg.segment_type in ("about", "hero"):
                self._extract_company(soup, result, url)
        return result

    def _extract_services(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for card in soup.select("div, section, article, li"):
            name = self._text(card, "h2, h3, h4, h5")
            if not name:
                continue
            desc_el = card.select_one("p")
            result.services.append(
                {
                    "name": name,
                    "description": desc_el.get_text(strip=True) if desc_el else None,
                    "category": None,
                    "starting_price": None,
                    "currency": "USD",
                    "estimated_duration": None,
                }
            )

    def _extract_pricing(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for card in soup.select("div, section, article, li"):
            name = self._text(card, "h2, h3, h4, h5")
            if not name:
                continue
            price_text = self._text(card, "p, span, strong")
            result.pricing.append(
                {
                    "service_name": name,
                    "category": None,
                    "base_price": self._parse_price(price_text),
                    "promotional_price": None,
                    "currency": self._detect_currency(price_text),
                    "discount": None,
                    "subscription_plans": {},
                    "membership_pricing": None,
                }
            )

    def _extract_content(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for card in soup.select("div, section, article"):
            title = self._text(card, "h2, h3, h4")
            if not title:
                continue
            link_el = card.select_one("a[href]")
            link = str(link_el.get("href", "")) if link_el else None
            summary_el = card.select_one("p")
            result.content.append(
                {
                    "title": title,
                    "author": None,
                    "publish_date": None,
                    "url": urljoin(url, link) if link else None,
                    "summary": summary_el.get_text(strip=True) if summary_el else None,
                    "content_type": "article",
                }
            )

    def _extract_company(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for card in soup.select("div, section, article"):
            if not result.description:
                desc_el = card.select_one("p")
                if desc_el:
                    result.description = desc_el.get_text(strip=True)

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
