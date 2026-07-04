import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.parsers.strategy import ParsedResult, ParsingStrategy

logger = logging.getLogger(__name__)

SCHEMA_ORG_TYPES = {
    "LocalBusiness",
    "Organization",
    "Corporation",
    "Company",
    "Service",
    "ServiceList",
    "Product",
    "Offer",
    "AggregateOffer",
    "ItemList",
    "FAQPage",
    "Article",
    "BlogPosting",
    "NewsArticle",
    "WebPage",
    "Person",
    "ContactPage",
    "BreadcrumbList",
}

SOCIAL_PLATFORMS: dict[str, str] = {
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "youtube.com": "youtube",
    "pinterest.com": "pinterest",
    "threads.net": "threads",
}


class JsonLdStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "json_ld"

    @property
    def weight(self) -> float:
        return 0.30

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        scripts = soup.select('script[type="application/ld+json"]')
        for script in scripts:
            try:
                raw = script.string or ""
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                # Flatten @graph arrays — common in Next.js / WordPress sites
                if isinstance(item, dict) and "@graph" in item:
                    for graph_item in item["@graph"]:
                        if isinstance(graph_item, dict):
                            self._process_item(graph_item, result, url)
                elif isinstance(item, dict):
                    self._process_item(item, result, url)
        return result

    def _process_item(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        item_type = item.get("@type", "")
        if isinstance(item_type, list):
            item_type = " ".join(item_type)

        if item_type in ("LocalBusiness", "Organization", "Corporation", "Company"):
            self._extract_organization(item, result, url)
        elif item_type in ("Service", "ServiceList"):
            self._extract_service(item, result)
        elif item_type == "ItemList":
            self._extract_item_list(item, result, url)
        elif item_type == "FAQPage":
            self._extract_faq(item, result, url)
        elif item_type == "Product":
            self._extract_product(item, result)
        elif item_type in ("Offer", "AggregateOffer"):
            self._extract_offer(item, result)
        elif item_type in ("Article", "BlogPosting", "NewsArticle"):
            self._extract_article(item, result, url)
        elif item_type in ("WebPage", "ContactPage"):
            self._extract_webpage(item, result, url)

        # Recurse into nested graph structures
        for child in item.get("hasPart", []):
            if isinstance(child, dict):
                self._process_item(child, result, url)
        for child in item.get("subEvent", []):
            if isinstance(child, dict):
                self._process_item(child, result, url)
        # Recurse into top-level offers arrays
        offers = item.get("offers")
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    self._extract_offer(offer, result)
        elif isinstance(offers, dict):
            self._extract_offer(offers, result)

    def _extract_organization(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        if not result.company_name:
            result.company_name = item.get("name")
        if not result.description:
            result.description = item.get("description")
        if not result.logo:
            logo = item.get("logo")
            if isinstance(logo, str):
                result.logo = urljoin(url, logo)
            elif isinstance(logo, dict):
                result.logo = urljoin(url, logo.get("url", ""))
        if not result.industry:
            result.industry = item.get("industry")
        if not result.headquarters:
            addr = item.get("address", {})
            if isinstance(addr, dict):
                parts = [
                    addr.get("streetAddress", ""),
                    addr.get("addressLocality", ""),
                    addr.get("addressRegion", ""),
                    addr.get("addressCountry", ""),
                ]
                result.headquarters = ", ".join(p for p in parts if p)
            elif isinstance(addr, str):
                result.headquarters = addr
        if not result.contact_email:
            email = item.get("email")
            if isinstance(email, str):
                result.contact_email = email.strip()
        if not result.contact_phone:
            phone = item.get("telephone")
            if isinstance(phone, str):
                result.contact_phone = phone.strip()
        links_raw = item.get("sameAs", [])
        if isinstance(links_raw, str):
            links_raw = [links_raw]
        for link in links_raw:
            if isinstance(link, str):
                platform = self._detect_platform(link)
                if platform and platform not in result.social_links:
                    result.social_links[platform] = link
        for member in item.get("member", []):
            if isinstance(member, dict):
                self._process_item(member, result, url)

    def _extract_service(self, item: dict[str, Any], result: ParsedResult) -> None:
        name = item.get("name", "")
        if not name:
            return
        starting_price = None
        currency = "USD"
        offers = item.get("offers")
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice")
            currency = offers.get("priceCurrency", "USD")
            if price:
                try:
                    starting_price = float(str(price).replace(",", ""))
                except ValueError:
                    pass
        elif isinstance(offers, list) and offers:
            first = offers[0]
            price = first.get("price") or first.get("lowPrice")
            currency = first.get("priceCurrency", "USD")
            if price:
                try:
                    starting_price = float(str(price).replace(",", ""))
                except ValueError:
                    pass
        result.services.append(
            {
                "name": name,
                "description": item.get("description"),
                "category": item.get("category"),
                "starting_price": starting_price,
                "currency": currency,
                "estimated_duration": None,
            }
        )

    def _extract_item_list(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        """Extract ItemList / ServiceList entries as services."""
        for element in item.get("itemListElement", []):
            if isinstance(element, dict):
                inner_type = element.get("@type", "")
                if inner_type in ("Service", "Product", "Offer"):
                    self._process_item(element, result, url)
                elif element.get("name"):
                    result.services.append(
                        {
                            "name": element.get("name", ""),
                            "description": element.get("description"),
                            "category": item.get("name"),
                            "starting_price": None,
                            "currency": "USD",
                            "estimated_duration": None,
                        }
                    )

    def _extract_faq(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        """Extract FAQPage Q&A pairs as content items."""
        for entity in item.get("mainEntity", []):
            if isinstance(entity, dict):
                question = entity.get("name", "")
                answer_block = entity.get("acceptedAnswer", {})
                answer = answer_block.get("text", "") if isinstance(answer_block, dict) else ""
                if question:
                    result.content.append(
                        {
                            "title": question,
                            "author": None,
                            "publish_date": None,
                            "url": url,
                            "summary": answer[:500] if answer else None,
                            "content_type": "faq",
                        }
                    )

    def _extract_product(self, item: dict[str, Any], result: ParsedResult) -> None:
        name = item.get("name", "")
        offers = item.get("offers", {})
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    self._extract_offer(
                        offer, result, service_name=name, category=item.get("category")
                    )
        elif isinstance(offers, dict):
            self._extract_offer(offers, result, service_name=name, category=item.get("category"))
        else:
            result.services.append(
                {
                    "name": name,
                    "description": item.get("description"),
                    "category": item.get("category"),
                    "starting_price": None,
                    "currency": "USD",
                    "estimated_duration": None,
                }
            )

    def _extract_offer(
        self,
        item: dict[str, Any],
        result: ParsedResult,
        *,
        service_name: str | None = None,
        category: Any = None,
    ) -> None:
        offer_type = item.get("@type", "Offer")
        name = service_name or item.get("name", "Offer")
        currency = item.get("priceCurrency", "USD")

        if offer_type == "AggregateOffer":
            low = item.get("lowPrice")
            high = item.get("highPrice")
            result.pricing.append(
                {
                    "service_name": name,
                    "category": category or item.get("category"),
                    "base_price": float(str(low).replace(",", "")) if low is not None else None,
                    "promotional_price": float(str(high).replace(",", ""))
                    if high is not None
                    else None,
                    "currency": currency,
                    "discount": None,
                    "subscription_plans": {},
                    "membership_pricing": None,
                }
            )
        else:
            price = item.get("price")
            result.pricing.append(
                {
                    "service_name": name,
                    "category": category or item.get("category"),
                    "base_price": float(str(price).replace(",", ""))
                    if price is not None
                    else None,
                    "promotional_price": None,
                    "currency": currency,
                    "discount": None,
                    "subscription_plans": {},
                    "membership_pricing": None,
                }
            )

    def _extract_article(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        headline = item.get("headline") or item.get("name")
        if not headline:
            return
        result.content.append(
            {
                "title": headline,
                "author": self._extract_author(item),
                "publish_date": self._normalize_date(item.get("datePublished")),
                "url": urljoin(url, item.get("url", "")),
                "summary": item.get("description"),
                "content_type": "article",
            }
        )

    def _extract_webpage(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        if not result.company_name:
            result.company_name = item.get("name")
        if not result.description:
            result.description = item.get("description")

    def _extract_author(self, item: dict[str, Any]) -> str | None:
        author = item.get("author")
        if isinstance(author, str):
            return author
        if isinstance(author, dict):
            return author.get("name")
        if isinstance(author, list) and author:
            first = author[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("name")
        return None

    def _normalize_date(self, raw: Any) -> str | None:
        """Normalize a date string to YYYY-MM-DD."""
        if not raw or not isinstance(raw, str):
            return None
        iso = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
        if iso:
            return iso.group(1)
        return raw[:10] if len(raw) >= 10 else raw

    def _detect_platform(self, url: str) -> str | None:
        for domain, platform in SOCIAL_PLATFORMS.items():
            if domain in url:
                return platform
        return None
