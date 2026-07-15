"""Preprocessing — clean and normalize HTML before extraction.

Removes scripts, styles, tracking, ads, cookie banners, hidden elements,
duplicate DOM, empty nodes, and other noise.  Normalizes the DOM tree
so that downstream parsers get clean, semantically meaningful markup.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import BeautifulSoup
from bs4.element import Comment, Tag

# Elements that contribute no semantic content
_REMOVE_TAGS: set[str] = {
    "script",
    "style",
    "noscript",
    "iframe",
    "canvas",
    "svg",
    "math",
    "template",
    "slot",
}

# Tracking / analytics patterns (selectors)
_TRACKING_SELECTORS: list[str] = [
    "[src*='google-analytics']",
    "[src*='googletagmanager']",
    "[src*='facebook.net']",
    "[src*='fbq']",
    "[src*='gtag']",
    "[src*='doubleclick']",
    "[src*='adservice']",
    "[src*='scorecardresearch']",
    "[src*='quantserve']",
    "[id*='google_ads']",
    "[class*='advertisement']",
    "[class*='ad-container']",
    "[class*='cookie']",
    "[id*='cookie']",
    "[class*='consent']",
    "[id*='consent']",
    "[aria-label*='cookie']",
    # Cookie / consent banners
    "[class*='cmp-wrapper']",
    "[id*='cmp']",
    "[class*='gdpr']",
    "[class*='cc-banner']",
    "[class*='notice']",
]

# Hidden element detection
_HIDDEN_SELECTORS: list[str] = [
    "[hidden]",
    "[style*='display:none']",
    "[style*='display: none']",
    "[style*='visibility:hidden']",
    "[style*='visibility: hidden']",
    "[aria-hidden='true']",
    "[type='hidden']",
]

_EMPTY_BLOCK_RE = re.compile(r"^\s*$")


class Preprocessor:
    """Clean and normalize HTML before parsing."""

    # Maximum recursion depth for cleanup
    _MAX_PASSES: ClassVar[int] = 3

    def process(self, html: str) -> str:
        """Apply all preprocessing steps and return clean HTML."""
        soup = BeautifulSoup(html, "html.parser")
        if not soup.find():
            return html  # no valid HTML found

        self._expose_accessible_text(soup)

        for _ in range(self._MAX_PASSES):
            changed = False
            changed |= self._remove_tags(soup)
            changed |= self._remove_tracking(soup)
            changed |= self._remove_hidden(soup)
            changed |= self._remove_empty_nodes(soup)
            changed |= self._remove_comments(soup)
            changed |= self._remove_nav_duplicates(soup)
            changed |= self._remove_footer_duplicates(soup)
            changed |= self._flatten_nested_siblings(soup)
            if not changed:
                break

        return str(soup)

    @staticmethod
    def _remove_tags(soup: BeautifulSoup) -> bool:
        count = 0
        for tag in list(soup.find_all(_REMOVE_TAGS)):
            # Preserve JSON-LD / structured data scripts
            if tag.name == "script" and tag.get("type") in (
                "application/ld+json",
                "application/json",
            ):
                continue
            tag.decompose()
            count += 1
        return count > 0

    @staticmethod
    def _remove_tracking(soup: BeautifulSoup) -> bool:
        count = 0
        for selector in _TRACKING_SELECTORS:
            for el in soup.select(selector):
                el.decompose()
                count += 1
        return count > 0

    @staticmethod
    def _remove_hidden(soup: BeautifulSoup) -> bool:
        count = 0
        for selector in _HIDDEN_SELECTORS:
            for el in soup.select(selector):
                el.decompose()
                count += 1
        return count > 0

    @staticmethod
    def _remove_comments(soup: BeautifulSoup) -> bool:
        count = 0
        for comment in list(soup.find_all(string=lambda s: isinstance(s, Comment))):
            comment.extract()
            count += 1
        return count > 0

    @staticmethod
    def _remove_empty_nodes(soup: BeautifulSoup) -> bool:
        """Remove elements that contain only whitespace or nothing."""
        count = 0
        for el in list(soup.find_all()):
            if el.name in ("br", "hr", "img", "input", "meta", "link"):
                continue
            if el.name in ("html", "head", "body", "div", "span"):
                # Only remove these if they are truly empty (no children at all)
                contents = el.get_text(strip=True)
                if not contents and not el.find_all(True):
                    el.decompose()
                    count += 1
            else:
                contents = el.get_text(strip=True)
                if not contents:
                    el.decompose()
                    count += 1
        return count > 0

    @staticmethod
    def _remove_nav_duplicates(soup: BeautifulSoup) -> bool:
        """Remove duplicate navigation elements."""
        navs = soup.find_all("nav")
        if len(navs) <= 1:
            return False
        # Keep the first nav, remove subsequent ones that look the same
        texts: list[str] = []
        count = 0
        for nav in navs:
            t = nav.get_text(" ", strip=True)[:200]
            if t in texts:
                nav.decompose()
                count += 1
            else:
                texts.append(t)
        return count > 0

    @staticmethod
    def _remove_footer_duplicates(soup: BeautifulSoup) -> bool:
        """Remove duplicate footer elements."""
        footers = soup.find_all("footer")
        if len(footers) <= 1:
            return False
        count = 0
        texts: list[str] = []
        for footer in footers:
            t = footer.get_text(" ", strip=True)[:200]
            if t in texts:
                footer.decompose()
                count += 1
            else:
                texts.append(t)
        return count > 0

    @staticmethod
    def _flatten_nested_siblings(soup: BeautifulSoup) -> bool:
        """Flatten deeply nested same-tag wrappers (div > div > div)."""
        changed = False
        for el in list(soup.find_all()):
            children = list(el.children)
            if (
                len(children) == 1
                and isinstance(children[0], Tag)
                and children[0].name == el.name
                and not el.attrs  # parent has no meaningful attributes
            ):
                # Move grand-children up
                for child in list(children[0].children):
                    el.insert(len(list(el.children)) - 1, child)
                children[0].decompose()
                changed = True
        return changed

    @staticmethod
    def _expose_accessible_text(soup: BeautifulSoup) -> bool:
        """Expose aria-label and alt text as real text nodes for downstream extraction."""
        count = 0

        # Expose aria-label
        for el in soup.find_all(attrs={"aria-label": True}):
            label = el.get("aria-label", "")
            if isinstance(label, list):
                label = " ".join(label)
            if not label:
                continue
            label = str(label).strip()
            if label and label not in el.get_text():
                span = soup.new_tag("span", attrs={"class": "a11y-exposed-label"})
                span.string = f" {label} "
                el.append(span)
                count += 1

        # Expose image alt text
        for img in soup.find_all("img", alt=True):
            alt_text = img.get("alt", "")
            if isinstance(alt_text, list):
                alt_text = " ".join(alt_text)
            if not alt_text:
                continue
            alt_text = str(alt_text).strip()
            if alt_text:
                span = soup.new_tag("span", attrs={"class": "a11y-exposed-alt"})
                span.string = f" {alt_text} "
                img.insert_after(span)
                count += 1

        return count > 0
