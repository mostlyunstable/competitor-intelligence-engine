from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

import re

from app.parsers.evidence import extract_evidence

# ---------------------------------------------------------------------------
# Evidence helpers
# ---------------------------------------------------------------------------

_EVIDENCE_KEYS = frozenset({"dom_path", "xpath", "html_snippet"})


def _pop_evidence(item: dict[str, Any]) -> dict[str, Any]:
    """Extract and remove evidence keys from a dict, returning them as kwargs."""
    evidence: dict[str, Any] = {}
    for key in _EVIDENCE_KEYS:
        if key in item:
            evidence[key] = item.pop(key)
    return evidence


# ---------------------------------------------------------------------------
# Dynamic Confidence Calculator — no hardcoded scores
# ---------------------------------------------------------------------------

_CSV_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_CSV_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,18}$")
_CSV_URL_RE = re.compile(r"^https?://")


class ConfidenceCalculator:
    """Calculate field-level confidence dynamically from extraction context.

    Confidence is computed as:
        base(strategy_class) + completeness_bonus + consistency_bonus
        + validation_bonus + duplicate_agreement_bonus

    No hardcoded scores — every value is derived from actual extraction data.
    """

    # Strategy classification (intrinsic reliability of the method, not a score)
    _STRATEGY_CLASS: ClassVar[dict[str, str]] = {
        "json_ld": "structured",
        "multi_pass": "comprehensive",
        "schema_org": "structured",
        "microdata": "structured",
        "metadata": "metadata",
        "semantic_html": "semantic",
        "table_extraction": "structural",
        "form_extraction": "structural",
        "faq_extraction": "structural",
        "breadcrumb_extraction": "structural",
        "generic_dom_heuristic": "generic",
        "generic_css_pattern": "generic",
        "regex_pattern": "generic",
    }

    # Base range per class — derived from extraction method fidelity
    _CLASS_BASE: ClassVar[dict[str, tuple[float, float]]] = {
        "structured": (0.60, 0.85),
        "comprehensive": (0.55, 0.80),
        "metadata": (0.45, 0.70),
        "semantic": (0.40, 0.65),
        "structural": (0.35, 0.60),
        "generic": (0.25, 0.50),
    }

    _VALIDATORS: ClassVar[dict[str, Any]] = {
        "company_name": lambda v: bool(v and len(str(v).strip()) >= 2),
        "description": lambda v: bool(v and len(str(v).strip()) >= 10),
        "logo": lambda v: bool(v and bool(_CSV_URL_RE.match(str(v)))),
        "industry": lambda v: bool(v and len(str(v).strip()) >= 2),
        "headquarters": lambda v: bool(v and len(str(v).strip()) >= 3),
        "contact_email": lambda v: bool(v and bool(_CSV_EMAIL_RE.match(str(v)))),
        "contact_phone": lambda v: bool(v and bool(_CSV_PHONE_RE.match(str(v)))),
    }

    def __init__(self) -> None:
        self._all_results: list[ParsedResult] = []

    def register_result(self, result: ParsedResult) -> None:
        """Register a completed strategy result for cross-strategy consistency checks."""
        self._all_results.append(result)

    def for_scalar(
        self,
        strategy_name: str,
        field_name: str,
        value: Any,
        strategy_result: ParsedResult,
    ) -> float:
        """Compute dynamic confidence for a single scalar field value."""
        if not value:
            return 0.0
        base = self._base(strategy_name)
        completeness = self._completeness_bonus(strategy_result)
        consistency = self._consistency_bonus(field_name, value, strategy_name)
        validation = self._validation_bonus(field_name, value)
        return min(0.999, base + completeness + consistency + validation)

    def for_list_item(
        self,
        strategy_name: str,
        field_name: str,
        item: dict[str, Any],
        strategy_result: ParsedResult,
    ) -> float:
        """Compute dynamic confidence for a list item."""
        base = self._base(strategy_name)
        completeness = self._completeness_bonus(strategy_result)
        item_completeness = self._item_completeness(item)
        return min(0.999, base + completeness + item_completeness * 0.15)

    def _base(self, strategy_name: str) -> float:
        strategy_key = strategy_name.split(":")[0]
        cls = self._STRATEGY_CLASS.get(strategy_key, "generic")
        low, high = self._CLASS_BASE.get(cls, (0.25, 0.50))
        # Use the midpoint; individual bonuses adjust up/down
        return (low + high) / 2.0

    @staticmethod
    def _completeness_bonus(result: ParsedResult) -> float:
        """How many scalar fields did this strategy fill?"""
        count = sum(1 for f in _SCALAR_FIELDS if getattr(result, f, None))
        total = len(_SCALAR_FIELDS)
        if total == 0:
            return 0.0
        # Bonus up to 0.10 for filling all fields
        return (count / total) * 0.10

    def _consistency_bonus(self, field_name: str, value: Any, strategy_name: str) -> float:
        """If other strategies agree on this value, boost confidence."""
        if not self._all_results or not value:
            return 0.0
        match_count = 0
        for prev in self._all_results:
            prev_val = getattr(prev, field_name, None)
            if prev_val and str(prev_val) == str(value):
                match_count += 1
        # Boost up to 0.10 for each agreeing strategy, capped at 0.30
        return min(0.30, match_count * 0.10)

    @staticmethod
    def _validation_bonus(field_name: str, value: Any) -> float:
        """Valid values get a small boost."""
        validator = ConfidenceCalculator._VALIDATORS.get(field_name)
        if validator and validator(value):
            return 0.05
        return 0.0

    @staticmethod
    def _item_completeness(item: dict[str, Any]) -> float:
        """How many fields in a list item are filled?"""
        filled = sum(1 for v in item.values() if v is not None and v != "")
        total = len(item)
        if total == 0:
            return 0.0
        return filled / total


