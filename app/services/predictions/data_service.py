"""Prediction Data Service.

Centralizes DB queries for all prediction modules. Pulls real time-series
data and feeds it to the MLForecaster for actual predictions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    ChangeLog,
    CollectionLog,
    CompetitorContent,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
    CompetitorSource,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class PredictionDataService:
    """Shared data access for all prediction modules."""

    async def get_time_series(
        self, session: AsyncSession, competitor_id: int, metric: str, days: int = 30
    ) -> list[float]:
        """Get daily counts for a metric over N days."""
        now = datetime.now(UTC)
        model_map = {
            "services": (CompetitorService, CompetitorService.collected_at),
            "pricing": (CompetitorPricing, CompetitorPricing.collected_at),
            "content": (CompetitorContent, CompetitorContent.collected_at),
            "changes": (ChangeLog, ChangeLog.detected_at),
        }
        if metric not in model_map:
            return []

        model, ts_col = model_map[metric]
        values: list[float] = []
        for i in range(days - 1, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            stmt = select(func.count()).select_from(model).where(
                model.competitor_id == competitor_id,
                ts_col >= day_start,
                ts_col < day_end,
            )
            count = (await session.execute(stmt)).scalar() or 0
            values.append(float(count))
        return values

    async def get_multi_metric_series(
        self, session: AsyncSession, competitor_id: int, days: int = 30
    ) -> dict[str, list[float]]:
        """Get all metric time series in one pass."""
        result: dict[str, list[float]] = {}
        for metric in ("services", "pricing", "content", "changes"):
            result[metric] = await self.get_time_series(session, competitor_id, metric, days)
        return result

    async def get_competitor_counts(
        self, session: AsyncSession, competitor_ids: list[int], since: datetime
    ) -> dict[str, dict[int, int]]:
        """Batch count multiple metrics for multiple competitors since a timestamp."""
        result: dict[str, dict[int, int]] = {}

        for model, label in [
            (CompetitorService, "services"),
            (CompetitorPricing, "pricing"),
            (CompetitorContent, "content"),
        ]:
            ts_col = model.collected_at
            stmt = (
                select(model.competitor_id, func.count().label("cnt"))
                .where(model.competitor_id.in_(competitor_ids))
                .where(ts_col >= since)
                .group_by(model.competitor_id)
            )
            result[label] = {r[0]: r[1] for r in (await session.execute(stmt)).all()}

        chg_stmt = (
            select(ChangeLog.competitor_id, func.count().label("cnt"))
            .where(ChangeLog.competitor_id.in_(competitor_ids))
            .where(ChangeLog.detected_at >= since)
            .group_by(ChangeLog.competitor_id)
        )
        result["changes"] = {r[0]: r[1] for r in (await session.execute(chg_stmt)).all()}

        col_stmt = (
            select(CollectionLog.competitor_id, func.count().label("cnt"))
            .where(CollectionLog.competitor_id.in_(competitor_ids))
            .where(CollectionLog.start_time >= since)
            .where(CollectionLog.success.is_(True))
            .group_by(CollectionLog.competitor_id)
        )
        result["collections"] = {r[0]: r[1] for r in (await session.execute(col_stmt)).all()}

        return result

    async def get_price_series(
        self, session: AsyncSession, competitor_id: int, days: int = 30
    ) -> list[float]:
        """Get price values ordered by time for trend analysis."""
        now = datetime.now(UTC)
        since = now - timedelta(days=days)
        stmt = (
            select(CompetitorPricing.base_price)
            .where(CompetitorPricing.competitor_id == competitor_id)
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.collected_at >= since)
            .order_by(CompetitorPricing.collected_at)
        )
        rows = (await session.execute(stmt)).all()
        return [float(r[0]) for r in rows]

    async def get_category_prices(
        self, session: AsyncSession
    ) -> dict[str, list[dict[str, Any]]]:
        """Get all prices grouped by category for opportunity detection."""
        stmt = (
            select(
                CompetitorPricing.category,
                CompetitorPricing.competitor_id,
                func.avg(CompetitorPricing.base_price).label("avg_price"),
                func.min(CompetitorPricing.base_price).label("min_price"),
                func.max(CompetitorPricing.base_price).label("max_price"),
                func.count().label("sample_count"),
            )
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.category.isnot(None))
            .group_by(CompetitorPricing.category, CompetitorPricing.competitor_id)
        )
        rows = (await session.execute(stmt)).all()
        result: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            result.setdefault(r[0], []).append({
                "competitor_id": r[1],
                "avg_price": float(r[2]) if r[2] else 0,
                "min_price": float(r[3]) if r[3] else 0,
                "max_price": float(r[4]) if r[4] else 0,
                "sample_count": r[5],
            })
        return result

    async def get_category_service_counts(
        self, session: AsyncSession
    ) -> dict[str, dict[int, int]]:
        """Get service counts per category per competitor."""
        stmt = (
            select(
                CompetitorService.service_category,
                CompetitorService.competitor_id,
                func.count().label("cnt"),
            )
            .where(CompetitorService.service_category.isnot(None))
            .group_by(CompetitorService.service_category, CompetitorService.competitor_id)
        )
        rows = (await session.execute(stmt)).all()
        result: dict[str, dict[int, int]] = {}
        for r in rows:
            result.setdefault(r[0], {})[r[1]] = r[2]
        return result

    async def get_competitor_totals(
        self, session: AsyncSession, competitor_ids: list[int]
    ) -> dict[str, dict[int, int]]:
        """Get total counts (all time) for each competitor."""
        result: dict[str, dict[int, int]] = {}

        for model, label in [
            (CompetitorService, "services"),
            (CompetitorPricing, "pricing"),
            (CompetitorContent, "content"),
            (CompetitorSocial, "social"),
            (CompetitorSource, "sources"),
        ]:
            stmt = (
                select(model.competitor_id, func.count().label("cnt"))
                .where(model.competitor_id.in_(competitor_ids))
                .group_by(model.competitor_id)
            )
            result[label] = {r[0]: r[1] for r in (await session.execute(stmt)).all()}

        return result


prediction_data = PredictionDataService()
