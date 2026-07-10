"""Alerting system for critical conditions.

Monitors system health and triggers alerts when thresholds are exceeded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""

    ACTIVE = "active"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Alert definition."""

    name: str
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    status: AlertStatus = AlertStatus.ACTIVE
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule definition."""

    name: str
    severity: AlertSeverity
    condition: Callable[[], bool]
    message_template: str
    cooldown_seconds: int = 300
    last_triggered: float = 0


class AlertManager:
    """Manages alerts and alert rules."""

    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []
        self._max_history = 1000

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.name] = rule
        logger.info("alert_rule_added", rule_name=rule.name, severity=rule.severity.value)

    def remove_rule(self, rule_name: str) -> None:
        """Remove an alert rule."""
        self._rules.pop(rule_name, None)
        logger.info("alert_rule_removed", rule_name=rule_name)

    def evaluate_rules(self) -> list[Alert]:
        """Evaluate all rules and return new alerts."""
        new_alerts = []
        current_time = time.time()

        for rule_name, rule in self._rules.items():
            # Check cooldown
            if current_time - rule.last_triggered < rule.cooldown_seconds:
                continue

            # Evaluate condition
            try:
                if rule.condition():
                    alert = Alert(
                        name=rule_name,
                        severity=rule.severity,
                        message=rule.message_template,
                        labels={"rule": rule_name},
                    )
                    new_alerts.append(alert)
                    rule.last_triggered = current_time
                    self._active_alerts[rule_name] = alert
                    self._alert_history.append(alert)

                    # Trim history
                    if len(self._alert_history) > self._max_history:
                        self._alert_history = self._alert_history[-self._max_history :]

                    logger.warning(
                        "alert_triggered",
                        alert_name=rule_name,
                        severity=rule.severity.value,
                        message=rule.message_template,
                    )
            except Exception as e:
                logger.error("alert_rule_evaluation_failed", rule_name=rule_name, error=str(e))

        return new_alerts

    def resolve_alert(self, alert_name: str) -> bool:
        """Resolve an active alert."""
        if alert_name in self._active_alerts:
            alert = self._active_alerts.pop(alert_name)
            alert.status = AlertStatus.RESOLVED
            self._alert_history.append(alert)
            logger.info("alert_resolved", alert_name=alert_name)
            return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> list[Alert]:
        """Get alert history."""
        return self._alert_history[-limit:]

    def get_alert_stats(self) -> dict[str, Any]:
        """Get alert statistics."""
        active_by_severity: dict[str, int] = {}
        for alert in self._active_alerts.values():
            severity = alert.severity.value
            active_by_severity[severity] = active_by_severity.get(severity, 0) + 1

        return {
            "active_alerts": len(self._active_alerts),
            "active_by_severity": active_by_severity,
            "total_rules": len(self._rules),
            "history_size": len(self._alert_history),
        }


# Global alert manager
alert_manager = AlertManager()


def setup_default_alerts() -> None:
    """Setup default alert rules for common conditions."""
    from app.observability.prometheus_metrics import _metrics

    # High error rate alert
    alert_manager.add_rule(
        AlertRule(
            name="high_error_rate",
            severity=AlertSeverity.CRITICAL,
            condition=lambda: _metrics["counters"].get("collection_errors_total", 0) > 10,
            message_template="Collection error rate exceeded threshold",
            cooldown_seconds=600,
        )
    )

    # High memory usage alert
    alert_manager.add_rule(
        AlertRule(
            name="high_memory_usage",
            severity=AlertSeverity.WARNING,
            condition=lambda: _check_memory_usage(),
            message_template="Memory usage exceeded 512MB",
            cooldown_seconds=300,
        )
    )

    # Database connection failure alert
    alert_manager.add_rule(
        AlertRule(
            name="database_connection_failure",
            severity=AlertSeverity.CRITICAL,
            condition=lambda: _metrics["counters"].get("database_errors_total", 0) > 5,
            message_template="Database connection failures detected",
            cooldown_seconds=300,
        )
    )

    # Low extraction confidence alert
    alert_manager.add_rule(
        AlertRule(
            name="low_extraction_confidence",
            severity=AlertSeverity.WARNING,
            condition=lambda: _check_low_confidence(),
            message_template="Average extraction confidence below 0.5",
            cooldown_seconds=600,
        )
    )

    # Crawl budget exceeded alert
    alert_manager.add_rule(
        AlertRule(
            name="crawl_budget_exceeded",
            severity=AlertSeverity.WARNING,
            condition=lambda: _metrics["counters"].get("crawl_budget_exceeded_total", 0) > 0,
            message_template="Crawl budget exceeded for one or more competitors",
            cooldown_seconds=900,
        )
    )


def _check_memory_usage() -> bool:
    """Check if memory usage is high."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = usage.ru_maxrss / 1024  # macOS: bytes → MB
        return bool(rss_mb > 512)
    except Exception:
        return False


def _check_low_confidence() -> bool:
    """Check if average extraction confidence is low."""
    from app.observability.parser_metrics import registry

    if registry.global_stats["total_pages"] == 0:
        return False

    total_confidence = sum(
        stats.get("confidence_sum", 0) for stats in registry.strategy_stats.values()
    )
    total_executions = sum(
        stats.get("execution_count", 0) for stats in registry.strategy_stats.values()
    )

    if total_executions == 0:
        return False

    avg_confidence = total_confidence / total_executions
    return bool(avg_confidence < 0.5)
