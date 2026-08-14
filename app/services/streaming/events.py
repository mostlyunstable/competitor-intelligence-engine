"""Event Streaming — minimal interface for API compatibility."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class EventType(str, Enum):
    PRICE_CHANGE = "price_change"
    SERVICE_LAUNCH = "service_launch"
    EXPANSION = "expansion"
    ALERT = "alert"
    FORECAST_UPDATE = "forecast_update"
    RECOMMENDATION = "recommendation"
    BENCHMARK_UPDATE = "benchmark_update"
    COLLECTION_COMPLETE = "collection_complete"
    COLLECTION_FAILED = "collection_failed"
    CHANGES_DETECTED = "changes_detected"


@dataclass
class Event:
    event_type: EventType
    data: dict
    source: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"{self.event_type.value}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"


class EventStreamingManager:
    """Lightweight event history for dashboard display."""

    def __init__(self) -> None:
        self._event_history: deque[Event] = deque(maxlen=200)
        self._stats: dict[str, int] = defaultdict(int)

    def publish_sync(self, event: Event) -> None:
        self._event_history.append(event)
        self._stats[event.event_type.value] += 1

    def get_recent_events(self, event_type: EventType | None = None, limit: int = 50) -> list[dict]:
        events = list(self._event_history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {"id": e.id, "type": e.event_type.value, "data": e.data, "timestamp": e.timestamp, "source": e.source}
            for e in events[-limit:]
        ]

    def get_stats(self) -> dict:
        return {
            "history_size": len(self._event_history),
            "events_by_type": dict(self._stats),
        }


event_streaming = EventStreamingManager()
