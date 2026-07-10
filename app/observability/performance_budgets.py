"""Performance budgets and APM metrics.

Defines performance targets and tracks compliance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class BudgetStatus(Enum):
    """Performance budget status."""

    WITHIN_BUDGET = "within_budget"
    WARNING = "warning"
    EXCEEDED = "exceeded"


@dataclass
class PerformanceBudget:
    """Performance budget definition."""

    name: str
    metric_name: str
    target_value: float
    warning_threshold: float  # Percentage of target (e.g., 0.8 = 80%)
    unit: str = "ms"
    description: str = ""


@dataclass
class BudgetViolation:
    """Performance budget violation."""

    budget: PerformanceBudget
    actual_value: float
    status: BudgetStatus
    timestamp: float = field(default_factory=time.time)


class PerformanceBudgetManager:
    """Manages performance budgets and tracks compliance."""

    def __init__(self) -> None:
        self._budgets: dict[str, PerformanceBudget] = {}
        self._measurements: dict[str, list[float]] = {}
        self._violations: list[BudgetViolation] = []

    def add_budget(self, budget: PerformanceBudget) -> None:
        """Add a performance budget."""
        self._budgets[budget.name] = budget
        self._measurements[budget.name] = []
        logger.info(
            "performance_budget_added",
            budget_name=budget.name,
            target=budget.target_value,
            unit=budget.unit,
        )

    def record_measurement(self, budget_name: str, value: float) -> BudgetStatus:
        """Record a measurement and check against budget."""
        if budget_name not in self._budgets:
            logger.warning("unknown_performance_budget", budget_name=budget_name)
            return BudgetStatus.WITHIN_BUDGET

        budget = self._budgets[budget_name]
        self._measurements[budget_name].append(value)

        # Keep only last 1000 measurements
        if len(self._measurements[budget_name]) > 1000:
            self._measurements[budget_name] = self._measurements[budget_name][-1000:]

        # Check budget
        status = self._check_budget(budget, value)

        if status != BudgetStatus.WITHIN_BUDGET:
            violation = BudgetViolation(
                budget=budget,
                actual_value=value,
                status=status,
            )
            self._violations.append(violation)

            # Keep only last 100 violations
            if len(self._violations) > 100:
                self._violations = self._violations[-100:]

            logger.warning(
                "performance_budget_violation",
                budget_name=budget_name,
                actual_value=value,
                target_value=budget.target_value,
                status=status.value,
            )

        return status

    def _check_budget(self, budget: PerformanceBudget, value: float) -> BudgetStatus:
        """Check if a value exceeds a budget."""
        if value > budget.target_value:
            return BudgetStatus.EXCEEDED
        elif value > budget.target_value * budget.warning_threshold:
            return BudgetStatus.WARNING
        return BudgetStatus.WITHIN_BUDGET

    def get_budget_status(self, budget_name: str) -> dict[str, Any]:
        """Get status for a specific budget."""
        if budget_name not in self._budgets:
            return {"error": f"Budget '{budget_name}' not found"}

        budget = self._budgets[budget_name]
        measurements = self._measurements.get(budget_name, [])

        if not measurements:
            return {
                "budget": budget.name,
                "target": budget.target_value,
                "unit": budget.unit,
                "status": "no_data",
                "measurements": 0,
            }

        avg = sum(measurements) / len(measurements)
        min_val = min(measurements)
        max_val = max(measurements)
        p95 = (
            sorted(measurements)[int(len(measurements) * 0.95)]
            if len(measurements) >= 20
            else max_val
        )
        p99 = (
            sorted(measurements)[int(len(measurements) * 0.99)]
            if len(measurements) >= 100
            else max_val
        )

        violations = [v for v in self._violations if v.budget.name == budget_name]
        recent_violations = [v for v in violations if time.time() - v.timestamp < 3600]

        return {
            "budget": budget.name,
            "target": budget.target_value,
            "warning_threshold": budget.warning_threshold,
            "unit": budget.unit,
            "description": budget.description,
            "measurements": {
                "count": len(measurements),
                "avg": round(avg, 2),
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            },
            "compliance": {
                "within_budget": sum(
                    1 for v in violations if v.status == BudgetStatus.WITHIN_BUDGET
                ),
                "warnings": sum(1 for v in violations if v.status == BudgetStatus.WARNING),
                "exceeded": sum(1 for v in violations if v.status == BudgetStatus.EXCEEDED),
            },
            "recent_violations": len(recent_violations),
        }

    def get_all_budgets_status(self) -> list[dict[str, Any]]:
        """Get status for all budgets."""
        return [self.get_budget_status(name) for name in self._budgets]

    def get_violations(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent violations."""
        return [
            {
                "budget": v.budget.name,
                "actual_value": v.actual_value,
                "target_value": v.budget.target_value,
                "unit": v.budget.unit,
                "status": v.status.value,
                "timestamp": v.timestamp,
            }
            for v in self._violations[-limit:]
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all budgets."""
        total_violations = len(self._violations)
        recent_violations = [v for v in self._violations if time.time() - v.timestamp < 3600]

        return {
            "total_budgets": len(self._budgets),
            "total_violations": total_violations,
            "recent_violations": len(recent_violations),
            "budgets": {
                name: {
                    "target": budget.target_value,
                    "unit": budget.unit,
                    "status": self._check_current_status(name),
                }
                for name, budget in self._budgets.items()
            },
        }

    def _check_current_status(self, budget_name: str) -> str:
        """Check current status for a budget."""
        measurements = self._measurements.get(budget_name, [])
        if not measurements:
            return "no_data"

        # Check last measurement
        last_measurement = measurements[-1]
        budget = self._budgets[budget_name]
        status = self._check_budget(budget, last_measurement)
        return status.value


# Global performance budget manager
performance_budget_manager = PerformanceBudgetManager()


def setup_default_budgets() -> None:
    """Setup default performance budgets."""
    # Parser performance budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="parse_time",
            metric_name="parse_duration_ms",
            target_value=1000,  # 1 second
            warning_threshold=0.8,  # 800ms warning
            unit="ms",
            description="HTML parsing time",
        )
    )

    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="strategy_execution_time",
            metric_name="strategy_duration_ms",
            target_value=500,  # 500ms per strategy
            warning_threshold=0.8,  # 400ms warning
            unit="ms",
            description="Individual strategy execution time",
        )
    )

    # Collection performance budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="collection_time",
            metric_name="collection_duration_seconds",
            target_value=120,  # 2 minutes
            warning_threshold=0.8,  # 96 seconds warning
            unit="s",
            description="Total collection time per competitor",
        )
    )

    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="page_fetch_time",
            metric_name="fetch_duration_ms",
            target_value=5000,  # 5 seconds
            warning_threshold=0.8,  # 4 seconds warning
            unit="ms",
            description="Individual page fetch time",
        )
    )

    # Extraction quality budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="extraction_confidence",
            metric_name="confidence_score",
            target_value=0.7,  # 70% confidence
            warning_threshold=1.1,  # Warning if below 77% (0.7 * 1.1)
            unit="score",
            description="Minimum extraction confidence score",
        )
    )

    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="extraction_false_positive_rate",
            metric_name="false_positive_rate",
            target_value=0.1,  # 10% false positive rate
            warning_threshold=0.8,  # Warning if above 8%
            unit="rate",
            description="Maximum false positive rate",
        )
    )

    # Database performance budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="database_query_time",
            metric_name="query_duration_ms",
            target_value=100,  # 100ms
            warning_threshold=0.8,  # 80ms warning
            unit="ms",
            description="Database query execution time",
        )
    )

    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="database_connection_latency",
            metric_name="connection_latency_ms",
            target_value=50,  # 50ms
            warning_threshold=0.8,  # 40ms warning
            unit="ms",
            description="Database connection latency",
        )
    )

    # Memory budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="memory_usage",
            metric_name="rss_mb",
            target_value=512,  # 512MB
            warning_threshold=0.8,  # 409MB warning
            unit="MB",
            description="Process memory usage (RSS)",
        )
    )

    # Cache performance budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="cache_hit_rate",
            metric_name="cache_hit_rate",
            target_value=0.8,  # 80% hit rate
            warning_threshold=1.1,  # Warning if below 88%
            unit="rate",
            description="Cache hit rate",
        )
    )

    # API performance budgets
    performance_budget_manager.add_budget(
        PerformanceBudget(
            name="api_response_time",
            metric_name="response_time_ms",
            target_value=200,  # 200ms
            warning_threshold=0.8,  # 160ms warning
            unit="ms",
            description="API endpoint response time",
        )
    )
