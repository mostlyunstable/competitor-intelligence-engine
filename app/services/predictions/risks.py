"""Risk Analysis.

Identifies and scores business risks using statistical analysis of
forecast confidence intervals, trend deviations, and activity anomalies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    ChangeLog,
    CollectionLog,
    CompetitorPricing,
    CompetitorService,
    RiskLevel,
)
from app.services.predictions.analytics import clamp as _clamp

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


def _risk_level(score: float) -> str:
    if score >= 70:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 30:
        return "medium"
    return "low"


class RiskAnalyzer:
    """Analyzes competitive risks using statistical forecasting."""

    async def analyze(
        self, competitor_id: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        from app.services.predictions.data_service import prediction_data
        from app.services.ml.forecaster import ml_forecaster

        risks: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        # Get all time series
        series = await prediction_data.get_multi_metric_series(session, competitor_id, days=30)

        # 1. Forecast-based volatility risk
        for metric in ("services", "pricing", "content", "changes"):
            values = series[metric]
            if sum(values) == 0:
                continue

            best_model, best_eval = ml_forecaster.select_best_model(values)
            forecast = ml_forecaster.forecast(values, steps=7, model_name=best_model)

            # Wide CI = high uncertainty = risk
            ci_widths = [hi - lo for lo, hi in forecast.confidence_intervals]
            avg_ci_width = sum(ci_widths) / max(len(ci_widths), 1)
            avg_value = sum(values) / max(len(values), 1)
            relative_uncertainty = avg_ci_width / max(avg_value, 0.1)

            if relative_uncertainty > 2.0:
                risks.append({
                    "competitor_id": competitor_id,
                    "risk_type": f"{metric}_volatility",
                    "risk_level": _risk_level(relative_uncertainty * 30),
                    "risk_score": round(min(100, relative_uncertainty * 30), 1),
                    "likelihood": round(min(1.0, relative_uncertainty / 3), 3),
                    "business_impact": f"{metric.title()} activity is highly volatile (uncertainty {relative_uncertainty:.1f}x average), making trends unpredictable",
                    "mitigation": f"Monitor {metric} patterns closely; consider scenario planning for {metric}-related strategies",
                    "detected_at": now.isoformat(),
                })

        # 2. Declining trend risk (negative slope from linear regression)
        for metric in ("services", "pricing"):
            values = series[metric]
            if len(values) < 7 or sum(values) == 0:
                continue

            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            den = sum((i - x_mean) ** 2 for i in range(n))
            slope = num / den if den else 0

            if slope < -0.05 and y_mean > 0:
                decline_pct = abs(slope) / max(y_mean, 0.1) * 100
                risks.append({
                    "competitor_id": competitor_id,
                    "risk_type": f"declining_{metric}",
                    "risk_level": _risk_level(decline_pct * 3),
                    "risk_score": round(min(100, decline_pct * 3), 1),
                    "likelihood": round(min(1.0, decline_pct / 20), 3),
                    "business_impact": f"{metric.title()} showing declining trend ({slope:+.3f}/day, {decline_pct:.1f}% daily decline)",
                    "mitigation": f"Investigate root cause of {metric} decline; may indicate strategic shift or operational issues",
                    "detected_at": now.isoformat(),
                })

        # 3. Price war detection (statistical: prices dropping faster than expected)
        price_values = series["pricing"]
        if len(price_values) >= 5:
            price_series = await prediction_data.get_price_series(session, competitor_id, days=30)
            if len(price_series) >= 4:
                drops = sum(1 for i in range(1, len(price_series)) if price_series[i] < price_series[i-1])
                drop_rate = drops / max(len(price_series) - 1, 1)
                if drop_rate > 0.4:
                    risks.append({
                        "competitor_id": competitor_id,
                        "risk_type": "price_war",
                        "risk_level": _risk_level(drop_rate * 120),
                        "risk_score": round(min(100, drop_rate * 120), 1),
                        "likelihood": round(min(1.0, drop_rate), 3),
                        "business_impact": f"Prices dropping in {drops}/{len(price_series)-1} transitions ({drop_rate:.0%} rate), indicating aggressive pricing",
                        "mitigation": "Focus on value-added services and customer loyalty rather than matching price cuts",
                        "detected_at": now.isoformat(),
                    })

        # 4. Rapid expansion (forecast shows accelerating growth)
        changes_values = series["changes"]
        if len(changes_values) >= 7 and sum(changes_values) > 0:
            first_week = sum(changes_values[:7])
            last_week = sum(changes_values[-7:])
            if last_week > first_week * 1.5 and last_week >= 5:
                acceleration = (last_week - first_week) / max(first_week, 1)
                risks.append({
                    "competitor_id": competitor_id,
                    "risk_type": "rapid_expansion",
                    "risk_level": _risk_level(acceleration * 40),
                    "risk_score": round(min(100, acceleration * 40), 1),
                    "likelihood": round(min(1.0, last_week / 20), 3),
                    "business_impact": f"Change activity accelerating ({first_week} → {last_week} weekly, {acceleration:.0%} increase)",
                    "mitigation": "Accelerate service innovation and strengthen customer relationships in affected categories",
                    "detected_at": now.isoformat(),
                })

        # 5. Collection reliability risk
        col_stmt = (
            select(func.count())
            .select_from(CollectionLog)
            .where(CollectionLog.competitor_id == competitor_id)
            .where(CollectionLog.start_time >= now - timedelta(days=30))
            .where(CollectionLog.success.is_(True))
        )
        successful = (await session.execute(col_stmt)).scalar() or 0

        total_stmt = (
            select(func.count())
            .select_from(CollectionLog)
            .where(CollectionLog.competitor_id == competitor_id)
            .where(CollectionLog.start_time >= now - timedelta(days=30))
        )
        total = (await session.execute(total_stmt)).scalar() or 0

        if total > 0:
            success_rate = successful / total
            if success_rate < 0.7:
                risks.append({
                    "competitor_id": competitor_id,
                    "risk_type": "collection_reliability",
                    "risk_level": _risk_level((1 - success_rate) * 120),
                    "risk_score": round(min(100, (1 - success_rate) * 120), 1),
                    "likelihood": round(1 - success_rate, 3),
                    "business_impact": f"Data collection success rate only {success_rate:.0%} ({successful}/{total}), limiting intelligence quality",
                    "mitigation": "Review collection configuration; competitor site may have anti-scraping measures",
                    "detected_at": now.isoformat(),
                })

        risks.sort(key=lambda x: x["risk_score"], reverse=True)
        return risks

    async def analyze_all(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Analyze risks for all enabled competitors."""
        from app.database.models import Competitor

        comps = (await session.execute(
            select(Competitor).where(Competitor.enabled.is_(True))
        )).scalars().all()

        all_risks: list[dict[str, Any]] = []
        for comp in comps:
            try:
                risks = await self.analyze(comp.id, session)
                for r in risks:
                    r["competitor_name"] = comp.name
                all_risks.extend(risks)
            except Exception:
                logger.warning("risk_analysis_failed", competitor_id=comp.id)
                continue

        all_risks.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        return all_risks


risk_analyzer = RiskAnalyzer()
