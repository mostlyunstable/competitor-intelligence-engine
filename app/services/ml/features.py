"""Feature engineering for multivariate time-series forecasting.

Builds feature matrices from DB data: service counts, pricing activity,
change velocity, content publish rate, seasonality, and lagged values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class FeatureSet:
    """A feature matrix for time-series forecasting."""
    target: list[float]
    features: list[list[float]]
    feature_names: list[str]
    labels: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


async def build_features(
    session: AsyncSession,
    competitor_id: int,
    metric: str = "services",
    days: int = 30,
) -> FeatureSet:
    """Build a multivariate feature set from DB data.

    Features engineered:
    - target: daily count of the primary metric
    - time_idx: sequential day index
    - day_of_week: cyclical encoding (sin/cos)
    - service_count: total services for the competitor
    - pricing_count: total pricing entries
    - content_count: total content entries
    - change_velocity_7d: rolling 7-day change count
    - pricing_velocity_7d: rolling 7-day pricing activity
    - lag_1d, lag_7d: lagged target values
    - rolling_mean_7d, rolling_std_7d: rolling statistics
    """
    from sqlalchemy import select, func
    from app.database.models import (
        CompetitorService, CompetitorPricing, CompetitorContent, ChangeLog,
    )

    now = datetime.now(UTC)

    # ── Primary target: daily count of metric ─────────────────────────────
    model_map = {
        "services": CompetitorService,
        "pricing": CompetitorPricing,
        "content": CompetitorContent,
    }
    target_model = model_map.get(metric, CompetitorService)

    daily_counts: list[float] = []
    labels: list[str] = []
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        stmt = select(func.count()).select_from(target_model).where(
            target_model.competitor_id == competitor_id,
            target_model.collected_at >= day_start,
            target_model.collected_at < day_end,
        )
        count = await session.scalar(stmt) or 0
        daily_counts.append(float(count))
        labels.append(day_start.strftime("%b %d"))

    # ── Service count (total, per day) ────────────────────────────────────
    service_daily = await _daily_count(session, CompetitorService, competitor_id, days, now)

    # ── Pricing count (total, per day) ────────────────────────────────────
    pricing_daily = await _daily_count(session, CompetitorPricing, competitor_id, days, now)

    # ── Content count (per day) ───────────────────────────────────────────
    content_daily = await _daily_count(session, CompetitorContent, competitor_id, days, now)

    # ── Change velocity (per day) ─────────────────────────────────────────
    change_daily = await _daily_count_changes(session, competitor_id, days, now)

    # ── Build feature matrix ──────────────────────────────────────────────
    features: list[list[float]] = []
    feature_names = [
        "time_idx",
        "day_of_week_sin", "day_of_week_cos",
        "service_count", "pricing_count", "content_count",
        "change_velocity_7d", "pricing_velocity_7d",
        "lag_1d", "lag_7d",
        "rolling_mean_7d", "rolling_std_7d",
    ]

    for i in range(days):
        row = [
            float(i),                                          # time_idx
            math.sin(2 * math.pi * (i % 7) / 7),             # day_of_week_sin
            math.cos(2 * math.pi * (i % 7) / 7),             # day_of_week_cos
            service_daily[i],                                   # service_count
            pricing_daily[i],                                   # pricing_count
            content_daily[i],                                   # content_count
            _rolling_sum(change_daily, i, 7),                  # change_velocity_7d
            _rolling_sum(pricing_daily, i, 7),                 # pricing_velocity_7d
            daily_counts[i - 1] if i > 0 else daily_counts[0], # lag_1d
            daily_counts[i - 7] if i >= 7 else daily_counts[0],# lag_7d
            _rolling_mean(daily_counts, i, 7),                 # rolling_mean_7d
            _rolling_std(daily_counts, i, 7),                  # rolling_std_7d
        ]
        features.append(row)

    return FeatureSet(
        target=daily_counts,
        features=features,
        feature_names=feature_names,
        labels=labels,
        metadata={
            "competitor_id": competitor_id,
            "metric": metric,
            "days": days,
            "feature_count": len(feature_names),
        },
    )


async def build_features_simple(
    values: list[float],
    extra_features: list[list[float]] | None = None,
) -> FeatureSet:
    """Build features from a simple value list (no DB access).

    Used for univariate fallback when DB session is unavailable.
    """
    n = len(values)
    labels = [f"day_{i}" for i in range(n)]

    features: list[list[float]] = []
    feature_names = ["time_idx", "lag_1d", "lag_7d", "rolling_mean_7d"]

    for i in range(n):
        row = [
            float(i),
            values[i - 1] if i > 0 else values[0],
            values[i - 7] if i >= 7 else values[0],
            _rolling_mean(values, i, 7),
        ]
        if extra_features and i < len(extra_features):
            row.extend(extra_features[i])
        features.append(row)

    if extra_features and extra_features[0]:
        features[0]  # noqa: just checking
        feature_names.extend([f"extra_{j}" for j in range(len(extra_features[0]))])

    return FeatureSet(
        target=values,
        features=features,
        feature_names=feature_names,
        labels=labels,
        metadata={"days": n, "feature_count": len(feature_names)},
    )


async def _daily_count(
    session: AsyncSession,
    model: Any,
    competitor_id: int,
    days: int,
    now: datetime,
) -> list[float]:
    """Get daily count for a model over N days."""
    from sqlalchemy import select, func

    counts: list[float] = []
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        stmt = select(func.count()).select_from(model).where(
            model.competitor_id == competitor_id,
            model.collected_at >= day_start,
            model.collected_at < day_end,
        )
        counts.append(float(await session.scalar(stmt) or 0))
    return counts


async def _daily_count_changes(
    session: AsyncSession,
    competitor_id: int,
    days: int,
    now: datetime,
) -> list[float]:
    """Get daily change log count over N days."""
    from sqlalchemy import select, func
    from app.database.models import ChangeLog

    counts: list[float] = []
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        stmt = select(func.count()).select_from(ChangeLog).where(
            ChangeLog.competitor_id == competitor_id,
            ChangeLog.detected_at >= day_start,
            ChangeLog.detected_at < day_end,
        )
        counts.append(float(await session.scalar(stmt) or 0))
    return counts


def _rolling_sum(values: list[float], index: int, window: int) -> float:
    """Compute rolling sum up to index with given window."""
    start = max(0, index - window + 1)
    return sum(values[start:index + 1])


def _rolling_mean(values: list[float], index: int, window: int) -> float:
    """Compute rolling mean up to index with given window."""
    start = max(0, index - window + 1)
    subset = values[start:index + 1]
    return sum(subset) / max(len(subset), 1)


def _rolling_std(values: list[float], index: int, window: int) -> float:
    """Compute rolling std up to index with given window."""
    start = max(0, index - window + 1)
    subset = values[start:index + 1]
    if len(subset) < 2:
        return 0.0
    mean = sum(subset) / len(subset)
    variance = sum((x - mean) ** 2 for x in subset) / (len(subset) - 1)
    return math.sqrt(variance)
