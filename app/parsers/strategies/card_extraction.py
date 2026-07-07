"""Card Extraction — detect and extract structured data from repeated card patterns.

Detects cards generically by finding groups of sibling elements with similar
internal structure (heading + body + optional metadata).  Extracts:
  - Title / heading
  - Description / body text
  - Price
  - Image URL
  - Button link / CTA
  - Badge / label
  - Rating / stars
  - Feature list (for feature/comparison cards)

No class names, no visual rendering, pure DOM structure analysis.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

_PRICE_RE = re.compile(r"[\$€£₹]\s*[\d,]+(?:\.\d{1,2})?")
_RATING_RE = re.compile(r"([\d.]+)\s*/\s*[\d.]+|\b(\d)\s*star|\b(\d)\s*-star")


class CardExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "card_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_cards(soup, result, url)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            if seg.segment_type in ("services", "pricing", "plans", "features", "reviews"):
                self._extract_cards(seg.to_soup(), result, url)
        return result

    def _find_card_containers(self, soup: BeautifulSoup) -> list[Tag]:
        """Find parent elements that contain 2+ direct child card-like elements.

        A card-like element is a div/article/section/li that contains
        at least one heading and one of: paragraph, list, button, image.
        """
        containers: list[Tag] = []
        seen: set[int] = set()

        for parent in soup.select("div, section, main, ul, ol"):
            children = [c for c in parent.children if isinstance(c, Tag)]
            if len(children) < 2:
                continue

            card_count = 0
            for child in children:
                if self._is_card_like(child):
                    card_count += 1

            if card_count >= 2:
                pid = id(parent)
                if pid not in seen:
                    seen.add(pid)
                    containers.append(parent)

        return containers

    @staticmethod
    def _is_card_like(el: Tag) -> bool:
        """Check if an element looks like a card.

        A card typically has:
          - A heading (h1-h6)
          - At least one of: paragraph, list, image, button, link, price
        """
        if el.name not in ("div", "article", "section", "li", "figure", "aside"):
            return False
        heading = el.select_one("h1, h2, h3, h4, h5, h6, strong")
        if not heading:
            return False
        text = heading.get_text(strip=True)
        if not text or len(text) < 2:
            return False
        # Must have at least one supporting element
        if el.select_one("p, ul, ol, img, button, a[href], span, table"):
            return True
        return len(el.find_all(True)) >= 2  # heading + at least one more element

    def _extract_cards(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        containers = self._find_card_containers(soup)

        for container in containers:
            children = [c for c in container.children if isinstance(c, Tag) and self._is_card_like(c)]
            for child in children:
                self._extract_card(child, result, url)

    def _extract_card(self, card: Tag, result: ParsedResult, url: str) -> None:
        heading = card.select_one("h1, h2, h3, h4, h5, h6, strong")
        if not heading:
            return
        title = heading.get_text(strip=True)
        if not title:
            return

        all_text = card.get_text(" ", strip=True)
        price_match = _PRICE_RE.search(all_text)
        rating_match = _RATING_RE.search(all_text)
        price_val = self._parse_price(price_match.group(0)) if price_match else None
        currency = self._detect_currency(all_text)
        rating_val = self._parse_rating(rating_match) if rating_match else None

        # Description
        desc_el = card.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else None

        # Image
        img_el = card.select_one("img")
        image_url = urljoin(url, str(img_el.get("src", ""))) if img_el else None

        # Button / CTA link
        button_el = card.select_one("a[href], button")
        button_url = None
        button_text = None
        if button_el:
            button_url = urljoin(url, str(button_el.get("href", ""))) if button_el.name == "a" else None
            button_text = button_el.get_text(strip=True) or None

        # Badge / label (small spans, strong elements near heading)
        badge_el = card.select_one("span.badge, span.tag, span.label, strong, em, small")
        badge = badge_el.get_text(strip=True) if badge_el else None
        if badge and badge == title:
            badge = None  # don't use heading as badge

        # Features (nested lists)
        features: list[str] = []
        for li in card.select("li"):
            ft = li.get_text(strip=True)
            if ft:
                features.append(ft)

        lower_title = title.lower()
        has_svc_kw = any(kw in lower_title for kw in (
            "service", "plan", "package", "tier", "membership", "subscription"
        ))

        if price_val is not None:
            result.pricing.append({
                "service_name": title,
                "category": None,
                "base_price": price_val,
                "promotional_price": None,
                "currency": currency,
                "discount": None,
                "subscription_plans": {},
                "membership_pricing": None,
            })

        if has_svc_kw:
            result.plans.append({
                "plan_name": title,
                "description": description,
                "price": price_val,
                "currency": currency,
                "features": features,
            })

        if rating_val is not None:
            result.reviews.append({
                "title": title,
                "rating": rating_val,
                "body": description,
                "author": None,
                "source_url": url,
            })

        if features:
            result.features.append({
                "name": title,
                "description": description,
                "price": price_val,
            })

        if image_url or button_url:
            media_entry: dict[str, Any] = {"type": "card", "title": title}
            if image_url:
                media_entry["image_url"] = image_url
            if button_url:
                media_entry["link_url"] = button_url
            if button_text:
                media_entry["label"] = button_text
            result.media.append(media_entry)

        result.services.append({
            "name": title,
            "description": description,
            "category": None,
            "starting_price": price_val,
            "currency": currency,
            "estimated_duration": None,
        })

    @staticmethod
    def _parse_rating(match: re.Match[str]) -> float | None:
        groups = match.groups()
        for g in groups:
            if g is not None:
                try:
                    return float(g)
                except ValueError:
                    return None
        return None

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
