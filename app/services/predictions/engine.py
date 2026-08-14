"""Core Prediction Intelligence Engine.

Heuristic-based prediction layer designed for easy ML model replacement.
Each predictor returns confidence scores and structured data.
Sprint 7.1: Enhanced with confidence scoring and explainability.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog

from app.services.predictions.analytics import clamp as _clamp, linear_trend as _linear_trend, direction_from_slope as _direction_from_slope  # noqa: F401

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class PredictionEngine:
    """Orchestrates all prediction modules. Facade over individual analyzers."""

    async def generate_all_predictions(
        self, competitor_id: int, session: AsyncSession
    ) -> dict[str, Any]:
        from app.services.predictions.growth import growth_forecaster
        from app.services.predictions.risks import risk_analyzer
        from app.services.predictions.recommendations import recommendation_engine
        from app.services.predictions.explanations import explanation_engine
        from app.services.predictions.data_quality import data_quality_evaluator

        growth, risks, recs = {}, [], []
        try:
            growth = await growth_forecaster.forecast(competitor_id, session)
        except Exception:
            logger.exception("growth_forecaster.forecast failed")

        try:
            risks = await risk_analyzer.analyze(competitor_id, session)
        except Exception:
            logger.exception("risk_analyzer.analyze failed")

        try:
            recs = await recommendation_engine.generate(competitor_id, session)
        except Exception:
            logger.exception("recommendation_engine.generate failed")

        quality = await data_quality_evaluator.evaluate(competitor_id, session)

        growth["explanation"] = await explanation_engine.explain_forecast(
            competitor_id, "services", session
        )

        for risk in risks:
            risk["explanation"] = await explanation_engine.explain_recommendation_async(risk, session)

        for rec in recs:
            rec["explanation"] = await explanation_engine.explain_recommendation_async(rec, session)

        return {
            "competitor_id": competitor_id,
            "growth": growth,
            "risks": risks,
            "recommendations": recs,
            "data_quality": quality,
            "generated_at": datetime.now(UTC).isoformat(),
        }


prediction_engine = PredictionEngine()
