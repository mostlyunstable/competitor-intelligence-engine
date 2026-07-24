"""Prometheus metrics using the prometheus_client library.

Exposes all system metrics in Prometheus format for scraping.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

router = APIRouter(tags=["Metrics"])

# ─── AI Metrics ──────────────────────────────────────────────────────────────

ai_analysis_total = Counter(
    "ci_ai_analysis_total",
    "Total AI analysis requests",
    ["competitor_id", "status"],
)

ai_analysis_duration = Histogram(
    "ci_ai_analysis_duration_seconds",
    "AI analysis duration in seconds",
    ["competitor_id"],
    buckets=[5, 10, 30, 60, 120, 300],
)

ai_tokens_total = Counter(
    "ci_ai_tokens_total",
    "Total tokens consumed by AI analysis",
    ["type"],  # prompt or completion
)

ai_cost_usd = Counter(
    "ci_ai_cost_usd_total",
    "Total estimated AI cost in USD",
)

ai_cache_hits = Counter(
    "ci_ai_cache_hits_total",
    "Total LLM cache hits",
)

ai_cache_misses = Counter(
    "ci_ai_cache_misses_total",
    "Total LLM cache misses",
)

ai_active_analyses = Gauge(
    "ci_ai_active_analyses",
    "Number of AI analyses currently running",
)

# ─── Collection Metrics ──────────────────────────────────────────────────────

collections_total = Counter(
    "ci_collections_total",
    "Total collection runs",
    ["competitor_id", "status"],
)

collection_duration = Histogram(
    "ci_collection_duration_seconds",
    "Collection duration in seconds",
    ["competitor_id"],
    buckets=[10, 30, 60, 120, 300, 600],
)

pages_crawled_total = Counter(
    "ci_pages_crawled_total",
    "Total pages crawled",
)

# ─── System Metrics ─────────────────────────────────────────────────────────

active_websockets = Gauge(
    "ci_active_websockets",
    "Number of active WebSocket connections",
)

scheduler_running = Gauge(
    "ci_scheduler_running",
    "Whether the scheduler is running (1=yes, 0=no)",
)

db_pool_size = Gauge(
    "ci_db_pool_size",
    "Database connection pool size",
)

db_pool_checked_out = Gauge(
    "ci_db_pool_checked_out",
    "Database connections currently in use",
)


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """Return all metrics in Prometheus exposition format."""
    content = generate_latest()
    return Response(content=content, media_type=CONTENT_TYPE_LATEST)
