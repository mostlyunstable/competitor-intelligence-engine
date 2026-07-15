from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import collection, competitors, dashboard, health, metrics, reports
from app.api.middleware import RateLimitMiddleware
from app.configuration.secrets import setup_secrets
from app.configuration.settings import Settings, get_settings
from app.database.connection import db_manager

logger = structlog.get_logger(__name__)

# Global message queue (initialized at module level, configured in lifespan)
message_queue = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global message_queue

    setup_secrets()

    await db_manager.connect()

    settings = get_settings()
    if settings.environment == "development" or settings.debug:
        await db_manager.create_tables()

    from app.messagequeue import MessageQueue
    from app.messagequeue.queue import InMemoryQueueBackend, MessageType

    message_queue = MessageQueue()

    async def _collection_handler(msg):
        from app.services.collection_service import collection_service

        competitor_id = msg.payload.get("competitor_id")
        if competitor_id:
            await collection_service.collect_competitor(competitor_id)
            return True
        return False

    message_queue.set_handler(MessageType.COLLECTION, _collection_handler)

    app.state.message_queue = message_queue

    from app.services.config_sync_service import config_sync_service

    await config_sync_service.sync_competitors()

    from app.schedulers.scheduler import scheduler

    await scheduler.start()

    from app.observability.alerting import setup_default_alerts

    setup_default_alerts()

    logger.info(
        "app_started",
        environment=settings.environment,
        debug=settings.debug,
        scheduler_enabled=settings.scheduler.enabled,
    )

    yield

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
        description="Production-grade competitor intelligence data collection engine.",
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
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
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

    try:
        from app.observability.prometheus_metrics import router as prometheus_router
        from app.observability.monitoring_dashboard import router as monitoring_router
        from app.observability.apm_endpoint import router as apm_router

        app.include_router(prometheus_router)
        app.include_router(monitoring_router)
        app.include_router(apm_router)
    except ImportError:
        logger.warning("observability_modules_not_available")

    from fastapi.responses import RedirectResponse

    @app.get("/", include_in_schema=False)
    async def root():
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
            global_log_buffer.add_log,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


app = create_app()
