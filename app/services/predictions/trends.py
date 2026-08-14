"""Market Trend Analysis.

Detects pricing trends, service popularity, content activity,
and marketing signals across competitors.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    CollectionLog,
    CompetitorContent,
    CompetitorPricing,
    CompetitorService,
    TrendDirection,
)
from app.services.predictions.analytics import (
    linear_trend as _linear_trend,
    direction_from_slope as _direction_from_slope,
    clamp as _clamp,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class TrendAnalyzer:
    """Detects market trends from historical data."""

    async def analyze_pricing_trends(
        self, session: AsyncSession, days: int = 90
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                CompetitorPricing.category,
                func.avg(CompetitorPricing.base_price).label("avg_price"),
                func.count(CompetitorPricing.id).label("count"),
            )
            .where(CompetitorPricing.collected_at >= since)
            .where(CompetitorPricing.base_price.isnot(None))
            .group_by(CompetitorPricing.category)
        )
        rows = (await session.execute(stmt)).all()

        trends = []
        for row in rows:
            if row.count < 2:
                continue
            category = row.category or "uncategorized"
            avg_price = float(row.avg_price)

            price_stmt = (
                select(CompetitorPricing.base_price, CompetitorPricing.collected_at)
                .where(CompetitorPricing.category == row.category)
                .where(CompetitorPricing.base_price.isnot(None))
                .where(CompetitorPricing.collected_at >= since)
                .order_by(CompetitorPricing.collected_at)
            )
            prices = (await session.execute(price_stmt)).all()

            if len(prices) >= 2:
                values = [float(p.base_price) for p in prices]
                slope = _linear_trend(values)
                direction = _direction_from_slope(slope, avg_price * 0.005 if avg_price else 0.5)
                strength = _clamp(abs(slope) / (avg_price * 0.01) if avg_price else 0.0)
            else:
                direction = "stable"
                strength = 0.3

            trends.append({
                "category": category,
                "direction": direction,
                "strength": round(strength, 3),
                "average_price": round(avg_price, 2),
                "sample_count": row.count,
                "description": f"Pricing for {category} is {direction} (avg ₹{avg_price:.0f}, {row.count} samples)",
            })

        return trends

    async def analyze_service_trends(
        self, session: AsyncSession, days: int = 90
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                CompetitorService.service_category,
                func.count(CompetitorService.id).label("count"),
            )
            .where(CompetitorService.collected_at >= since)
            .group_by(CompetitorService.service_category)
            .order_by(func.count(CompetitorService.id).desc())
            .limit(20)
        )
        rows = (await session.execute(stmt)).all()

        trends = []
        for row in rows:
            cat = row.service_category or "uncategorized"
            trends.append({
                "category": cat,
                "direction": "emerging" if row.count > 5 else "stable",
                "strength": _clamp(row.count / 20.0),
                "service_count": row.count,
                "description": f"Service category '{cat}' has {row.count} listings",
            })

        return trends

    async def analyze_content_trends(
        self, session: AsyncSession, days: int = 90
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                CompetitorContent.content_type,
                func.count(CompetitorContent.id).label("count"),
            )
            .where(CompetitorContent.collected_at >= since)
            .group_by(CompetitorContent.content_type)
            .order_by(func.count(CompetitorContent.id).desc())
            .limit(20)
        )
        rows = (await session.execute(stmt)).all()

        trends = []
        for row in rows:
            ct = row.content_type or "unknown"
            trends.append({
                "category": ct,
                "direction": "increasing" if row.count > 3 else "stable",
                "strength": _clamp(row.count / 15.0),
                "content_count": row.count,
                "description": f"Content type '{ct}' has {row.count} items",
            })

        return trends

    async def analyze_collection_frequency(
        self, session: AsyncSession, days: int = 30
    ) -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                CollectionLog.competitor_id,
                func.count(CollectionLog.id).label("runs"),
                func.sum(func.cast(CollectionLog.success, type_=func.count().type)).label("successes"),
            )
            .where(CollectionLog.start_time >= since)
            .group_by(CollectionLog.competitor_id)
        )
        rows = (await session.execute(stmt)).all()

        active = sum(1 for r in rows if r.runs >= 3)
        dormant = sum(1 for r in rows if r.runs == 0)

        return {
            "active_competitors": active,
            "dormant_competitors": dormant,
            "total_tracked": len(rows),
            "collection_health": "healthy" if active > dormant else "needs_attention",
        }

    async def detect_emerging_trends(
        self, session: AsyncSession
    ) -> list[dict[str, Any]]:
        pricing = await self.analyze_pricing_trends(session, days=30)
        services = await self.analyze_service_trends(session, days=30)
        content = await self.analyze_content_trends(session, days=30)

        emerging = []
        for t in pricing + services + content:
            if t.get("direction") in ("increasing", "emerging"):
                emerging.append({
                    "category": t["category"],
                    "type": "pricing" if "price" in str(t) else "service" if "service" in str(t) else "content",
                    "direction": t["direction"],
                    "strength": t.get("strength", 0.5),
                    "description": t.get("description", ""),
                })

        emerging.sort(key=lambda x: x["strength"], reverse=True)
        return emerging[:10]

    async def get_all_trends(
        self, session: AsyncSession, days: int = 90
    ) -> dict[str, Any]:
        pricing = await self.analyze_pricing_trends(session, days)
        services = await self.analyze_service_trends(session, days)
        content = await self.analyze_content_trends(session, days)
        collection = await self.analyze_collection_frequency(session, days)
        emerging = await self.detect_emerging_trends(session)

        return {
            "pricing_trends": pricing,
            "service_trends": services,
            "content_trends": content,
            "collection_health": collection,
            "emerging_trends": emerging,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }


trend_analyzer = TrendAnalyzer()
