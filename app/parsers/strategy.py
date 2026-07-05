from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Strategy confidence baseline — used when a strategy doesn't supply its own.
# Higher weight  →  more trustworthy extraction method.
# ---------------------------------------------------------------------------
STRATEGY_CONFIDENCE: dict[str, float] = {
    "json_ld": 0.95,
    "multi_pass": 0.90,
    "schema_org": 0.85,
    "microdata": 0.80,
    "semantic_html": 0.70,
    "metadata": 0.65,
    "generic_dom_heuristic": 0.55,
    "generic_css_pattern": 0.50,
    "regex_pattern": 0.35,
}


def _strategy_confidence(strategy_name: str) -> float:
    """Return the baseline confidence for a given strategy name."""
    base = strategy_name.split(":")[0]
    return STRATEGY_CONFIDENCE.get(base, 0.40)


# ---------------------------------------------------------------------------
# FieldValue — wraps a single extracted scalar with full provenance metadata
# ---------------------------------------------------------------------------


@dataclass
class FieldValue:
    """
    A single extracted field value with provenance and confidence metadata.

    Attributes
    ----------
    value:                The extracted value (str, float, etc.).
    confidence:           Float in [0, 1].  Higher = more trustworthy.
    extraction_strategy:  Name of the strategy that produced this value.
    pass_number:          Which pass produced this (1-6 for MultiPass, 0 otherwise).
    source_url:           The URL of the page this was extracted from.
    extraction_timestamp: UTC ISO-8601 timestamp of when extraction occurred.
    """

    value: Any
    confidence: float
    extraction_strategy: str
    pass_number: int = 0
    source_url: str = ""
    extraction_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "extraction_strategy": self.extraction_strategy,
            "pass_number": self.pass_number,
            "source_url": self.source_url,
            "extraction_timestamp": self.extraction_timestamp,
        }

    def beats(self, other: FieldValue) -> bool:
        """Return True if self has strictly higher confidence than other."""
        return self.confidence > other.confidence


# ---------------------------------------------------------------------------
# FieldedResult — parallel store of FieldValue objects for every parsed field
# ---------------------------------------------------------------------------

_SCALAR_FIELDS = (
    "company_name",
    "description",
    "logo",
    "industry",
    "headquarters",
    "contact_email",
    "contact_phone",
)


@dataclass
class FieldedResult:
    """
    Stores a FieldValue per field, enabling field-level confidence comparison
    across multiple extraction strategies.
    """

    company_name: FieldValue | None = None
    description: FieldValue | None = None
    logo: FieldValue | None = None
    industry: FieldValue | None = None
    headquarters: FieldValue | None = None
    contact_email: FieldValue | None = None
    contact_phone: FieldValue | None = None
    social_links: dict[str, FieldValue] = field(default_factory=dict)
    services: list[FieldValue] = field(default_factory=list)
    pricing: list[FieldValue] = field(default_factory=list)
    content: list[FieldValue] = field(default_factory=list)
    social_profiles: list[FieldValue] = field(default_factory=list)

    def set_scalar(
        self,
        field_name: str,
        value: Any,
        strategy: str,
        pass_number: int = 0,
        source_url: str = "",
        confidence: float | None = None,
    ) -> None:
        """Set a scalar field only if the new value has higher confidence."""
        if not value:
            return
        conf = confidence if confidence is not None else _strategy_confidence(strategy)
        fv = FieldValue(
            value=value,
            confidence=conf,
            extraction_strategy=strategy,
            pass_number=pass_number,
            source_url=source_url,
        )
        existing: FieldValue | None = getattr(self, field_name, None)
        if existing is None or fv.beats(existing):
            setattr(self, field_name, fv)

    def set_social_link(
        self,
        platform: str,
        url: str,
        strategy: str,
        pass_number: int = 0,
        source_url: str = "",
        confidence: float | None = None,
    ) -> None:
        conf = confidence if confidence is not None else _strategy_confidence(strategy)
        fv = FieldValue(
            value=url,
            confidence=conf,
            extraction_strategy=strategy,
            pass_number=pass_number,
            source_url=source_url,
        )
        existing = self.social_links.get(platform)
        if existing is None or fv.beats(existing):
            self.social_links[platform] = fv

    def add_list_item(
        self,
        list_name: str,
        item: dict[str, Any],
        dedup_key: str,
        strategy: str,
        pass_number: int = 0,
        source_url: str = "",
        confidence: float | None = None,
    ) -> None:
        """Add an item to a list field if the dedup key is not already present."""
        conf = confidence if confidence is not None else _strategy_confidence(strategy)
        items: list[FieldValue] = getattr(self, list_name)
        key_val = item.get(dedup_key)
        if not key_val:
            return
        if any(fv.value.get(dedup_key) == key_val for fv in items):
            return
        fv = FieldValue(
            value=item,
            confidence=conf,
            extraction_strategy=strategy,
            pass_number=pass_number,
            source_url=source_url,
        )
        items.append(fv)

    def raw(self, field_name: str) -> Any:
        fv: FieldValue | None = getattr(self, field_name, None)
        return fv.value if fv else None

    def raw_social_links(self) -> dict[str, str]:
        return {k: fv.value for k, fv in self.social_links.items()}

    def raw_list(self, list_name: str) -> list[dict[str, Any]]:
        return [fv.value for fv in getattr(self, list_name)]

    def to_scored_dict(self) -> dict[str, Any]:
        """Return the full field-level confidence map."""
        out: dict[str, Any] = {}
        for f in _SCALAR_FIELDS:
            fv: FieldValue | None = getattr(self, f, None)
            out[f] = fv.to_dict() if fv else None
        out["social_links"] = {k: fv.to_dict() for k, fv in self.social_links.items()}
        for lst in ("services", "pricing", "content", "social_profiles"):
            out[lst] = [fv.to_dict() for fv in getattr(self, lst)]
        return out


