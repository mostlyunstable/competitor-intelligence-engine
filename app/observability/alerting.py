"""Alerting system: monitors thresholds and sends notifications."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger("alerting")


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Status(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"


@dataclass
class Alert:
    name: str
    severity: Severity
    message: str
    timestamp: str
    status: Status


@dataclass
class AlertRule:
    name: str
    severity: Severity
    check_fn: Any  # Callable returning (bool, str)
    enabled: bool = True


class AlertManager:
    def __init__(self) -> None:
        self._active_alerts: dict[str, Alert] = {}
        self._history: list[Alert] = []
        self._rules: list[AlertRule] = []
        self._webhook_urls: list[str] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def set_webhooks(self, urls: list[str]) -> None:
        self._webhook_urls = urls

    def _fire_alert(self, alert: Alert) -> None:
        if alert.name in self._active_alerts:
            return  # Already active
        self._active_alerts[alert.name] = alert
        self._history.append(alert)
        logger.warning("alert_fired", name=alert.name, severity=alert.severity.value, message=alert.message)
        # Send webhook if configured
        if self._webhook_urls:
            import asyncio
            asyncio.create_task(self._send_webhook(alert))

    def _resolve_alert(self, name: str) -> None:
        if name in self._active_alerts:
            alert = self._active_alerts.pop(name)
            alert.status = Status.RESOLVED
            self._history.append(alert)
            logger.info("alert_resolved", name=name)

    async def _send_webhook(self, alert: Alert) -> None:
        import httpx
        payload = {
            "text": f"🚨 [{alert.severity.value.upper()}] {alert.name}: {alert.message}",
            "severity": alert.severity.value,
            "alert": alert.name,
        }
        for url in self._webhook_urls:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(url, json=payload, timeout=10)
            except Exception as e:
                logger.error("webhook_failed", url=url, error=str(e))

    async def evaluate(self, db_session: Any = None) -> None:
        """Evaluate all rules and fire/resolve alerts."""
        for rule in self._rules:
            if not rule.enabled:
                continue
            try:
                if db_session:
                    fired, message = await rule.check_fn(db_session)
                else:
                    fired, message = rule.check_fn()
                if fired:
                    self._fire_alert(Alert(
                        name=rule.name,
                        severity=rule.severity,
                        message=message,
                        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                        status=Status.ACTIVE,
                    ))
                else:
                    self._resolve_alert(rule.name)
            except Exception as e:
                logger.error("rule_evaluation_failed", rule=rule.name, error=str(e))

    def get_alert_stats(self) -> dict[str, Any]:
        by_severity = {}
        for alert in self._active_alerts.values():
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
        return {
            "active_alerts": len(self._active_alerts),
            "active_by_severity": by_severity,
        }

    def get_alert_history(self, limit: int = 10) -> list[Alert]:
        return self._history[-limit:]


alert_manager = AlertManager()


def setup_default_rules() -> None:
    """Set up default alert rules."""

    async def check_collection_failure_rate(session: Any) -> tuple[bool, str]:
        from sqlalchemy import text
        result = await session.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE success = false) as failed
            FROM collection_logs
            WHERE start_time > NOW() - INTERVAL '1 hour'
        """))
        row = result.one()
        if row.total > 0:
            rate = row.failed / row.total
            if rate > 0.2:
                return True, f"Collection failure rate is {rate:.0%} ({row.failed}/{row.total} in last hour)"
        return False, ""

    async def check_llm_provider_health(session: Any) -> tuple[bool, str]:
        try:
            from app.ai.infrastructure.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider()
            health = await provider.health()
            if not health.healthy:
                return True, f"LLM provider unhealthy: {health.error}"
        except Exception as e:
            return True, f"LLM provider check failed: {e}"
        return False, ""

    async def check_queue_depth(session: Any) -> tuple[bool, str]:
        from sqlalchemy import text
        result = await session.execute(text("""
            SELECT COUNT(*) FROM collection_logs
            WHERE end_time IS NULL AND start_time > NOW() - INTERVAL '10 minutes'
        """))
        count = result.scalar()
        if count and count > 5:
            return True, f"Collection queue depth is {count} (stalled collections)"
        return False, ""

    alert_manager.add_rule(AlertRule(
        name="high_collection_failure_rate",
        severity=Severity.CRITICAL,
        check_fn=check_collection_failure_rate,
    ))
    alert_manager.add_rule(AlertRule(
        name="llm_provider_unhealthy",
        severity=Severity.WARNING,
        check_fn=check_llm_provider_health,
    ))
    alert_manager.add_rule(AlertRule(
        name="queue_depth_high",
        severity=Severity.WARNING,
        check_fn=check_queue_depth,
    ))
