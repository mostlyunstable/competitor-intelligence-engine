"""Entity Resolution Engine — deduplicate and canonicalize extracted entities.

Resolves variants like "Kitchen Cleaning", "Kitchen Deep Cleaning" and "Kitchen
Cleaning Service" into a single canonical entity using:

1. **Normalization** — lowercase, punctuation removal, whitespace collapse
2. **Abbreviation expansion** — HVAC → Heating Ventilation Air Conditioning
3. **Fuzzy matching** — token Jaccard similarity + Levenshtein distance
4. **Clustering** — greedy merging of similar names
5. **Canonicalization** — richest entity becomes the merged target
6. **Cross-reference update** — pricing[].service_name, plans[].features

No company-specific rules. No hardcoded selectors. Fully generic.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.parsers.strategy import ParsedResult

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_PUNCTUATION_RE = re.compile(f"[{re.escape(string.punctuation)}]+")
_WHITESPACE_RE = re.compile(r"\s+")

# Stop words removed entirely during comparison
_STOP_WORDS: frozenset[str] = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "in",
        "at",
        "to",
        "for",
        "with",
        "by",
        "on",
        "is",
        "are",
        "was",
        "were",
        "per",
        "its",
        "our",
        "your",
        "their",
        "this",
        "that",
        "these",
        "those",
    ]
)

# Generic qualifier words that don't carry entity identity (safe to drop)
_REMOVABLE_WORDS: frozenset[str] = frozenset(
    [
        "service",
        "services",
        "plan",
        "plans",
        "package",
        "packages",
        "tier",
        "tiers",
        "option",
        "options",
        "solution",
        "solutions",
        "program",
        "programs",
        "system",
        "systems",
        "type",
        "types",
        "category",
        "categories",
        "feature",
        "features",
        "product",
        "products",
    ]
)

# Industry-standard abbreviations (not company-specific)
_ABBREVIATIONS: dict[str, str] = {
    "hvac": "heating ventilation air conditioning",
    "ac": "air conditioning",
    "seo": "search engine optimization",
    "it": "information technology",
    "hr": "human resources",
    "diy": "do it yourself",
    "ui": "user interface",
    "ux": "user experience",
    "api": "application programming interface",
    "saas": "software as a service",
    "crm": "customer relationship management",
    "erp": "enterprise resource planning",
    "pos": "point of sale",
    "roi": "return on investment",
    "sla": "service level agreement",
    "qa": "quality assurance",
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "devops": "development operations",
    "bi": "business intelligence",
}


def normalize(name: str, *, expand_abbrevs: bool = True) -> str:
    """Normalize a name for comparison.

    Steps: lowercase, punctuation → space, expand abbreviations, remove
    stop/removable words, collapse whitespace, strip.
    """
    if not name:
        return ""
    s = name.lower()
    s = _PUNCTUATION_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()

    if expand_abbrevs:
        for abbr, expansion in _ABBREVIATIONS.items():
            # Replace standalone abbreviation tokens
            s = re.sub(rf"\b{re.escape(abbr)}\b", expansion, s)

    # Tokenize, remove stop words and removable words
    tokens = s.split()
    tokens = [t for t in tokens if t not in _STOP_WORDS and t not in _REMOVABLE_WORDS]
    return " ".join(tokens)


def levenshtein(a: str, b: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def name_similarity(a: str, b: str) -> float:
    """Compute a similarity score in [0, 1] between two entity names.

    Uses token Jaccard and token-level containment on normalized forms.
    Edit distance is deliberately excluded: it produces false positives
    when long shared substrings appear in unrelated names (e.g. "Basic
    Cleaning" vs "Deep Cleaning" both contain "cleaning").
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    na = normalize(a)
    nb = normalize(b)

    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    a_tokens = set(na.split())
    b_tokens = set(nb.split())

    if not a_tokens or not b_tokens:
        return 0.0

    # --- Token Jaccard ---
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    jaccard = len(intersection) / len(union) if union else 0.0

    # --- Token containment: all tokens of the shorter set appear in the longer ---
    # Only meaningful when one set is strictly smaller (avoids the degenerate
    # case where equal-size sets compare with themselves).
    containment = 0.0
    if len(a_tokens) != len(b_tokens):
        shorter_tokens = min(a_tokens, b_tokens, key=len)
        longer_tokens = max(a_tokens, b_tokens, key=len)
        containment = (
            len(shorter_tokens & longer_tokens) / len(shorter_tokens) if shorter_tokens else 0.0
        )

    # Exact containment (all tokens of one name are in the other) → strong signal
    if containment >= 0.80:
        return containment * 0.90

    return jaccard


# ---------------------------------------------------------------------------
# Entity resolution metadata
# ---------------------------------------------------------------------------

_ENTITY_KEYS: dict[str, tuple[str, ...]] = {
    "services": ("name",),
    "pricing": ("service_name",),
    "plans": ("plan_name", "name"),
    "offers": ("title", "offer_title"),
    "reviews": ("title", "review_title"),
    "features": ("name", "feature_name"),
    "media": ("url", "src"),
    "locations": ("name", "location_name"),
    "content": ("title",),
}

# Which lists reference other entity types (cross-references to update)
_CROSS_REFERENCE_UPDATES: list[tuple[str, str, str]] = [
    # (list_to_update, field_name, source_resolution_map)
    ("pricing", "service_name", "services"),
    ("plans", "features", "features"),
]


@dataclass
class ResolutionResult:
    """Result of resolving a single entity cluster.

    Attributes
    ----------
    canonical_name: The chosen canonical name.
    merged_indices: Indices of original items merged into this one.
    confidence:     How confident we are this merge is correct.
    method:         How the resolution was performed.
    """

    canonical_name: str
    merged_indices: list[int]
    confidence: float
    method: str
    enriched_fields: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------


class EntityResolver:
    """Resolve duplicate entity variants within a ParsedResult.

    Resolves services, pricing, plans, offers, reviews, features, media,
    locations, and content.  Updates cross-references so pricing entries
    still point to the correct service after resolution.
    """

    # Threshold for considering two names as the same entity
    SIMILARITY_THRESHOLD: float = 0.55

    # Minimum name length to attempt resolution (avoid single-char matches)
    MIN_NAME_LENGTH: int = 3

    def resolve(self, result: ParsedResult) -> ParsedResult:
        """Resolve duplicate entities across all lists in the result.

        Operates in-place for efficiency; also returns the result for
        chaining convenience.
        """
        # Phase 1 — Resolve each entity list independently
        resolution_maps: dict[str, dict[str, str]] = {}

        for list_name in (
            "services",
            "plans",
            "features",
            "locations",
            "reviews",
            "offers",
        ):
            items: list[dict[str, Any]] = getattr(result, list_name, [])
            keys = _ENTITY_KEYS.get(list_name, ("name",))
            if items and keys:
                resolution_maps[list_name] = self._resolve_list(items, keys, list_name)

        # Phase 2 — Update cross-references
        for list_name, ref_field, source_type in _CROSS_REFERENCE_UPDATES:
            target_items: list[dict[str, Any]] = getattr(result, list_name, [])
            name_map = resolution_maps.get(source_type, {})
            if name_map:
                self._update_cross_references(target_items, ref_field, name_map)

        # Phase 3 — Deduplicate after renaming
        for list_name in (
            "services",
            "pricing",
            "plans",
            "features",
            "locations",
            "reviews",
            "offers",
        ):
            items = getattr(result, list_name, [])
            keys = _ENTITY_KEYS.get(list_name, ("name",))
            if items and keys:
                self._deduplicate_list(items, keys)

        return result

    # ------------------------------------------------------------------
    # Resolution logic
    # ------------------------------------------------------------------

    def _resolve_list(
        self,
        items: list[dict[str, Any]],
        keys: tuple[str, ...],
        list_name: str,
    ) -> dict[str, str]:
        """Cluster similar items and return {original_name: canonical_name}."""
        if len(items) < 2:
            return {}

        # Build list of (index, primary_name)
        named_items: list[tuple[int, str]] = []
        for idx, item in enumerate(items):
            name = _first_value(item, keys)
            if name and len(name.strip()) >= self.MIN_NAME_LENGTH:
                named_items.append((idx, name.strip()))

        if len(named_items) < 2:
            return {}

        # Greedy clustering: sort by length (longest first so more descriptive
        # names become cluster seeds)
        named_items.sort(key=lambda x: len(x[1]), reverse=True)

        clusters: list[list[tuple[int, str]]] = []
        for idx, name in named_items:
            assigned = False
            for cluster in clusters:
                # Compare against the seed (first) item in the cluster
                seed_name = cluster[0][1]
                sim = name_similarity(name, seed_name)
                if sim >= self.SIMILARITY_THRESHOLD:
                    cluster.append((idx, name))
                    assigned = True
                    break
            if not assigned:
                clusters.append([(idx, name)])

        # Build resolution map and merge data
        result_map: dict[str, str] = {}
        for cluster in clusters:
            if len(cluster) < 2:
                continue  # singleton, no resolution needed
            self._merge_cluster(items, cluster, keys, list_name, result_map)

        return result_map

    # ------------------------------------------------------------------
    # Cluster merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_cluster(
        items: list[dict[str, Any]],
        cluster: list[tuple[int, str]],
        keys: tuple[str, ...],
        list_name: str,
        result_map: dict[str, str],
    ) -> None:
        """Merge a cluster of similar items into one canonical item."""
        cluster_indices = [t[0] for t in cluster]
        cluster_names = [t[1] for t in cluster]

        # Find the canonical (richest) item
        canonical_idx, canonical_name = _pick_canonical(items, cluster_indices, cluster_names)

        # Enrich canonical item with data from all variants
        variant_indices = [i for i in cluster_indices if i != canonical_idx]
        for vi in variant_indices:
            variant = items[vi]
            for key, value in variant.items():
                if (
                    value is not None
                    and value != ""
                    and (
                        items[canonical_idx].get(key) is None or items[canonical_idx].get(key) == ""
                    )
                ):
                    items[canonical_idx][key] = value

        # Build variant → canonical mapping
        for name in cluster_names:
            if name != canonical_name:
                result_map[name] = canonical_name

        # Mark variant items as merged (will be removed during dedup)
        for vi in variant_indices:
            items[vi]["__merged__"] = True

    # ------------------------------------------------------------------
    # Cross-reference updates
    # ------------------------------------------------------------------

    @staticmethod
    def _update_cross_references(
        items: list[dict[str, Any]],
        field: str,
        name_map: dict[str, str],
    ) -> None:
        """Update references in items using a resolution map."""
        for item in items:
            current = item.get(field)
            if current and current in name_map:
                item[field] = name_map[current]

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_list(
        items: list[dict[str, Any]],
        keys: tuple[str, ...],
    ) -> None:
        """Remove items that have been merged or are exact duplicates."""
        seen: set[str] = set()
        i = 0
        while i < len(items):
            item = items[i]
            # Remove merged items
            if item.pop("__merged__", False):
                items.pop(i)
                continue
            # Remove exact duplicates (same key value)
            key_val = _first_value(item, keys)
            if key_val:
                if key_val in seen:
                    items.pop(i)
                    continue
                seen.add(key_val)
            i += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_value(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first non-empty value for any of the given keys."""
    for k in keys:
        v = item.get(k)
        if v:
            s = str(v).strip()
            if s:
                return s
    return None


def _pick_canonical(
    items: list[dict[str, Any]],
    indices: list[int],
    names: list[str],
) -> tuple[int, str]:
    """Pick the canonical item from a cluster.

    Prefers the item with the most non-null, non-empty fields.
    On a tie, picks the longest descriptive name.
    Returns (index, canonical_name).
    """

    def _score(idx: int) -> tuple[int, int]:
        item = items[idx]
        filled = sum(1 for v in item.values() if v is not None and v != "" and v is not True)
        if item.get("__merged__"):
            filled = -1
        name_len = len(str(item.get("name", item.get("plan_name", ""))))
        return (filled, name_len)

    best_idx = max(indices, key=_score)
    best_name = items[best_idx].get("name") or items[best_idx].get("plan_name") or names[0]

    return best_idx, best_name
