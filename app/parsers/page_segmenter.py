"""Page Segmentation Engine.

Splits any HTML page into logical, typed sections *before* parsing.
Each strategy then receives a pre-labelled BeautifulSoup fragment instead
of the whole raw document, which improves extraction accuracy and lets each
strategy focus on the content that matters for its pass.

Design rules
------------
- Zero company-specific selectors.  No hardcoded class names.
- Generic signals only: ARIA landmarks, HTML5 sectioning elements,
  heading hierarchy, repeated DOM patterns, and keyword scoring.
- Never raises — always returns at least one UNKNOWN segment covering
  the full document.
- The rest of the parser stack is completely unmodified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Segment type catalogue
# ---------------------------------------------------------------------------

SEGMENT_HERO = "hero"
SEGMENT_NAVIGATION = "navigation"
SEGMENT_SERVICES = "services"
SEGMENT_PRICING = "pricing"
SEGMENT_PLANS = "plans"
SEGMENT_MEMBERSHIP = "membership"
SEGMENT_ABOUT = "about"
SEGMENT_FAQ = "faq"
SEGMENT_REVIEWS = "reviews"
SEGMENT_BLOG = "blog"
SEGMENT_CONTACT = "contact"
SEGMENT_CITIES = "cities"
SEGMENT_COVERAGE = "coverage"
SEGMENT_FEATURES = "features"
SEGMENT_LEGAL = "legal"
SEGMENT_GALLERY = "gallery"
SEGMENT_FOOTER = "footer"
SEGMENT_UNKNOWN = "unknown"

ALL_TYPES = (
    SEGMENT_HERO,
    SEGMENT_NAVIGATION,
    SEGMENT_SERVICES,
    SEGMENT_PRICING,
    SEGMENT_PLANS,
    SEGMENT_MEMBERSHIP,
    SEGMENT_ABOUT,
    SEGMENT_FAQ,
    SEGMENT_REVIEWS,
    SEGMENT_BLOG,
    SEGMENT_CONTACT,
    SEGMENT_CITIES,
    SEGMENT_COVERAGE,
    SEGMENT_FEATURES,
    SEGMENT_LEGAL,
    SEGMENT_GALLERY,
    SEGMENT_FOOTER,
    SEGMENT_UNKNOWN,
)

# ---------------------------------------------------------------------------
# Keyword vocabularies (multi-language friendly, all lower-case)
# ---------------------------------------------------------------------------

_KW: dict[str, list[str]] = {
    SEGMENT_HERO: [
        "welcome",
        "hero",
        "banner",
        "tagline",
        "get started",
        "start free",
        "try for free",
        "sign up",
        "book now",
        "request demo",
        "watch demo",
    ],
    SEGMENT_NAVIGATION: [
        "menu",
        "navigation",
        "nav",
        "sitemap",
        "breadcrumb",
        "skip to",
        "main menu",
    ],
    SEGMENT_SERVICES: [
        "service",
        "what we do",
        "offering",
        "solution",
        "product",
        "feature",
        "capability",
        "expertise",
        "how it works",
        "what you get",
        "our work",
        "we offer",
    ],
    SEGMENT_PRICING: [
        "price",
        "pricing",
        "plan",
        "subscription",
        "cost",
        "rate",
        "package",
        "tier",
        "per month",
        "per year",
        "billed annually",
        "free trial",
        "enterprise",
        # currency symbols covered separately by regex
    ],
    SEGMENT_PLANS: [
        "plan",
        "our plans",
        "choose your plan",
        "compare plans",
        "plan comparison",
        "plan options",
        "pricing plans",
        "subscription plans",
        "membership plans",
    ],
    SEGMENT_MEMBERSHIP: [
        "membership",
        "become a member",
        "member benefits",
        "join",
        "sign up",
        "register",
        "create account",
        "member area",
        "premium",
        "pro plan",
        "business plan",
    ],
    SEGMENT_ABOUT: [
        "about",
        "our story",
        "who we are",
        "our mission",
        "our vision",
        "our team",
        "leadership",
        "founded",
        "values",
        "culture",
        "history",
        "why us",
    ],
    SEGMENT_REVIEWS: [
        "review",
        "testimonial",
        "rating",
        "what our customers say",
        "customer story",
        "success story",
        "trustpilot",
        "g2",
        "capterra",
        "client feedback",
        "customer review",
        "star",
        "rated",
        "recommended",
    ],
    SEGMENT_FAQ: [
        "faq",
        "frequently asked",
        "question",
        "answer",
        "help",
        "how do i",
        "what is",
        "can i",
        "is there",
        "do you",
    ],
    SEGMENT_BLOG: [
        "blog",
        "article",
        "news",
        "post",
        "latest",
        "insight",
        "resource",
        "update",
        "press",
        "media",
    ],
    SEGMENT_CITIES: [
        "city",
        "cities",
        "service area",
        "location",
        "where we serve",
        "coverage area",
        "regions",
        "states",
        "zip code",
        "postal code",
        "available in",
        "nationwide",
        "local",
    ],
    SEGMENT_COVERAGE: [
        "coverage",
        "service area",
        "network",
        "supported region",
        "availability",
        "operating area",
        "footprint",
        "reach",
    ],
    SEGMENT_FEATURES: [
        "feature",
        "capability",
        "specification",
        "what's included",
        "includes",
        "included",
        "comparison",
        "compare",
        "vs",
        "feature matrix",
        "feature list",
    ],
    SEGMENT_LEGAL: [
        "legal",
        "privacy",
        "terms",
        "policy",
        "cookie policy",
        "gdpr",
        "ccpa",
        "disclaimer",
        "license",
        "agreement",
    ],
    SEGMENT_GALLERY: [
        "gallery",
        "portfolio",
        "showcase",
        "our work",
        "projects",
        "case study",
        "screenshot",
        "photo",
        "image gallery",
        "video gallery",
        "media gallery",
    ],
    SEGMENT_CONTACT: [
        "contact",
        "get in touch",
        "reach us",
        "reach out",
        "send message",
        "write to us",
        "email us",
        "call us",
        "phone",
        "address",
        "location",
        "find us",
    ],
    SEGMENT_FOOTER: [
        "copyright",
        "©",
        "all rights reserved",
        "privacy policy",
        "terms of service",
        "terms & conditions",
        "sitemap",
        "cookie policy",
    ],
}

# Compiled lower-case keyword sets (used for fast O(1) lookups)
_KW_SETS: dict[str, set[str]] = {k: set(v) for k, v in _KW.items()}

# Regex for currency / price patterns (language-agnostic)
_PRICE_RE = re.compile(r"[\$\€\£\₹\¥]\s*[\d,]+|[\d,]+\s*(?:USD|EUR|GBP|INR|JPY)\b", re.I)

# Regex for FAQ-style question patterns
_FAQ_RE = re.compile(r"^\s*(how|what|why|when|where|who|can|do|is|are|will|does)\b", re.I)


# ---------------------------------------------------------------------------
# Landmark / element → segment type mappings
# ---------------------------------------------------------------------------

# HTML5 ARIA role → segment type
_ROLE_MAP: dict[str, str] = {
    "banner": SEGMENT_HERO,
    "navigation": SEGMENT_NAVIGATION,
    "main": SEGMENT_UNKNOWN,  # main alone is not enough; let keyword scoring decide
    "contentinfo": SEGMENT_FOOTER,
    "complementary": SEGMENT_UNKNOWN,
    "search": SEGMENT_UNKNOWN,
    "form": SEGMENT_CONTACT,
    "region": SEGMENT_UNKNOWN,
}

# HTML5 element name → strong segment hint
_TAG_HINT: dict[str, str] = {
    "header": SEGMENT_HERO,
    "nav": SEGMENT_NAVIGATION,
    "footer": SEGMENT_FOOTER,
    "aside": SEGMENT_UNKNOWN,
}

# Schema.org @type → segment
_SCHEMA_MAP: dict[str, str] = {
    "FAQPage": SEGMENT_FAQ,
    "Question": SEGMENT_FAQ,
    "Answer": SEGMENT_FAQ,
    "Product": SEGMENT_SERVICES,
    "Service": SEGMENT_SERVICES,
    "ServiceList": SEGMENT_SERVICES,
    "ItemList": SEGMENT_SERVICES,
    "Offer": SEGMENT_PRICING,
    "AggregateOffer": SEGMENT_PRICING,
    "PriceSpecification": SEGMENT_PRICING,
    "BlogPosting": SEGMENT_BLOG,
    "Article": SEGMENT_BLOG,
    "NewsArticle": SEGMENT_BLOG,
    "ContactPage": SEGMENT_CONTACT,
    "AboutPage": SEGMENT_ABOUT,
    "Organization": SEGMENT_ABOUT,
    "LocalBusiness": SEGMENT_ABOUT,
    "WPFooter": SEGMENT_FOOTER,
    "WPHeader": SEGMENT_HERO,
    "SiteNavigationElement": SEGMENT_NAVIGATION,
}


# ---------------------------------------------------------------------------
# PageSegment dataclass
# ---------------------------------------------------------------------------


@dataclass
class PageSegment:
    """
    A single logical section of a page.

    Attributes
    ----------
    segment_type : One of the SEGMENT_* constants.
    confidence   : Float in [0, 1] expressing how confident the classifier is.
    element      : The original BeautifulSoup Tag this segment covers.
    heading      : The first heading text found inside this element, if any.
    signals      : List of signals that contributed to the classification.
    depth        : DOM depth of the element (0 = direct child of <body>).
    position     : 0-based index among all top-level candidate elements.
    metadata     : Arbitrary extra data (e.g. detected schema types).
    """

    segment_type: str
    confidence: float
    element: Tag
    heading: str = ""
    signals: list[str] = field(default_factory=list)
    depth: int = 0
    position: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Convenience — render the segment back to HTML for sub-parsing
    def to_soup(self) -> BeautifulSoup:
        return BeautifulSoup(str(self.element), "lxml")

    def text_content(self) -> str:
        return self.element.get_text(" ", strip=True)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _score_keywords(text: str, segment_type: str) -> float:
    """
    Return a keyword score for the given text against a segment type.
    Scoring:  exact keyword hit = 0.12,  price regex = 0.15,
              FAQ question pattern = 0.10.  Capped at 0.6.
    """
    lower = text.lower()
    score = 0.0
    for kw in _KW_SETS.get(segment_type, set()):
        if kw in lower:
            score += 0.12
    if segment_type == SEGMENT_PRICING and _PRICE_RE.search(text):
        score += 0.15
    if segment_type == SEGMENT_FAQ and _FAQ_RE.search(text):
        score += 0.10
    return min(score, 0.60)


def _heading_in(el: Tag) -> str:
    """Return the text of the first heading element found inside el."""
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        h = el.find(tag)
        if h:
            return h.get_text(strip=True)
    return ""


def _schema_type_in(el: Tag) -> str | None:
    """Return the Schema.org @type found in itemprop/itemtype or JSON-LD, if any."""
    # itemtype attribute
    itemtype = el.get("itemtype", "")
    if isinstance(itemtype, str) and itemtype:
        parts = itemtype.rsplit("/", 1)
        return parts[-1] if parts else None

    # itemprop descendants may carry useful itemtype
    for child in el.find_all(lambda tag: tag.has_attr("itemtype"), limit=3):
        it = child.get("itemtype", "")
        if isinstance(it, str) and it:
            return it.rsplit("/", 1)[-1]

    return None


def _repeated_children(el: Tag, min_count: int = 3) -> bool:
    """
    Return True when el has ≥ min_count direct block children that share
    the same tag name — the hallmark of a grid / card / list pattern.
    """
    child_tags: list[str] = [
        c.name
        for c in el.children
        if isinstance(c, Tag) and c.name in ("div", "li", "article", "section", "a")
    ]
    if not child_tags:
        return False
    most_common = max(set(child_tags), key=child_tags.count)
    return child_tags.count(most_common) >= min_count


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------


def _classify_element(
    el: Tag,
    position: int,
    total: int,
    depth: int = 0,
) -> tuple[str, float, list[str]]:
    """
    Classify a single Tag into a segment type.

    Returns (segment_type, confidence, signals).
    Uses six independent signal groups, each capped at a max contribution:

    1. HTML5 / ARIA landmarks        → up to 0.50
    2. Schema.org type               → up to 0.40
    3. Heading text keywords         → up to 0.35
    4. Full text keywords            → up to 0.25  (attenuated for large blocks)
    5. Structural / positional cues  → up to 0.25
    6. Repeated child pattern        → up to 0.10
    """
    scores: dict[str, float] = dict.fromkeys(ALL_TYPES, 0.0)
    signals: list[str] = []

    tag = el.name or ""
    role = str(el.get("role", "") or "").lower()
    aria_label = str(el.get("aria-label", "") or "").lower()

    # ------------------------------------------------------------------
    # 1. Landmark / element hints
    # ------------------------------------------------------------------
    if tag in _TAG_HINT:
        hint = _TAG_HINT[tag]
        scores[hint] += 0.50
        signals.append(f"tag:{tag}")

    if role in _ROLE_MAP:
        hint = _ROLE_MAP[role]
        scores[hint] = max(scores[hint], 0.45)
        signals.append(f"role:{role}")

    if aria_label:
        for seg_type in ALL_TYPES:
            for kw in _KW_SETS.get(seg_type, set()):
                if kw in aria_label:
                    scores[seg_type] += 0.20
                    signals.append(f"aria-label:{kw}")
                    break

    # ------------------------------------------------------------------
    # 2. Schema.org type
    # ------------------------------------------------------------------
    schema_type = _schema_type_in(el)
    if schema_type and schema_type in _SCHEMA_MAP:
        seg = _SCHEMA_MAP[schema_type]
        scores[seg] += 0.40
        signals.append(f"schema:{schema_type}")

    # ------------------------------------------------------------------
    # 3. Heading text
    # ------------------------------------------------------------------
    heading_text = _heading_in(el)
    if heading_text:
        for seg_type in ALL_TYPES:
            h_score = _score_keywords(heading_text, seg_type)
            if h_score:
                scores[seg_type] += min(h_score * 1.4, 0.35)  # headings weighted more
                signals.append(f"heading_kw:{seg_type}")

    # ------------------------------------------------------------------
    # 4. Full text keyword scoring (attenuated for large blocks)
    # ------------------------------------------------------------------
    full_text = el.get_text(" ", strip=True)
    text_len = len(full_text)
    text_attenuation = 1.0 if text_len < 800 else max(0.3, 800 / text_len)

    for seg_type in ALL_TYPES:
        kw_score = _score_keywords(full_text, seg_type)
        if kw_score:
            scores[seg_type] += kw_score * text_attenuation * 0.25 / 0.60
            signals.append(f"text_kw:{seg_type}")

    # ------------------------------------------------------------------
    # 5. Structural / positional cues
    # ------------------------------------------------------------------
    # First body-level block → likely hero or navigation
    if position == 0:
        scores[SEGMENT_HERO] += 0.20
        signals.append("position:first")

    # Last body-level block → likely footer
    if position == total - 1:
        scores[SEGMENT_FOOTER] += 0.25
        signals.append("position:last")

    # Presence of a form → contact likelihood
    if el.find("form"):
        scores[SEGMENT_CONTACT] += 0.20
        signals.append("struct:form")

    # Presence of a <table> with headers → pricing or services
    table = el.find("table")
    if table:
        headers = [th.get_text(strip=True).lower() for th in table.select("th")]
        if any(w in " ".join(headers) for w in ("price", "cost", "plan", "rate")):
            scores[SEGMENT_PRICING] += 0.25
            signals.append("struct:price_table")
        else:
            scores[SEGMENT_SERVICES] += 0.10
            signals.append("struct:table")

    # Q&A pattern: alternating dt/dd or details/summary pairs
    qa_pairs = len(el.find_all("details")) + len(el.find_all("summary"))
    if qa_pairs >= 2:
        scores[SEGMENT_FAQ] += min(0.15 * qa_pairs, 0.25)
        signals.append(f"struct:qa_pairs({qa_pairs})")

    # Link-heavy sections → navigation
    links = el.find_all("a", limit=30)
    paragraphs = el.find_all("p", limit=10)
    if links and len(links) > len(paragraphs) * 3:
        scores[SEGMENT_NAVIGATION] += 0.15
        signals.append("struct:link_heavy")

    # Copyright text in a trailing element → footer boost
    lower_text = full_text.lower()
    if "©" in lower_text or "copyright" in lower_text:
        scores[SEGMENT_FOOTER] += 0.30
        signals.append("text:copyright")

    # ------------------------------------------------------------------
    # 6. Repeated child pattern → card/grid → services or pricing
    # ------------------------------------------------------------------
    if _repeated_children(el, min_count=3):
        if scores[SEGMENT_PRICING] > scores[SEGMENT_SERVICES]:
            scores[SEGMENT_PRICING] += 0.10
        else:
            scores[SEGMENT_SERVICES] += 0.10
        signals.append("struct:grid")

    # ------------------------------------------------------------------
    # Pick winner
    # ------------------------------------------------------------------
    best_type = max(scores, key=scores.__getitem__)
    raw_conf = scores[best_type]

    # Normalise to [0.1, 0.95]
    confidence = max(0.10, min(0.95, raw_conf))

    # If nothing scored above a tiny threshold, fall back to UNKNOWN
    if raw_conf < 0.08:
        best_type = SEGMENT_UNKNOWN
        confidence = 0.10

    return best_type, confidence, signals


# ---------------------------------------------------------------------------
# Public API — PageSegmenter
# ---------------------------------------------------------------------------


class PageSegmenter:
    """
    Splits an HTML page into typed PageSegment objects.

    Segmentation algorithm
    ----------------------
    1. Locate top-level block candidates (direct children of <body>,
       plus <header>, <nav>, <main>, <aside>, <footer> wherever they sit).
    2. Classify each candidate independently using six signal groups.
    3. Post-process: merge consecutive same-type fragments, ensure there is
       always at least one segment covering the full document.

    Usage
    -----
    >>> segmenter = PageSegmenter()
    >>> segments = segmenter.segment(html, url)
    >>> for seg in segments:
    ...     print(seg.segment_type, seg.confidence)
    """

    # Minimum number of non-whitespace characters for a block to qualify
    MIN_TEXT_LEN: int = 20

    def segment(self, html: str, url: str = "") -> list[PageSegment]:
        """
        Segment ``html`` into typed PageSegment objects.

        Parameters
        ----------
        html : Raw HTML string.
        url  : Source URL (currently unused, reserved for future URL-signal use).

        Returns
        -------
        List of PageSegment, ordered by DOM position.
        Always returns at least one segment.
        """
        try:
            return self._segment(html, url)
        except Exception:
            # Never crash the caller — return a single UNKNOWN segment
            soup = BeautifulSoup(html, "lxml")
            body = soup.body or soup
            return [
                PageSegment(
                    segment_type=SEGMENT_UNKNOWN,
                    confidence=0.10,
                    element=body,
                    signals=["fallback:exception"],
                )
            ]

    def _segment(self, html: str, url: str) -> list[PageSegment]:
        soup = BeautifulSoup(html, "lxml")
        candidates = self._collect_candidates(soup)

        if not candidates:
            body = soup.body or soup
            return [
                PageSegment(
                    segment_type=SEGMENT_UNKNOWN,
                    confidence=0.10,
                    element=body,
                    signals=["fallback:no_candidates"],
                )
            ]

        total = len(candidates)
        segments: list[PageSegment] = []

        for pos, (el, depth) in enumerate(candidates):
            seg_type, conf, sigs = _classify_element(el, pos, total, depth)
            heading = _heading_in(el)
            segments.append(
                PageSegment(
                    segment_type=seg_type,
                    confidence=conf,
                    element=el,
                    heading=heading,
                    signals=sigs,
                    depth=depth,
                    position=pos,
                )
            )

        return self._post_process(segments)

    def _collect_candidates(self, soup: BeautifulSoup) -> list[tuple[Tag, int]]:
        """
        Collect candidate block elements.

        Priority order:
        1. Named landmark elements (<header>, <nav>, <main>, <footer>, <aside>)
           regardless of nesting depth.
        2. Direct <body> children that are block-level and have enough text.
        3. Top-level <section> / <article> / <div> children of <main>.
        """
        candidates: list[tuple[Tag, int]] = []
        seen: set[int] = set()

        body = soup.body
        if not body:
            return candidates

        def _add(el: Tag, depth: int) -> None:
            eid = id(el)
            if eid in seen:
                return
            # Landmark elements (header, nav, main, footer, aside) bypass the
            # minimum text length filter — they're structural even if sparse.
            text = el.get_text(strip=True)
            if (
                el.name not in ("header", "nav", "main", "footer", "aside")
                and len(text) < self.MIN_TEXT_LEN
            ):
                return
            seen.add(eid)
            candidates.append((el, depth))

        # --- Pass A: named landmarks (wherever they sit) ---
        for tag_name in ("header", "nav", "main", "footer", "aside"):
            for el in soup.find_all(tag_name):
                if isinstance(el, Tag):
                    _add(el, depth=0)

        # --- Pass B: direct children of <body> that are blocks ---
        _block = {"div", "section", "article", "header", "nav", "main", "footer", "aside"}
        for child in body.children:
            if isinstance(child, Tag) and child.name in _block:
                _add(child, depth=0)

        # --- Pass C: children of <main> (if <main> exists and has sub-structure) ---
        main = soup.find("main")
        if isinstance(main, Tag):
            for child in main.children:
                if isinstance(child, Tag) and child.name in {"section", "article", "div"}:
                    _add(child, depth=1)

        # --- Pass D: top-level <section> / <article> direct-children of <body> ---
        for child in body.children:
            if isinstance(child, Tag) and child.name in {"section", "article"}:
                _add(child, depth=0)

        # Sort by document order (position in soup)
        all_tags = list(soup.find_all(True))
        tag_order = {id(t): i for i, t in enumerate(all_tags)}
        candidates.sort(key=lambda x: tag_order.get(id(x[0]), 0))

        return candidates

    def _post_process(self, segments: list[PageSegment]) -> list[PageSegment]:
        """
        Light post-processing:
        - Deduplicate segments where a child was already covered by its parent.
        - Nothing else (we preserve all segments for the parser stack).
        """
        if len(segments) <= 1:
            return segments

        # Build element → segment map by id
        kept: list[PageSegment] = []
        covered_ids: set[int] = set()

        for seg in segments:
            # If this element is already a descendant of a kept element, skip it
            # (unless it's a landmark which we always keep)
            is_landmark = seg.element.name in ("header", "nav", "main", "footer", "aside")
            if id(seg.element) in covered_ids and not is_landmark:
                continue
            kept.append(seg)
            # Mark all descendants
            for desc in seg.element.find_all(True):
                covered_ids.add(id(desc))

        return kept


# ---------------------------------------------------------------------------
# Convenience filter helpers (used by strategy_parser integration)
# ---------------------------------------------------------------------------


def segments_of_type(segments: list[PageSegment], *types: str) -> list[PageSegment]:
    """Return only segments whose type is in the given set."""
    return [s for s in segments if s.segment_type in types]


def best_segment(segments: list[PageSegment], seg_type: str) -> PageSegment | None:
    """Return the highest-confidence segment of the given type, or None."""
    matches = [s for s in segments if s.segment_type == seg_type]
    return max(matches, key=lambda s: s.confidence) if matches else None
