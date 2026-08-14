"""Multi-factor confidence scoring for predictions."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    score: float  # 0.0 to 1.0
    factors: dict[str, float]
    reliability: str  # high, medium, low


class ConfidenceScorer:
    """Calculates prediction confidence from multiple factors."""

    def score(
        self,
        sample_size: int = 0,
        data_age_days: float = 0.0,
        completeness: float = 1.0,
        historical_accuracy: float = 0.5,
        variance: float = 0.0,
    ) -> ConfidenceResult:
        factors = {
            "sample_size": self._score_sample_size(sample_size),
            "data_freshness": self._score_freshness(data_age_days),
            "completeness": max(0.0, min(1.0, completeness)),
            "historical_accuracy": max(0.0, min(1.0, historical_accuracy)),
            "stability": max(0.0, min(1.0, 1.0 - min(variance, 1.0))),
        }

        weights = {
            "sample_size": 0.20,
            "data_freshness": 0.20,
            "completeness": 0.15,
            "historical_accuracy": 0.25,
            "stability": 0.20,
        }

        score = sum(factors[k] * weights[k] for k in factors)
        score = max(0.0, min(1.0, score))

        reliability = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"

        return ConfidenceResult(score=round(score, 4), factors={k: round(v, 4) for k, v in factors.items()}, reliability=reliability)

    def _score_sample_size(self, n: int) -> float:
        if n >= 30:
            return 1.0
        elif n >= 20:
            return 0.9
        elif n >= 10:
            return 0.7
        elif n >= 5:
            return 0.5
        elif n >= 2:
            return 0.3
        return 0.1

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

    def t_adjusted_interval(
        self, mean: float, std: float, df: int, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Prediction interval using t-distribution for small samples."""
        t_val = self._t_value(df, confidence)
        return (mean - t_val * std, mean + t_val * std)

    def _t_value(self, df: int, confidence: float = 0.95) -> float:
        if df >= 30:
            return 1.96
        z = 1.96
        return z * (1 + (z ** 2 + 1) / (4 * df))
