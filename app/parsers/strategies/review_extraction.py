"""Review & Testimonial Extraction — customer reviews, ratings, case studies.

Detects reviews from:
  - Schema.org Review/AggregateRating microdata
  - JSON-LD: Review, AggregateRating types
  - Semantic HTML: blockquote, testimonial patterns, rating stars
  - Section headings: "reviews", "testimonials", "what our customers say"
  - Rating patterns: "4.5/5", "5 stars", star icons

No company-specific selectors. No class name dependencies.
"""

from __future__ import annotations

import contextlib
import json
import re
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

# Heading keywords for review/testimonial sections
_REVIEW_HEADING_KW = frozenset(
    {
        "reviews",
        "review",
        "testimonials",
        "testimonial",
        "what our customers say",
        "customer reviews",
        "client reviews",
        "feedback",
        "ratings",
        "imonials",
    }
)

# Rating patterns
_RATING_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)|"  # 4.5/5
    r"(\d+(?:\.\d+)?)\s*stars?|"  # 4.5 stars
    r"(\d+(?:\.\d+)?)\s*out of\s*(\d+)",  # 4.5 out of 5
    re.IGNORECASE,
)

# Star rating unicode characters
_STAR_CHARS = {"★", "☆", "⭐"}


class ReviewExtractionStrategy(ParsingStrategy):
    """Extracts customer reviews, ratings, and testimonials."""

    @property
    def name(self) -> str:
        return "review_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_from_jsonld(soup, result, url)
        self._extract_from_microdata(soup, result, url)
        self._extract_from_review_sections(soup, result, url)
        self._extract_from_blockquotes(soup, result, url)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._extract_from_jsonld(soup, result, url)
            self._extract_from_microdata(soup, result, url)
            if seg.segment_type in ("reviews", "about", "hero", "unknown"):
                self._extract_from_review_sections(soup, result, url)
                self._extract_from_blockquotes(soup, result, url)
        return result

    def _extract_from_jsonld(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    self._process_jsonld_item(item, result, url)

    def _process_jsonld_item(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        raw_type = item.get("@type", "")
        item_type = raw_type if isinstance(raw_type, str) else " ".join(raw_type)

        if "Review" in item_type:
            self._add_review_from_jsonld(item, result, url)

        if "AggregateRating" in item_type:
            self._add_aggregate_rating(item, result)

        # Process reviews nested in other types
        reviews = item.get("review", [])
        if isinstance(reviews, dict):
            reviews = [reviews]
        for review in reviews:
            if isinstance(review, dict):
                self._add_review_from_jsonld(review, result, url)

        # Recurse into @graph
        for graph_item in item.get("@graph", []):
            if isinstance(graph_item, dict):
                self._process_jsonld_item(graph_item, result, url)

    def _add_review_from_jsonld(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        author = item.get("author", "")
        if isinstance(author, dict):
            author = author.get("name", "")
        review_body = item.get("reviewBody", "")
        title = item.get("name", "")

        rating = None
        rating_obj = item.get("reviewRating")
        if isinstance(rating_obj, dict):
            rating = rating_obj.get("ratingValue")
            if rating is not None:
                try:
                    rating = float(rating)
                except (ValueError, TypeError):
                    rating = None

        date = item.get("datePublished", "")

        if review_body or title:
            display_title = str(title) if title else f"Review from {author}" if author else "Review"
            result.reviews.append(
                {
                    "title": display_title[:300],
                    "author": str(author) if author else None,
                    "body": str(review_body)[:1000] if review_body else None,
                    "rating": rating,
                    "publish_date": str(date)[:10] if date else None,
                    "source_url": url,
                    "source": "json_ld",
                }
            )

    def _add_aggregate_rating(self, item: dict[str, Any], result: ParsedResult) -> None:
        rating_value = item.get("ratingValue")
        review_count = item.get("reviewCount") or item.get("ratingCount")
        best = item.get("bestRating", 5)
        worst = item.get("worstRating", 1)

        if rating_value is not None:
            try:
                rating_float = float(rating_value)
            except (ValueError, TypeError):
                return
            count = None
            if review_count is not None:
                with contextlib.suppress(ValueError, TypeError):
                    count = int(review_count)
            # Store as a special aggregate review entry
            result.reviews.append(
                {
                    "title": "Aggregate Rating",
                    "author": None,
                    "body": None,
                    "rating": rating_float,
                    "review_count": count,
                    "best_rating": int(best) if best else 5,
                    "worst_rating": int(worst) if worst else 1,
                    "source_url": "",
                    "source": "json_ld_aggregate",
                }
            )

    def _extract_from_microdata(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        def _is_review_itemtype(value: str | None) -> bool:
            return bool(value and "Review" in value)

        for el in soup.find_all(attrs={"itemtype": _is_review_itemtype}):  # type: ignore[call-overload]
            author = self._text(el, '[itemprop="author"]')
            review_body = self._text(el, '[itemprop="reviewBody"]')
            title = self._text(el, '[itemprop="name"]')

            rating = None
            rating_el = el.select_one('[itemprop="ratingValue"]')
            if rating_el:
                rating_text = rating_el.get("content") or rating_el.get_text(strip=True)
                if rating_text:
                    with contextlib.suppress(ValueError, TypeError):
                        rating = float(str(rating_text))

            date = self._text(el, '[itemprop="datePublished"]')

            if review_body or title or author:
                display_title = title if title else f"Review from {author}" if author else "Review"
                result.reviews.append(
                    {
                        "title": display_title[:300],
                        "author": author,
                        "body": review_body[:1000] if review_body else None,
                        "rating": rating,
                        "publish_date": date[:10] if date and len(date) >= 10 else date,
                        "source_url": url,
                        "source": "microdata",
                    }
                )

    def _extract_from_review_sections(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        for heading in soup.select("h1, h2, h3, h4, h5, h6"):
            text = heading.get_text(strip=True).lower()
            if not any(kw in text for kw in _REVIEW_HEADING_KW):
                continue

            section = self._collect_section(heading)
            if not section:
                continue

            # Look for review cards/blocks
            for card in section.select("div, article, section, li, blockquote"):
                self._extract_review_from_card(card, result, url)

    def _extract_review_from_card(self, card: Tag, result: ParsedResult, url: str) -> None:
        # Find review text
        text_el = card.select_one("p, .review-text, .body, blockquote, [class*='text']")
        if not text_el:
            return
        text = text_el.get_text(strip=True)
        if not text or len(text) < 10:
            return

        # Find author
        author_el = card.select_one(".author, .name, cite, strong, [class*='author']")
        author = author_el.get_text(strip=True) if author_el else None

        # Find rating
        rating = self._parse_rating(card)

        # Find title
        title_el = card.select_one("h2, h3, h4, h5, .title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else None

        # Deduplicate
        if any(r.get("body") == text for r in result.reviews):
            return

        result.reviews.append(
            {
                "title": title[:300] if title else f"Review from {author}" if author else "Review",
                "author": author,
                "body": text[:1000],
                "rating": rating,
                "source_url": url,
                "source": "section_heuristic",
            }
        )

    def _extract_from_blockquotes(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        for bq in soup.select("blockquote"):
            text = bq.get_text(strip=True)
            if not text or len(text) < 20:
                continue

            # Check if it's in a review section
            parent_section = bq.find_parent(["section", "article", "div"])
            in_review_section = False
            if parent_section:
                heading = parent_section.select_one("h1, h2, h3, h4, h5, h6")
                if heading:
                    heading_text = heading.get_text(strip=True).lower()
                    in_review_section = any(kw in heading_text for kw in _REVIEW_HEADING_KW)

            if not in_review_section:
                continue

            # Find attribution
            author = None
            cite_el = bq.select_one("cite, .author, .attribution")
            if cite_el:
                author = cite_el.get_text(strip=True)

            if any(r.get("body") == text for r in result.reviews):
                return

            result.reviews.append(
                {
                    "title": f"Testimonial from {author}" if author else "Testimonial",
                    "author": author,
                    "body": text[:1000],
                    "rating": None,
                    "source_url": url,
                    "source": "blockquote",
                }
            )

    def _parse_rating(self, element: Tag) -> float | None:
        # Try numeric rating patterns
        text = element.get_text(" ", strip=True)
        match = _RATING_PATTERN.search(text)
        if match:
            groups = match.groups()
            if groups[0] and groups[1]:
                try:
                    return float(groups[0])
                except ValueError:
                    pass
            if groups[2]:
                try:
                    return float(groups[2])
                except ValueError:
                    pass
            if groups[3] and groups[4]:
                try:
                    return float(groups[3])
                except ValueError:
                    pass

        # Try star characters
        stars = text.count("★")
        half_stars = text.count("☆")
        if stars or half_stars:
            return float(stars + half_stars * 0.5)

        # Try itemprop rating
        rating_el = element.select_one('[itemprop="ratingValue"]')
        if rating_el:
            content_val = rating_el.get("content")
            text_val = rating_el.get_text(strip=True)
            rating_text = str(content_val) if content_val else text_val
            if rating_text:
                try:
                    return float(rating_text)
                except (ValueError, TypeError):
                    pass

        return None

    def _collect_section(self, heading: Tag) -> Tag | None:
        heading_level = int(heading.name[1]) if heading.name and heading.name[0] == "h" else 3
        container = heading.parent
        if not container:
            return None

        collecting = False
        elements: list[Tag] = []
        for sibling in container.children:
            if not isinstance(sibling, Tag):
                continue
            if sibling is heading:
                collecting = True
                continue
            if collecting:
                if sibling.name and sibling.name[0] == "h":
                    try:
                        sib_level = int(sibling.name[1])
                        if sib_level <= heading_level:
                            break
                    except (ValueError, IndexError):
                        pass
                elements.append(sibling)

        if not elements:
            return None

        wrapper = BeautifulSoup("", "html.parser").new_tag("div")
        for el in elements:
            wrapper.append(el)
        return wrapper
