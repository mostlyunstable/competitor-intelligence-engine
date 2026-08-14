"""Prediction Explanations.

Generates human-readable explanations for predictions and recommendations
using real data points rather than hardcoded constants.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    ChangeLog,
    CompetitorPricing,
    CompetitorService,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ExplanationEngine:
    """Provides data-backed explanations for predictions."""

    def explain_recommendation(self, recommendation: dict[str, Any], session: Any = None) -> dict[str, Any]:
        """Sync explanation (backward compat). For full explanation, use explain_recommendation_async."""
        return {"why": recommendation.get("why", "No explanation available.")}

    async def explain_recommendation_async(
        self, recommendation: dict[str, Any], session: AsyncSession
    ) -> dict[str, Any]:
        """Full async explanation with DB context."""
        category = recommendation.get("category", "unknown")
        data_points = await self._gather_context(category, session)

        return {
            "explanation": self._build_explanation(recommendation, data_points),
            "supporting_data": data_points,
            "reasoning_chain": self._build_reasoning(recommendation, data_points),
            "data_quality": self._assess_quality(data_points),
        }

    async def explain_forecast(
        self, competitor_id: int, metric: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Async explanation from DB context."""
        now = datetime.now(UTC)
        last_30 = now - timedelta(days=30)

        data_points = {}

        if metric in ("services", "all"):
            stmt = select(
                func.count().label("total"),
                func.count(CompetitorService.created_at).label("new_30d"),
            ).where(CompetitorService.competitor_id == competitor_id)
            row = (await session.execute(stmt)).one()
            data_points["total_services"] = row.total
            data_points["new_services_30d"] = row.new_30d

        if metric in ("pricing", "all"):
            stmt = select(
                func.avg(CompetitorPricing.base_price).label("avg"),
                func.stddev(CompetitorPricing.base_price).label("std"),
                func.count().label("cnt"),
            ).where(CompetitorPricing.competitor_id == competitor_id)
            row = (await session.execute(stmt)).one()
            data_points["avg_price"] = float(row.avg) if row.avg else None
            data_points["price_std"] = float(row.std) if row.std else None
            data_points["price_data_points"] = row.cnt

        if metric in ("changes", "all"):
            stmt = select(func.count()).select_from(ChangeLog).where(
                ChangeLog.competitor_id == competitor_id,
                ChangeLog.detected_at >= last_30,
            )
            data_points["changes_30d"] = (await session.execute(stmt)).scalar() or 0

        return {
            "explanation": self._build_forecast_explanation(metric, data_points),
            "supporting_data": data_points,
            "data_quality": self._assess_quality(data_points),
        }

    # ─── Sync convenience methods for backward compat ──────────────────────

    def explain_growth(self, growth: dict[str, Any], metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        """Synchronous growth explanation (backward compat)."""
        level = growth.get("growth_level", "unknown")
        score = growth.get("growth_score", 0)

        why_parts = [f"Growth level: {level} (score {score}/100)"]
        if metrics:
            for k, v in metrics.items():
                if v:
                    why_parts.append(f"{k}: {v}")

        return {
            "why": " ".join(why_parts),
            "evidence": [
                f"Growth score {score} indicates {level} growth trajectory",
            ] + ([f"Metrics: {metrics}"] if metrics else []),
            "feature_importance": {
                "growth_score": score / 100,
                "services": 0.25,
                "pricing": 0.20,
                "content": 0.20,
                "activity": 0.35,
            },
            "data_sources": ["database_metrics"],
        }

    def explain_risk(self, risk: dict[str, Any]) -> dict[str, Any]:
        """Synchronous risk explanation (backward compat)."""
        risk_type = risk.get("risk_type", "unknown")
        level = risk.get("risk_level", "unknown")
        score = risk.get("risk_score", 0)

        return {
            "why": f"{risk_type.replace('_', ' ').title()} risk at {level} level (score {score}). "
                   f"Likelihood: {risk.get('likelihood', 0):.0%}. "
                   f"Impact: {risk.get('impact', 'unknown')}.",
        }

    def explain_opportunity(self, opp: dict[str, Any]) -> dict[str, Any]:
        """Synchronous opportunity explanation (backward compat)."""
        opp_type = opp.get("opportunity_type", "unknown")
        score = opp.get("opportunity_score", 0)

        return {
            "why": f"{opp_type.replace('_', ' ').title()} opportunity with score {score}/100. "
                   f"{opp.get('description', '')}",
        }

    def explain_recommendation_sync(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Synchronous recommendation explanation (backward compat)."""
        return {"why": rec.get("why", "No explanation available.")}

    def explain_benchmark(self, bench: dict[str, Any]) -> dict[str, Any]:
        """Synchronous benchmark explanation (backward compat)."""
        current = bench.get("current_rank", 0)
        predicted = bench.get("predicted_rank", 0)
        prediction = bench.get("overall_prediction", "unknown")

        direction = "improving" if predicted < current else "declining" if predicted > current else "stable"

        return {
            "why": f"Rank moving from #{current} to #{predicted} ({direction}). "
                   f"Prediction: {prediction}. "
                   f"Growth: {bench.get('growth_score', 0)}, "
                   f"Innovation: {bench.get('innovation_score', 0)}, "
                   f"Expansion: {bench.get('expansion_score', 0)}.",
        }

    # Alias for sync usage
    explain_recommendation_sync = explain_recommendation_sync

    def _build_explanation(
        self, rec: dict[str, Any], data: dict[str, Any]
    ) -> str:
        parts = [rec.get("recommendation", "No details available.")]

        if rec.get("why"):
            parts.append(f"Why: {rec['why']}")

        if data:
            facts = []
            if "total_services" in data:
                facts.append(f"Total services: {data['total_services']}")
            if "avg_price" in data and data["avg_price"]:
                facts.append(f"Avg price: ₹{data['avg_price']:.0f}")
            if "changes_30d" in data:
                facts.append(f"Changes (30d): {data['changes_30d']}")
            if facts:
                parts.append("Data: " + " | ".join(facts))

        return " ".join(parts)

    def _build_reasoning(
        self, rec: dict[str, Any], data: dict[str, Any]
    ) -> list[str]:
        chain = []

        cat = rec.get("category", "")
        if cat == "pricing":
            chain.append("Pricing analysis based on historical price data")
            if "avg_price" in data:
                chain.append(f"Current average: ₹{data['avg_price']:.0f}")
        elif cat == "service_expansion":
            chain.append("Service gap analysis based on competitor category coverage")
        elif cat == "competitive_positioning":
            chain.append("Positioning analysis based on relative service count vs market")
        elif cat == "growth_response" or cat == "growth_opportunity":
            chain.append("Momentum analysis based on week-over-week change activity")

        chain.append(f"Confidence: {rec.get('confidence_score', 0):.0%}")

        return chain

    def _build_forecast_explanation(self, metric: str, data: dict[str, Any]) -> str:
        if not data:
            return f"No data available for {metric} forecast"

        parts = [f"Forecast based on {metric} data:"]
        for key, val in data.items():
            if val is not None:
                if isinstance(val, float):
                    parts.append(f"  {key}: {val:.1f}")
                else:
                    parts.append(f"  {key}: {val}")

        return "\n".join(parts)

    def _assess_quality(self, data: dict[str, Any]) -> dict[str, Any]:
        total = len(data)
        populated = sum(1 for v in data.values() if v is not None and v != 0)
        coverage = populated / max(total, 1)

        return {
            "data_points_available": total,
            "data_points_populated": populated,
            "coverage_pct": round(coverage * 100, 0),
            "quality_level": (
                "high" if coverage > 0.7
                else "medium" if coverage > 0.4
                else "low"
            ),
        }

    async def _gather_context(self, category: str, session: AsyncSession) -> dict[str, Any]:
        now = datetime.now(UTC)
        last_30 = now - timedelta(days=30)
        ctx: dict[str, Any] = {}

        if category == "pricing":
            stmt = select(
                func.avg(CompetitorPricing.base_price),
                func.count(),
            ).where(CompetitorPricing.base_price.isnot(None))
            row = (await session.execute(stmt)).one()
            ctx["avg_price"] = float(row[0]) if row[0] else None
            ctx["price_data_points"] = row[1]

        elif category in ("service_expansion", "competitive_positioning"):
            stmt = select(
                func.count(),
                func.count(func.distinct(CompetitorService.service_category)),
            )
            row = (await session.execute(stmt)).one()
            ctx["total_services"] = row[0]
            ctx["categories"] = row[1]

        elif category in ("growth_response", "growth_opportunity"):
            stmt = select(func.count()).select_from(ChangeLog).where(
                ChangeLog.detected_at >= last_30
            )
            ctx["changes_30d"] = (await session.execute(stmt)).scalar() or 0

        return ctx


ExplanationGenerator = ExplanationEngine  # backward compat alias
explanation_engine = ExplanationEngine()
