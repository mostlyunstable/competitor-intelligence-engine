"""Continuous Learning.

Tracks prediction accuracy and auto-adjusts weights. In-memory store
sufficient for demo; swap for DB persistence in production.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ContinuousLearner:
    """Learns from prediction outcomes and adjusts system behavior."""

    def __init__(self) -> None:
        self._outcomes: list[dict[str, Any]] = []
        self._weight_adjustments: dict[str, float] = {}
        self._prediction_log: list[dict[str, Any]] = []

    def log_prediction(
        self, prediction_type: str, prediction_id: int, data: dict, accuracy: float
    ) -> None:
        """Sync logging (backward compat)."""
        self._prediction_log.append({
            "prediction_type": prediction_type,
            "prediction_id": prediction_id,
            "data": data,
            "accuracy": accuracy,
            "recorded_at": datetime.now(UTC).isoformat(),
        })

    def record_outcome(
        self, prediction_type: str, prediction_id: int, actual: Any
    ) -> dict[str, Any] | None:
        """Sync outcome recording (backward compat)."""
        matched = [p for p in self._prediction_log if p["prediction_id"] == prediction_id]
        if not matched:
            return None

        predicted = matched[-1]["accuracy"]
        error = abs(predicted - actual) / max(abs(actual), 1)
        accuracy = max(0.0, 1.0 - error)

        self._outcomes.append({
            "prediction_id": prediction_id,
            "prediction_type": prediction_type,
            "predicted": predicted,
            "actual": actual,
            "error_pct": round(error * 100, 2),
            "accuracy": round(accuracy, 4),
            "recorded_at": datetime.now(UTC).isoformat(),
        })

        self._adjust_weight(prediction_type, accuracy)

        return self._outcomes[-1]

    def get_accuracy_report(self) -> dict[str, Any]:
        """Sync accuracy report (backward compat)."""
        if not self._outcomes:
            return {"total_predictions": 0, "recorded_outcomes": 0, "average_accuracy": 0, "by_type": {}}

        by_type: dict[str, list[float]] = {}
        for o in self._outcomes:
            by_type.setdefault(o["prediction_type"], []).append(o["accuracy"])

        avg = round(
            sum(sum(v) / len(v) for v in by_type.values()) / max(len(by_type), 1), 3
        )

        return {
            "total_predictions": len(self._outcomes),
            "recorded_outcomes": len(self._outcomes),
            "average_accuracy": avg,
            "avg_accuracy": avg,
            "by_type": {
                k: {"count": len(v), "avg_accuracy": round(sum(v) / len(v), 3)}
                for k, v in by_type.items()
            },
        }

    def get_confidence_drift(self) -> dict[str, Any]:
        """Sync drift report (backward compat)."""
        if len(self._outcomes) < 2:
            return {"drift": "insufficient_data", "drifting": False, "reason": "Insufficient data"}

        recent = self._outcomes[-5:]
        older = self._outcomes[:-5] or self._outcomes[:1]

        recent_avg = sum(o["accuracy"] for o in recent) / len(recent)
        older_avg = sum(o["accuracy"] for o in older) / len(older)

        return {
            "drift": "drifting" if abs(recent_avg - older_avg) > 0.1 else "stable",
            "drifting": abs(recent_avg - older_avg) > 0.1,
            "recent_accuracy": round(recent_avg, 3),
            "older_accuracy": round(older_avg, 3),
            "delta": round(recent_avg - older_avg, 3),
        }

    def get_model_versions(self) -> list[dict[str, Any]]:
        """Sync model versions (backward compat)."""
        if not self._weight_adjustments:
            return [{"type": "heuristic", "version": "heuristic_v1", "adjustment": 0}]
        return [{"type": k, "version": f"{k}_v1", "adjustment": round(v, 4)} for k, v in self._weight_adjustments.items()]

    def get_feature_effectiveness(self) -> dict[str, Any]:
        """Sync feature effectiveness (backward compat)."""
        features = ["services", "pricing", "content", "changes", "growth"]
        return {
            "features": features,
            "feature_count": len(features),
            "weights": {k: round(self._weight_adjustments.get(k, 0), 4) for k in features},
        }

    async def record_outcome_async(
        self,
        prediction_id: int,
        prediction_type: str,
        predicted: Any,
        actual: Any,
    ) -> None:
        error = abs(float(predicted) - float(actual)) / max(abs(float(actual)), 1)
        accuracy = max(0.0, 1.0 - error)

        self._outcomes.append({
            "prediction_id": prediction_id,
            "prediction_type": prediction_type,
            "predicted": predicted,
            "actual": actual,
            "error_pct": round(error * 100, 2),
            "accuracy": round(accuracy, 4),
            "recorded_at": datetime.now(UTC).isoformat(),
        })

        self._adjust_weight(prediction_type, accuracy)

    async def get_accuracy_stats(
        self, prediction_type: str | None = None, days: int = 30
    ) -> dict[str, Any]:
        return self.get_accuracy_report()

    def _adjust_weight(self, prediction_type: str, accuracy: float) -> None:
        adjustment = (accuracy - 0.5) * 0.1
        current = self._weight_adjustments.get(prediction_type, 0.0)
        self._weight_adjustments[prediction_type] = current + adjustment

    def get_weight_adjustment(self, prediction_type: str) -> float:
        return self._weight_adjustments.get(prediction_type, 0.0)

    async def should_recalibrate(self) -> bool:
        stats = self.get_accuracy_report()
        if stats["total_predictions"] < 10:
            return False
        return stats["avg_accuracy"] < 0.6

    async def get_learning_summary(self) -> dict[str, Any]:
        stats = self.get_accuracy_report()
        return {
            "tracked_types": list(self._weight_adjustments.keys()),
            "weight_adjustments": dict(self._weight_adjustments),
            "accuracy_stats": stats,
        }


ContinuousLearningFramework = ContinuousLearner  # backward compat alias
continuous_learner = ContinuousLearner()
