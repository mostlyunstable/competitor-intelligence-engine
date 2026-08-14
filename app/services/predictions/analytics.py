"""Shared Analytics: math utilities, time-series helpers, forecasting primitives.

All prediction modules import from here instead of duplicating logic.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def linear_trend(values: list[float]) -> float:
    """Simple linear regression slope. Returns change per step."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def direction_from_slope(slope: float, threshold: float = 0.01) -> str:
    if slope > threshold:
        return "increasing"
    elif slope < -threshold:
        return "decreasing"
    return "stable"


def moving_average(values: list[float], window: int = 3) -> list[float]:
    """Simple moving average over `window` steps."""
    if not values or window < 1:
        return list(values)
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(sum(values[start:i + 1]) / (i - start + 1))
    return result


def weighted_moving_average(values: list[float], window: int = 3) -> float:
    """Exponentially weighted moving average. Recent values weighted more."""
    if not values:
        return 0.0
    w = min(window, len(values))
    alpha = 2.0 / (w + 1)
    ewma = values[0]
    for v in values[1:]:
        ewma = alpha * v + (1 - alpha) * ewma
    return ewma


def volatility(values: list[float]) -> float:
    """Coefficient of variation (stddev / mean). Returns 0 if mean is 0."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if abs(mean) < 1e-10:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance) / abs(mean)


def momentum(values: list[float]) -> float:
    """Rate of change acceleration: (last - mid) - (mid - first)."""
    if len(values) < 3:
        return 0.0
    n = len(values)
    mid = n // 2
    first_half_avg = sum(values[:mid]) / mid if mid else 0.0
    second_half_avg = sum(values[mid:]) / (n - mid) if n - mid else 0.0
    return second_half_avg - first_half_avg


def growth_rate(values: list[float]) -> float:
    """Compound growth rate from first to last value."""
    if len(values) < 2 or values[0] <= 0:
        return 0.0
    return (values[-1] / values[0]) ** (1 / (len(values) - 1)) - 1


def trend_stability(values: list[float]) -> float:
    """Returns 0-1 stability score. 1 = perfectly stable."""
    if len(values) < 2:
        return 1.0
    v = volatility(values)
    return clamp(1.0 - v, 0.0, 1.0)


def seasonality_strength(values: list[float], period: int = 4) -> float:
    """Detect seasonal strength by comparing period means."""
    if len(values) < period * 2:
        return 0.0
    groups: list[list[float]] = [[] for _ in range(period)]
    for i, v in enumerate(values):
        groups[i % period].append(v)
    means = [sum(g) / len(g) if g else 0.0 for g in groups]
    overall_mean = sum(values) / len(values)
    if abs(overall_mean) < 1e-10:
        return 0.0
    between_var = sum((m - overall_mean) ** 2 for m in means) / period
    total_var = sum((v - overall_mean) ** 2 for v in values) / len(values)
    return clamp(math.sqrt(between_var / total_var) if total_var > 0 else 0.0)


def _t_value(df: int, confidence: float = 0.95) -> float:
    """Approximate t-value for given degrees of freedom."""
    # Approximation: t ≈ z * (1 + (z^2 + 1) / (4 * df))
    if df >= 30:
        return 1.96
    z = 1.96
    return z * (1 + (z**2 + 1) / (4 * df))


def prediction_interval(
    values: list[float], confidence: float = 0.95
) -> tuple[float, float]:
    """Simple prediction interval based on historical stddev."""
    if len(values) < 2:
        v = values[0] if values else 0.0
        return (v, v)
    mean = sum(values) / len(values)
    stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
    df = len(values) - 1
    if df >= 30:
        crit = 1.96 if confidence >= 0.95 else 1.645 if confidence >= 0.90 else 1.0
    else:
        crit = _t_value(df)
    return (mean - crit * stddev, mean + crit * stddev)


def forecast_next(values: list[float], steps: int = 1) -> list[float]:
    """Naive forecast: extrapolate linear trend."""
    if not values:
        return [0.0] * steps
    slope = linear_trend(values)
    last = values[-1]
    return [last + slope * (i + 1) for i in range(steps)]


def percentile(values: list[float], p: float) -> float:
    """Returns the p-th percentile (0-100) of values."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_v[int(k)]
    return sorted_v[f] * (c - k) + sorted_v[c] * (k - f)


def z_score(value: float, values: list[float]) -> float:
    """How many standard deviations from the mean."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
    if stddev < 1e-10:
        return 0.0
    return (value - mean) / stddev


def horizon_days(horizon: str) -> int:
    """Convert horizon string to days."""
    mapping = {
        "7d": 7, "7days": 7, "1w": 7,
        "30d": 30, "30days": 30, "1m": 30, "1month": 30,
        "90d": 90, "90days": 90, "3m": 90, "3months": 90, "1q": 90, "1quarter": 90,
        "180d": 180, "180days": 180, "6m": 180, "6months": 180,
        "365d": 365, "365days": 365, "1y": 365, "1year": 365,
    }
    return mapping.get(horizon.lower().strip(), 30)
