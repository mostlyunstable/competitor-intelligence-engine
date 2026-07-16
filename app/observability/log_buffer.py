import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any


class LogBuffer:
    def __init__(self, max_len: int = 500):
        self.buffer: deque[dict[str, Any]] = deque(maxlen=max_len)
        self.lock = threading.Lock()

    def add_log(self, _: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
        """A structlog processor that captures logs."""
        log_entry = dict(event_dict)
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.now(UTC).isoformat()
        with self.lock:
            self.buffer.append(log_entry)
        return event_dict

    def get_logs_for_competitor(self, competitor_id: int) -> list[dict[str, Any]]:
        with self.lock:
            return [log for log in self.buffer if log.get("competitor_id") == competitor_id]


global_log_buffer = LogBuffer()