# ---------------------------------------------------------------------------
# ParsedResult — unchanged public API; FieldedResult lives inside it
# ---------------------------------------------------------------------------


@dataclass
class ParsedResult:
    # Scalar fields — raw values, preserved for full backward compatibility
    company_name: str | None = None
    description: str | None = None
    logo: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    social_links: dict[str, str] = field(default_factory=dict)
    services: list[dict[str, Any]] = field(default_factory=list)
    pricing: list[dict[str, Any]] = field(default_factory=list)
    content: list[dict[str, Any]] = field(default_factory=list)
    social_profiles: list[dict[str, str | None]] = field(default_factory=list)
    confidence: float = 0.0
    strategy_results: dict[str, float] = field(default_factory=dict)

    # Field-level confidence store — new, opt-in, never breaks existing callers
    _fielded: FieldedResult = field(default_factory=FieldedResult, repr=False, compare=False)

    def __post_init__(self) -> None:
        """
        Seed _fielded for any scalar values set directly at construction time.
        These get confidence=1.0 (the "ground truth" sentinel) so that
        merge() never overwrites them — preserving the original contract.
        """
        _scalar_map = (
            "company_name",
            "description",
            "logo",
            "industry",
            "headquarters",
            "contact_email",
            "contact_phone",
        )
        for attr in _scalar_map:
            val = getattr(self, attr)
            if val:
                self._fielded.set_scalar(attr, val, "initial", confidence=1.0)
        for platform, url in self.social_links.items():
            self._fielded.set_social_link(platform, url, "initial", confidence=1.0)

    # ------------------------------------------------------------------
    # Confidence-aware merge
    # ------------------------------------------------------------------

    def merge(self, other: ParsedResult, strategy_name: str, weight: float) -> None:
        conf = _strategy_confidence(strategy_name)

        # Scalar fields: replace if incoming strategy has strictly higher confidence
        _scalar_map = (
            "company_name",
            "description",
            "logo",
            "industry",
            "headquarters",
            "contact_email",
            "contact_phone",
        )
        for attr in _scalar_map:
            incoming_val = getattr(other, attr)
            if not incoming_val:
                continue
            existing_fv: FieldValue | None = getattr(self._fielded, attr)
            if existing_fv is None or conf > existing_fv.confidence:
                setattr(self, attr, incoming_val)
                self._fielded.set_scalar(attr, incoming_val, strategy_name, confidence=conf)

        # Social links: replace if higher confidence
        for k, v in other.social_links.items():
            existing_fv = self._fielded.social_links.get(k)
            if existing_fv is None or conf > existing_fv.confidence:
                self.social_links[k] = v
                self._fielded.set_social_link(k, v, strategy_name, confidence=conf)

        # List fields: add new items only (deduplicated by key)
        existing_svc_names = {s.get("name") for s in self.services}
        for svc in other.services:
            if svc.get("name") and svc["name"] not in existing_svc_names:
                self.services.append(svc)
                existing_svc_names.add(svc["name"])
                self._fielded.add_list_item("services", svc, "name", strategy_name, confidence=conf)

        existing_price_names = {p.get("service_name") for p in self.pricing}
        for price in other.pricing:
            if price.get("service_name") and price["service_name"] not in existing_price_names:
                self.pricing.append(price)
                existing_price_names.add(price["service_name"])
                self._fielded.add_list_item(
                    "pricing", price, "service_name", strategy_name, confidence=conf
                )

        existing_titles = {c.get("title") for c in self.content}
        for item in other.content:
            if item.get("title") and item["title"] not in existing_titles:
                self.content.append(item)
                existing_titles.add(item["title"])
                self._fielded.add_list_item(
                    "content", item, "title", strategy_name, confidence=conf
                )

        existing_platforms = {p.get("platform") for p in self.social_profiles}
        for profile in other.social_profiles:
            if profile.get("platform") and profile["platform"] not in existing_platforms:
                self.social_profiles.append(profile)
                existing_platforms.add(profile["platform"])
                self._fielded.add_list_item(
                    "social_profiles", profile, "platform", strategy_name, confidence=conf
                )

        # Overall page confidence — unchanged behaviour
        self.strategy_results[strategy_name] = weight
        self.confidence = min(1.0, self.confidence + weight)

    # ------------------------------------------------------------------
    # New opt-in field-level metadata access
    # ------------------------------------------------------------------

    def get_field_confidence(self, field_name: str) -> FieldValue | None:
        """Return the FieldValue (with full provenance) for a scalar field."""
        return getattr(self._fielded, field_name, None)

    def to_scored_dict(self) -> dict[str, Any]:
        """Return the full field-level confidence map for every extracted field."""
        return self._fielded.to_scored_dict()

    # ------------------------------------------------------------------
    # Existing to_*_dict() methods — completely unchanged
    # ------------------------------------------------------------------

    def to_company_dict(self) -> dict[str, Any]:
        return {
            "url": "",
            "name": self.company_name,
            "logo": self.logo,
            "description": self.description,
            "industry": self.industry,
            "headquarters": self.headquarters,
            "operating_countries": [],
            "operating_cities": [],
            "service_categories": [],
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "social_links": self.social_links,
        }

    def to_service_dict(self) -> dict[str, Any]:
        return {"url": "", "services": self.services}

    def to_pricing_dict(self) -> dict[str, Any]:
        return {"url": "", "pricing": self.pricing}

    def to_content_dict(self) -> dict[str, Any]:
        return {"url": "", "content": self.content}

    def to_social_dict(self) -> dict[str, Any]:
        profiles = list(self.social_profiles)
        existing_platforms = {p.get("platform") for p in profiles}
        for platform, url in self.social_links.items():
            if platform not in existing_platforms:
                profiles.append(
                    {
                        "platform": platform,
                        "profile_url": url,
                        "username": None,
                    }
                )
                existing_platforms.add(platform)
        return {"url": "", "social_profiles": profiles}


# ---------------------------------------------------------------------------
# ParsingStrategy ABC — completely unchanged
# ---------------------------------------------------------------------------


class ParsingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def weight(self) -> float: ...

    @abstractmethod
    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult: ...

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def _text(self, soup: BeautifulSoup | Tag, selector: str) -> str | None:
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None

    def _texts(self, soup: BeautifulSoup | Tag, selector: str) -> list[str]:
        return [el.get_text(strip=True) for el in soup.select(selector)]

    def _attr(self, soup: BeautifulSoup | Tag, selector: str, attribute: str) -> str | None:
        element = soup.select_one(selector)
        value = element.get(attribute) if element else None
        if isinstance(value, list):
            return str(value[0]) if value else None
        return str(value) if value is not None else None

    def _attrs(self, soup: BeautifulSoup | Tag, selector: str, attribute: str) -> list[str]:
        result: list[str] = []
        for el in soup.select(selector):
            value = el.get(attribute)
            if isinstance(value, list):
                if value:
                    result.append(str(value[0]))
            elif value is not None:
                result.append(str(value))
        return result
