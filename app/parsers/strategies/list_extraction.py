"""List Extraction — extract structured information from HTML lists.

Detects and extracts entities from:
  - Unordered lists (<ul>)  → services, features, locations
  - Ordered lists (<ol>)    → ranked services, step-by-step features
  - Definition lists (<dl>) → term/description pairs (services, pricing)
  - Nested lists            → hierarchical categories with sub-services
  - Combo lists             → list items with embedded spans/divs containing structured data
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

    from app.parsers.page_segmenter import PageSegment

_PRICE_RE = re.compile(r"[\$€£₹]\s*[\d,]+(?:\.\d{1,2})?")
_DURATION_RE = re.compile(r"(\d+[\s-]*(?:min|hr|hour|day|week|month|year|session|visit))", re.IGNORECASE)


class ListExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "list_extraction"

    @property
    def weight(self) -> float:
        return 0.10

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_definition_lists(soup, result)
        self._extract_unordered_lists(soup, result, url)
        self._extract_ordered_lists(soup, result, url)
        self._extract_nested_lists(soup, result)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._extract_definition_lists(soup, result)
            self._extract_unordered_lists(soup, result, url)
            self._extract_ordered_lists(soup, result, url)
            self._extract_nested_lists(soup, result)
        return result

    def _extract_definition_lists(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        """Extract service/pricing/feature data from <dl> definition lists."""
        for dl in soup.select("dl"):
            terms = dl.select("dt")
            defs = dl.select("dd")
            for dt, dd in zip(terms, defs, strict=False):
                term = dt.get_text(strip=True)
                definition = dd.get_text(strip=True)
                if not term or not definition:
                    continue
                lower = (term + " " + definition).lower()

                # Detect price + duration in definition
                price_match = _PRICE_RE.search(definition)
                duration_match = _DURATION_RE.search(lower)
                price_val = self._parse_price(price_match.group(0)) if price_match else None
                currency = self._detect_currency(definition)

                # Classify the term
                if any(kw in lower for kw in ("price", "pricing", "cost", "$", "£", "€")):
                    result.pricing.append({
                        "service_name": term,
                        "category": None,
                        "base_price": price_val,
                        "promotional_price": None,
                        "currency": currency,
                        "discount": None,
                        "subscription_plans": {},
                        "membership_pricing": None,
                    })
                else:
                    result.services.append({
                        "name": term,
                        "description": definition,
                        "category": None,
                        "starting_price": price_val,
                        "currency": currency,
                        "estimated_duration": duration_match.group(1) if duration_match else None,
                    })

    def _extract_unordered_lists(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """Extract structured data from <ul> lists.

        Detects: locations/cities, features, plans from heading context.
        """
        for ul in soup.select("ul"):
            items = [li.get_text(strip=True) for li in ul.select("li") if li.get_text(strip=True)]
            if len(items) < 2:
                continue

            # Get context from preceding heading
            context_heading = ul.find_previous(["h1", "h2", "h3", "h4"])
            context = context_heading.get_text(strip=True).lower() if context_heading else ""

            # Detect item type from keywords
            all_text = " ".join(items).lower()
            has_price = bool(_PRICE_RE.search(all_text))

            if any(kw in context for kw in ("city", "location", "area", "region", "coverage", "where we serve")):
                for item in items:
                    result.locations.append({
                        "name": item,
                        "type": "city",
                    })
            elif any(kw in context for kw in ("feature", "capability", "includes", "included", "what you get")):
                for item in items:
                    price_match = _PRICE_RE.search(item)
                    result.features.append({
                        "name": item,
                        "description": None,
                        "price": self._parse_price(price_match.group(0)) if price_match else None,
                    })
            elif has_price:
                for item in items:
                    price_match = _PRICE_RE.search(item)
                    result.pricing.append({
                        "service_name": item,
                        "category": None,
                        "base_price": self._parse_price(price_match.group(0)) if price_match else None,
                        "promotional_price": None,
                        "currency": self._detect_currency(item),
                        "discount": None,
                        "subscription_plans": {},
                        "membership_pricing": None,
                    })
            else:
                for item in items:
                    result.services.append({
                        "name": item,
                        "description": None,
                        "category": None,
                        "starting_price": None,
                        "currency": "USD",
                        "estimated_duration": None,
                    })

    def _extract_ordered_lists(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """Extract ranked/ordered data from <ol> lists.

        Ordered lists often contain ranked services, step-by-step features,
        or prioritized plans.
        """
        for ol in soup.select("ol"):
            items = [li.get_text(strip=True) for li in ol.select("li") if li.get_text(strip=True)]
            if len(items) < 2:
                continue

            context_heading = ol.find_previous(["h1", "h2", "h3", "h4"])
            context_heading.get_text(strip=True).lower() if context_heading else ""
            all_text = " ".join(items).lower()

            if any(kw in all_text for kw in ("plan", "tier", "package", "subscription")):
                for item in items:
                    result.plans.append({
                        "plan_name": item,
                        "description": None,
                        "price": None,
                        "currency": "USD",
                        "features": [],
                    })
            elif _PRICE_RE.search(all_text):
                for item in items:
                    price_match = _PRICE_RE.search(item)
                    result.pricing.append({
                        "service_name": item,
                        "category": None,
                        "base_price": self._parse_price(price_match.group(0)) if price_match else None,
                        "promotional_price": None,
                        "currency": self._detect_currency(item),
                        "discount": None,
                        "subscription_plans": {},
                        "membership_pricing": None,
                    })

    def _extract_nested_lists(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        """Extract hierarchical categories from nested lists.

        Pattern: <ul><li>Category<ul><li>Sub-service</li></ul></li></ul>
        """
        for li in soup.select("li"):
            nested = li.select("ul, ol")
            if not nested:
                continue
            category = li.contents[0] if li.contents else None
            if hasattr(category, "get_text"):
                category_name = category.get_text(strip=True)  # type: ignore[union-attr]
            else:
                category_name = str(category).strip() if category else ""

            if not category_name or not isinstance(category_name, str):
                continue
            if len(category_name) > 60:
                continue

            for child in nested[0].select("li"):
                child_text = child.get_text(strip=True)
                if not child_text:
                    continue
                price_match = _PRICE_RE.search(child_text)
                result.services.append({
                    "name": child_text,
                    "description": None,
                    "category": category_name,
                    "starting_price": self._parse_price(price_match.group(0)) if price_match else None,
                    "currency": self._detect_currency(child_text),
                    "estimated_duration": None,
                })

    @staticmethod
    def _parse_price(price_text: str | None) -> float | None:
        if not price_text:
            return None
        numbers = re.findall(r"[\d,]+\.?\d*", price_text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None

    @staticmethod
    def _detect_currency(price_text: str | None) -> str:
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
