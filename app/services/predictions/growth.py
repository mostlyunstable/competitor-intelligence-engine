"""Competitor Growth Forecasting.

Uses MLForecaster time-series models to predict future growth trajectories
based on real collected data (services, pricing, content, changes).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class GrowthForecaster:
    """Forecasts competitor growth using real time-series models."""

    async def forecast(
        self, competitor_id: int, session: AsyncSession
    ) -> dict[str, Any]:
        from app.services.predictions.data_service import prediction_data
        from app.services.ml.forecaster import ml_forecaster

        now = datetime.now(UTC)
        series = await prediction_data.get_multi_metric_series(session, competitor_id, days=30)

        # Build composite activity signal: weighted sum of daily activity
        composite = []
        for i in range(30):
            val = (
                series["services"][i] * 3.0
                + series["pricing"][i] * 1.0
                + series["content"][i] * 0.5
                + series["changes"][i] * 0.1
            )
            composite.append(val)

        # Forecast next 7 days of composite activity
        best_model, best_eval = ml_forecaster.select_best_model(composite)
        forecast_result = ml_forecaster.forecast(composite, steps=7, model_name=best_model)

        # Compute growth from forecast vs historical average
        recent_avg = sum(composite[-7:]) / max(len(composite[-7:]), 1)
        forecast_avg = sum(forecast_result.predictions) / max(len(forecast_result.predictions), 1)
        growth_ratio = (forecast_avg - recent_avg) / max(recent_avg, 0.1)

        # Classify growth level based on forecast trajectory
        if growth_ratio > 0.15:
            level = "high"
        elif growth_ratio > 0.0:
            level = "medium"
        elif growth_ratio > -0.15:
            level = "low"
        else:
            level = "declining"

        # Confidence from model quality + data quantity
        data_points = sum(1 for v in composite if v > 0)
        model_quality = max(0, best_eval.r2) if best_eval.r2 > -1 else 0
        confidence = min(0.95, 0.3 + model_quality * 0.4 + (data_points / 30) * 0.3)

        # Growth percentage from actual forecast slope
        if recent_avg > 0:
            pct_value = round(growth_ratio * 100, 1)
            growth_pct = f"{pct_value:+.1f}%"
        else:
            growth_pct = "+0.0%"

        # Compare first-half vs second-half of 30-day window for momentum
        first_half = sum(composite[:15]) / 15
        second_half = sum(composite[15:]) / 15
        momentum = second_half - first_half

        return {
            "competitor_id": competitor_id,
            "growth_level": level,
            "growth_score": round(min(100, max(0, 50 + growth_ratio * 200)), 2),
            "growth_percentage": growth_pct,
            "confidence_score": round(confidence, 3),
            "forecast_model": best_model,
            "forecast_values": [round(v, 2) for v in forecast_result.predictions],
            "forecast_ci": [(round(lo, 2), round(hi, 2)) for lo, hi in forecast_result.confidence_intervals],
            "momentum": round(momentum, 2),
            "recent_activity_avg": round(recent_avg, 2),
            "forecast_activity_avg": round(forecast_avg, 2),
            "breakdown": {
                "service_signals": round(sum(series["services"][-7:]) / 7, 2),
                "pricing_signals": round(sum(series["pricing"][-7:]) / 7, 2),
                "content_signals": round(sum(series["content"][-7:]) / 7, 2),
                "change_signals": round(sum(series["changes"][-7:]) / 7, 2),
            },
            "metrics": {
                "services_last_30": sum(series["services"]),
                "pricing_last_30": sum(series["pricing"]),
                "content_last_30": sum(series["content"]),
                "changes_last_30": sum(series["changes"]),
            },
            "predicted_at": now.isoformat(),
        }

    async def forecast_all(
        self, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Batch forecast for all enabled competitors."""
        from app.database.models import Competitor

        comps = (await session.execute(
            select(Competitor).where(Competitor.enabled.is_(True))
        )).scalars().all()

        results = []
        for comp in comps:
            try:
                result = await self.forecast(comp.id, session)
                result["competitor_name"] = comp.name
                results.append(result)
            except Exception:
                logger.warning("forecast_failed", competitor_id=comp.id)
                continue

        results.sort(key=lambda x: x.get("growth_score", 0), reverse=True)
        return results


from sqlalchemy import select  # noqa: E402

growth_forecaster = GrowthForecaster()

from app.services.predictions.analytics import clamp as _clamp  # noqa: E402, F401 — backward compat
