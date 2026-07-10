"""Prometheus metrics endpoint for production monitoring.

Exposes all system metrics in Prometheus format for scraping.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Response

router = APIRouter(tags=["Metrics"])

# In-memory metrics storage
_metrics: dict[str, Any] = {
    "counters": {},
    "gauges": {},
    "histograms": {},
    "timestamps": {},
}


def _escape_label_value(value: str) -> str:
    """Escape special characters in Prometheus label values."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class PrometheusMetrics:
    """Prometheus metrics collector."""

    @staticmethod
    def counter(name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Increment a counter."""
        key = name
        if labels:
            label_str = ",".join(f'{k}="{_escape_label_value(v)}"' for k, v in labels.items())
            key = f"{name}{{{label_str}}}"
        _metrics["counters"][key] = _metrics["counters"].get(key, 0) + value

    @staticmethod
    def gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        key = name
        if labels:
            label_str = ",".join(f'{k}="{_escape_label_value(v)}"' for k, v in labels.items())
            key = f"{name}{{{label_str}}}"
        _metrics["gauges"][key] = value

    @staticmethod
    def histogram(name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram value."""
        key = name
        if labels:
            label_str = ",".join(f'{k}="{_escape_label_value(v)}"' for k, v in labels.items())
            key = f"{name}{{{label_str}}}"
        if key not in _metrics["histograms"]:
            _metrics["histograms"][key] = {"values": [], "sum": 0, "count": 0}
        _metrics["histograms"][key]["values"].append(value)
        _metrics["histograms"][key]["sum"] += value
        _metrics["histograms"][key]["count"] += 1

    @staticmethod
    def info(name: str, value: dict[str, Any]) -> None:
        """Set an info metric."""
        label_str = ",".join(f'{k}="{_escape_label_value(str(v))}"' for k, v in value.items())
        _metrics["gauges"][f"{name}{{{label_str}}}"] = 1


# Global metrics instance
metrics = PrometheusMetrics()


def _format_prometheus_metrics() -> str:
    """Format all metrics in Prometheus exposition format."""
    lines = []

    # Counters
    for name, value in _metrics["counters"].items():
        lines.append(f"# TYPE {name.split('{')[0]} counter")
        lines.append(f"{name} {value}")

    # Gauges
    for name, value in _metrics["gauges"].items():
        lines.append(f"# TYPE {name.split('{')[0]} gauge")
        lines.append(f"{name} {value}")

    # Histograms
    for name, stats in _metrics["histograms"].items():
        base_name = name.split("{")[0]
        lines.append(f"# TYPE {base_name} histogram")
        # Sort values for quantile calculation
        sorted_values = sorted(stats["values"])
        count = len(sorted_values)
        if count > 0:
            # Calculate quantiles
            for q in [0.5, 0.9, 0.95, 0.99]:
                idx = int(count * q)
                if idx >= count:
                    idx = count - 1
                lines.append(f'{base_name}{{quantile="{q}"}} {sorted_values[idx]}')
            lines.append(f"{base_name}_sum {stats['sum']}")
            lines.append(f"{base_name}_count {count}")

    return "\n".join(lines) + "\n"


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Exposes all system metrics in Prometheus format for scraping.",
    responses={
        200: {
            "description": "Prometheus metrics",
            "content": {
                "text/plain": {
                    "example": "# HELP collections_total Total collections\n# TYPE collections_total counter\ncollections_total 150\n"
                }
            },
        }
    },
)
async def prometheus_metrics() -> Response:
    """Return all metrics in Prometheus exposition format."""
    content = _format_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get(
    "/metrics/json",
    summary="Metrics JSON",
    description="Returns all metrics in JSON format for dashboards.",
    responses={
        200: {
            "description": "Metrics in JSON format",
            "content": {
                "application/json": {
                    "example": {
                        "counters": {"collections_total": 150},
                        "gauges": {"active_crawls": 3},
                        "histograms": {"parse_time_ms": {"avg": 250, "p95": 400}},
                        "timestamp": "2026-07-09T10:00:00Z",
                    }
                }
            },
        }
    },
)
async def prometheus_metrics_json() -> dict[str, Any]:
    """Return all metrics in JSON format."""
    # Calculate histogram summaries
    histogram_summaries = {}
    for name, stats in _metrics["histograms"].items():
        sorted_values = sorted(stats["values"])
        count = len(sorted_values)
        if count > 0:
            histogram_summaries[name] = {
                "avg": stats["sum"] / count,
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "p50": sorted_values[int(count * 0.5)],
                "p95": sorted_values[int(count * 0.95)],
                "p99": sorted_values[min(int(count * 0.99), count - 1)],
                "count": count,
                "sum": stats["sum"],
            }

    return {
        "counters": _metrics["counters"],
        "gauges": _metrics["gauges"],
        "histograms": histogram_summaries,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def reset_metrics() -> None:
    """Reset all metrics (for testing)."""
    _metrics["counters"].clear()
    _metrics["gauges"].clear()
    _metrics["histograms"].clear()
    _metrics["timestamps"].clear()
