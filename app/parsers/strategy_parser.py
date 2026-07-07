import time
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.parsers.adaptive_orderer import AdaptiveStrategyOrderer
from app.parsers.block_extractor import DomBlockExtractor
from app.parsers.page_segmenter import PageSegment
from app.parsers.preprocessing import Preprocessor
from app.parsers.relationships import RelationshipEngine
from app.parsers.resolution import EntityResolver
from app.parsers.strategies import (
    AssetExtractionStrategy,
    BreadcrumbExtractionStrategy,
    CardExtractionStrategy,
    FaqExtractionStrategy,
    FormExtractionStrategy,
    GenericCssPatternStrategy,
    GenericDomHeuristicStrategy,
    JsonLdStrategy,
    ListExtractionStrategy,
    LocationExtractionStrategy,
    MediaExtractionStrategy,
    MetadataStrategy,
    MicrodataStrategy,
    MultiPassStrategy,
    RegexPatternStrategy,
    ReviewExtractionStrategy,
    SchemaOrgStrategy,
    SemanticHtmlStrategy,
    TableExtractionStrategy,
    TeamExtractionStrategy,
    TrustSignalExtractionStrategy,
)
from app.parsers.strategy import ParsedResult, ParsingStrategy, _reset_calculator
from app.utilities.performance import cached_parse

# Segment type for the synthetic <head> block
_SEGMENT_HEAD = "head"

# MultiPassStrategy runs first — it performs all 6 extraction passes in
# sequence and returns the richest possible merged result.  The remaining
# single-concern strategies act as supplementary gap-fillers.
DEFAULT_STRATEGIES: list[ParsingStrategy] = [
    MultiPassStrategy(),  # Pass 1-6 combined (highest confidence)
    JsonLdStrategy(),  # supplementary JSON-LD
    SchemaOrgStrategy(),  # supplementary Schema.org
    MicrodataStrategy(),  # supplementary microdata
    TableExtractionStrategy(),  # HTML table extraction
    FormExtractionStrategy(),  # HTML form extraction
    FaqExtractionStrategy(),  # FAQ extraction
    BreadcrumbExtractionStrategy(),  # Breadcrumb extraction
    SemanticHtmlStrategy(),  # supplementary semantic HTML
    CardExtractionStrategy(),  # card/plan/review extraction
    ListExtractionStrategy(),  # structured list extraction
    LocationExtractionStrategy(), # locations and coverage areas
    TeamExtractionStrategy(), # team and leadership
    ReviewExtractionStrategy(), # reviews and testimonials
    TrustSignalExtractionStrategy(), # trust signals and badges
    AssetExtractionStrategy(), # assets and documents
    MediaExtractionStrategy(),  # image/video/document extraction
    GenericDomHeuristicStrategy(),
    GenericCssPatternStrategy(),
    RegexPatternStrategy(),
    MetadataStrategy(),
]


