import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import ai, collection, competitors, dashboard, health, reports
from app.api.middleware import RateLimitMiddleware
from app.configuration.settings import Settings, get_settings
from app.database.connection import db_manager
from app.observability.monitoring_dashboard import router as monitoring_router
from app.services.websocket_manager import ws_manager

logger = structlog.get_logger(__name__)

# Global message queue (initialized at module level, configured in lifespan)
message_queue = None
_queue_worker_task: asyncio.Task[Any] | None = None



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await db_manager.connect()

    settings = get_settings()
    if settings.environment == "development" or settings.debug:
        await db_manager.create_tables()

    from app.messagequeue.queue import MessageQueue, MessageType

    message_queue = MessageQueue()

    async def _collection_handler(msg):  # type: ignore
        from app.services.collection_service import collection_service

        competitor_id = msg.payload.get("competitor_id")
        if competitor_id:
            await collection_service.collect_competitor(competitor_id)
            return True
        return False

    message_queue.set_handler(MessageType.COLLECTION, _collection_handler)  # type: ignore

    app.state.message_queue = message_queue

    async def _queue_worker() -> None:
        """Background task that continuously processes messages from the queue."""
        logger.info("queue_worker_started")
        while True:
            try:
                processed = await message_queue.process_all(max_messages=10)
                if processed == 0:
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("queue_worker_error")
                await asyncio.sleep(5)

    global _queue_worker_task
    _queue_worker_task = asyncio.create_task(_queue_worker())

    from app.services.config_sync_service import config_sync_service

    await config_sync_service.sync_competitors()

    from app.schedulers.scheduler import scheduler

    await scheduler.start()



    logger.info(
        "app_started",
        environment=settings.environment,
        debug=settings.debug,
        scheduler_enabled=settings.scheduler.enabled,
    )

    yield

    if _queue_worker_task and not _queue_worker_task.done():
        _queue_worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _queue_worker_task

    from app.schedulers.scheduler import scheduler as sched

    await sched.stop()
    await db_manager.disconnect()
    logger.info("app_stopped")


OPENAPI_TAGS = [
    {"name": "Health", "description": "System health checks and status monitoring"},
    {"name": "Competitors", "description": "CRUD operations for competitor management"},
    {"name": "Collection", "description": "Data collection pipeline triggers and monitoring"},
    {"name": "Metrics", "description": "Runtime metrics and performance monitoring"},
    {"name": "Dashboard", "description": "Dashboard data and analytics"},
    {"name": "Reports", "description": "Extraction reports and analytics"},
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

    from app.chaos import ChaosMonkeyMiddleware
    app.add_middleware(ChaosMonkeyMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=settings.debug,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware, requests_per_minute=300000)

    app.include_router(health.router)
    app.include_router(competitors.router)
    app.include_router(collection.router)
    app.include_router(dashboard.router)
    app.include_router(reports.router)
    app.include_router(monitoring_router)
    app.include_router(ai.router)

    if settings.debug:
        from app.api.endpoints.debug import router as debug_router
        app.include_router(debug_router, prefix="/debug", tags=["Debug"])

    from fastapi.responses import RedirectResponse

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await ws_manager.connect(websocket)
        try:
            while True:
                # Keep connection alive, handle client messages if needed
                data = await websocket.receive_text()
                # Client can send ping/pong or commands
                if data == "ping":
                    await websocket.send_text('{"type":"pong"}')
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)
        except Exception:
            await ws_manager.disconnect(websocket)

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
