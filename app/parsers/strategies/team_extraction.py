"""Team Extraction — extract team members, leadership, and founders.

Detects team information from:
  - Schema.org Person microdata (itemprop="name" + itemprop="jobTitle")
  - JSON-LD Person/Organization.member types
  - Semantic HTML patterns: heading + role chains, card grids
  - Section headings: "team", "leadership", "staff", "people", "founders"

No company-specific selectors. No class name dependencies.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

# Keywords that indicate a team/people section
_TEAM_HEADING_KW = frozenset(
    {
        "team",
        "leadership",
        "staff",
        "people",
        "founders",
        "our people",
        "meet the team",
        "our team",
        "the team",
        "who we are",
        "about us",
        "management",
        "executives",
        "directors",
        "leadership team",
        "senior leadership",
        "founding team",
        "board of directors",
    }
)

# Keywords that indicate a role/title
_ROLE_KW = re.compile(
    r"\b(ceo|cto|cfo|coo|cmo|cro|co-founder|founder|president|vp|vice president|"
    r"director|manager|lead|head|principal|senior|junior|associate|"
    r"engineer|developer|designer|architect|consultant|specialist|"
    r"analyst|coordinator|administrator|officer|partner|advisor|"
    r"chief|executive|operating|marketing|sales|finance|technology|"
    r"engineering|product|design|human resources|hr|legal|operations)\b",
    re.IGNORECASE,
)


class TeamExtractionStrategy(ParsingStrategy):
    """Extracts team members, leadership, and founders."""

    @property
    def name(self) -> str:
        return "team_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_from_jsonld(soup, result, url)
        self._extract_from_microdata(soup, result, url)
        self._extract_from_team_sections(soup, result, url)
        self._extract_from_card_patterns(soup, result, url)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._extract_from_jsonld(soup, result, url)
            self._extract_from_microdata(soup, result, url)
            if seg.segment_type in ("about", "hero", "unknown"):
                self._extract_from_team_sections(soup, result, url)
                self._extract_from_card_patterns(soup, result, url)
        return result

    def _extract_from_jsonld(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                import json

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

        # Process Person types
        if "Person" in item_type:
            self._add_person_from_jsonld(item, result, url)

        # Process employee/founder/member arrays
        for key in ("employee", "founder", "member", "author"):
            members = item.get(key)
            if isinstance(members, list):
                for m in members:
                    if isinstance(m, dict):
                        self._add_person_from_jsonld(m, result, url)
            elif isinstance(members, dict):
                self._add_person_from_jsonld(members, result, url)

        # Recurse into @graph
        for graph_item in item.get("@graph", []):
            if isinstance(graph_item, dict):
                self._process_jsonld_item(graph_item, result, url)

    def _add_person_from_jsonld(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        name = item.get("name", "")
        if not name or len(str(name)) > 100:
            return
        job_title = item.get("jobTitle", "")
        description = item.get("description", "")
        image = item.get("image", "")
        if isinstance(image, dict):
            image = image.get("url", "")
        same_as = item.get("sameAs", "")
        if isinstance(same_as, list):
            same_as = next(
                (s for s in same_as if isinstance(s, str) and "linkedin" in s.lower()), ""
            )

        # Avoid duplicates
        if any(m.get("name") == name for m in result.team):
            return

        result.team.append(
            {
                "name": str(name),
                "title": str(job_title) if job_title else None,
                "bio": str(description) if description else None,
                "image_url": urljoin(url, str(image)) if image else None,
                "linkedin_url": (
                    str(same_as) if same_as and "linkedin" in str(same_as).lower() else None
                ),
                "source": "json_ld",
            }
        )

    def _extract_from_microdata(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for el in soup.select('[itemtype*="Person"]'):
            name = self._text(el, '[itemprop="name"]')
            job_title = self._text(el, '[itemprop="jobTitle"]')
            description = self._text(el, '[itemprop="description"]')
            image_el = el.select_one('[itemprop="image"]')
            image_url = None
            if image_el:
                image_url = image_el.get("src") or image_el.get("content")
            same_as_el = el.select_one('[itemprop="sameAs"]')
            linkedin_url = None
            if same_as_el:
                href = same_as_el.get("href", "")
                if "linkedin" in str(href).lower():
                    linkedin_url = str(href)

            if name and len(name) < 100 and not any(m.get("name") == name for m in result.team):
                result.team.append(
                    {
                        "name": name,
                        "title": job_title,
                        "bio": description,
                        "image_url": urljoin(url, str(image_url)) if image_url else None,
                        "linkedin_url": linkedin_url,
                        "source": "microdata",
                    }
                )

    def _extract_from_team_sections(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        for heading in soup.select("h1, h2, h3, h4, h5, h6"):
            text = heading.get_text(strip=True).lower()
            if not any(kw in text for kw in _TEAM_HEADING_KW):
                continue

            # Walk siblings after this heading to find team cards
            section = self._collect_section_content(heading)
            if not section:
                continue

            # Look for card-like patterns within the section
            for card in section.select("div, article, section, li, figure"):
                self._extract_person_from_card(card, result, url)

    def _collect_section_content(self, heading: Tag) -> Tag | None:
        """Collect sibling elements after a heading until the next heading of same or higher level."""
        heading_level = int(heading.name[1]) if heading.name and heading.name[0] == "h" else 3
        container = heading.parent
        if not container:
            return None

        # Find all siblings between this heading and the next same-or-higher-level heading
        collecting = False
        elements: list[Tag] = []
        for sibling in container.children:
            if not isinstance(sibling, Tag):
                continue
            if sibling is heading:
                collecting = True
                continue
            if collecting:
                # Stop at next heading of same or higher level
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

        # Wrap in a temporary container
        wrapper = BeautifulSoup("", "lxml").new_tag("div")
        for el in elements:
            wrapper.append(el)
        return wrapper

    def _extract_person_from_card(self, card: Tag, result: ParsedResult, url: str) -> None:
        """Extract a person from a card-like element."""
        # Find the name (heading or strong element)
        name_el = card.select_one("h2, h3, h4, h5, h6, strong, .name, [class*='name']")
        if not name_el:
            return
        name = name_el.get_text(strip=True)
        if not name or len(name) > 100 or len(name) < 2:
            return

        # Skip if this looks like a service/product card, not a person
        if any(kw in name.lower() for kw in ("service", "plan", "pricing", "product", "package")):
            return

        # Find role/title
        role = None
        for role_selector in [
            ".role",
            ".title",
            ".job-title",
            ".position",
            ".designation",
            "p",
            "span",
        ]:
            role_el = card.select_one(role_selector)
            if role_el:
                role_text = role_el.get_text(strip=True)
                if role_text and _ROLE_KW.search(role_text):
                    role = role_text
                    break

        # Find image
        img_el = card.select_one("img")
        image_url = None
        if img_el:
            src = img_el.get("src", "")
            if src:
                image_url = urljoin(url, str(src))

        # Find LinkedIn
        linkedin_url = None
        for a in card.select("a[href]"):
            href = str(a.get("href", ""))
            if "linkedin" in href.lower():
                linkedin_url = href
                break

        # Find bio
        bio = None
        bio_el = card.select_one("p, .bio, .description, [class*='bio']")
        if bio_el:
            bio_text = bio_el.get_text(strip=True)
            if bio_text and bio_text != role and len(bio_text) > 10:
                bio = bio_text[:500]

        if not any(m.get("name") == name for m in result.team):
            result.team.append(
                {
                    "name": name,
                    "title": role,
                    "bio": bio,
                    "image_url": image_url,
                    "linkedin_url": linkedin_url,
                    "source": "section_heuristic",
                }
            )

    def _extract_from_card_patterns(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        """Detect repeated card patterns that look like team grids."""
        for container in soup.select("div, section, main, ul"):
            children = [
                c
                for c in container.children
                if isinstance(c, Tag) and c.name in ("div", "li", "article", "section")
            ]
            if len(children) < 2:
                continue

            # Check if most children look like person cards
            person_cards = 0
            for child in children:
                heading = child.select_one("h2, h3, h4, h5, h6, strong")
                if heading:
                    heading_text = heading.get_text(strip=True)
                    if heading_text and len(heading_text) < 100:
                        person_cards += 1

            if person_cards < len(children) // 2:
                continue

            for child in children:
                self._extract_person_from_card(child, result, url)
