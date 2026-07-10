from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

_BC_NAV_KWS = frozenset(
    {
        "breadcrumb",
        "breadcrumb trail",
        "bread crumbs",
        "you are here",
        "current page",
        "navigation path",
    }
)

_SEPARATOR_RE = re.compile(r"[>»/|→▶⋙]")


def _parse_jsonld_breadcrumb(soup: BeautifulSoup) -> list[str] | None:
    """Extract breadcrumb path from JSON-LD BreadcrumbList."""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            raw = script.string or ""
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") in (
                "BreadcrumbList",
                "http://schema.org/BreadcrumbList",
                "https://schema.org/BreadcrumbList",
            ):
                elements = item.get("itemListElement", [])
                if isinstance(elements, list) and elements:
                    path: list[str] = []
                    for el in elements:
                        if isinstance(el, dict):
                            name = ""
                            if isinstance(el.get("item"), dict):
                                name = el["item"].get("name", "")
                            if not name:
                                name = el.get("name", "")
                            if isinstance(name, str) and name.strip():
                                path.append(name.strip())
                    if len(path) >= 2:
                        return path
    return None


def _parse_microdata_breadcrumb(soup: BeautifulSoup) -> list[str] | None:
    """Extract breadcrumb path from schema.org BreadcrumbList microdata."""
    bc_list = soup.find(attrs={"itemtype": re.compile(r"BreadcrumbList", re.I)})  # type: ignore[call-overload]
    if not bc_list:
        return None
    items = bc_list.find_all(attrs={"itemprop": re.compile(r"itemListElement|item", re.I)})
    if not items:
        items = bc_list.find_all("li")
    path: list[str] = []
    for item in items:
        name_el = item.find(attrs={"itemprop": "name"})
        text = name_el.get_text(strip=True) if name_el else item.get_text(strip=True)
        if text and text not in path:
            path.append(text)
    return path if len(path) >= 2 else None


def _parse_nav_breadcrumb(soup: BeautifulSoup) -> list[str] | None:
    """Extract breadcrumb path from <nav> with breadcrumb aria-label."""
    for nav in soup.find_all("nav"):
        aria = str(nav.get("aria-label") or "").lower()
        label = str(nav.get("label") or "").lower()
        combined = aria + " " + label
        if not any(kw in combined for kw in _BC_NAV_KWS):
            continue
        path = _extract_list_path(nav)
        if path and len(path) >= 2:
            return path
    return None


def _parse_ordered_list(soup: BeautifulSoup) -> list[str] | None:
    """Extract breadcrumb path from <ol> elements that look like breadcrumbs."""
    for ol in soup.find_all("ol"):
        aria = str(ol.get("aria-label") or "").lower()
        if aria and any(kw in aria for kw in _BC_NAV_KWS):
            path = _extract_list_path(ol)
            if path and len(path) >= 2:
                return path
        path = _extract_list_path(ol)
        if path and _looks_like_breadcrumb(path, ol):
            return path
    return None


def _parse_separator_pattern(soup: BeautifulSoup) -> list[str] | None:
    """Detect inline breadcrumb pattern: elements separated by > or /."""
    for container in soup.find_all(["div", "p", "span"]):
        text = container.get_text(" ", strip=True)
        if not text or len(text) > 300:
            continue
        if _SEPARATOR_RE.search(text):
            parts = _SEPARATOR_RE.split(text)
            parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
            if len(parts) >= 2:
                links = container.find_all("a")
                if links and len(links) >= 1:
                    return parts
    return None


def _extract_list_path(container: Tag) -> list[str]:
    """Extract text path from a list container (ol/ul)."""
    items = container.find_all("li", recursive=True)
    if not items:
        for a in container.find_all("a"):
            text = a.get_text(strip=True)
            if text:
                return [text]
        return []
    path: list[str] = []
    for li in items:
        text = li.get_text(strip=True)
        if text and (not path or text != path[-1]):
            path.append(text)
    return path


def _looks_like_breadcrumb(path: list[str], container: Tag) -> bool:
    """Heuristic: breadcrumbs have short labels, mostly links, hierarchical structure."""
    if len(path) < 2:
        return False
    links = container.find_all("a")
    short_labels = all(len(p) < 60 for p in path)
    has_links = len(links) >= len(path) - 1
    return short_labels and has_links


def _categorize_from_breadcrumb(path: list[str]) -> list[dict[str, Any]]:
    """Derive service categorization from breadcrumb hierarchy."""
    results: list[dict[str, Any]] = []
    if len(path) < 3:
        return results
    leaf = path[-1]
    parent = path[-2] if len(path) >= 2 else ""
    if len(leaf) < 2:
        return results
    _skip_tokens = {"home", "page", "breadcrumb", "you are here"}
    if leaf.lower() in _skip_tokens or parent.lower() in _skip_tokens:
        return results
    results.append(
        {
            "name": leaf,
            "description": " → ".join(path[1:]),
            "category": parent,
            "starting_price": None,
            "currency": "USD",
            "estimated_duration": None,
            "source": "breadcrumb",
        }
    )
    return results


class BreadcrumbExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "breadcrumb_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()

        path = _parse_jsonld_breadcrumb(soup)
        if not path:
            path = _parse_microdata_breadcrumb(soup)
        if not path:
            path = _parse_nav_breadcrumb(soup)
        if not path:
            path = _parse_ordered_list(soup)
        if not path:
            path = _parse_separator_pattern(soup)

        if path:
            result.strategy_results["__breadcrumb__"] = path

            result.content.append(
                {
                    "title": "Breadcrumb Path",
                    "author": None,
                    "publish_date": None,
                    "url": url,
                    "summary": " → ".join(path),
                    "content_type": "breadcrumb",
                }
            )

            for svc in _categorize_from_breadcrumb(path):
                existing = {s.get("name") for s in result.services}
                if svc["name"] not in existing:
                    result.services.append(svc)

        return result

    def parse_segments(self, segments: list[Any], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            if isinstance(seg, Tag):
                sub = self.parse(BeautifulSoup(str(seg), "html.parser"), url)
            else:
                sub_soup = (
                    seg.to_soup()
                    if hasattr(seg, "to_soup")
                    else BeautifulSoup(str(seg), "html.parser")
                )
                sub = self.parse(sub_soup, url)
            for svc in sub.services:
                existing = {s.get("name") for s in result.services}
                if svc["name"] not in existing:
                    result.services.append(svc)
            if "__breadcrumb__" in sub.strategy_results:
                result.strategy_results["__breadcrumb__"] = sub.strategy_results["__breadcrumb__"]
            for c in sub.content:
                existing = {c2.get("summary") for c2 in result.content}
                if c.get("summary") not in existing:
                    result.content.append(c)
        return result
