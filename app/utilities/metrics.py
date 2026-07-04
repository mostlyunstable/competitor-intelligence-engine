"""Observability — Prometheus metrics for the crawling engine.

Exposes metrics for:
- Pages discovered, crawled, skipped
- Cache hits and misses
- Playwright fallbacks
- Strategy success/failure
- Crawl, parse, and discovery durations
"""

import os
import time
from collections import deque
from typing import Any

import structlog
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects and stores Prometheus-compatible metrics.

    Thread-safe metric collection for concurrent crawling operations.
    Supports counters, gauges, and histograms. Uses prometheus-client under the hood.
    """

    def __init__(self) -> None:
        self._registry = CollectorRegistry()
        if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
            multiprocess.MultiProcessCollector(self._registry)  # type: ignore[no-untyped-call]

        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._start_time = time.time()

        # Bounded sliding window for stats (e.g. tests, summaries) to prevent memory leak
        self._histogram_windows: dict[str, deque[float]] = {}
        self._max_window_size = 1000

    def _get_or_create_counter(self, name: str, label_names: list[str]) -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(
                name, f"Counter {name}", labelnames=label_names, registry=self._registry
            )
        return self._counters[name]

    def _get_or_create_gauge(self, name: str, label_names: list[str]) -> Gauge:
        if name not in self._gauges:
            self._gauges[name] = Gauge(
                name, f"Gauge {name}", labelnames=label_names, registry=self._registry
            )
        return self._gauges[name]

    def _get_or_create_histogram(self, name: str, label_names: list[str]) -> Histogram:
        if name not in self._histograms:
            self._histograms[name] = Histogram(
                name, f"Histogram {name}", labelnames=label_names, registry=self._registry
            )
        return self._histograms[name]

    def inc_counter(self, name: str, value: float = 1.0, **labels: str) -> None:
        """Increment a counter metric."""
        label_names = sorted(labels.keys())
        counter = self._get_or_create_counter(name, label_names)
        if labels:
            counter.labels(**{k: labels[k] for k in label_names}).inc(value)
        else:
            counter.inc(value)

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        """Set a gauge metric."""
        label_names = sorted(labels.keys())
        gauge = self._get_or_create_gauge(name, label_names)
        if labels:
            gauge.labels(**{k: labels[k] for k in label_names}).set(value)
        else:
            gauge.set(value)

    def observe_histogram(self, name: str, value: float, **labels: str) -> None:
        """Record a histogram observation."""
        label_names = sorted(labels.keys())
        histogram = self._get_or_create_histogram(name, label_names)
        if labels:
            histogram.labels(**{k: labels[k] for k in label_names}).observe(value)
        else:
            histogram.observe(value)

        # Record to bounded window for local statistics
        if name not in self._histogram_windows:
            self._histogram_windows[name] = deque(maxlen=self._max_window_size)
        self._histogram_windows[name].append(value)

    def get_counter_total(self, name: str, **labels: str) -> float:
        """Get total value of a counter."""
        counter = self._counters.get(name)
        if not counter:
            return 0.0
        if labels:
            return float(
                counter.labels(**{k: labels[k] for k in sorted(labels.keys())})._value.get()
            )
        return float(counter._value.get())

    def get_gauge(self, name: str, **labels: str) -> float | None:
        """Get gauge value."""
        gauge = self._gauges.get(name)
        if not gauge:
            return None
        if labels:
            return float(gauge.labels(**{k: labels[k] for k in sorted(labels.keys())})._value.get())
        return float(gauge._value.get())

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        """Get histogram statistics from the sliding window."""
        values = list(self._histogram_windows.get(name, []))
        if not values:
            return {
                "count": 0.0,
                "sum": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_vals = sorted(values)
        count = len(sorted_vals)
        return {
            "count": float(count),
            "sum": sum(sorted_vals),
            "avg": sum(sorted_vals) / count,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "p50": sorted_vals[count // 2],
            "p95": sorted_vals[int(count * 0.95)] if count > 20 else sorted_vals[-1],
            "p99": sorted_vals[int(count * 0.99)] if count > 100 else sorted_vals[-1],
        }

    def render_prometheus(self) -> str:
        """Render all metrics in Prometheus exposition format."""
        uptime = time.time() - self._start_time
        # Ensure process_uptime_seconds gauge exists
        self.set_gauge("process_uptime_seconds", uptime)

        # generate_latest returns bytes, decode to string
        return generate_latest(self._registry).decode("utf-8")

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        summary: dict[str, Any] = {
            "counters": {},
            "gauges": {},
            "histograms": {},
        }

        for name, counter in self._counters.items():
            summary["counters"][name] = counter._value.get()

        for name, gauge in self._gauges.items():
            summary["gauges"][name] = gauge._value.get()

        for name in self._histogram_windows:
            summary["histograms"][name] = self.get_histogram_stats(name)

        return summary


metrics = MetricsCollector()


def time_operation(name: str, **labels: str) -> Any:
    """Context manager to time an operation and record to histogram."""
    return _TimerContext(metrics, name, labels)


class _TimerContext:
    def __init__(self, collector: MetricsCollector, name: str, labels: dict[str, str]) -> None:
        self._collector = collector
        self._name = name
        self._labels = labels
        self._start: float = 0

    def __enter__(self) -> "_TimerContext":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        self._collector.observe_histogram(self._name, elapsed_ms, **self._labels)
