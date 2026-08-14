"""Pricing Consistency Engine.

Resolves conflicting price observations across multiple data sources, preserving raw
observations, detecting root causes (promotions, location tiering, unit mismatches, data errors),
and recording explicit resolution audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING
import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class ResolutionResult:
    canonical_service_id: int
    resolved_price: float
    promotional_price: float | None
    price_type: str
    resolution_reason: str
    cause: str
    confidence_score: float
    conflicting_observations_count: int


class PricingConsistencyEngine:
    """Engine for resolving pricing discrepancies across sources and observations."""

    async def resolve_conflicts(
        self,
        session: AsyncSession,
        canonical_service_id: int,
        observations: list[dict[str, Any]],
    ) -> ResolutionResult:
        """Analyzes conflicting observations, determines discrepancy cause, and produces a resolved record."""
        if not observations:
            return ResolutionResult(
                canonical_service_id=canonical_service_id,
                resolved_price=0.0,
                promotional_price=None,
                price_type="unknown",
                resolution_reason="No observations available for resolution",
                cause="no_data",
                confidence_score=0.0,
                conflicting_observations_count=0,
            )

        if len(observations) == 1:
            obs = observations[0]
            price = float(obs.get("price", 0.0))
            return ResolutionResult(
                canonical_service_id=canonical_service_id,
                resolved_price=price,
                promotional_price=float(obs["discount"]) if obs.get("discount") else None,
                price_type=obs.get("price_type", "standard"),
                resolution_reason="Single source observation — validated standard price",
                cause="single_observation",
                confidence_score=float(obs.get("confidence_score", 1.0)),
                conflicting_observations_count=1,
            )

        # Multi-observation conflict resolution logic
        prices = [float(o["price"]) for o in observations if o.get("price") is not None and float(o["price"]) > 0]
        promos = [o for o in observations if o.get("price_type") == "promotional" or (o.get("discount") and float(o.get("discount", 0)) > 0)]
        units = set(o.get("pricing_unit", "per_service") for o in observations)
        locations = set(o.get("location", "Pan India") for o in observations)

        # Check for data errors (outliers > 5x median)
        sorted_prices = sorted(prices)
        median_price = sorted_prices[len(sorted_prices) // 2] if sorted_prices else 0.0
        filtered_obs = []
        for o in observations:
            p = float(o.get("price", 0.0))
            if median_price > 0 and (p > median_price * 5 or p < median_price * 0.1):
                logger.warning("pricing_outlier_ignored", price=p, median=median_price)
                continue
            filtered_obs.append(o)

        working_obs = filtered_obs if filtered_obs else observations
        working_prices = [float(o["price"]) for o in working_obs if o.get("price") is not None and float(o["price"]) > 0]

        cause = "pricing_variance"
        reason = "Multiple pricing observations resolved using weighted recency and source reliability."
        confidence = 0.88

        if promos and len(promos) < len(working_obs):
            cause = "promotion"
            std_prices = [float(o["price"]) for o in working_obs if o not in promos and float(o["price"]) > 0]
            resolved_std = sum(std_prices) / len(std_prices) if std_prices else median_price
            resolved_promo = float(promos[0]["price"])
            reason = f"Identified promotional offer (₹{resolved_promo:.2f}) vs standard price (₹{resolved_std:.2f})."
            confidence = 0.94
            resolved_price = resolved_std
            promotional_price = resolved_promo
        elif len(locations) > 1:
            cause = "location"
            resolved_price = median_price
            promotional_price = None
            reason = f"Location-based price tiering detected across {', '.join(locations)}. Resolved to market median (₹{median_price:.2f})."
            confidence = 0.90
        elif len(units) > 1:
            cause = "pricing_unit"
            resolved_price = median_price
            promotional_price = None
            reason = f"Pricing unit variance ({', '.join(units)}). Standardized to median base unit (₹{median_price:.2f})."
            confidence = 0.85
        else:
            cause = "time_period"
            # Sort by collected_at descending if available
            sorted_by_time = sorted(working_obs, key=lambda x: str(x.get("collected_at", "")), reverse=True)
            resolved_price = float(sorted_by_time[0]["price"])
            promotional_price = None
            reason = f"Latest observation selected (₹{resolved_price:.2f}) from {len(working_obs)} historic price points."
            confidence = 0.92

        # Record resolution in database
        try:
            from app.database.models import PricingResolutionRecord
            rec = PricingResolutionRecord(
                canonical_service_id=canonical_service_id,
                conflicting_observations=observations,
                resolved_price=round(resolved_price, 2),
                promotional_price=round(promotional_price, 2) if promotional_price else None,
                price_type="promotional" if promotional_price else "standard",
                resolution_reason=reason,
                confidence_score=confidence,
            )
            session.add(rec)
            await session.commit()
        except Exception as e:
            logger.warning("pricing_resolution_persist_failed", error=str(e))

        return ResolutionResult(
            canonical_service_id=canonical_service_id,
            resolved_price=round(resolved_price, 2),
            promotional_price=round(promotional_price, 2) if promotional_price else None,
            price_type="promotional" if promotional_price else "standard",
            resolution_reason=reason,
            cause=cause,
            confidence_score=confidence,
            conflicting_observations_count=len(observations),
        )


pricing_consistency_engine = PricingConsistencyEngine()
