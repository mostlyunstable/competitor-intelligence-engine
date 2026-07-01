from typing import Any

from bs4 import BeautifulSoup

from app.parsers.strategies import (
    GenericCssPatternStrategy,
    GenericDomHeuristicStrategy,
    JsonLdStrategy,
    MetadataStrategy,
    MicrodataStrategy,
    RegexPatternStrategy,
    SchemaOrgStrategy,
    SemanticHtmlStrategy,
)
from app.parsers.strategy import ParsedResult, ParsingStrategy

DEFAULT_STRATEGIES: list[ParsingStrategy] = [
    JsonLdStrategy(),
    SchemaOrgStrategy(),
    MicrodataStrategy(),
    SemanticHtmlStrategy(),
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
    ) -> None:
        self._strategies = strategies or DEFAULT_STRATEGIES
        self._confidence_threshold = confidence_threshold

    def parse(self, html: str, url: str) -> ParsedResult:
        soup = BeautifulSoup(html, "html.parser")
        combined = ParsedResult()
        for strategy in self._strategies:
            try:
                partial = strategy.parse(soup, url)
                combined.merge(partial, strategy.name, strategy.weight)
            except Exception:
                continue
            if combined.confidence >= self._confidence_threshold:
                break
        return combined

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
        return output
