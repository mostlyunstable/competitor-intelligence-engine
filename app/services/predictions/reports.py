"""Forecast Report Generator.

Generates comprehensive forecast reports combining all prediction modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ForecastReportGenerator:
    """Generates comprehensive forecast reports."""

    async def generate(self, session: AsyncSession) -> dict[str, Any]:
        from app.services.predictions.trends import trend_analyzer
        from app.services.predictions.growth import growth_forecaster
        from app.services.predictions.risks import risk_analyzer
        from app.services.predictions.opportunities import opportunity_detector
        from app.services.predictions.recommendations import recommendation_engine
        from app.services.predictions.benchmarking import predictive_benchmarker

        defaults = {
            "trends": {"emerging_trends": [], "seasonal_patterns": [], "competitive_shifts": []},
            "growth": [],
            "risks": [],
            "opportunities": [],
            "recommendations": [],
            "benchmarks": {},
        }
        trends, growth, risks, opportunities, recommendations, benchmarks = (
            defaults["trends"], defaults["growth"], defaults["risks"],
            defaults["opportunities"], defaults["recommendations"], defaults["benchmarks"],
        )

        try:
            trends = await trend_analyzer.get_all_trends(session)
        except Exception:
            logger.exception("trend_analyzer.get_all_trends failed")

        try:
            growth = await growth_forecaster.forecast_all(session)
        except Exception:
            logger.exception("growth_forecaster.forecast_all failed")

        try:
            risks = await risk_analyzer.analyze_all(session)
        except Exception:
            logger.exception("risk_analyzer.analyze_all failed")

        try:
            opportunities = await opportunity_detector.detect(session)
        except Exception:
            logger.exception("opportunity_detector.detect failed")

        try:
            recommendations = await recommendation_engine.generate_all(session)
        except Exception:
            logger.exception("recommendation_engine.generate_all failed")

        try:
            benchmarks = await predictive_benchmarker.benchmark_all(session)
        except Exception:
            logger.exception("predictive_benchmarker.benchmark_all failed")

        executive_summary = self._build_summary(trends, growth, risks, opportunities, recommendations)

        report = {
            "title": f"Competitor Intelligence Forecast - {datetime.now(UTC).strftime('%B %Y')}",
            "executive_summary": executive_summary,
            "predictions": {
                "growth_forecasts": growth,
                "market_trends": trends,
            },
            "risks": risks,
            "opportunities": opportunities,
            "recommendations": recommendations,
            "benchmark_data": benchmarks,
            "regional_insights": self._extract_regional(trends, opportunities),
            "business_actions": self._extract_actions(recommendations, opportunities),
            "generated_at": datetime.now(UTC).isoformat(),
        }

        return report

    def _build_summary(
        self,
        trends: dict[str, Any],
        growth: list[dict[str, Any]],
        risks: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> str:
        parts = []

        if not isinstance(growth, list):
            growth = []
        if not isinstance(risks, list):
            risks = []
        if not isinstance(opportunities, list):
            opportunities = []
        if not isinstance(recommendations, list):
            recommendations = []
        if not isinstance(trends, dict):
            trends = {}

        high_growth = [g for g in growth if g.get("growth_level") == "high"]
        if high_growth:
            parts.append(f"{len(high_growth)} competitor(s) showing high growth.")

        high_risks = [r for r in risks if r.get("risk_level") in ("high", "critical")]
        if high_risks:
            parts.append(f"{len(high_risks)} high-priority risk(s) identified.")

        if opportunities:
            parts.append(f"{len(opportunities)} business opportunity(ies) detected.")

        if recommendations:
            parts.append(f"{len(recommendations)} strategic recommendation(s) generated.")

        emerging = trends.get("emerging_trends", [])
        if emerging:
            parts.append(f"{len(emerging)} emerging trend(s) in the market.")

        return " ".join(parts) if parts else "No significant findings at this time."

    def _extract_regional(
        self, trends: dict[str, Any], opportunities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        regional = []
        for opp in opportunities:
            opp_type = opp.get("opportunity_type", "")
            if opp_type in ("underserved_category", "dominance_gap", "underserved_region"):
                regional.append({
                    "region": opp.get("title", ""),
                    "opportunity_score": opp.get("opportunity_score", 0),
                    "action": opp.get("recommended_action", ""),
                })
        return regional

    def _extract_actions(
        self,
        recommendations: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        actions = []
        for rec in recommendations[:5]:
            actions.append({
                "type": "recommendation",
                "title": rec.get("title", ""),
                "action": rec.get("recommendation", ""),
                "priority": rec.get("priority", "medium"),
                "expected_benefit": rec.get("expected_benefit", ""),
            })
        for opp in opportunities[:3]:
            actions.append({
                "type": "opportunity",
                "title": opp.get("title", ""),
                "action": opp.get("recommended_action", ""),
                "priority": opp.get("priority", "medium"),
                "expected_benefit": f"Score: {opp.get('opportunity_score', 0)}/100",
            })
        return actions


forecast_report_generator = ForecastReportGenerator()
