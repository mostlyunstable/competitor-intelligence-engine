"""Application Performance Monitoring (APM) module.

Tracks detailed performance metrics for all system components.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Generator

logger = structlog.get_logger()


@dataclass
class Span:
    """APM span representing a unit of work."""

    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: float | None = None
    status: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)
    parent_span_id: str | None = None
    span_id: str = ""

    def __post_init__(self) -> None:
        if not self.span_id:
            self.span_id = f"span_{id(self)}"

    def finish(self, status: str = "ok") -> None:
        """Finish the span."""
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status


@dataclass
class Transaction:
    """APM transaction representing a complete operation."""

    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: float | None = None
    status: str = "ok"
    spans: list[Span] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    transaction_id: str = ""

    def __post_init__(self) -> None:
        if not self.transaction_id:
            self.transaction_id = f"txn_{id(self)}"

    def finish(self, status: str = "ok") -> None:
        """Finish the transaction."""
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Span:
        """Start a new span within this transaction."""
        span = Span(
            name=name,
            start_time=time.monotonic(),
            attributes=attributes or {},
            parent_span_id=self.transaction_id,
        )
        self.spans.append(span)
        return span


class APMCollector:
    """Collects APM data."""

    def __init__(self, max_transactions: int = 1000) -> None:
        self._transactions: list[Transaction] = []
        self._max_transactions = max_transactions
        self._stats: dict[str, Any] = {
            "total_transactions": 0,
            "total_spans": 0,
            "avg_transaction_duration": 0,
            "p95_transaction_duration": 0,
            "p99_transaction_duration": 0,
            "error_rate": 0,
        }

    def start_transaction(self, name: str, attributes: dict[str, Any] | None = None) -> Transaction:
        """Start a new transaction."""
        transaction = Transaction(
            name=name,
            start_time=time.monotonic(),
            attributes=attributes or {},
        )
        self._transactions.append(transaction)
        self._stats["total_transactions"] += 1

        # Trim old transactions
        if len(self._transactions) > self._max_transactions:
            self._transactions = self._transactions[-self._max_transactions :]

        return transaction

    def get_transactions(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent transactions."""
        return [
            {
                "transaction_id": txn.transaction_id,
                "name": txn.name,
                "start_time": txn.start_time,
                "duration_ms": txn.duration_ms,
                "status": txn.status,
                "span_count": len(txn.spans),
                "attributes": txn.attributes,
            }
            for txn in self._transactions[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get APM statistics."""
        completed = [t for t in self._transactions if t.duration_ms is not None]

        if not completed:
            return self._stats

        durations = [t.duration_ms for t in completed if t.duration_ms is not None]
        errors = [t for t in completed if t.status == "error"]

        self._stats.update(
            {
                "total_transactions": len(completed),
                "total_spans": sum(len(t.spans) for t in completed),
                "avg_transaction_duration": round(sum(durations) / len(durations), 2),
                "p95_transaction_duration": round(
                    (
                        sorted(durations)[int(len(durations) * 0.95)]
                        if len(durations) >= 20
                        else max(durations)
                    ),
                    2,
                ),
                "p99_transaction_duration": round(
                    (
                        sorted(durations)[int(len(durations) * 0.99)]
                        if len(durations) >= 100
                        else max(durations)
                    ),
                    2,
                ),
                "error_rate": round(len(errors) / len(completed), 3) if completed else 0,
            }
        )

        return self._stats

    def reset(self) -> None:
        """Reset all data."""
        self._transactions.clear()
        self._stats = {
            "total_transactions": 0,
            "total_spans": 0,
            "avg_transaction_duration": 0,
            "p95_transaction_duration": 0,
            "p99_transaction_duration": 0,
            "error_rate": 0,
        }


# Global APM collector
apm_collector = APMCollector()


@contextmanager
def apm_transaction(
    name: str, attributes: dict[str, Any] | None = None
) -> Generator[Transaction, None, None]:
    """Context manager for APM transactions."""
    transaction = apm_collector.start_transaction(name, attributes)
    try:
        yield transaction
        transaction.finish("ok")
    except Exception as e:
        transaction.finish("error")
        transaction.attributes["error"] = str(e)
        raise


@contextmanager
def apm_span(
    transaction: Transaction, name: str, attributes: dict[str, Any] | None = None
) -> Generator[Span, None, None]:
    """Context manager for APM spans."""
    span = transaction.start_span(name, attributes)
    try:
        yield span
        span.finish("ok")
    except Exception as e:
        span.finish("error")
        span.attributes["error"] = str(e)
        raise
