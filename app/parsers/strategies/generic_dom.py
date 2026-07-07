import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.parsers.page_segmenter import PageSegment
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
        social_platforms = {
            "linkedin.com": "linkedin",
            "facebook.com": "facebook",
            "instagram.com": "instagram",
            "twitter.com": "twitter",
            "x.com": "twitter",
            "youtube.com": "youtube",
            "pinterest.com": "pinterest",
            "threads.net": "threads",
        }
        for a_tag in soup.select("a[href]"):
            href = str(a_tag.get("href", ""))
            for domain, platform in social_platforms.items():
                if domain in href and platform not in result.social_links:
                    result.social_links[platform] = urljoin(url, href)

    def _analyze_price_elements(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        if result.pricing:
            return
        price_pattern = re.compile(r"\$\d+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR)")
        for element in soup.select(
            "th, td, li, span, strong, em"
        ):
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
        if not result.contact_phone:
            phone_link = soup.select_one("a[href^='tel:']")
            if phone_link:
                result.contact_phone = str(phone_link["href"]).replace("tel:", "")

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
