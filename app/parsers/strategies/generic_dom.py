import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.parsers.constants import SOCIAL_PLATFORMS
from app.parsers.page_segmenter import PageSegment
from app.parsers.price_utils import detect_currency, parse_price
from app.parsers.strategy import ParsedResult, ParsingStrategy


class GenericDomHeuristicStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "generic_dom_heuristic"

    @property
    def weight(self) -> float:
        return 0.10

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._analyze_heading_hierarchy(soup, result)
        self._analyze_link_density(soup, result, url)
        self._analyze_price_elements(soup, result)
        self._analyze_contact_elements(soup, result)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        """Process each segment independently."""
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._analyze_heading_hierarchy(soup, result)
            self._analyze_link_density(soup, result, url)
            self._analyze_price_elements(soup, result)
            self._analyze_contact_elements(soup, result)
        return result

    def _analyze_heading_hierarchy(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        h1_tags = soup.select("h1")
        if h1_tags and not result.company_name:
            result.company_name = h1_tags[0].get_text(strip=True)

    def _analyze_link_density(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for a_tag in soup.select("a[href]"):
            href = str(a_tag.get("href", ""))
            for domain, platform in SOCIAL_PLATFORMS.items():
                if domain in href and platform not in result.social_links:
                    result.social_links[platform] = urljoin(url, href)

    def _analyze_price_elements(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        if result.pricing:
            return
        price_pattern = re.compile(r"[\$€£₹]\s*[\d,]+(?:\.\d{2})?|rs\.?\s*[\d,]+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR)|\d+[\d,]*(?:\.\d{2})?/-|from\s+₹?\s*[\d,]+|starting\s+(?:at|from)\s+₹?\s*[\d,]+")
        for element in soup.select("th, td, li, span, strong, em"):
            text = element.get_text(strip=True)
            if not text or len(text) > 60:
                continue
            if not price_pattern.search(text):
                continue
            price = self._parse_price(text)
            if price is not None:
                parent = element.find_parent(["div", "section", "article", "li"])
                service_name = "Detected Price"
                if parent:
                    heading = parent.select_one("h2, h3, h4, h5")
                    if heading:
                        service_name = heading.get_text(strip=True)
                result.pricing.append(
                    {
                        "service_name": service_name,
                        "category": None,
                        "base_price": price,
                        "promotional_price": None,
                        "currency": self._detect_currency(text),
                        "discount": None,
                        "subscription_plans": {},
                        "membership_pricing": None,
                    }
                )

    def _analyze_contact_elements(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        if not result.contact_email:
            email_link = soup.select_one("a[href^='mailto:']")
            if email_link:
                result.contact_email = str(email_link["href"]).replace("mailto:", "")
            else:
                # Extract plain text email
                import re as re_mod
                text = soup.get_text(" ", strip=True)
                email_match = re_mod.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
                if email_match:
                    result.contact_email = email_match.group(0)
        if not result.contact_phone:
            phone_link = soup.select_one("a[href^='tel:']")
            if phone_link:
                result.contact_phone = str(phone_link["href"]).replace("tel:", "")
            else:
                # Extract plain text Indian phone number
                import re as re_mod
                text = soup.get_text(" ", strip=True)
                phone_match = re_mod.search(r'(?:\+91[-.\s]?)?\d{5}\s?\d{5}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', text)
                if phone_match:
                    result.contact_phone = phone_match.group(0).strip()

    def _parse_price(self, price_text: str | None) -> float | None:
        return parse_price(price_text)

    def _detect_currency(self, price_text: str | None) -> str:
        return detect_currency(price_text)
