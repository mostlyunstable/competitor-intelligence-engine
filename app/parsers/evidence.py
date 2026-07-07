"""Evidence extraction utilities for parsing traceability.

Provides helper functions to extract DOM path, XPath, and HTML snippet
from a BeautifulSoup Tag, enabling field-level provenance tracking.
"""

from __future__ import annotations

from typing import Any

from bs4 import Tag

MAX_SNIPPET_LENGTH = 300


def dom_path(tag: Tag) -> str:
    """Build a CSS-selector-like DOM path from root to this tag.

    Example: html > body > div.content > table#pricing > tbody > tr:nth-of-type(2) > td
    """
    parts: list[str] = []
    current: Tag | None = tag
    while current is not None and current.name not in ("[document]", "html"):
        selector = current.name
        if current.get("id"):
            selector = f"{selector}#{_first_id(current)}"
        class_attr = current.get("class")
        if class_attr:
            if isinstance(class_attr, str):
                classes = [class_attr]
            else:
                classes = [str(c) for c in class_attr if c]
            if classes:
                selector = f"{selector}.{'.'.join(classes)}"
        # nth-of-type: find position among siblings with same tag
        parent = current.parent
        if parent and hasattr(parent, "children"):
            siblings = [c for c in parent.children if isinstance(c, Tag) and c.name == current.name]
            if len(siblings) > 1:
                pos = siblings.index(current) + 1
                selector = f"{selector}:nth-of-type({pos})"
        parts.append(selector)
        current = current.parent if isinstance(current.parent, Tag) else None
    parts.reverse()
    return " > ".join(parts) if parts else tag.name or "unknown"


def _first_id(tag: Tag) -> str:
    ids = tag.get("id")
    if isinstance(ids, str):
        return ids
    if isinstance(ids, list) and ids:
        return str(ids[0])
    return ""


def xpath(tag: Tag) -> str:
    """Build an XPath from root to this tag.

    Example: /html/body/div[2]/table[1]/tbody/tr[3]/td[1]
    """
    parts: list[str] = []
    current: Tag | None = tag
    while current is not None and current.name not in ("[document]", "html"):
        parent = current.parent
        if parent and hasattr(parent, "children"):
            siblings = [
                c
                for c in parent.children
                if isinstance(c, Tag) and c.name == current.name
            ]
            if len(siblings) > 1:
                pos = siblings.index(current) + 1
                parts.append(f"{current.name}[{pos}]")
            else:
                parts.append(current.name)
        else:
            parts.append(current.name)
        current = parent if isinstance(parent, Tag) else None
    parts.reverse()
    return "/" + "/".join(parts)


def html_snippet(tag: Tag, max_length: int = MAX_SNIPPET_LENGTH) -> str:
    """Return a truncated HTML string for this tag."""
    raw = str(tag)
    if len(raw) <= max_length:
        return raw
    return raw[:max_length] + "..."


def extract_evidence(tag: Tag | None, snippet_length: int = MAX_SNIPPET_LENGTH) -> dict[str, Any]:
    """Extract all evidence fields from a Tag.

    Returns a dict with keys: dom_path, xpath, html_snippet.
    All values are None if tag is None.
    """
    if tag is None:
        return {"dom_path": None, "xpath": None, "html_snippet": None}
    return {
        "dom_path": dom_path(tag),
        "xpath": xpath(tag),
        "html_snippet": html_snippet(tag, snippet_length),
    }
