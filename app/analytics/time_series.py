"""Time-series forecasting for pricing and service metrics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ForecastResult:
    predictions: list[float]
    confidence_intervals: list[tuple[float, float]]
    model_name: str
    metrics: dict[str, float]


class PriceForecaster:
    """Forecasts price trends using Linear Trend + Exponential Smoothing."""

    def linear_trend_forecast(self, values: list[float], steps: int = 7) -> ForecastResult:
        n = len(values)
        if n < 2:
            v = values[0] if values else 0.0
            return ForecastResult(
                predictions=[v] * steps,
                confidence_intervals=[(v, v)] * steps,
                model_name="linear_trend",
                metrics={"r2": 0.0},
            )

        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0
        intercept = y_mean - slope * x_mean

        preds = [slope * (n + i) + intercept for i in range(steps)]

        residuals = [values[i] - (slope * i + intercept) for i in range(n)]
        std = math.sqrt(sum(r ** 2 for r in residuals) / max(n - 2, 1))

        # CI widens with sqrt(step) — more uncertainty further out
        ci = [
            (p - 1.96 * std * math.sqrt(i + 1), p + 1.96 * std * math.sqrt(i + 1))
            for i, p in enumerate(preds)
        ]

        ss_tot = sum((v - y_mean) ** 2 for v in values)
        ss_res = sum(r ** 2 for r in residuals)
        r2 = max(0.0, 1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        return ForecastResult(
            predictions=[round(p, 2) for p in preds],
            confidence_intervals=[(round(lo, 2), round(hi, 2)) for lo, hi in ci],
            model_name="linear_trend",
            metrics={"r2": round(r2, 4), "slope": round(slope, 4), "std": round(std, 4)},
        )

    def exponential_smoothing_forecast(
        self, values: list[float], steps: int = 7, alpha: float = 0.3
    ) -> ForecastResult:
        if not values:
            return ForecastResult([0.0] * steps, [(0, 0)] * steps, "exp_smoothing", {})

        # Single exponential smoothing
        smoothed = [values[0]]
        for v in values[1:]:
            smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])

        level = smoothed[-1]
        # Trend component from last differences
        trend = 0.0
        if len(smoothed) >= 2:
            diffs = [smoothed[i] - smoothed[i - 1] for i in range(max(1, len(smoothed) - 5), len(smoothed))]
            trend = sum(diffs) / len(diffs) if diffs else 0

        preds = [level + trend * (i + 1) for i in range(steps)]

        residuals = [values[i] - smoothed[i] for i in range(len(values))]
        std = math.sqrt(sum(r ** 2 for r in residuals) / max(len(values) - 1, 1))

        ci = [
            (p - 1.96 * std * math.sqrt(i + 1), p + 1.96 * std * math.sqrt(i + 1))
            for i, p in enumerate(preds)
        ]

        return ForecastResult(
            predictions=[round(max(0, p), 2) for p in preds],
            confidence_intervals=[(round(max(0, lo), 2), round(hi, 2)) for lo, hi in ci],
            model_name="exp_smoothing",
            metrics={"alpha": alpha, "level": round(level, 4), "trend": round(trend, 4), "std": round(std, 4)},
        )

    def forecast(self, values: list[float], steps: int = 7, model: str = "linear_trend") -> ForecastResult:
        if model == "exp_smoothing":
            return self.exponential_smoothing_forecast(values, steps)
        return self.linear_trend_forecast(values, steps)
