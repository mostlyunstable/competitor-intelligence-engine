"""Monitoring dashboard endpoint for real-time system visibility.

Provides a comprehensive view of system health, performance, and alerts.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import get_session
from app.database.models import CollectionLog, Competitor
from app.observability.alerting import alert_manager
from app.observability.parser_metrics import registry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Monitoring"])


@router.get(
    "/monitoring/dashboard",
    summary="Monitoring Dashboard",
    description="""
Comprehensive monitoring dashboard showing:

- **System Health**: Database, scheduler, fetcher, memory status
- **Collection Metrics**: Success rate, average duration, records collected
- **Extraction Metrics**: Confidence scores, entity counts, strategy performance
- **Alert Status**: Active alerts, alert history, alert statistics
- **Performance Metrics**: Parse times, memory usage, cache hit rates
    """,
    responses={
        200: {
            "description": "Monitoring dashboard data",
            "content": {
                "application/json": {
                    "example": {
                        "timestamp": "2026-07-09T10:00:00Z",
                        "system_health": {
                            "status": "healthy",
                            "database": {"status": "healthy", "latency_ms": 5},
                            "scheduler": {"status": "healthy", "running": True},
                            "fetcher": {"status": "healthy", "cache_entries": 150},
                            "memory": {"status": "healthy", "rss_mb": 256},
                        },
                        "collection_metrics": {
                            "total_competitors": 5,
                            "active_competitors": 4,
                            "total_collections": 150,
                            "successful_collections": 145,
                            "failed_collections": 5,
                            "success_rate": 0.967,
                            "avg_duration_seconds": 25.5,
                            "total_records_collected": 1250,
                        },
                        "extraction_metrics": {
                            "total_pages_parsed": 500,
                            "avg_confidence": 0.85,
                            "avg_parse_time_ms": 250,
                            "total_entities_extracted": 2500,
                            "top_strategies": [
                                {"name": "json_ld", "entities": 800, "confidence": 0.92},
                                {"name": "card_extraction", "entities": 600, "confidence": 0.88},
                            ],
                        },
                        "alerts": {
                            "active_count": 0,
                            "by_severity": {},
                            "recent_alerts": [],
                        },
                    }
                }
            },
        }
    },
)
async def monitoring_dashboard(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Comprehensive monitoring dashboard."""
    # System health
    system_health = await _get_system_health(session)

    # Collection metrics
    collection_metrics = await _get_collection_metrics(session)

    # Extraction metrics
    extraction_metrics = _get_extraction_metrics()

    # Alert status
    alert_status = _get_alert_status()

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "system_health": system_health,
        "collection_metrics": collection_metrics,
        "extraction_metrics": extraction_metrics,
        "alerts": alert_status,
    }


async def _get_system_health(session: AsyncSession) -> dict[str, Any]:
    """Get system health status."""
    checks = {}
    overall_healthy = True

    # Database
    try:
        start = time.monotonic()
        await session.scalar(select(func.count()).select_from(Competitor))
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        checks["database"] = {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Scheduler
    try:
        from app.schedulers.scheduler import scheduler

        checks["scheduler"] = {
            "status": "healthy" if scheduler.is_running else "stopped",
            "running": scheduler.is_running,
        }
    except Exception as e:
        checks["scheduler"] = {"status": "unhealthy", "error": str(e)}

    # Fetcher
    try:
        from app.collectors.base import get_shared_fetcher

        fetcher = get_shared_fetcher()
        client_ok = fetcher._client is not None and not (
            fetcher._client.is_closed if fetcher._client else True
        )
        checks["fetcher"] = {
            "status": "healthy" if client_ok else "degraded",
            "cache_entries": fetcher.cache_layer.size,
        }
    except Exception as e:
        checks["fetcher"] = {"status": "unhealthy", "error": str(e)}

    # Memory
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = round(usage.ru_maxrss / 1024, 1)
        checks["memory"] = {
            "status": "healthy" if rss_mb < 512 else "warning",
            "rss_mb": rss_mb,
        }
    except Exception:
        checks["memory"] = {"status": "unknown"}

    return {
        "status": "healthy" if overall_healthy else "degraded",
        **checks,
    }


async def _get_collection_metrics(session: AsyncSession) -> dict[str, Any]:
    """Get collection metrics from database."""
    # Total competitors
    total_competitors = await session.scalar(select(func.count()).select_from(Competitor)) or 0

    # Active competitors
    active_competitors = (
        await session.scalar(
            select(func.count()).select_from(Competitor).where(Competitor.enabled.is_(True))
        )
        or 0
    )

    # Collection logs
    total_collections = await session.scalar(select(func.count()).select_from(CollectionLog)) or 0

    successful_collections = (
        await session.scalar(
            select(func.count()).select_from(CollectionLog).where(CollectionLog.success.is_(True))
        )
        or 0
    )

    failed_collections = total_collections - successful_collections

    # Average duration
    avg_duration = await session.scalar(select(func.avg(CollectionLog.duration_seconds))) or 0

    # Total records collected
    total_records = await session.scalar(select(func.sum(CollectionLog.records_collected))) or 0

    success_rate = successful_collections / total_collections if total_collections > 0 else 0

    return {
        "total_competitors": total_competitors,
        "active_competitors": active_competitors,
        "total_collections": total_collections,
        "successful_collections": successful_collections,
        "failed_collections": failed_collections,
        "success_rate": round(success_rate, 3),
        "avg_duration_seconds": round(float(avg_duration), 2),
        "total_records_collected": int(total_records),
    }


def _get_extraction_metrics() -> dict[str, Any]:
    """Get extraction metrics from parser registry."""
    total_pages = registry.global_stats["total_pages"]
    total_entities = registry.global_stats["total_entities_found"]
    total_accepted = registry.global_stats["total_entities_accepted"]

    # Calculate average confidence
    total_confidence = sum(
        stats.get("confidence_sum", 0) for stats in registry.strategy_stats.values()
    )
    total_executions = sum(
        stats.get("execution_count", 0) for stats in registry.strategy_stats.values()
    )
    avg_confidence = total_confidence / total_executions if total_executions > 0 else 0

    # Calculate average parse time
    avg_parse_time = (
        registry.global_stats["total_runtime_ms"] / total_pages if total_pages > 0 else 0
    )

    # Top strategies by entity count
    sorted_strategies = sorted(
        registry.strategy_stats.items(),
        key=lambda x: x[1].get("entities_accepted", 0),
        reverse=True,
    )
    top_strategies = [
        {
            "name": name,
            "entities": stats.get("entities_accepted", 0),
            "confidence": round(stats.get("average_confidence", 0), 3),
        }
        for name, stats in sorted_strategies[:5]
    ]

    return {
        "total_pages_parsed": total_pages,
        "avg_confidence": round(avg_confidence, 3),
        "avg_parse_time_ms": round(avg_parse_time, 2),
        "total_entities_extracted": total_entities,
        "total_entities_accepted": total_accepted,
        "rejection_rate": round(
            1 - (total_accepted / total_entities if total_entities > 0 else 0), 3
        ),
        "top_strategies": top_strategies,
    }


def _get_alert_status() -> dict[str, Any]:
    """Get alert status."""
    alert_stats = alert_manager.get_alert_stats()
    recent_history = alert_manager.get_alert_history(limit=10)

    return {
        "active_count": alert_stats["active_alerts"],
        "by_severity": alert_stats["active_by_severity"],
        "recent_alerts": [
            {
                "name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "status": alert.status.value,
            }
            for alert in recent_history
        ],
    }
