from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import collection, competitors, dashboard, health, metrics, reports
from app.api.middleware import RateLimitMiddleware
from app.configuration.secrets import setup_secrets
from app.configuration.settings import Settings, get_settings
from app.crawlfrontier import CrawlFrontier
from app.database.connection import db_manager
from app.messagequeue import MessageQueue
from app.observability.apm_endpoint import router as apm_router
from app.observability.monitoring_dashboard import router as monitoring_router
from app.observability.prometheus_metrics import router as prometheus_router

# Global crawl frontier
crawl_frontier = CrawlFrontier()

# Global message queue
message_queue = MessageQueue()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Setup secrets
    setup_secrets()

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

OPENAPI_EXAMPLES = {
    "CompetitorCreate": {
        "summary": "Create a new competitor",
        "description": "Register a new competitor website for monitoring",
        "value": {
            "name": "Example Corp",
            "website_url": "https://example.com",
            "industry": "Technology",
            "collection_frequency": "daily",
        },
    },
    "CompetitorResponse": {
        "summary": "Competitor with extracted data",
        "description": "Full competitor object with extracted services and pricing",
        "value": {
            "id": 1,
            "name": "Example Corp",
            "website_url": "https://example.com",
            "industry": "Technology",
            "collection_frequency": "daily",
            "services": [
                {
                    "name": "Cloud Hosting",
                    "description": "Managed cloud hosting service",
                    "starting_price": 99.99,
                    "currency": "USD",
                }
            ],
            "pricing": [
                {
                    "service_name": "Cloud Hosting",
                    "base_price": 99.99,
                    "currency": "USD",
                }
            ],
        },
    },
    "CollectionTrigger": {
        "summary": "Trigger collection for a competitor",
        "description": "Start a collection run for a specific competitor",
        "value": {
            "competitor_id": 1,
            "full_collection": True,
        },
    },
    "CollectionResponse": {
        "summary": "Collection started",
        "description": "Collection job has been queued",
        "value": {
            "status": "started",
            "competitor_id": 1,
            "job_id": "col_abc123",
        },
    },
    "HealthResponse": {
        "summary": "System health check",
        "description": "Comprehensive health status of all subsystems",
        "value": {
            "status": "healthy",
            "timestamp": "2026-07-09T10:00:00Z",
            "subsystems": {
                "database": {"status": "healthy", "latency_ms": 5},
                "scheduler": {"status": "healthy", "active_jobs": 2},
                "fetcher": {"status": "healthy", "cache_size": 150},
                "crawls": {"status": "healthy", "active": 3},
                "memory": {"status": "healthy", "rss_mb": 256},
            },
        },
    },
    "MetricsResponse": {
        "summary": "Runtime metrics",
        "description": "Prometheus-format metrics",
        "value": {
            "collections_total": 150,
            "collections_failed": 3,
            "avg_parse_time_ms": 250,
            "avg_confidence": 0.85,
            "entities_extracted": 1250,
        },
    },
}


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
- **Crawl Budget**: Per-competitor page/byte/time limits
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
- **Crawl budget**: Per-competitor page/byte/time limits

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
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
        openapi_url="/openapi.json" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=settings.debug,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    app.include_router(health.router)
    app.include_router(competitors.router)
    app.include_router(collection.router)
    app.include_router(metrics.router)
    app.include_router(dashboard.router)
    app.include_router(reports.router)
    app.include_router(prometheus_router)
    app.include_router(monitoring_router)
    app.include_router(apm_router)

    _configure_logging(settings.log_level)

    return app


def _configure_logging(log_level: str) -> None:
    import logging

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


app = create_app()
