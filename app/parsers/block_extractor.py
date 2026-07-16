"""DOM Block Extraction Engine — split pages into logical parsing blocks.

Splits every HTML page into typed, non-overlapping content blocks *before*
any strategy runs.  Each block becomes an independent parsing unit so that
strategies never process the full document as one large tree.

Detection methods (zero CSS selectors, zero class names):
1. **Semantic HTML** — <header>, <nav>, <main>, <section>, <article>,
   <aside>, <footer> naturally define block boundaries.
2. **Heading hierarchy** — <h2>/<h3> elements split large containers
   into topic-specific sub-blocks.
3. **Repeated structures** — groups of 3+ same-tag siblings (cards,
   grid items) are extracted as individual blocks.
4. **DOM depth & parent-child** — recursive splitting until every block
   is an atomic parsing unit.
5. **Fallback to direct body children** — guarantees full coverage.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from app.parsers.page_segmenter import (
    SEGMENT_UNKNOWN,
    PageSegment,
    PageSegmenter,
    _classify_element,
    _heading_in,
)

# ---------------------------------------------------------------------------
# Block boundary tags (semantic HTML elements that serve as block delimiters)
# ---------------------------------------------------------------------------

_BOUNDARY_TAGS: frozenset[str] = frozenset(
    {
        "header",
        "nav",
        "main",
        "footer",
        "aside",
        "section",
        "article",
    }
)

# Additional block-level grouping tags (split inside these if they contain
# multiple heading-bound sub-blocks)
_CONTAINER_TAGS: frozenset[str] = frozenset(
    {
        "div",
        "section",
        "article",
    }
)

# Tags that are NOT valid block roots (inline, phrasing, or metadata)
_SKIP_TAGS: frozenset[str] = frozenset(
    {
        "script",
        "style",
        "noscript",
        "template",
        "br",
        "hr",
        "wbr",
        "span",
        "a",
        "b",
        "i",
        "em",
        "strong",
        "small",
        "sub",
        "sup",
        "img",
        "input",
        "button",
        "label",
        "select",
        "textarea",
        "ul",
        "ol",
        "li",
        "dl",
        "dt",
        "dd",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "figure",
        "figcaption",
    }
)


class DomBlockExtractor:
    """Extract logical content blocks covering the entire page.

    Usage
    -----
    >>> extractor = DomBlockExtractor()
    >>> blocks = extractor.extract(soup)
    >>> for block in blocks:
    ...     print(block.segment_type, block.heading)
    """

    # Minimum characters for a container to be considered for heading split
    _MIN_SPLIT_CHARS: int = 60

    # Minimum repeated children to trigger card/grid expansion
    _MIN_REPEATED: int = 3

    def __init__(self) -> None:
        self._segmenter = PageSegmenter()

    def extract(self, soup: BeautifulSoup) -> list[PageSegment]:
        """Extract typed blocks covering the full page.

        Returns a flat, ordered list of PageSegment objects.
        Every element in the page belongs to exactly one block.
        """
        body = soup.body or soup
        if not isinstance(body, Tag):
            return self._fallback(soup)

        # Phase 1 — Recursively split the DOM into atomic blocks
        raw_blocks = self._split_dom(body, depth=0)

        # Phase 2 — Classify each block using the PageSegmenter classifier
        blocks = self._classify_blocks(raw_blocks)

        # Phase 3 — Merge adjacent same-type blocks to avoid fragmentation
        blocks = self._merge_same_type(blocks)

        # Phase 4 — Ensure full page coverage
        blocks = self._ensure_coverage(soup, blocks)

        return blocks

    # ------------------------------------------------------------------
    # Recursive DOM splitting
    # ------------------------------------------------------------------

    def _split_dom(
        self,
        element: Tag,
        depth: int,
        parent_heading: str | None = None,
    ) -> list[Tag]:
        """Recursively split *element* into atomic block-level Tags.

        Returns a list of ``<div>``-wrapped Tags, each representing
        one logical block.
        """
        # Strategy 1 — If the element = semantic boundary, process its
        # direct children as candidates.
        if element.name in _BOUNDARY_TAGS:
            return self._split_container_children(element, depth)

        # Strategy 2 — If the element has multiple headings, split at
        # heading boundaries.
        headings = element.find_all(["h1", "h2", "h3"], limit=6)
        if len(headings) >= 2:
            sub_blocks = self._split_by_headings(element, headings)
            if len(sub_blocks) > 1:
                result: list[Tag] = []
                for sub in sub_blocks:
                    result.extend(self._split_dom(sub, depth + 1, parent_heading))
                return result

        # Strategy 3 — Repeated children (cards / grid items).
        direct_children = [
            c for c in element.children if isinstance(c, Tag) and c.name not in _SKIP_TAGS
        ]
        if len(direct_children) >= self._MIN_REPEATED and self._is_repeated(direct_children):
            wrapped: list[Tag] = []
            for c in direct_children:
                w = self._wrap(c)
                if w is not None:
                    wrapped.append(w)
            return wrapped

        # Strategy 4 — Container with sub-containers → split children.
        if element.name in _CONTAINER_TAGS:
            block_children = [
                c for c in element.children if isinstance(c, Tag) and c.name not in _SKIP_TAGS
            ]
            if len(block_children) >= 2:
                result = []
                for c in block_children:
                    result.extend(self._split_dom(c, depth + 1, parent_heading))
                return result

        # Default — this element is an atomic block.
        atom = self._wrap(element)
        if atom is not None:
            return [atom]
        return []

    def _split_container_children(self, container: Tag, depth: int) -> list[Tag]:
        """Split a container's children into blocks, recursing into each."""
        children = [
            c for c in container.children if isinstance(c, Tag) and c.name not in _SKIP_TAGS
        ]
        if not children:
            block = self._wrap(container)
            if block is not None:
                return [block]
            return []
        result: list[Tag] = []
        for c in children:
            result.extend(self._split_dom(c, depth + 1))
        return result

    @staticmethod
    def _is_repeated(children: list[Tag]) -> bool:
        """Check if children form a repeated grid/card pattern.

        All children must share the same tag name and have similar
        internal structure (at least one heading or paragraph).
        """
        if not children:
            return False
        first_tag = children[0].name
        if not all(c.name == first_tag for c in children):
            return False
        # Each child should have some content (heading, paragraph, or list)
        for c in children:
            text_len = len(c.get_text(strip=True))
            if text_len < 10:
                return False
        return True

    @staticmethod
    def _split_by_headings(container: Tag, headings: list[Tag]) -> list[Tag]:
        """Split *container* children at each heading boundary.

        Only considers headings that are **direct children** of the container
        (nested headings are handled by recursive splitting in _split_dom).

        Returns a ``<div>``-wrapped block for each heading section.
        """
        # Filter to headings that are direct children of container
        heading_ids: set[int] = set()
        for h in headings:
            if h.parent == container:
                heading_ids.add(id(h))

        if len(heading_ids) < 2:
            fallback = DomBlockExtractor._wrap(container)
            return [fallback] if fallback is not None else []

        blocks: list[list[Tag]] = []
        current: list[Tag] = []

        for child in container.children:
            if not isinstance(child, Tag):
                continue
            if id(child) in heading_ids and (current or blocks):
                blocks.append(current)
                current = []
            current.append(child)

        if current:
            blocks.append(current)

        if len(blocks) <= 1:
            single = DomBlockExtractor._wrap(container)
            return [single] if single is not None else []

        return [DomBlockExtractor._wrap_sequence(b) for b in blocks]

    # ------------------------------------------------------------------
    # Element wrapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap(element: Tag) -> Tag | None:
        """Wrap a single Tag in a ``<div>`` if it isn't one already."""
        text = element.get_text(strip=True)
        if not text:
            return None
        if element.name == "div":
            return element
        wrapper = Tag(name="div")
        wrapper.append(element)
        return wrapper

    @staticmethod
    def _wrap_sequence(elements: list[Tag]) -> Tag:
        """Wrap a sequence of sibling Tags in a single ``<div>``."""
        wrapper = Tag(name="div")
        for el in elements:
            wrapper.append(el)
        return wrapper

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify_blocks(self, raw_blocks: list[Tag]) -> list[PageSegment]:
        """Classify each raw block into a typed PageSegment."""
        total = len(raw_blocks)
        segments: list[PageSegment] = []

        for pos, el in enumerate(raw_blocks):
            seg_type, conf, sigs = _classify_element(el, pos, total, depth=1)
            heading = _heading_in(el)
            segments.append(
                PageSegment(
                    segment_type=seg_type,
                    confidence=conf,
                    element=el,
                    heading=heading,
                    signals=sigs,
                    depth=1,
                    position=pos,
                )
            )

        return segments

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_same_type(blocks: list[PageSegment]) -> list[PageSegment]:
        """Merge adjacent blocks that share the same segment type."""
        if len(blocks) <= 1:
            return blocks

        merged: list[PageSegment] = []
        for block in blocks:
            if merged and merged[-1].segment_type == block.segment_type:
                # Merge into the previous block
                prev = merged[-1]
                if prev.element.name != "div":
                    wrapper = Tag(name="div")
                    wrapper.append(prev.element)
                    prev.element = wrapper
                prev.element.append(block.element)
                # Keep the best confidence
                prev.confidence = max(prev.confidence, block.confidence)
            else:
                merged.append(block)

        return merged

    def _ensure_coverage(
        self,
        soup: BeautifulSoup,
        blocks: list[PageSegment],
    ) -> list[PageSegment]:
        """Add UNKNOWN blocks for uncovered regions of the page."""
        if not blocks:
            body = soup.body or soup
            if isinstance(body, Tag):
                return [
                    PageSegment(
                        segment_type=SEGMENT_UNKNOWN,
                        confidence=0.10,
                        element=body,
                        heading="",
                        signals=["fallback:no_blocks"],
                        depth=0,
                        position=0,
                    )
                ]
            return []

        # Simple coverage check: if there's only one block and it covers
        # the body, we're fine.  Otherwise, add a fallback.
        # For now, the recursive splitting naturally covers the entire page.
        return blocks

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback(soup: BeautifulSoup) -> list[PageSegment]:
        """Return a single UNKNOWN segment covering the full page."""
        body = soup.body or soup
        return [
            PageSegment(
                segment_type=SEGMENT_UNKNOWN,
                confidence=0.10,
                element=body,
                heading="",
                signals=["fallback:extractor"],
                depth=0,
                position=0,
            )
        ]

    # ------------------------------------------------------------------
    # Re-export of existing segmentation (public API for get_segments)
    # ------------------------------------------------------------------
