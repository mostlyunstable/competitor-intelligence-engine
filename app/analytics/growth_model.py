"""Growth velocity analysis across multiple time windows."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class GrowthMetrics:
    catalog_velocity_30d: float
    catalog_velocity_60d: float
    catalog_velocity_90d: float
    digital_footprint_rate: float
    content_publishing_velocity: float
    overall_growth_score: float
    growth_direction: str  # growing, stable, declining


class GrowthAnalyzer:
    """Computes growth velocity scores from time-series data."""

    def analyze(self, service_counts: list[float], pricing_counts: list[float], content_counts: list[float]) -> GrowthMetrics:
        svc_30 = self._velocity(service_counts, 30)
        svc_60 = self._velocity(service_counts, 60)
        svc_90 = self._velocity(service_counts, 90)

        # Digital footprint = combined pricing + content activity
        digital = [p + c for p, c in zip(pricing_counts, content_counts)]
        digital_rate = self._velocity(digital, 30)

        content_vel = self._velocity(content_counts, 30)

        # Overall score: weighted average
        overall = (svc_30 * 0.4 + svc_60 * 0.25 + digital_rate * 0.2 + content_vel * 0.15)

        if overall > 0.1:
            direction = "growing"
        elif overall < -0.1:
            direction = "declining"
        else:
            direction = "stable"

        return GrowthMetrics(
            catalog_velocity_30d=round(svc_30, 4),
            catalog_velocity_60d=round(svc_60, 4),
            catalog_velocity_90d=round(svc_90, 4),
            digital_footprint_rate=round(digital_rate, 4),
            content_publishing_velocity=round(content_vel, 4),
            overall_growth_score=round(overall, 4),
            growth_direction=direction,
        )

    def _velocity(self, values: list[float], window: int) -> float:
        if len(values) < 2:
            return 0.0
        w = min(window, len(values))
        recent = values[-w:]
        if len(recent) < 2:
            return 0.0
        first_half = sum(recent[: len(recent) // 2]) / max(len(recent) // 2, 1)
        second_half = sum(recent[len(recent) // 2 :]) / max(len(recent) - len(recent) // 2, 1)
        if first_half == 0:
            return (second_half - first_half) if second_half > 0 else 0.0
        return (second_half - first_half) / max(abs(first_half), 1)
