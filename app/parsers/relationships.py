"""Relationship Engine — generic entity-to-entity relationship detection.

Discovers how extracted entities (services, pricing, plans, offers, reviews,
locations, features, FAQs) relate to each other using:

1. **Name matching** — direct key-to-key matches (e.g. services[].name ↔ pricing[].service_name)
2. **Text overlap** — entity names appearing in other entities' text fields
3. **DOM proximity** — items sharing the same parent container in the DOM
4. **Plan-feature dereferencing** — plans[].features strings matched to features[].name

No CSS class names. No company-specific logic. Fully generic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from app.parsers.strategy import ParsedResult


@dataclass
class Relationship:
    """A single directional relationship between two extracted entities.

    Attributes
    ----------
    source_type:   Entity type of the source (e.g. "service", "plan", "location").
    source_value:  Identifying value of the source (e.g. service name).
    target_type:   Entity type of the target (e.g. "pricing", "feature", "offer").
    target_value:  Identifying value of the target (e.g. price service_name).
    relation:      Semantic relation label (e.g. "has_price", "has_feature").
    confidence:    Float in [0, 1]. Higher = more trustworthy.
    method:        How the relationship was detected.
    """

    source_type: str
    source_value: str
    target_type: str
    target_value: str
    relation: str
    confidence: float
    method: str = "name_match"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "source_type": self.source_type,
            "source_value": self.source_value,
            "target_type": self.target_type,
            "target_value": self.target_value,
            "relation": self.relation,
            "confidence": round(self.confidence, 4),
            "method": self.method,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d


# ---------------------------------------------------------------------------
# Relation labels
# ---------------------------------------------------------------------------

REL_HAS_PRICE = "has_price"
REL_HAS_OFFER = "has_offer"
REL_HAS_FEATURE = "has_feature"
REL_HAS_LOCATION = "has_location"
REL_HAS_REVIEW = "has_review"
REL_HAS_SERVICE = "has_service"
REL_HAS_PLAN = "has_plan"
REL_HAS_FAQ = "has_faq"
REL_IS_ABOUT = "is_about"


# ---------------------------------------------------------------------------
# Entity type constants (for source_type / target_type)
# ---------------------------------------------------------------------------

ENT_SERVICE = "service"
ENT_PRICING = "pricing"
ENT_PLAN = "plan"
ENT_OFFER = "offer"
ENT_REVIEW = "review"
ENT_FEATURE = "feature"
ENT_LOCATION = "location"
ENT_FAQ = "faq"
ENT_MEDIA = "media"


# ---------------------------------------------------------------------------
# Container tags (elements that define a logical grouping region)
# ---------------------------------------------------------------------------

_CONTAINER_TAGS = frozenset(
    {
        "div",
        "section",
        "article",
        "main",
        "aside",
        "header",
        "footer",
    }
)


class RelationshipEngine:
    """Detect relationships between extracted entities.

    Usage
    -----
    >>> engine = RelationshipEngine()
    >>> rels = engine.run(result, soup)
    >>> result.relationships = rels
    """

    # Minimum text match length to avoid false positives
    _MIN_OVERLAP_LEN: int = 4

    def run(
        self,
        result: ParsedResult,
        soup: BeautifulSoup | None = None,
    ) -> list[Relationship]:
        """Run all relationship detection strategies.

        Parameters
        ----------
        result: The fully merged ParsedResult.
        soup:   The original BeautifulSoup (required for DOM proximity).

        Returns
        -------
        A list of detected Relationship objects (deduplicated).
        """
        rels: list[Relationship] = []

        # Strategy 1 — Name matching (highest confidence, no soup needed)
        self._match_services_pricing(result, rels)
        self._match_plans_features(result, rels)
        self._match_plans_services(result, rels)
        self._match_offers_services(result, rels)
        self._match_reviews_services(result, rels)
        self._match_locations_services(result, rels)
        self._match_faq_services(result, rels)
        self._match_pricing_plans(result, rels)

        # Strategy 2 — DOM proximity (medium confidence, requires soup)
        if soup is not None:
            self._match_by_dom_proximity(result, soup, rels)

        return self._deduplicate(rels)

    # ------------------------------------------------------------------
    # Name-matching helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _match_services_pricing(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Service ↔ Pricing: match services[].name with pricing[].service_name."""
        service_names = {s["name"] for s in result.services if s.get("name")}
        for price in result.pricing:
            pn = price.get("service_name")
            if not pn:
                continue
            # Exact match
            if pn in service_names:
                rels.append(
                    Relationship(
                        ENT_SERVICE,
                        pn,
                        ENT_PRICING,
                        pn,
                        REL_HAS_PRICE,
                        0.92,
                        "name_match",
                        {"match": "exact"},
                    )
                )
            else:
                # Partial / substring match
                matched = _best_substring_match(pn, service_names, min_ratio=0.4)
                if matched:
                    rels.append(
                        Relationship(
                            ENT_SERVICE,
                            matched,
                            ENT_PRICING,
                            pn,
                            REL_HAS_PRICE,
                            0.60,
                            "text_overlap",
                            {
                                "match": "partial",
                                "match_detail": f"'{pn}' contained in '{matched}'",
                            },
                        )
                    )

    @staticmethod
    def _match_plans_features(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Plan ↔ Features: plans[].features strings matched to features[].name."""
        feature_names = {f["name"] for f in result.features if f.get("name")}
        if not feature_names:
            return
        for plan in result.plans:
            pn = plan.get("plan_name")
            if not pn:
                continue
            plan_features: list[str] = plan.get("features", []) or []
            for pf in plan_features:
                if pf in feature_names:
                    rels.append(
                        Relationship(
                            ENT_PLAN,
                            pn,
                            ENT_FEATURE,
                            pf,
                            REL_HAS_FEATURE,
                            0.95,
                            "name_match",
                            {"match": "exact"},
                        )
                    )
                else:
                    matched = _best_substring_match(pf, feature_names, min_ratio=0.4)
                    if matched:
                        rels.append(
                            Relationship(
                                ENT_PLAN,
                                pn,
                                ENT_FEATURE,
                                matched,
                                REL_HAS_FEATURE,
                                0.55,
                                "text_overlap",
                                {"match": "partial"},
                            )
                        )

    @staticmethod
    def _match_plans_services(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Plan ↔ Service: plans[].plan_name may reference a service name."""
        service_names = {s["name"] for s in result.services if s.get("name")}
        if not service_names:
            return
        for plan in result.plans:
            pn = plan.get("plan_name")
            if not pn:
                continue
            if pn in service_names:
                rels.append(
                    Relationship(
                        ENT_PLAN,
                        pn,
                        ENT_SERVICE,
                        pn,
                        REL_HAS_SERVICE,
                        0.90,
                        "name_match",
                        {"match": "exact"},
                    )
                )
            else:
                matched = _best_substring_match(pn, service_names, min_ratio=0.4)
                if matched:
                    rels.append(
                        Relationship(
                            ENT_PLAN,
                            pn,
                            ENT_SERVICE,
                            matched,
                            REL_HAS_SERVICE,
                            0.55,
                            "text_overlap",
                            {"match": "partial"},
                        )
                    )

    @staticmethod
    def _match_offers_services(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Offer ↔ Service: offers referenced by service or plan context."""
        offers = result.offers
        if not offers:
            return
        service_names = {s["name"] for s in result.services if s.get("name")}
        plan_names = {p["plan_name"] for p in result.plans if p.get("plan_name")}
        all_names = service_names | plan_names

        for offer in offers:
            title = offer.get("title") or offer.get("offer_title")
            if not title:
                continue
            title_lower = title.lower()
            for name in all_names:
                # Check if offer title contains the service/plan name
                if name.lower() in title_lower:
                    rels.append(
                        Relationship(
                            ENT_SERVICE,
                            name,
                            ENT_OFFER,
                            title,
                            REL_HAS_OFFER,
                            0.70,
                            "text_overlap",
                        )
                    )

    @staticmethod
    def _match_reviews_services(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Review ↔ Service: review title or body references a service."""
        reviews = result.reviews
        if not reviews:
            return
        service_names = {s["name"] for s in result.services if s.get("name")}
        if not service_names:
            return

        for review in reviews:
            rev_title = review.get("title") or ""
            rev_body = review.get("body") or ""
            rev_text = f"{rev_title} {rev_body}".lower()
            for sn in service_names:
                if sn.lower() in rev_text:
                    rels.append(
                        Relationship(
                            ENT_SERVICE,
                            sn,
                            ENT_REVIEW,
                            rev_title,
                            REL_HAS_REVIEW,
                            0.65,
                            "text_overlap",
                        )
                    )

    @staticmethod
    def _match_locations_services(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Location ↔ Service: location name appears in service context."""
        locations = result.locations
        if not locations:
            return
        for loc in locations:
            loc_name = loc.get("name")
            if not loc_name:
                continue
            loc_lower = loc_name.lower()
            for svc in result.services:
                svc_name = svc.get("name", "")
                svc_desc = svc.get("description", "")
                svc_cat = svc.get("category", "")
                context = f"{svc_name} {svc_desc} {svc_cat}".lower()
                if loc_lower in context:
                    rels.append(
                        Relationship(
                            ENT_SERVICE,
                            svc_name,
                            ENT_LOCATION,
                            loc_name,
                            REL_HAS_LOCATION,
                            0.60,
                            "text_overlap",
                        )
                    )

    @staticmethod
    def _match_faq_services(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """FAQ ↔ Service: FAQ content title/summary mentions a service name."""
        faq_items = [
            c
            for c in result.content
            if c.get("content_type") == "faq" and (c.get("title") or c.get("summary"))
        ]
        if not faq_items:
            return
        service_names = {s["name"] for s in result.services if s.get("name")}
        if not service_names:
            return

        for faq in faq_items:
            faq_text = f"{faq.get('title', '')} {faq.get('summary', '')}".lower()
            for sn in service_names:
                if sn.lower() in faq_text:
                    rels.append(
                        Relationship(
                            ENT_FAQ,
                            faq.get("title", ""),
                            ENT_SERVICE,
                            sn,
                            REL_IS_ABOUT,
                            0.65,
                            "text_overlap",
                        )
                    )

    @staticmethod
    def _match_pricing_plans(
        result: ParsedResult,
        rels: list[Relationship],
    ) -> None:
        """Pricing → Plan: pricing.subscription_plans keys match plans[].plan_name."""
        plan_names = {p["plan_name"] for p in result.plans if p.get("plan_name")}
        if not plan_names:
            return
        for price in result.pricing:
            subs = price.get("subscription_plans", {}) or {}
            svc_name = price.get("service_name", "")
            for plan_key in subs:
                if plan_key in plan_names:
                    rels.append(
                        Relationship(
                            ENT_PRICING,
                            svc_name,
                            ENT_PLAN,
                            plan_key,
                            REL_HAS_PLAN,
                            0.88,
                            "name_match",
                        )
                    )
                else:
                    matched = _best_substring_match(plan_key, plan_names, min_ratio=0.4)
                    if matched:
                        rels.append(
                            Relationship(
                                ENT_PRICING,
                                svc_name,
                                ENT_PLAN,
                                matched,
                                REL_HAS_PLAN,
                                0.55,
                                "text_overlap",
                            )
                        )

    # ------------------------------------------------------------------
    # DOM proximity detection
    # ------------------------------------------------------------------

    def _match_by_dom_proximity(
        self,
        result: ParsedResult,
        soup: BeautifulSoup,
        rels: list[Relationship],
    ) -> None:
        """Group entities by their DOM container and create relations within groups.

        For each entity type, we extract identifying text and search for it
        in the soup.  All entities whose identifying text appears inside the
        same container element are linked.
        """
        entity_groups: dict[int, list[dict[str, str]]] = {}

        # Collect text -> entity mappings for each entity type
        for svc in result.services:
            self._add_to_container_groups(
                soup,
                svc.get("name", ""),
                ENT_SERVICE,
                "name",
                entity_groups,
            )
        for price in result.pricing:
            self._add_to_container_groups(
                soup,
                price.get("service_name", ""),
                ENT_PRICING,
                "service_name",
                entity_groups,
            )
        for plan in result.plans:
            self._add_to_container_groups(
                soup,
                plan.get("plan_name", ""),
                ENT_PLAN,
                "plan_name",
                entity_groups,
            )
        for offer in result.offers:
            self._add_to_container_groups(
                soup,
                offer.get("title", ""),
                ENT_OFFER,
                "title",
                entity_groups,
            )
        for review in result.reviews:
            self._add_to_container_groups(
                soup,
                review.get("title", ""),
                ENT_REVIEW,
                "title",
                entity_groups,
            )
        for feature in result.features:
            self._add_to_container_groups(
                soup,
                feature.get("name", ""),
                ENT_FEATURE,
                "name",
                entity_groups,
            )
        for loc in result.locations:
            self._add_to_container_groups(
                soup,
                loc.get("name", ""),
                ENT_LOCATION,
                "name",
                entity_groups,
            )

        # Generate relationships between entities in the same container
        self._create_relations_from_groups(entity_groups, rels)

    @staticmethod
    def _add_to_container_groups(
        soup: BeautifulSoup,
        text: str,
        entity_type: str,
        value_key: str,
        groups: dict[int, list[dict[str, str]]],
    ) -> None:
        """Find the container element for a piece of entity text and register it."""
        if not text or len(text) < 3:
            return
        container = _find_container_for_text(soup, text)
        if container is None:
            return
        cid = id(container)
        if cid not in groups:
            groups[cid] = []
        groups[cid].append(
            {
                "type": entity_type,
                "value": text,
                "value_key": value_key,
            }
        )

    @staticmethod
    def _create_relations_from_groups(
        groups: dict[int, list[dict[str, str]]],
        rels: list[Relationship],
    ) -> None:
        """Within each container group, generate typed relationships."""
        # Define which entity pairs to link within a container
        relation_map: list[tuple[str, str, str, float]] = [
            (ENT_SERVICE, ENT_PRICING, REL_HAS_PRICE, 0.55),
            (ENT_SERVICE, ENT_OFFER, REL_HAS_OFFER, 0.50),
            (ENT_SERVICE, ENT_REVIEW, REL_HAS_REVIEW, 0.50),
            (ENT_SERVICE, ENT_LOCATION, REL_HAS_LOCATION, 0.50),
            (ENT_PLAN, ENT_PRICING, REL_HAS_PRICE, 0.55),
            (ENT_PLAN, ENT_FEATURE, REL_HAS_FEATURE, 0.55),
            (ENT_PLAN, ENT_OFFER, REL_HAS_OFFER, 0.50),
            (ENT_PRICING, ENT_PLAN, REL_HAS_PLAN, 0.50),
            (ENT_FAQ, ENT_SERVICE, REL_IS_ABOUT, 0.45),
        ]

        for container_id, entities in groups.items():
            # Build lookup by type
            by_type: dict[str, list[str]] = {}
            for ent in entities:
                et = ent["type"]
                if et not in by_type:
                    by_type[et] = []
                by_type[et].append(ent["value"])

            for src_type, tgt_type, relation, conf in relation_map:
                sources = by_type.get(src_type, [])
                targets = by_type.get(tgt_type, [])
                if not sources or not targets:
                    continue
                for src_val in sources:
                    for tgt_val in targets:
                        # Skip self-relations
                        if src_type == tgt_type and src_val == tgt_val:
                            continue
                        # Skip if this exact relation already exists
                        if _has_relation(rels, src_type, src_val, tgt_type, tgt_val, relation):
                            continue
                        rels.append(
                            Relationship(
                                src_type,
                                src_val,
                                tgt_type,
                                tgt_val,
                                relation,
                                conf,
                                "dom_proximity",
                                {"container_id": container_id},
                            )
                        )

    # ------------------------------------------------------------------
    # Dedup
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(rels: list[Relationship]) -> list[Relationship]:
        """Remove duplicates, keeping the highest-confidence version."""
        seen: dict[tuple[str, str, str, str, str], Relationship] = {}
        for r in rels:
            key = (r.source_type, r.source_value, r.target_type, r.target_value, r.relation)
            if key not in seen or r.confidence > seen[key].confidence:
                seen[key] = r
        return sorted(seen.values(), key=lambda r: r.confidence, reverse=True)


# ---------------------------------------------------------------------------
# DOM helper functions
# ---------------------------------------------------------------------------


def _find_container_for_text(soup: BeautifulSoup, text: str) -> Tag | None:
    """Find the nearest container element (div/section/article/etc.) that
    contains the given text in the DOM."""
    text_lower = text.lower().strip()
    if not text_lower or len(text_lower) < 3:
        return None

    # Search for text nodes containing this text
    for tag in soup.find_all(string=lambda s: text_lower in s.lower()):
        parent = tag.parent
        if not isinstance(parent, Tag):
            continue
        # Walk up to find a container element
        container = _nearest_container(parent)
        if container is not None:
            return container

    return None


def _nearest_container(tag: Tag) -> Tag | None:
    """Walk up from a tag to find the nearest container element.

    A container is any element that groups content: div, section, article,
    main, aside, header, or footer.  If the tag itself is a container,
    return it.  Otherwise return the first container ancestor.
    """
    current: Tag | None = tag
    while current is not None:
        if current.name in _CONTAINER_TAGS:
            return current
        current = current.parent if isinstance(current.parent, Tag) else None
    return None


def _best_substring_match(
    needle: str,
    candidates: set[str],
    min_ratio: float = 0.3,
) -> str | None:
    """Find the candidate that is a substring/superstring match for needle.

    Returns the best-matching candidate, or None if no match meets min_ratio.
    The ratio is max(len(overlap)/len(needle), len(overlap)/len(candidate)).
    """
    if not needle or not candidates:
        return None
    needle_lower = needle.lower()
    best: tuple[str | None, float] = (None, 0.0)

    for cand in candidates:
        if not cand:
            continue
        cand_lower = cand.lower()
        # Exact case-insensitive match
        if needle_lower == cand_lower:
            return cand
        # Substring
        if needle_lower in cand_lower:
            ratio = len(needle) / len(cand)
            if ratio > best[1]:
                best = (cand, ratio)
        elif cand_lower in needle_lower:
            ratio = len(cand) / len(needle)
            if ratio > best[1]:
                best = (cand, ratio)

    # Word-level overlap: count shared words
    if best[1] < min_ratio:
        needle_words = set(needle_lower.split())
        for cand in candidates:
            cand_words = set(cand.lower().split())
            overlap = needle_words & cand_words
            if overlap:
                # Use Jaccard-like similarity
                union = needle_words | cand_words
                ratio = len(overlap) / len(union) if union else 0.0
                if ratio > best[1]:
                    best = (cand, ratio)

    return best[0] if best[1] >= min_ratio else None


def _has_relation(
    rels: list[Relationship],
    src_type: str,
    src_val: str,
    tgt_type: str,
    tgt_val: str,
    relation: str,
) -> bool:
    """Check if a relationship already exists in the list."""
    key = (src_type, src_val, tgt_type, tgt_val, relation)
    for r in rels:
        rk = (r.source_type, r.source_value, r.target_type, r.target_value, r.relation)
        if rk == key:
            return True
    return False
