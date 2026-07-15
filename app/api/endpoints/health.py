import time
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.database.models import CollectionLog, Competitor

router = APIRouter(tags=["Health"])


class StatusResponse(BaseModel):
    """System status response."""

    status: str
    competitors: int
    collection_logs: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "running",
                    "competitors": 5,
                    "collection_logs": 150,
                }
            ]
        }
    }


class HealthCheck(BaseModel):
    """Individual subsystem health check."""

    status: str
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Comprehensive health check response.

    Returns 200 if all subsystems are healthy, 503 if any are degraded.
    """

    status: str
    checks: dict[str, Any]
    http_status: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "checks": {
                        "database": {"status": "healthy", "latency_ms": 5.23},
                        "scheduler": {"status": "healthy", "running": True},
                        "fetcher": {
                            "status": "healthy",
                            "http_client_ready": True,
                            "cache_entries": 150,
                        },
                        "collection": {"status": "healthy", "active_crawls": 3},
                        "memory": {"status": "healthy", "rss_mb": 256.0},
                    },
                    "http_status": 200,
                }
            ]
        }
    }


class CollectionLogResponse(BaseModel):
    """Collection log entry."""

    id: int
    competitor_id: int
    start_time: str | None
    end_time: str | None
    success: bool
    duration_seconds: float | None
    records_collected: int
    errors: list[str]
    retry_count: int


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="System Status",
    description="Quick status check showing competitor count and collection log count.",
    responses={
        200: {
            "description": "System is running",
            "content": {
                "application/json": {
                    "example": {
                        "status": "running",
                        "competitors": 5,
                        "collection_logs": 150,
                    }
                }
            },
        }
    },
)
async def status(session: AsyncSession = Depends(get_session)) -> StatusResponse:
    competitor_count = await session.scalar(select(func.count()).select_from(Competitor))
    log_count = await session.scalar(select(func.count()).select_from(CollectionLog))
    return StatusResponse(
        status="running",
        competitors=competitor_count or 0,
        collection_logs=log_count or 0,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="""
Comprehensive health check verifying all subsystems:

- **Database**: Connectivity and latency
- **Scheduler**: Collection scheduler status
- **Fetcher**: HTTP client and cache status
- **Collection**: Active crawl count
- **Memory**: RSS memory usage

Returns 200 if all subsystems are healthy, 503 if any are degraded.
    """,
    responses={
        200: {
            "description": "All subsystems healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "checks": {
                            "database": {"status": "healthy", "latency_ms": 5.23},
                            "scheduler": {"status": "healthy", "running": True},
                            "fetcher": {
                                "status": "healthy",
                                "http_client_ready": True,
                                "cache_entries": 150,
                            },
                            "collection": {"status": "healthy", "active_crawls": 3},
                            "memory": {"status": "healthy", "rss_mb": 256.0},
                        },
                        "http_status": 200,
                    }
                }
            },
        },
        503: {
            "description": "One or more subsystems degraded",
            "content": {
                "application/json": {
                    "example": {
                        "status": "degraded",
                        "checks": {
                            "database": {"status": "unhealthy", "error": "Connection refused"},
                            "scheduler": {"status": "healthy", "running": True},
                            "fetcher": {
                                "status": "healthy",
                                "http_client_ready": True,
                                "cache_entries": 150,
                            },
                            "collection": {"status": "healthy", "active_crawls": 0},
                            "memory": {"status": "healthy", "rss_mb": 128.0},
                        },
                        "http_status": 503,
                    }
                }
            },
        },
    },
)
async def health(
    response: Response, session: AsyncSession = Depends(get_session)
) -> HealthResponse:
    """Composite health check verifying all subsystems.

    Returns 200 if all subsystems are healthy, 503 if any are degraded.
    """
    checks: dict[str, Any] = {}
    overall_healthy = True

    # 1. Database connectivity
    try:
        start = time.monotonic()
        await session.scalar(select(func.count()).select_from(Competitor))
        db_latency_ms = round((time.monotonic() - start) * 1000, 2)
        checks["database"] = {"status": "healthy", "latency_ms": db_latency_ms}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # 2. Scheduler status
    try:
        from app.schedulers.scheduler import scheduler

        checks["scheduler"] = {
            "status": "healthy" if scheduler.is_running else "stopped",
            "running": scheduler.is_running,
        }
        if not scheduler.is_running:
            overall_healthy = False
    except Exception as e:
        checks["scheduler"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # 3. Fetcher / HTTP client
    try:
        from app.collectors.base import get_shared_fetcher

        fetcher = get_shared_fetcher()
        client_ok = True
        for client in fetcher._clients.values():
            if client.is_closed:
                client_ok = False
                break
        cache_size = fetcher.cache_layer.size
        checks["fetcher"] = {
            "status": "healthy" if client_ok else "degraded",
            "http_client_ready": client_ok,
            "cache_entries": cache_size,
        }
    except Exception as e:
        checks["fetcher"] = {"status": "unhealthy", "error": str(e)}

    # 4. Active crawls
    try:
        from app.services.collection_service import collection_service

        active = len(collection_service._active_crawls)
        checks["collection"] = {
            "status": "healthy",
            "active_crawls": active,
        }
    except Exception as e:
        checks["collection"] = {"status": "unhealthy", "error": str(e)}

    # 5. Memory usage
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = round(usage.ru_maxrss / 1024, 1)  # macOS: bytes → MB
        checks["memory"] = {
            "status": "healthy",
            "rss_mb": rss_mb,
        }
    except Exception:
        checks["memory"] = {"status": "unknown"}

    http_status = 200 if overall_healthy else 503
    response.status_code = http_status
    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        checks=checks,
        http_status=http_status,
    )


@router.get(
    "/logs",
    response_model=list[CollectionLogResponse],
    summary="Collection Logs",
    description="Retrieve recent collection logs with execution details.",
    responses={
        200: {
            "description": "List of collection logs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "competitor_id": 1,
                            "start_time": "2026-07-09T10:00:00Z",
                            "end_time": "2026-07-09T10:00:25Z",
                            "success": True,
                            "duration_seconds": 25.5,
                            "records_collected": 45,
                            "errors": [],
                            "retry_count": 0,
                        }
                    ]
                }
            },
        }
    },
)
async def get_logs(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[CollectionLogResponse]:
    stmt = select(CollectionLog).order_by(CollectionLog.id.desc()).limit(limit)
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return [
        CollectionLogResponse(
            id=log.id,
            competitor_id=log.competitor_id,
            start_time=log.start_time.isoformat() if log.start_time else None,
            end_time=log.end_time.isoformat() if log.end_time else None,
            success=log.success,
            duration_seconds=float(log.duration_seconds) if log.duration_seconds else None,
            records_collected=log.records_collected,
            errors=log.errors or [],
            retry_count=log.retry_count,
        )
        for log in logs
    ]
