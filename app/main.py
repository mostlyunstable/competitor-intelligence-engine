from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import collection, competitors, dashboard, health, metrics, reports
from app.api.middleware import RateLimitMiddleware
from app.configuration.settings import Settings, get_settings
from app.database.connection import db_manager
from app.observability.monitoring_dashboard import router as monitoring_router
from app.observability.prometheus_metrics import router as prometheus_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await db_manager.connect()

    settings = get_settings()
    if settings.environment == "development" or settings.debug:
        await db_manager.create_tables()

    from app.services.config_sync_service import config_sync_service

    await config_sync_service.sync_competitors()

    from app.schedulers.scheduler import scheduler

    await scheduler.start()

    yield

    await scheduler.stop()
    await db_manager.disconnect()


# OpenAPI metadata with comprehensive examples
OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "System health checks and status monitoring",
    },
    {
        "name": "Competitors",
        "description": "CRUD operations for competitor management",
    },
    {
        "name": "Collection",
        "description": "Data collection pipeline triggers and monitoring",
    },
    {
        "name": "Metrics",
        "description": "Runtime metrics and performance monitoring",
    },
    {
        "name": "Dashboard",
        "description": "Dashboard data and analytics",
    },
    {
        "name": "Reports",
        "description": "Extraction reports and analytics",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Utservio Competitor Intelligence Engine",
        description="""
## Overview

Production-grade competitor intelligence data collection engine.

### Features

- **Generic HTML Extraction**: 23 parsing strategies with zero CSS selectors
- **Entity Resolution**: Automatic deduplication with fuzzy matching
- **Relationship Linking**: Connect extracted entities into graphs
- **Dynamic Confidence Scoring**: Per-field confidence with cross-strategy consistency
- **Evidence Metadata**: DOM path, XPath, and HTML snippet for every extraction
- **Hybrid Fetching**: Static HTML + JavaScript rendering via Playwright
- **Incremental Crawling**: ETag/Last-Modified conditional requests
- **Structured Logging**: Production-ready observability via structlog
- **Prometheus Metrics**: Runtime performance monitoring

### Architecture

```
API Layer (FastAPI)
    ↓
Service Layer (Collection Service)
    ↓
Collector Layer (Company, Service, Pricing, Content, Social, Discovery)
    ↓
Parser Layer (23 Strategies + Entity Resolution + Relationship Linking)
    ↓
Repository Layer (13 Repositories with Native Upsert)
    ↓
Database Layer (PostgreSQL via SQLAlchemy Async)
```

### Authentication

API endpoints require Bearer token authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-api-token>
```

### Rate Limiting

- **Global**: 60 requests per minute
- **Per-domain**: Configurable per competitor domain

### Error Handling

All errors follow RFC 7807 Problem Details format:

```json
{
    "type": "https://api.utservio.com/errors/not-found",
    "title": "Competitor Not Found",
    "status": 404,
    "detail": "Competitor with id 999 does not exist"
}
```
        """,
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_url="/openapi.json",
    )

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Any:
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:"
            )
            return response

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=settings.debug,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware, requests_per_minute=300)

    app.include_router(health.router)
    app.include_router(competitors.router)
    app.include_router(collection.router)
    app.include_router(metrics.router)
    app.include_router(dashboard.router)
    app.include_router(reports.router)
    app.include_router(prometheus_router)
    app.include_router(monitoring_router)

    from fastapi.responses import RedirectResponse

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    _configure_logging(settings.log_level)

    return app


def _configure_logging(log_level: str) -> None:
    import logging

    from app.observability.log_buffer import global_log_buffer

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            global_log_buffer.add_log,  # type: ignore[list-item]
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


app = create_app()
