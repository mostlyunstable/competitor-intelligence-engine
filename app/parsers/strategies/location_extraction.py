"""Location & Service Area Extraction — offices, coverage, cities, regions.

Detects location data from:
  - Schema.org PostalAddress microdata
  - JSON-LD: Organization.address, ServiceArea
  - Semantic HTML: <address> elements, city/state lists
  - Section headings: "service areas", "coverage", "where we serve", "locations"
  - Lists of city/state names under coverage headings

No company-specific selectors. No class name dependencies.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

# Heading keywords for service area / location sections
_LOCATION_HEADING_KW = frozenset(
    {
        "locations",
        "office",
        "offices",
        "service areas",
        "coverage",
        "where we serve",
        "areas served",
        "service area",
        "coverage area",
        "regions",
        "cities",
        "neighbourhoods",
        "neighborhoods",
        "find us",
        "visit us",
        "contact us",
        "our offices",
        "serving",
        "serving areas",
    }
)

# Heading keywords that indicate coverage (different from physical locations)
_COVERAGE_HEADING_KW = frozenset(
    {
        "service areas",
        "coverage",
        "areas served",
        "where we serve",
        "coverage area",
        "serving",
        "serving areas",
        "our reach",
    }
)


class LocationExtractionStrategy(ParsingStrategy):
    """Extracts office locations and service coverage areas."""

    @property
    def name(self) -> str:
        return "location_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_from_jsonld(soup, result, url)
        self._extract_from_microdata(soup, result, url)
        self._extract_from_address_elements(soup, result, url)
        self._extract_from_location_sections(soup, result, url)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._extract_from_jsonld(soup, result, url)
            self._extract_from_microdata(soup, result, url)
            self._extract_from_address_elements(soup, result, url)
            if seg.segment_type in ("about", "contact", "footer", "hero", "unknown"):
                self._extract_from_location_sections(soup, result, url)
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
        raw_type if isinstance(raw_type, str) else " ".join(raw_type)

        # Extract address
        address = item.get("address")
        if isinstance(address, dict):
            self._add_address_from_dict(address, result, url)
        elif isinstance(address, str) and address.strip():
            self._add_location(result, address.strip(), "json_ld")

        # Extract geo coordinates
        geo = item.get("geo")
        if isinstance(geo, dict):
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            if lat and lon:
                # Try to find the most recent location and add coordinates
                for loc in reversed(result.locations):
                    if not loc.get("latitude"):
                        loc["latitude"] = float(lat)
                        loc["longitude"] = float(lon)
                        break

        # Extract service area
        service_area = item.get("serviceArea")
        if isinstance(service_area, dict):
            self._process_service_area(service_area, result)
        elif isinstance(service_area, list):
            for area in service_area:
                if isinstance(area, dict):
                    self._process_service_area(area, result)

        # Process hasPart for multi-location organizations
        for part in item.get("hasPart", []):
            if isinstance(part, dict):
                self._process_jsonld_item(part, result, url)

        # Process @graph
        for graph_item in item.get("@graph", []):
            if isinstance(graph_item, dict):
                self._process_jsonld_item(graph_item, result, url)

    def _process_service_area(self, area: dict[str, Any], result: ParsedResult) -> None:
        name = area.get("name", "")
        geo_type = area.get("@type", "")

        if "GeoCircle" in str(geo_type) or "GeoRadius" in str(geo_type):
            description = area.get("description", "")
            if description:
                self._add_location(
                    result, str(description), "json_ld_service_area", area_type="radius"
                )
        elif (
            "AdministrativeArea" in str(geo_type)
            or "City" in str(geo_type)
            or "State" in str(geo_type)
        ):
            if name:
                area_type = "city" if "City" in str(geo_type) else "region"
                self._add_location(result, str(name), "json_ld_service_area", area_type=area_type)

    def _add_address_from_dict(
        self, address: dict[str, Any], result: ParsedResult, url: str
    ) -> None:
        street = address.get("streetAddress", "")
        city = address.get("addressLocality", "")
        region = address.get("addressRegion", "")
        postal = address.get("postalCode", "")
        country = address.get("addressCountry", "")
        if isinstance(country, dict):
            country = country.get("name", "")

        parts = [p for p in (street, city, region, postal, country) if p]
        if parts:
            name = ", ".join(str(p) for p in parts)
            self._add_location(
                result,
                name,
                "json_ld",
                street=str(street) if street else None,
                city=str(city) if city else None,
                region=str(region) if region else None,
                postal_code=str(postal) if postal else None,
                country=str(country) if country else None,
            )

    def _extract_from_microdata(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        def _is_postal_address(value: str | None) -> bool:
            return bool(value and "PostalAddress" in value)

        for el in soup.find_all(attrs={"itemtype": _is_postal_address}):  # type: ignore[call-overload]
            street = self._text(el, '[itemprop="streetAddress"]')
            city = self._text(el, '[itemprop="addressLocality"]')
            region = self._text(el, '[itemprop="addressRegion"]')
            postal = self._text(el, '[itemprop="postalCode"]')
            country = self._text(el, '[itemprop="addressCountry"]')

            parts = [p for p in (street, city, region, postal, country) if p]
            if parts:
                name = ", ".join(parts)
                if not any(loc.get("name") == name for loc in result.locations):
                    result.locations.append(
                        {
                            "name": name,
                            "street": street,
                            "city": city,
                            "region": region,
                            "postal_code": postal,
                            "country": country,
                            "type": "physical",
                            "source": "microdata",
                        }
                    )

    def _extract_from_address_elements(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        for address in soup.find_all("address"):
            text = address.get_text(separator=", ", strip=True)
            if (
                text
                and 10 < len(text) < 200
                and not any(loc.get("name") == text for loc in result.locations)
            ):
                result.locations.append(
                    {
                        "name": text,
                        "type": "physical",
                        "source": "semantic_address",
                    }
                )

    def _extract_from_location_sections(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        for heading in soup.select("h1, h2, h3, h4, h5, h6"):
            text = heading.get_text(strip=True).lower()
            if not any(kw in text for kw in _LOCATION_HEADING_KW):
                continue

            is_coverage = any(kw in text for kw in _COVERAGE_HEADING_KW)

            # Collect sibling content after this heading
            section = self._collect_section(heading)
            if not section:
                continue

            # Look for lists of locations
            for ul in section.select("ul, ol"):
                for li in ul.select("li"):
                    li_text = li.get_text(strip=True)
                    if li_text and self._looks_like_location(li_text):
                        area_type = "coverage" if is_coverage else "city"
                        self._add_location(
                            result, li_text, "section_heuristic", area_type=area_type
                        )

            # Look for comma-separated location lists in paragraphs
            for p in section.select("p"):
                p_text = p.get_text(strip=True)
                if p_text and "," in p_text:
                    parts = [part.strip() for part in p_text.split(",")]
                    for part in parts:
                        if self._looks_like_location(part):
                            area_type = "coverage" if is_coverage else "city"
                            self._add_location(
                                result, part, "section_heuristic", area_type=area_type
                            )

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

    @staticmethod
    def _looks_like_location(text: str) -> bool:
        """Heuristic: does this text look like a location name?

        Rejects navigation items and CTA text. Accepts city names,
        addresses, state abbreviations, and coverage areas.
        """
        if len(text) < 3 or len(text) > 100:
            return False
        lower = text.lower()

        # Reject common navigation / CTA patterns
        nav_patterns = frozenset(
            {
                "learn more",
                "read more",
                "click here",
                "sign up",
                "log in",
                "register",
                "subscribe",
                "contact us",
                "get started",
                "try free",
                "view all",
                "see all",
                "show more",
                "load more",
                "home",
                "about us",
                "our story",
                "careers",
                "press",
                "investors",
                "terms",
                "privacy",
                "policy",
                "legal",
                "copyright",
                "faq",
                "help",
                "support",
                "blog",
                "news",
                "real estate plans",
                "home warranty cost",
                "warranty renewal",
                "promos & discounts",
                "member testimonials",
                "site map",
                "frontdoor",
                "hsa home",
                "landmark",
                "oneguard",
            }
        )
        if lower in nav_patterns:
            return False

        # Reject if it's a sentence (contains "we ", "our ", "the ", etc.)
        sentence_starters = frozenset({"we ", "our ", "the ", "this ", "that ", "it "})
        if any(lower.startswith(s) for s in sentence_starters):
            return False

        # Reject items with nav-like suffixes
        nav_suffixes = ("details", "cost", "renewal", "more", "info", "options", "plans")
        if lower.endswith(nav_suffixes):
            return False

        # Reject items containing nav/CTA keywords
        nav_keywords = frozenset(
            {
                "warranty",
                "coverage",
                "plan",
                "cost",
                "price",
                "renewal",
                "details",
                "options",
                "learn",
                "read",
                "click",
                "sign",
                "subscribe",
                "register",
                "terms",
                "privacy",
                "policy",
            }
        )
        if any(kw in lower for kw in nav_keywords):
            return False

        # Accept if contains comma (likely "City, State" format)
        if "," in text:
            return True

        # Accept if 2+ words and all capitalized (proper nouns = place names)
        words_list = text.split()
        if len(words_list) >= 2:
            return all(w[0].isupper() for w in words_list if w and w[0].isalpha())

        # Single word: only accept if it looks like a city name (3+ chars, no special chars)
        return len(words_list) == 1 and len(text) >= 3 and text.isalpha()

    @staticmethod
    def _add_location(
        result: ParsedResult,
        name: str,
        source: str,
        area_type: str = "physical",
        street: str | None = None,
        city: str | None = None,
        region: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
    ) -> None:
        name = name.strip()[:200]
        if not name:
            return
        # Deduplicate by name
        if any(loc.get("name") == name for loc in result.locations):
            return
        entry: dict[str, Any] = {
            "name": name,
            "type": area_type,
            "source": source,
        }
        if street:
            entry["street"] = street
        if city:
            entry["city"] = city
        if region:
            entry["region"] = region
        if postal_code:
            entry["postal_code"] = postal_code
        if country:
            entry["country"] = country
        result.locations.append(entry)
