from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.parsers.constants import SOCIAL_PLATFORMS
from app.parsers.price_utils import parse_price
from app.parsers.strategy import ParsedResult, ParsingStrategy

SCHEMA_ORG_TYPES = {
    "http://schema.org/LocalBusiness",
    "http://schema.org/Organization",
    "http://schema.org/Corporation",
    "http://schema.org/Company",
    "http://schema.org/Service",
    "http://schema.org/Product",
    "http://schema.org/Offer",
    "http://schema.org/AggregateOffer",
    "http://schema.org/Article",
    "http://schema.org/BlogPosting",
    "http://schema.org/NewsArticle",
    "http://schema.org/WebPage",
    "http://schema.org/ContactPage",
    "https://schema.org/LocalBusiness",
    "https://schema.org/Organization",
    "https://schema.org/Corporation",
    "https://schema.org/Company",
    "https://schema.org/Service",
    "https://schema.org/Product",
    "https://schema.org/Offer",
    "https://schema.org/AggregateOffer",
    "https://schema.org/Article",
    "https://schema.org/BlogPosting",
    "https://schema.org/NewsArticle",
    "https://schema.org/WebPage",
    "https://schema.org/ContactPage",
}


import re


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        match = re.search(r"[\d.]+", str(val))
        return float(match.group(0)) if match else None
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        match = re.search(r"\d+", str(val).replace(",", ""))
        return int(match.group(0)) if match else None
    except (ValueError, TypeError):
        return None


class SchemaOrgStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "schema_org"

    @property
    def weight(self) -> float:
        return 0.25

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        for element in soup.select("[itemscope]"):
            itemtype = str(element.get("itemtype", ""))
            if itemtype in SCHEMA_ORG_TYPES:
                self._extract_item(element, itemtype, result, url)
        return result

    def _extract_article_item(
        self, props: dict[str, list[str]], result: ParsedResult, url: str
    ) -> None:
        from urllib.parse import urljoin as _urljoin

        headline = (props.get("headline") or props.get("name") or [""])[0] or None
        if not headline:
            return
        author_raw: str | None = (props.get("author") or [""])[0] or None
        date_raw: str | None = (props.get("datePublished") or [""])[0] or None
        article_url: str | None = (props.get("url") or [""])[0] or None
        result.content.append(
            {
                "title": str(headline),
                "author": author_raw,
                "publish_date": date_raw[:10] if date_raw and len(date_raw) >= 10 else date_raw,
                "url": _urljoin(url, article_url) if article_url else url,
                "summary": (props.get("description") or [""])[0] or None,
                "content_type": "article",
            }
        )

    def _extract_item(self, element: Any, itemtype: str, result: ParsedResult, url: str) -> None:
        props = self._get_properties(element)
        if (
            "LocalBusiness" in itemtype
            or "Organization" in itemtype
            or "Corporation" in itemtype
            or "Company" in itemtype
        ):
            self._extract_organization(props, result, url)
        elif "Service" in itemtype:
            name = props.get("name", [""])[0] if props.get("name") else ""
            # Extract price range if present
            min_price_text = props.get("minPrice", [None])[0] if props.get("minPrice") else None
            price_text = props.get("price", [None])[0] if props.get("price") else min_price_text
            # Extract AggregateRating if present
            rating_value = props.get("ratingValue", [None])[0] if props.get("ratingValue") else None
            review_count = props.get("reviewCount", [None])[0] if props.get("reviewCount") else None
            result.services.append(
                {
                    "name": name,
                    "description": (
                        props.get("description", [None])[0] if props.get("description") else None
                    ),
                    "category": props.get("category", [None])[0] if props.get("category") else None,
                    "starting_price": self._parse_price(price_text),
                    "currency": (
                        props.get("priceCurrency", ["USD"])[0]
                        if props.get("priceCurrency")
                        else "USD"
                    ),
                    "estimated_duration": None,
                    "rating": _safe_float(rating_value),
                    "review_count": _safe_int(review_count),
                }
            )
        elif "AggregateOffer" in itemtype:
            name = props.get("name", [""])[0] if props.get("name") else "Service"
            low = props.get("lowPrice", [None])[0] if props.get("lowPrice") else None
            high = props.get("highPrice", [None])[0] if props.get("highPrice") else None
            result.pricing.append(
                {
                    "service_name": name,
                    "category": props.get("category", [None])[0] if props.get("category") else None,
                    "base_price": self._parse_price(low),
                    "promotional_price": self._parse_price(high),
                    "currency": (
                        props.get("priceCurrency", ["USD"])[0]
                        if props.get("priceCurrency")
                        else "USD"
                    ),
                    "discount": None,
                    "subscription_plans": {},
                    "membership_pricing": None,
                }
            )
        elif "Product" in itemtype or "Offer" in itemtype:
            name = props.get("name", [""])[0] if props.get("name") else ""
            price_text = props.get("price", [None])[0] if props.get("price") else None
            min_price = props.get("minPrice", [None])[0] if props.get("minPrice") else None
            max_price = props.get("maxPrice", [None])[0] if props.get("maxPrice") else None
            result.pricing.append(
                {
                    "service_name": name,
                    "category": props.get("category", [None])[0] if props.get("category") else None,
                    "base_price": self._parse_price(price_text or min_price),
                    "promotional_price": self._parse_price(max_price),
                    "currency": (
                        props.get("priceCurrency", ["USD"])[0]
                        if props.get("priceCurrency")
                        else "USD"
                    ),
                    "discount": None,
                    "subscription_plans": {},
                    "membership_pricing": None,
                }
            )
        elif "Article" in itemtype or "BlogPosting" in itemtype or "NewsArticle" in itemtype:
            self._extract_article_item(props, result, url)

    def _get_properties(self, element: Any) -> dict[str, list[str]]:
        props: dict[str, list[str]] = {}
        for prop in element.select("[itemprop]"):
            name = prop.get("itemprop", "")
            value = prop.get("content") or prop.get("href") or prop.get_text(strip=True)
            if value:
                props.setdefault(name, []).append(value)
        return props

    def _extract_organization(
        self, props: dict[str, list[str]], result: ParsedResult, url: str
    ) -> None:
        if not result.company_name and props.get("name"):
            result.company_name = props["name"][0]
        if not result.description and props.get("description"):
            result.description = props["description"][0]
        if not result.logo and props.get("logo"):
            result.logo = urljoin(url, props["logo"][0])
        if not result.headquarters and props.get("address"):
            result.headquarters = props["address"][0]
        if not result.contact_email and props.get("email"):
            result.contact_email = props["email"][0]
        if not result.contact_phone and props.get("telephone"):
            result.contact_phone = props["telephone"][0]
        if props.get("sameAs"):
            for link in props["sameAs"]:
                platform = self._detect_platform(link)
                if platform and platform not in result.social_links:
                    result.social_links[platform] = link

    def _parse_price(self, price_text: str | None) -> float | None:
        return parse_price(price_text)

    def _detect_platform(self, url: str) -> str | None:
        for domain, platform in SOCIAL_PLATFORMS.items():
            if domain in url:
                return platform
        return None