class StrategyParser:
    def __init__(
        self,
        strategies: list[ParsingStrategy] | None = None,
        confidence_threshold: float = 0.8,
        use_adaptive_ordering: bool = True,
        enable_preprocessing: bool = True,
    ) -> None:
        self._strategies = strategies or DEFAULT_STRATEGIES
        self._confidence_threshold = confidence_threshold
        self._orderer = AdaptiveStrategyOrderer() if use_adaptive_ordering else None
        self._segmenter = DomBlockExtractor()
        self._preprocessor = Preprocessor() if enable_preprocessing else None

    @cached_parse(max_size=500, ttl_seconds=1800)
    def parse(self, html: str, url: str) -> ParsedResult:
        # Optional: preprocess HTML (remove noise, normalize DOM)
        if self._preprocessor is not None:
            html = self._preprocessor.process(html)

        soup = BeautifulSoup(html, "html.parser")
        combined = ParsedResult()

        # --- DOM Block Extraction (splits page into typed blocks before all strategies) ---
        blocks = self._segmenter.extract(soup)

        # Add a synthetic <head> block so strategies that read global metadata
        # (JSON-LD, OpenGraph, Twitter Card, title, meta) still find it.
        head = soup.find("head")
        if isinstance(head, Tag) and self._head_has_content(head):
            head_block = PageSegment(
                segment_type=_SEGMENT_HEAD,
                confidence=1.0,
                element=head,
                heading="",
                signals=["tag:head"],
                depth=0,
                position=0,
            )
            blocks.insert(0, head_block)
            # Re-number positions
            for i, b in enumerate(blocks):
                b.position = i

        combined.strategy_results["__blocks__"] = {
            s.segment_type: round(s.confidence, 3) for s in blocks
        }
        # Legacy key for backward compatibility
        combined.strategy_results["__segments__"] = combined.strategy_results["__blocks__"]

        strategies = self._get_ordered_strategies()

        # Reset the confidence calculator for a fresh parse cycle
        _reset_calculator()

        for strategy in strategies:
            start = time.perf_counter()
            try:
                partial = strategy.parse_segments(blocks, url)
                elapsed_ms = (time.perf_counter() - start) * 1000
                combined.merge(partial, strategy.name, strategy.weight)

                if self._orderer and partial.confidence > 0:
                    self._orderer.record_success(strategy.name, partial.confidence, elapsed_ms)
                elif self._orderer:
                    self._orderer.record_failure(strategy.name, elapsed_ms)
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if self._orderer:
                    self._orderer.record_failure(strategy.name, elapsed_ms)
                continue

            # Every strategy contributes — no early break
            # Confidence threshold is only informational now

        # --- Entity Resolution: deduplicate and canonicalize ---
        resolver = EntityResolver()
        resolver.resolve(combined)

        # --- Relationship Engine: link entities together ---
        rel_engine = RelationshipEngine()
        relationships = rel_engine.run(combined, soup)
        combined.relationships = [r.to_dict() for r in relationships]

        if self._orderer:
            self._orderer.save_stats()

        return combined

    def get_segments(self, html: str, url: str = "") -> list[PageSegment]:
        """Return the raw PageSegment list for a page without running strategies."""
        soup = BeautifulSoup(html, "html.parser")
        blocks = list(self._segmenter.extract(soup))
        head = soup.find("head")
        if isinstance(head, Tag) and self._head_has_content(head):
            blocks.insert(
                0,
                PageSegment(
                    segment_type=_SEGMENT_HEAD,
                    confidence=1.0,
                    element=head,
                    heading="",
                    signals=["tag:head"],
                    depth=0,
                    position=0,
                ),
            )
            for i, b in enumerate(blocks):
                b.position = i
        return blocks

    @staticmethod
    def _head_has_content(head: Tag) -> bool:
        """Check whether <head> contains meaningful extraction data."""
        if head.select('script[type="application/ld+json"]'):
            return True
        if head.select("meta[property^='og:'], meta[name^='twitter:'], meta[name='description'], meta[name='keywords']"):
            return True
        if head.select('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]'):
            return True
        title = head.find("title")
        return bool(title and title.get_text(strip=True))

    def _get_ordered_strategies(self) -> list[ParsingStrategy]:
        """Get strategies ordered by historical performance."""
        if not self._orderer:
            return list(self._strategies)

        names = [s.name for s in self._strategies]
        ordered_names = self._orderer.rank_strategies(names)
        name_to_strategy = {s.name: s for s in self._strategies}
        return [name_to_strategy[n] for n in ordered_names if n in name_to_strategy]

    def parse_for_type(self, html: str, url: str, parse_type: str) -> dict[str, Any]:
        result = self.parse(html, url)
        type_map: dict[str, dict[str, Any]] = {
            "company": result.to_company_dict(),
            "services": result.to_service_dict(),
            "pricing": result.to_pricing_dict(),
            "content": result.to_content_dict(),
            "social": result.to_social_dict(),
        }
        output = type_map.get(parse_type, result.to_company_dict())
        output["url"] = url
        return dict(output)