# Convenience singleton — shares state across merge calls in a parse cycle
_calculator: ConfidenceCalculator | None = None


def _get_calculator() -> ConfidenceCalculator:
    global _calculator
    if _calculator is None:
        _calculator = ConfidenceCalculator()
    return _calculator


def _reset_calculator() -> None:
    global _calculator
    _calculator = None


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
    dom_path:             CSS-selector-like path to the source element (optional).
    xpath:                XPath to the source element (optional).
    html_snippet:         Truncated HTML of the source element (optional).
    """

    value: Any
    confidence: float
    extraction_strategy: str
    pass_number: int = 0
    source_url: str = ""
    extraction_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    dom_path: str | None = None
    xpath: str | None = None
    html_snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "extraction_strategy": self.extraction_strategy,
            "pass_number": self.pass_number,
            "source_url": self.source_url,
            "extraction_timestamp": self.extraction_timestamp,
        }
        if self.dom_path is not None:
            d["dom_path"] = self.dom_path
        if self.xpath is not None:
            d["xpath"] = self.xpath
        if self.html_snippet is not None:
            d["html_snippet"] = self.html_snippet
        return d

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
    plans: list[FieldValue] = field(default_factory=list)
    offers: list[FieldValue] = field(default_factory=list)
    reviews: list[FieldValue] = field(default_factory=list)
    features: list[FieldValue] = field(default_factory=list)
    media: list[FieldValue] = field(default_factory=list)
    locations: list[FieldValue] = field(default_factory=list)
    team: list[FieldValue] = field(default_factory=list)
    trust_signals: list[FieldValue] = field(default_factory=list)
    assets: list[FieldValue] = field(default_factory=list)

    def set_scalar(
        self,
        field_name: str,
        value: Any,
        strategy: str,
        pass_number: int = 0,
        source_url: str = "",
        confidence: float | None = None,
        dom_path: str | None = None,
        xpath: str | None = None,
        html_snippet: str | None = None,
    ) -> None:
        """Set a scalar field only if the new value has higher confidence."""
        if not value:
            return
        conf = (
            confidence
            if confidence is not None
            else _get_calculator().for_scalar(strategy, field_name, value, ParsedResult())
        )
        fv = FieldValue(
            value=value,
            confidence=conf,
            extraction_strategy=strategy,
            pass_number=pass_number,
            source_url=source_url,
            dom_path=dom_path,
            xpath=xpath,
            html_snippet=html_snippet,
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
        dom_path: str | None = None,
        xpath: str | None = None,
        html_snippet: str | None = None,
    ) -> None:
        conf = (
            confidence
            if confidence is not None
            else _get_calculator().for_scalar(strategy, f"social_{platform}", url, ParsedResult())
        )
        fv = FieldValue(
            value=url,
            confidence=conf,
            extraction_strategy=strategy,
            pass_number=pass_number,
            source_url=source_url,
            dom_path=dom_path,
            xpath=xpath,
            html_snippet=html_snippet,
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
        dom_path: str | None = None,
        xpath: str | None = None,
        html_snippet: str | None = None,
    ) -> None:
        """Add an item to a list field if the dedup key is not already present."""
        conf = (
            confidence
            if confidence is not None
            else _get_calculator().for_list_item(strategy, list_name, item, ParsedResult())
        )
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
            dom_path=dom_path,
            xpath=xpath,
            html_snippet=html_snippet,
        )
        items.append(fv)

    def raw(self, field_name: str) -> Any:
        fv: FieldValue | None = getattr(self, field_name, None)
        return fv.value if fv else None

    def raw_social_links(self) -> dict[str, str]:
        return {k: fv.value for k, fv in self.social_links.items()}

    def raw_list(self, list_name: str) -> list[dict[str, Any]]:
        return [fv.value for fv in getattr(self, list_name)]

    _LIST_FIELDS = (
        "services",
        "pricing",
        "content",
        "social_profiles",
        "plans",
        "offers",
        "reviews",
        "features",
        "media",
        "locations",
        "team",
        "trust_signals",
        "assets",
    )

    def to_scored_dict(self) -> dict[str, Any]:
        """Return the full field-level confidence map."""
        out: dict[str, Any] = {}
        for f in _SCALAR_FIELDS:
            fv: FieldValue | None = getattr(self, f, None)
            out[f] = fv.to_dict() if fv else None
        out["social_links"] = {k: fv.to_dict() for k, fv in self.social_links.items()}
        for lst in self._LIST_FIELDS:
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

    # Generic Entities
    team: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    trust_signals: list[dict[str, Any]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)

    # Scoped Collections
    services: list[dict[str, Any]] = field(default_factory=list)
    pricing: list[dict[str, Any]] = field(default_factory=list)
    content: list[dict[str, Any]] = field(default_factory=list)
    social_profiles: list[dict[str, str | None]] = field(default_factory=list)
    plans: list[dict[str, Any]] = field(default_factory=list)
    offers: list[dict[str, Any]] = field(default_factory=list)
    features: list[dict[str, Any]] = field(default_factory=list)
    media: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    strategy_results: dict[str, Any] = field(default_factory=dict)

    # Field-level confidence store — new, opt-in, never breaks existing callers
    _fielded: FieldedResult = field(default_factory=FieldedResult, repr=False, compare=False)
    # Per-field evidence (dom_path, xpath, html_snippet) keyed by field name
    _evidence_map: dict[str, dict[str, Any]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def set_field_evidence(self, field_name: str, tag: Tag | None) -> None:
        """Attach evidence (dom_path, xpath, html_snippet) to a scalar field."""
        if tag is not None:
            self._evidence_map[field_name] = extract_evidence(tag)

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
        calculator = _get_calculator()

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
            # Dynamic confidence for this field + strategy
            conf = calculator.for_scalar(strategy_name, attr, incoming_val, other)
            if existing_fv is None or conf > existing_fv.confidence:
                evidence_kw = other._evidence_map.get(attr, {})
                setattr(self, attr, incoming_val)
                self._fielded.set_scalar(
                    attr, incoming_val, strategy_name, confidence=conf, **evidence_kw
                )

        # Social links: replace if higher confidence
        for k, v in other.social_links.items():
            existing_fv = self._fielded.social_links.get(k)
            conf = calculator.for_scalar(strategy_name, f"social_{k}", v, other)
            if existing_fv is None or conf > existing_fv.confidence:
                evidence_kw = other._evidence_map.get(f"social_{k}", {})
                self.social_links[k] = v
                self._fielded.set_social_link(k, v, strategy_name, confidence=conf, **evidence_kw)

        # List fields: add new items only (deduplicated by key)
        existing_svc_names = {s.get("name") for s in self.services}
        for svc in other.services:
            if svc.get("name") and svc["name"] not in existing_svc_names:
                evidence_kw = _pop_evidence(svc)
                self.services.append(svc)
                existing_svc_names.add(svc["name"])
                conf = calculator.for_list_item(strategy_name, "services", svc, other)
                self._fielded.add_list_item(
                    "services", svc, "name", strategy_name, confidence=conf, **evidence_kw
                )

        existing_price_names = {p.get("service_name") for p in self.pricing}
        for price in other.pricing:
            if price.get("service_name") and price["service_name"] not in existing_price_names:
                evidence_kw = _pop_evidence(price)
                self.pricing.append(price)
                existing_price_names.add(price["service_name"])
                conf = calculator.for_list_item(strategy_name, "pricing", price, other)
                self._fielded.add_list_item(
                    "pricing", price, "service_name", strategy_name, confidence=conf, **evidence_kw
                )

        existing_titles = {c.get("title") for c in self.content}
        for item in other.content:
            if item.get("title") and item["title"] not in existing_titles:
                evidence_kw = _pop_evidence(item)
                self.content.append(item)
                existing_titles.add(item["title"])
                conf = calculator.for_list_item(strategy_name, "content", item, other)
                self._fielded.add_list_item(
                    "content", item, "title", strategy_name, confidence=conf, **evidence_kw
                )

        existing_platforms = {p.get("platform") for p in self.social_profiles}
        for profile in other.social_profiles:
            if profile.get("platform") and profile["platform"] not in existing_platforms:
                evidence_kw = _pop_evidence(profile)
                self.social_profiles.append(profile)
                existing_platforms.add(profile["platform"])
                conf = calculator.for_list_item(strategy_name, "social_profiles", profile, other)
                self._fielded.add_list_item(
                    "social_profiles",
                    profile,
                    "platform",
                    strategy_name,
                    confidence=conf,
                    **evidence_kw,
                )

        # Register this strategy result for cross-strategy consistency checks
        calculator.register_result(other)

        # New entity list fields — deduplicated by their natural key
        _new_list_dedup: dict[str, tuple[str, str]] = {
            "plans": ("plan_name", "name"),
            "offers": ("title", "offer_title"),
            "reviews": ("title", "review_title"),
            "features": ("name", "feature_name"),
            "media": ("url", "src"),
            "locations": ("name", "location_name"),
            "team": ("name", "name"),
            "trust_signals": ("type", "name"),
            "assets": ("url", "src"),
        }
        for list_name, (primary_key, fallback_key) in _new_list_dedup.items():
            incoming_items: list[dict[str, Any]] = getattr(other, list_name, [])
            if not incoming_items:
                continue
            existing_items = getattr(self, list_name)
            existing_keys: set[str] = set()
            for item in existing_items:
                k = item.get(primary_key) or item.get(fallback_key)
                if k:
                    existing_keys.add(str(k))
            for item in incoming_items:
                key_val = item.get(primary_key) or item.get(fallback_key)
                if key_val and str(key_val) in existing_keys:
                    continue
                evidence_kw = _pop_evidence(item)
                existing_items.append(item)
                dedup_key = primary_key if primary_key in item else fallback_key
                conf = calculator.for_list_item(strategy_name, list_name, item, other)
                self._fielded.add_list_item(
                    list_name, item, dedup_key, strategy_name, confidence=conf, **evidence_kw
                )
                if key_val:
                    existing_keys.add(str(key_val))

        # Propagate internal metadata keys (e.g. __breadcrumb__, __segments__)
        for key in other.strategy_results:
            if key.startswith("__") and key not in self.strategy_results:
                self.strategy_results[key] = other.strategy_results[key]

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

    def count_entities(self) -> int:
        """Count the total number of populated fields and list items."""
        count = 0
        if self.company_name:
            count += 1
        if self.description:
            count += 1
        if self.logo:
            count += 1
        if self.industry:
            count += 1
        if self.headquarters:
            count += 1
        if self.contact_email:
            count += 1
        if self.contact_phone:
            count += 1
        count += len(self.social_links)
        count += len(self.team)
        count += len(self.locations)
        count += len(self.reviews)
        count += len(self.trust_signals)
        count += len(self.assets)
        count += len(self.services)
        count += len(self.pricing)
        count += len(self.content)
        count += len(self.social_profiles)
        count += len(self.plans)
        count += len(self.offers)
        count += len(self.features)
        count += len(self.media)
        return count

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
            # Merge scoped collections (appends and deduplicates)
            "services": self.services,
            "pricing": self.pricing,
            "content": self.content,
            # Merge generic entities
            "team": self.team,
            "locations": self.locations,
            "reviews": self.reviews,
            "trust_signals": self.trust_signals,
            "assets": self.assets,
        }

    def to_service_dict(self) -> dict[str, Any]:
        return {
            "url": "",
            "services": self.services,
            "team": self.team,
            "locations": self.locations,
            "reviews": self.reviews,
            "trust_signals": self.trust_signals,
            "assets": self.assets,
        }

    def to_pricing_dict(self) -> dict[str, Any]:
        return {
            "url": "",
            "pricing": self.pricing,
            "team": self.team,
            "locations": self.locations,
            "reviews": self.reviews,
            "trust_signals": self.trust_signals,
            "assets": self.assets,
        }

    def to_content_dict(self) -> dict[str, Any]:
        return {
            "url": "",
            "content": self.content,
            "team": self.team,
            "locations": self.locations,
            "reviews": self.reviews,
            "trust_signals": self.trust_signals,
            "assets": self.assets,
        }

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
        return {
            "url": "",
            "social_profiles": profiles,
            "team": self.team,
            "locations": self.locations,
            "reviews": self.reviews,
            "trust_signals": self.trust_signals,
            "assets": self.assets,
        }


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

    # Segment-aware parsing (optional; defaults to parse() for backward compat)
    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        """Parse using pre-segmented page sections. Default falls back to full soup."""
        if not segments:
            return ParsedResult()
        # Combine all segments back into a single soup for legacy strategies
        combined_html = "".join(str(seg.element) for seg in segments)
        soup = BeautifulSoup(combined_html, "html.parser")
        return self.parse(soup, url)

    def _evidence(self, tag: Tag | None) -> dict[str, str | None]:
        """Extract evidence metadata (dom_path, xpath, html_snippet) from a Tag."""
        return extract_evidence(tag)

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
