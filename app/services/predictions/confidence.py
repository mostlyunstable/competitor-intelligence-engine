"""Prediction Confidence Engine.

Multi-factor confidence scoring considering historical accuracy,
data freshness, completeness, sample size, and market conditions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog

from app.services.predictions.analytics import clamp, volatility

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ConfidenceEngine:
    """Calculates prediction confidence from multiple factors."""

    def calculate(
        self,
        data_points: int = 0,
        data_age_days: float = 0.0,
        completeness: float = 1.0,
        historical_accuracy: float = 0.5,
        market_volatility: float = 0.0,
        trend_consistency: float = 0.5,
        source_reliability: float = 0.8,
    ) -> dict[str, Any]:
        factors = {
            "sample_size": self._score_sample_size(data_points),
            "data_freshness": self._score_freshness(data_age_days),
            "completeness": clamp(completeness),
            "historical_accuracy": clamp(historical_accuracy),
            "market_stability": clamp(1.0 - market_volatility),
            "trend_consistency": clamp(trend_consistency),
            "source_reliability": clamp(source_reliability),
        }

        weights = {
            "sample_size": 0.15,
            "data_freshness": 0.15,
            "completeness": 0.15,
            "historical_accuracy": 0.20,
            "market_stability": 0.10,
            "trend_consistency": 0.15,
            "source_reliability": 0.10,
        }

        score = sum(factors[k] * weights[k] for k in factors)
        score = clamp(score)

        reliability = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"
        stability = "stable" if factors["trend_consistency"] >= 0.7 else "moderate" if factors["trend_consistency"] >= 0.4 else "volatile"

        return {
            "confidence_score": round(score, 4),
            "reliability_level": reliability,
            "prediction_stability": stability,
            "factors": {k: round(v, 4) for k, v in factors.items()},
            "weights": weights,
        }

    def calculate_batch(
        self, predictions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Add confidence data to each prediction dict."""
        for pred in predictions:
            metrics = pred.get("metrics", {})
            data_points = (
                metrics.get("successful_collections", 0)
                + metrics.get("changes_last_30", 0)
                + metrics.get("services_last_30", 0)
            )
            completeness = min(1.0, (
                metrics.get("services_last_30", 0)
                + metrics.get("pricing_last_30", 0)
                + metrics.get("content_last_30", 0)
            ) / 10.0)

            # Extract real values if provided, else use defaults
            source_reliability = metrics.get("source_reliability", 0.7)
            market_volatility = metrics.get("market_volatility", 0.0)
            trend_consistency = metrics.get("trend_consistency", 0.5)

            confidence = self.calculate(
                data_points=data_points,
                completeness=completeness,
                historical_accuracy=pred.get("confidence_score", 0.5),
                market_volatility=market_volatility,
                trend_consistency=trend_consistency,
                source_reliability=source_reliability,
            )
            pred["confidence"] = confidence
            pred["confidence_score"] = confidence["confidence_score"]
        return predictions

    def _score_sample_size(self, n: int) -> float:
        if n >= 20:
            return 1.0
        elif n >= 10:
            return 0.8
        elif n >= 5:
            return 0.6
        elif n >= 2:
            return 0.4
        return 0.2

    def _score_freshness(self, age_days: float) -> float:
        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.9
        elif age_days <= 30:
            return 0.7
        elif age_days <= 90:
            return 0.5
        return 0.3

    async def get_data_quality_metrics(
        self, competitor_id: int, session: AsyncSession
    ) -> dict[str, Any]:
        """Fetch real data quality metrics for a competitor."""
        from datetime import timedelta
        from sqlalchemy import func, select
        from app.database.models import (
            CompetitorService, CompetitorPricing, CompetitorContent,
            CollectionLog, RawStorage,
        )

        now = datetime.now(UTC)
        last_30 = now - timedelta(days=30)

        svc_count = (await session.execute(
            select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == competitor_id)
        )).scalar() or 0

        prc_count = (await session.execute(
            select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == competitor_id)
        )).scalar() or 0

        cnt_count = (await session.execute(
            select(func.count()).select_from(CompetitorContent).where(
                CompetitorContent.competitor_id == competitor_id)
        )).scalar() or 0

        last_log = (await session.execute(
            select(CollectionLog.start_time)
            .where(CollectionLog.competitor_id == competitor_id)
            .order_by(CollectionLog.start_time.desc())
            .limit(1)
        )).scalar()

        age_days = (now - last_log).total_seconds() / 86400 if last_log else 999

        raw_count = (await session.execute(
            select(func.count()).select_from(RawStorage).where(
                RawStorage.competitor_id == competitor_id)
        )).scalar() or 0

        extracted_count = (await session.execute(
            select(func.count()).select_from(RawStorage).where(
                RawStorage.competitor_id == competitor_id,
                RawStorage.extracted_data.isnot(None))
        )).scalar() or 0

        completeness = extracted_count / raw_count if raw_count > 0 else 0.0

        # Source reliability: success rate of recent collections
        recent_logs = (await session.execute(
            select(CollectionLog.success)
            .where(CollectionLog.competitor_id == competitor_id)
            .where(CollectionLog.start_time >= last_30)
        )).scalars().all()

        if recent_logs:
            source_reliability = sum(1 for s in recent_logs if s) / len(recent_logs)
        else:
            source_reliability = 0.5

        # Market volatility: price coefficient of variation across recent pricing
        recent_prices = (await session.execute(
            select(CompetitorPricing.base_price)
            .where(CompetitorPricing.competitor_id == competitor_id)
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.collected_at >= last_30)
        )).scalars().all()

        if recent_prices and len(recent_prices) >= 3:
            import statistics
            price_values = [float(p) for p in recent_prices]
            avg_price = statistics.mean(price_values)
            stdev_price = statistics.stdev(price_values) if len(price_values) > 1 else 0
            market_volatility = stdev_price / avg_price if avg_price > 0 else 0
        else:
            market_volatility = 0.0

        return {
            "data_points": svc_count + prc_count + cnt_count,
            "data_age_days": round(age_days, 1),
            "completeness": round(completeness, 3),
            "source_reliability": round(source_reliability, 3),
            "market_volatility": round(market_volatility, 3),
        }


confidence_engine = ConfidenceEngine()
