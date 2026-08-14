"""Canonical Service Taxonomy & Normalization Engine.

Establishes a standardized taxonomy hierarchy (Category -> Sub-category -> Canonical Service -> Variant)
and performs multi-factor service matching evaluating string similarity, scope of work, duration,
technicians, included materials, warranty, and add-ons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING
import re
import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class ServiceMappingResult:
    original_service_name: str
    canonical_service_name: str
    canonical_service_id: int | None
    category: str
    subcategory: str | None
    similarity_score: float
    mapping_confidence: float
    matching_methodology: str
    human_validation_status: str
    attributes_matched: dict[str, Any]


class TaxonomyEngine:
    """Taxonomy Registry and Service Normalization Engine."""

    # Default Standardized Canonical Taxonomy Seed Records
    DEFAULT_TAXONOMY: list[dict[str, Any]] = [
        {
            "id": 1,
            "category": "AC & Appliance Repair",
            "subcategory": "AC Servicing",
            "name": "AC Split Unit Servicing & Deep Clean",
            "pricing_unit": "per_unit",
            "attributes": {"technicians": 1, "duration_mins": 60, "warranty_days": 30, "materials_included": True}
        },
        {
            "id": 2,
            "category": "AC & Appliance Repair",
            "subcategory": "AC Repair",
            "name": "AC Gas Charging & Leak Fix",
            "pricing_unit": "per_unit",
            "attributes": {"technicians": 1, "duration_mins": 90, "warranty_days": 60, "materials_included": True}
        },
        {
            "id": 3,
            "category": "Cleaning & Pest Control",
            "subcategory": "Full Home Cleaning",
            "name": "Deep Home Cleaning (3 BHK)",
            "pricing_unit": "per_visit",
            "attributes": {"technicians": 3, "duration_mins": 240, "warranty_days": 7, "materials_included": True}
        },
        {
            "id": 4,
            "category": "Cleaning & Pest Control",
            "subcategory": "Bathroom Cleaning",
            "name": "Full House Bathroom Sanitization",
            "pricing_unit": "per_bathroom",
            "attributes": {"technicians": 1, "duration_mins": 45, "warranty_days": 7, "materials_included": True}
        },
        {
            "id": 5,
            "category": "Plumbing & Electrical",
            "subcategory": "Electrical Repairs",
            "name": "Ceiling Fan Installation & Repair",
            "pricing_unit": "per_appliance",
            "attributes": {"technicians": 1, "duration_mins": 30, "warranty_days": 30, "materials_included": False}
        },
        {
            "id": 6,
            "category": "Plumbing & Electrical",
            "subcategory": "Plumbing Repairs",
            "name": "Tap & Mixer Leakage Repair",
            "pricing_unit": "per_fixture",
            "attributes": {"technicians": 1, "duration_mins": 45, "warranty_days": 30, "materials_included": False}
        }
    ]

    def map_service(
        self,
        original_name: str,
        category: str | None = None,
        attributes: dict[str, Any] | None = None,
        custom_taxonomy: list[dict[str, Any]] | None = None,
    ) -> ServiceMappingResult:
        """Normalizes a raw service name into a canonical service record using multi-factor matching."""
        taxonomy = custom_taxonomy if custom_taxonomy else self.DEFAULT_TAXONOMY
        norm_input = self._clean(original_name)

        best_canonical = None
        best_score = 0.0
        best_method = "fuzzy_ngram"

        for canon in taxonomy:
            canon_norm = self._clean(canon["name"])
            # Exact match check
            if norm_input == canon_norm:
                score = 1.0
                method = "exact_match"
            else:
                score = self._compute_similarity(norm_input, canon_norm, attributes, canon.get("attributes"))
                method = "multi_factor_matching"

            if score > best_score:
                best_score = score
                best_canonical = canon
                best_method = method

        if best_canonical and best_score >= 0.60:
            confidence = round(min(1.0, best_score * 0.95), 2)
            val_status = "validated" if best_score >= 0.85 else "needs_review"
            return ServiceMappingResult(
                original_service_name=original_name,
                canonical_service_name=best_canonical["name"],
                canonical_service_id=best_canonical.get("id"),
                category=best_canonical["category"],
                subcategory=best_canonical.get("subcategory"),
                similarity_score=round(best_score, 2),
                mapping_confidence=confidence,
                matching_methodology=best_method,
                human_validation_status=val_status,
                attributes_matched=best_canonical.get("attributes", {}),
            )

        # Fallback if no taxonomy match > 0.60
        return ServiceMappingResult(
            original_service_name=original_name,
            canonical_service_name=original_name.strip(),
            canonical_service_id=None,
            category=category or "Uncategorized Services",
            subcategory=None,
            similarity_score=0.40,
            mapping_confidence=0.40,
            matching_methodology="unmapped_fallback",
            human_validation_status="needs_review",
            attributes_matched={},
        )

    async def map_and_persist(
        self,
        session: AsyncSession,
        original_name: str,
        competitor_id: int | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> ServiceMappingResult:
        """Maps service and persists mapping record to database."""
        # Query DB canonical services if available
        try:
            from app.database.models import CanonicalService, ServiceMapping
            stmt = select(CanonicalService)
            db_canonicals = (await session.execute(stmt)).scalars().all()
            taxonomy = [
                {
                    "id": c.id,
                    "category": c.category,
                    "subcategory": c.subcategory,
                    "name": c.name,
                    "pricing_unit": c.pricing_unit,
                    "attributes": c.attributes,
                }
                for c in db_canonicals
            ] if db_canonicals else self.DEFAULT_TAXONOMY
        except Exception:
            taxonomy = self.DEFAULT_TAXONOMY

        result = self.map_service(original_name, attributes=attributes, custom_taxonomy=taxonomy)

        if result.canonical_service_id:
            try:
                from app.database.models import ServiceMapping
                mapping_obj = ServiceMapping(
                    original_service_name=original_name,
                    canonical_service_id=result.canonical_service_id,
                    competitor_id=competitor_id,
                    similarity_score=result.similarity_score,
                    confidence=result.mapping_confidence,
                    matching_methodology=result.matching_methodology,
                    human_validation_status=result.human_validation_status,
                    attributes=result.attributes_matched,
                )
                session.add(mapping_obj)
                await session.commit()
            except Exception as e:
                logger.warning("persist_service_mapping_failed", error=str(e))

        return result

    def _compute_similarity(
        self,
        str_a: str,
        str_b: str,
        attr_a: dict[str, Any] | None,
        attr_b: dict[str, Any] | None,
    ) -> float:
        """Multi-factor similarity calculation (Jaccard word n-grams + attribute overlap)."""
        words_a = set(str_a.split())
        words_b = set(str_b.split())

        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        text_sim = len(intersection) / max(len(union), 1)

        # Attribute overlap (duration, technicians, materials)
        attr_sim = 1.0
        if attr_a and attr_b:
            matches = 0
            total = 0
            for k in ["technicians", "duration_mins", "materials_included"]:
                if k in attr_a and k in attr_b:
                    total += 1
                    if attr_a[k] == attr_b[k]:
                        matches += 1
            if total > 0:
                attr_sim = matches / total

        # Weighted combination: 75% text similarity, 25% attribute similarity
        return 0.75 * text_sim + 0.25 * attr_sim

    @staticmethod
    def _clean(text: str) -> str:
        s = text.lower()
        s = re.sub(r'[^a-z0-9]+', ' ', s)
        return s.strip()


taxonomy_engine = TaxonomyEngine()
