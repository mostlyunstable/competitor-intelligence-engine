from dataclasses import dataclass
from enum import Enum
from typing import Any


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


class AlertManager:
    def get_alert_stats(self) -> dict[str, Any]:
        return {"active_alerts": 0, "active_by_severity": {}}

    def get_alert_history(self, limit: int = 10) -> list[Alert]:
        return []


alert_manager = AlertManager()
