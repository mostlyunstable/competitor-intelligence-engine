"""Regional Expansion Forecasting.

Predicts where competitors are likely to expand based on
historical patterns, market signals, and geographic factors.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    CollectionLog,
    Competitor,
    CompetitorSource,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

INDIAN_CITIES = {
    "chennai": {"population": 11e6, "tier": 1, "demand": "high"},
    "mumbai": {"population": 21e6, "tier": 1, "demand": "high"},
    "delhi": {"population": 32e6, "tier": 1, "demand": "high"},
    "bangalore": {"population": 13e6, "tier": 1, "demand": "high"},
    "hyderabad": {"population": 10e6, "tier": 1, "demand": "high"},
    "pune": {"population": 7e6, "tier": 1, "demand": "medium"},
    "kolkata": {"population": 15e6, "tier": 1, "demand": "medium"},
    "ahmedabad": {"population": 8e6, "tier": 2, "demand": "medium"},
    "jaipur": {"population": 4e6, "tier": 2, "demand": "medium"},
    "lucknow": {"population": 3e6, "tier": 2, "demand": "medium"},
    "coimbatore": {"population": 2e6, "tier": 2, "demand": "medium"},
    "madurai": {"population": 1.5e6, "tier": 2, "demand": "medium"},
    "trichy": {"population": 1e6, "tier": 3, "demand": "low"},
    "salem": {"population": 0.8e6, "tier": 3, "demand": "low"},
}


class ExpansionForecaster:
    """Forecasts regional expansion probabilities."""

    async def forecast(
        self, competitor_id: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        stmt = select(Competitor).where(Competitor.id == competitor_id)
        comp = (await session.execute(stmt)).scalar_one_or_none()
        if not comp:
            return []

        tags = [t.lower() for t in (comp.tags or [])]
        sources_stmt = select(CompetitorSource).where(CompetitorSource.competitor_id == competitor_id)
        sources = (await session.execute(sources_stmt)).scalars().all()
        source_urls = [s.url.lower() for s in sources]

        logs_stmt = (
            select(func.count())
            .select_from(CollectionLog)
            .where(CollectionLog.competitor_id == competitor_id)
            .where(CollectionLog.success.is_(True))
        )
        success_count = (await session.execute(logs_stmt)).scalar() or 0

        is_chennai_based = any("chennai" in t for t in tags)
        is_national = any(t in ("national", "pan-india", "tier-1") for t in tags)

        forecasts = []
        for city, info in INDIAN_CITIES.items():
            if any(city in url for url in source_urls):
                continue

            probability = 0.0
            factors: dict[str, Any] = {}

            if is_national:
                probability += 0.3
                factors["national_presence"] = 0.3

            if is_chennai_based and city in ("coimbatore", "madurai", "trichy", "salem"):
                probability += 0.25
                factors["nearby_expansion"] = 0.25

            if info["demand"] == "high":
                probability += 0.2
                factors["high_demand"] = 0.2
            elif info["demand"] == "medium":
                probability += 0.1
                factors["medium_demand"] = 0.1

            if info["tier"] == 1:
                probability += 0.15
                factors["tier_1_city"] = 0.15
            elif info["tier"] == 2:
                probability += 0.05
                factors["tier_2_city"] = 0.05

            if success_count > 10:
                probability += 0.1
                factors["active_collection"] = 0.1

            probability = min(probability, 0.95)

            if probability >= 0.6:
                timeline = "3-6 months"
                priority = "high"
            elif probability >= 0.3:
                timeline = "6-12 months"
                priority = "medium"
            else:
                timeline = "12+ months"
                priority = "low"

            forecasts.append({
                "region": city.title(),
                "expansion_probability": round(probability, 3),
                "expansion_score": round(probability * 100, 1),
                "expected_timeline": timeline,
                "priority": priority,
                "factors": factors,
                "population": info["population"],
                "tier": info["tier"],
                "market_demand": info["demand"],
            })

        forecasts.sort(key=lambda x: x["expansion_probability"], reverse=True)
        return forecasts[:10]


expansion_forecaster = ExpansionForecaster()
