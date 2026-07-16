"""Trust Signal Extraction — certifications, awards, guarantees, badges.

Detects trust signals from:
  - JSON-LD: Organization.award, Organization.certification
  - Schema.org microdata: itemprop="award", itemprop="hasCredential"
  - Badge/icon sections: ul > li with img + text
  - Text patterns: "licensed", "insured", "certified", "accredited", "award"
  - Section headings: "certifications", "awards", "accreditations", "badges"
  - Guarantee/warranty policies

No company-specific selectors. No class name dependencies.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

# Heading keywords that indicate a trust signals section
_TRUST_HEADING_KW = frozenset(
    {
        "certifications",
        "certification",
        "awards",
        "recognition",
        "accreditations",
        "accreditation",
        "badges",
        "trust",
        "trust badges",
        "licensed",
        "insured",
        "bonded",
        "compliance",
        "why choose us",
        "our guarantees",
        "guarantees",
        "warranties",
        "as featured in",
        "featured in",
        "partners",
        "partnerships",
        "affiliations",
        "memberships",
        "associations",
    }
)

# Patterns for trust-related content
_CERT_PATTERN = re.compile(
    r"\b(iso\s?\d{3,4}|soc\s?[123]|gdpr|hipaa|pci[\s-]dss|"
    r"bbb|better business|epa|osha|ansi|ul[\s-]listed|"
    r"certified|accredited|licensed|insured|bonded|"
    r"award[\s-]winning|top[\s-]rated|best[\s-]of|"
    r"guarantee|warranty|satisfaction)\b",
    re.IGNORECASE,
)

# Image alt text patterns that indicate badges/certifications
_BADGE_ALT_PATTERN = re.compile(
    r"(certified|award|badge|accredited|licensed|insured|bonded|"
    r"partner|member|compliance|iso|soc|bbb|top rated|best of)",
    re.IGNORECASE,
)


class TrustSignalExtractionStrategy(ParsingStrategy):
    """Extracts trust signals: certifications, awards, guarantees, badges."""

    @property
    def name(self) -> str:
        return "trust_signal_extraction"

    @property
    def weight(self) -> float:
        return 0.10

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_from_jsonld(soup, result, url)
        self._extract_from_microdata(soup, result, url)
        self._extract_badges_from_images(soup, result, url)
        self._extract_from_trust_sections(soup, result)
        self._extract_from_text_patterns(soup, result)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._extract_from_jsonld(soup, result, url)
            self._extract_from_microdata(soup, result, url)
            self._extract_badges_from_images(soup, result, url)
            if seg.segment_type in ("about", "footer", "hero", "unknown"):
                self._extract_from_trust_sections(soup, result)
                self._extract_from_text_patterns(soup, result)
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
                    self._process_jsonld_item(item, result)

    def _process_jsonld_item(self, item: dict[str, Any], result: ParsedResult) -> None:
        # Extract awards
        awards = item.get("award", [])
        if isinstance(awards, str):
            awards = [awards]
        for award in awards:
            if isinstance(award, str) and award.strip():
                self._add_signal(result, "award", award.strip())

        # Extract certifications
        certs = item.get("hasCredential", [])
        if isinstance(certs, dict):
            certs = [certs]
        elif isinstance(certs, str):
            certs = [{"name": certs}]
        for cert in certs:
            if isinstance(cert, dict):
                cert_name = cert.get("name", "")
                if cert_name:
                    self._add_signal(result, "certification", str(cert_name))

        # Recurse into @graph
        for graph_item in item.get("@graph", []):
            if isinstance(graph_item, dict):
                self._process_jsonld_item(graph_item, result)

    def _extract_from_microdata(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for el in soup.select("[itemprop='award']"):
            text = el.get_text(strip=True) or el.get("content", "")
            if text and len(str(text)) < 200:
                self._add_signal(result, "award", str(text))

        for el in soup.select("[itemprop='hasCredential'], [itemprop='credential']"):
            text = el.get_text(strip=True) or el.get("content", "")
            if text and len(str(text)) < 200:
                self._add_signal(result, "certification", str(text))

    def _extract_badges_from_images(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        for img in soup.select("img"):
            alt = str(img.get("alt", ""))
            title = str(img.get("title", ""))
            text = f"{alt} {title}".strip()
            if not text:
                continue
            if _BADGE_ALT_PATTERN.search(text):
                # Determine the category
                category = self._classify_signal(text)
                # Try to get the parent text for more context
                parent = img.find_parent(["li", "div", "a", "figure"])
                full_text = parent.get_text(strip=True) if parent else text
                if len(full_text) > 200:
                    full_text = full_text[:200]
                self._add_signal(result, category, full_text if full_text else text)

    def _extract_from_trust_sections(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for heading in soup.select("h1, h2, h3, h4, h5, h6"):
            text = heading.get_text(strip=True).lower()
            if not any(kw in text for kw in _TRUST_HEADING_KW):
                continue

            # Collect sibling content after this heading
            section = self._collect_section(heading)
            if not section:
                continue

            # Look for list items (common for badge/cert lists)
            for li in section.select("li"):
                li_text = li.get_text(strip=True)
                if li_text and 5 < len(li_text) < 200:
                    category = self._classify_signal(li_text)
                    self._add_signal(result, category, li_text)

            # Look for standalone text blocks
            for p in section.select("p, span, div"):
                p_text = p.get_text(strip=True)
                if p_text and 10 < len(p_text) < 200 and _CERT_PATTERN.search(p_text):
                    category = self._classify_signal(p_text)
                    self._add_signal(result, category, p_text)

    def _extract_from_text_patterns(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        """Scan full page text for trust signal patterns."""
        body = soup.get_text(" ", strip=True)
        # Find short text segments matching trust patterns
        for match in _CERT_PATTERN.finditer(body):
            start = max(0, match.start() - 30)
            end = min(len(body), match.end() + 30)
            segment = body[start:end].strip()
            if 5 < len(segment) < 150:
                category = self._classify_signal(segment)
                self._add_signal(result, category, segment)

    def _collect_section(self, heading: Tag) -> Tag | None:
        """Collect sibling elements after a heading until the next heading."""
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

        wrapper = BeautifulSoup("", "lxml").new_tag("div")
        for el in elements:
            wrapper.append(el)
        return wrapper

    @staticmethod
    def _classify_signal(text: str) -> str:
        lower = text.lower()
        if "award" in lower or "winning" in lower or "best of" in lower or "top rated" in lower:
            return "award"
        if "guarantee" in lower or "warranty" in lower or "satisfaction" in lower:
            return "guarantee"
        if "partner" in lower or "partnership" in lower or "affiliate" in lower:
            return "partnership"
        if "license" in lower or "licensed" in lower:
            return "license"
        if "insured" in lower or "insurance" in lower:
            return "insurance"
        if "bonded" in lower:
            return "bonded"
        return "certification"

    @staticmethod
    def _add_signal(result: ParsedResult, category: str, name: str) -> None:
        name = name.strip()[:200]
        if not name:
            return
        # Deduplicate by type+name combination
        if any(s.get("type") == category and s.get("name") == name for s in result.trust_signals):
            return
        result.trust_signals.append(
            {
                "type": category,
                "name": name,
                "source": "trust_signal_extraction",
            }
        )
