import json
import os
import secrets
import time
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import cast, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_session
from app.configuration.settings import get_settings
from app.database.connection import db_manager
from app.database.models import (
    CollectionFrequency,
    CollectionLog,
    Competitor,
    CompetitorContent,
    CompetitorPage,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
    CompetitorSource,
    CompetitorTechStack,
    RawStorage,
)
from app.schedulers.scheduler import scheduler
from app.services.collection_service import collection_service

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(
        credentials.username, os.getenv("ADMIN_USER", "admin")
    )
    correct_password = secrets.compare_digest(
        credentials.password, os.getenv("ADMIN_PASSWORD", "admin123")
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


router = APIRouter(tags=["Dashboard"], dependencies=[Depends(verify_credentials)])


class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: str = Field(..., min_length=1)
    enabled: bool = True
    collection_frequency: str = "daily"
    modules: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: Any) -> Any:
        import socket
        from urllib.parse import urlparse

        if not v or not v.strip():
            raise ValueError("Website URL is required.")

        v = v.strip()

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must start with http:// or https://")

        domain = parsed.hostname
        if not domain or "." not in domain:
            raise ValueError("URL must contain a valid domain (e.g. https://example.com)")

        try:
            ip = socket.gethostbyname(domain)
            if ip.startswith("127.") or ip.startswith("169.254.") or ip.startswith("10.") or ip.startswith("192.168."):
                raise ValueError("Internal or private IPs are forbidden (SSRF Protection).")
        except socket.gaierror:
            raise ValueError(f"Could not resolve domain '{domain}'. Check the URL.")

        return v


class CompetitorUpdate(BaseModel):
    name: str | None = None
    website_url: str | None = None
    enabled: bool | None = None
    collection_frequency: str | None = None
    modules: list[str] | None = None
    tags: list[str] | None = None
    notes: str | None = None


class BulkAction(BaseModel):
    competitor_ids: list[int]


class BulkFrequencyUpdate(BulkAction):
    frequency: str


# ─── Dashboard UI ───────────────────────────────────────────────────────────


@router.get("/dashboard", response_class=FileResponse)
async def get_dashboard(response: Response) -> str:
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return "app/static/dashboard.html"


# ─── Competitor CRUD ────────────────────────────────────────────────────────


@router.get("/api/dashboard/competitors")
async def get_dashboard_competitors(
    search: str | None = None,
    enabled: bool | None = None,
    frequency: str | None = None,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    stmt = select(Competitor)
    if search:
        stmt = stmt.where(Competitor.name.ilike(f"%{search}%"))
    if enabled is not None:
        stmt = stmt.where(Competitor.enabled.is_(enabled))
    if frequency:
        stmt = stmt.where(Competitor.collection_frequency == frequency)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0

    stmt = stmt.order_by(Competitor.name)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    competitors = result.scalars().all()

    out = []
    for c in competitors:
        last_log_stmt = (
            select(CollectionLog.start_time)
            .where(CollectionLog.competitor_id == c.id)
            .where(CollectionLog.success.is_(True))
            .order_by(CollectionLog.start_time.desc())
            .limit(1)
        )
        last_collected = await session.scalar(last_log_stmt)

        failed_log_stmt = (
            select(func.count())
            .select_from(CollectionLog)
            .where(CollectionLog.competitor_id == c.id)
            .where(CollectionLog.success.is_(False))
        )
        failed_count = await session.scalar(failed_log_stmt) or 0

        total_log_stmt = (
            select(func.count())
            .select_from(CollectionLog)
            .where(CollectionLog.competitor_id == c.id)
        )
        total_count = await session.scalar(total_log_stmt) or 0

        out.append({
            "id": c.id,
            "name": c.name,
            "website_url": c.website_url,
            "enabled": c.enabled,
            "collection_frequency": c.collection_frequency.value if c.collection_frequency else "daily",
            "modules": c.modules or [],
            "tags": c.tags or [],
            "notes": c.notes,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_collected": last_collected.isoformat() if last_collected else None,
            "failed_collections": failed_count,
            "total_collections": total_count,
        })

    return {
        "competitors": out,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/api/dashboard/competitors/{competitor_id}")
async def get_competitor_detail(
    competitor_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    services_stmt = select(CompetitorService).where(CompetitorService.competitor_id == competitor_id)
    services = (await session.execute(services_stmt)).scalars().all()

    pricing_stmt = select(CompetitorPricing).where(CompetitorPricing.competitor_id == competitor_id)
    pricing = (await session.execute(pricing_stmt)).scalars().all()

    content_stmt = select(CompetitorContent).where(CompetitorContent.competitor_id == competitor_id)
    content = (await session.execute(content_stmt)).scalars().all()

    social_stmt = select(CompetitorSocial).where(CompetitorSocial.competitor_id == competitor_id)
    social = (await session.execute(social_stmt)).scalars().all()

    tech_stmt = select(CompetitorTechStack).where(CompetitorTechStack.competitor_id == competitor_id)
    tech = (await session.execute(tech_stmt)).scalars().all()

    sources_stmt = select(CompetitorSource).where(CompetitorSource.competitor_id == competitor_id)
    sources = (await session.execute(sources_stmt)).scalars().all()

    pages_stmt = select(CompetitorPage).where(CompetitorPage.competitor_id == competitor_id).limit(50)
    pages = (await session.execute(pages_stmt)).scalars().all()

    logs_stmt = (
        select(CollectionLog)
        .where(CollectionLog.competitor_id == competitor_id)
        .order_by(CollectionLog.start_time.desc())
        .limit(20)
    )
    logs = (await session.execute(logs_stmt)).scalars().all()

    return {
        "competitor": {
            "id": comp.id,
            "name": comp.name,
            "website_url": comp.website_url,
            "enabled": comp.enabled,
            "collection_frequency": comp.collection_frequency.value if comp.collection_frequency else "daily",
            "modules": comp.modules or [],
            "tags": comp.tags or [],
            "notes": comp.notes,
            "created_at": comp.created_at.isoformat() if comp.created_at else None,
            "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
        },
        "services": [{"id": s.id, "name": s.service_name, "description": s.description, "collected_at": s.collected_at.isoformat() if s.collected_at else None} for s in services],
        "pricing": [{"id": p.id, "service_name": p.service_name, "base_price": float(p.base_price) if p.base_price else None, "currency": p.currency, "category": p.category, "collected_at": p.collected_at.isoformat() if p.collected_at else None} for p in pricing],
        "content": [{"id": c.id, "title": c.title, "url": c.url, "content_type": c.content_type, "collected_at": c.collected_at.isoformat() if c.collected_at else None} for c in content],
        "social": [{"id": s.id, "platform": s.platform.value if hasattr(s.platform, 'value') else s.platform, "url": s.profile_url, "username": s.username, "collected_at": s.collected_at.isoformat() if s.collected_at else None} for s in social],
        "tech_stack": [{"id": t.id, "technology_name": t.technology_name, "category": t.category, "confidence": float(t.confidence) if t.confidence else None} for t in tech],
        "sources": [{"id": s.id, "url": s.url, "page_type": s.page_type, "is_active": s.is_active, "last_crawled_at": s.last_crawled_at.isoformat() if s.last_crawled_at else None} for s in sources],
        "pages": [{"id": p.id, "url": p.source.url if p.source else None, "status_code": p.metadata_.get("status_code") if p.metadata_ else None, "title": p.extracted_data.get("title") if p.extracted_data else None} for p in pages],
        "collection_logs": [{"id": l.id, "start_time": l.start_time.isoformat() if l.start_time else None, "success": l.success, "duration_seconds": float(l.duration_seconds) if l.duration_seconds else None, "records_collected": l.records_collected} for l in logs],
    }


@router.post("/api/dashboard/competitors")
async def create_dashboard_competitor(
    payload: CompetitorCreate, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    from sqlalchemy.exc import IntegrityError

    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=422, detail="Competitor name is required")

    if not payload.website_url or not payload.website_url.strip():
        raise HTTPException(status_code=422, detail="Website URL is required")

    comp = Competitor(
        name=payload.name.strip(),
        website_url=payload.website_url.strip(),
        enabled=payload.enabled,
        collection_frequency=payload.collection_frequency,
        modules=payload.modules,
        tags=payload.tags,
        notes=payload.notes,
    )
    session.add(comp)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A competitor named '{payload.name.strip()}' already exists. Choose a different name.",
        )
    await session.refresh(comp)
    return {"id": comp.id, "name": comp.name, "website_url": comp.website_url, "status": "created"}


@router.put("/api/dashboard/competitors/{competitor_id}")
async def update_dashboard_competitor(
    competitor_id: int, payload: CompetitorUpdate, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    from sqlalchemy.exc import IntegrityError

    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(comp, key, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Update would violate constraints.")

    return {"id": comp.id, "name": comp.name, "website_url": comp.website_url, "status": "updated"}


@router.delete("/api/dashboard/competitors/{competitor_id}")
async def delete_dashboard_competitor(
    competitor_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await session.delete(comp)
    await session.commit()
    return {"status": "deleted", "message": f"Competitor {competitor_id} deleted"}


# ─── Bulk Operations ────────────────────────────────────────────────────────


@router.post("/api/dashboard/competitors/bulk/delete")
async def bulk_delete(
    payload: BulkAction, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    deleted = 0
    for cid in payload.competitor_ids:
        stmt = select(Competitor).where(Competitor.id == cid)
        result = await session.execute(stmt)
        comp = result.scalar_one_or_none()
        if comp:
            await session.delete(comp)
            deleted += 1
    await session.commit()
    return {"deleted": deleted}


@router.post("/api/dashboard/competitors/bulk/enable")
async def bulk_enable(
    payload: BulkAction, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    updated = 0
    for cid in payload.competitor_ids:
        stmt = select(Competitor).where(Competitor.id == cid)
        result = await session.execute(stmt)
        comp = result.scalar_one_or_none()
        if comp:
            comp.enabled = True
            updated += 1
    await session.commit()
    return {"updated": updated}


@router.post("/api/dashboard/competitors/bulk/disable")
async def bulk_disable(
    payload: BulkAction, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    updated = 0
    for cid in payload.competitor_ids:
        stmt = select(Competitor).where(Competitor.id == cid)
        result = await session.execute(stmt)
        comp = result.scalar_one_or_none()
        if comp:
            comp.enabled = False
            updated += 1
    await session.commit()
    return {"updated": updated}


@router.post("/api/dashboard/competitors/bulk/frequency")
async def bulk_update_frequency(
    payload: BulkFrequencyUpdate, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    updated = 0
    for cid in payload.competitor_ids:
        stmt = select(Competitor).where(Competitor.id == cid)
        result = await session.execute(stmt)
        comp = result.scalar_one_or_none()
        if comp:
            comp.collection_frequency = payload.frequency
            updated += 1
    await session.commit()
    return {"updated": updated}


@router.post("/api/dashboard/competitors/{competitor_id}/duplicate")
async def duplicate_competitor(
    competitor_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    new_comp = Competitor(
        name=f"{comp.name} (Copy)",
        website_url=comp.website_url,
        enabled=False,
        collection_frequency=comp.collection_frequency,
        modules=list(comp.modules) if comp.modules else [],
        tags=list(comp.tags) if comp.tags else [],
        notes=comp.notes,
    )
    session.add(new_comp)
    await session.commit()
    await session.refresh(new_comp)
    return {"id": new_comp.id, "name": new_comp.name, "status": "duplicated"}


# ─── Dashboard Stats & Overview ─────────────────────────────────────────────


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    total_competitors = await session.scalar(select(func.count()).select_from(Competitor)) or 0
    active_competitors = await session.scalar(
        select(func.count()).select_from(Competitor).where(Competitor.enabled.is_(True))
    ) or 0
    urls_count = await session.scalar(select(func.count()).select_from(CompetitorSource)) or 0
    pages_count = await session.scalar(select(func.count()).select_from(CompetitorPage)) or 0
    services_count = await session.scalar(select(func.count()).select_from(CompetitorService)) or 0
    pricing_count = await session.scalar(select(func.count()).select_from(CompetitorPricing)) or 0
    content_count = await session.scalar(select(func.count()).select_from(CompetitorContent)) or 0
    social_count = await session.scalar(select(func.count()).select_from(CompetitorSocial)) or 0

    total_logs = await session.scalar(select(func.count()).select_from(CollectionLog)) or 0
    success_logs = await session.scalar(
        select(func.count()).select_from(CollectionLog).where(CollectionLog.success.is_(True))
    ) or 0
    failed_logs = await session.scalar(
        select(func.count()).select_from(CollectionLog).where(CollectionLog.success.is_(False))
    ) or 0

    success_rate = round((success_logs / total_logs * 100) if total_logs > 0 else 0, 1)

    last_log_stmt = (
        select(CollectionLog.start_time)
        .order_by(CollectionLog.start_time.desc())
        .limit(1)
    )
    last_collection = await session.scalar(last_log_stmt)

    active_crawls = len(collection_service._active_crawls)

    running_jobs = 0
    try:
        from app.main import message_queue as mq
        queue_stats = await mq.get_stats()
        running_jobs = queue_stats.get("queue_size", 0)
    except Exception:
        pass

    return {
        "total_competitors": total_competitors,
        "active_competitors": active_competitors,
        "collections_running": active_crawls,
        "successful_collections": success_logs,
        "failed_collections": failed_logs,
        "total_collections": total_logs,
        "success_rate": success_rate,
        "queue_size": running_jobs,
        "scheduler_status": "running" if scheduler.is_running else "stopped",
        "last_collection": last_collection.isoformat() if last_collection else None,
        "urls_discovered": urls_count,
        "pages_crawled": pages_count,
        "services_extracted": services_count,
        "pricing_extracted": pricing_count,
        "content_extracted": content_count,
        "social_extracted": social_count,
        "db_status": "connected",
        "api_status": "healthy",
    }


@router.get("/api/dashboard/summary")
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    stmt = (
        select(
            Competitor.id,
            Competitor.name,
            Competitor.enabled,
            Competitor.collection_frequency,
            func.count(func.distinct(CompetitorService.id)).label("services_count"),
            func.count(func.distinct(CompetitorPricing.id)).label("pricing_count"),
            func.count(func.distinct(CompetitorContent.id)).label("content_count"),
            func.count(func.distinct(CompetitorSocial.id)).label("socials_count"),
        )
        .outerjoin(CompetitorService, Competitor.id == CompetitorService.competitor_id)
        .outerjoin(CompetitorPricing, Competitor.id == CompetitorPricing.competitor_id)
        .outerjoin(CompetitorContent, Competitor.id == CompetitorContent.competitor_id)
        .outerjoin(CompetitorSocial, Competitor.id == CompetitorSocial.competitor_id)
        .group_by(Competitor.id, Competitor.name, Competitor.enabled, Competitor.collection_frequency)
        .order_by(Competitor.name)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "enabled": row.enabled,
            "collection_frequency": row.collection_frequency.value if row.collection_frequency else "daily",
            "services_count": row.services_count,
            "pricing_count": row.pricing_count,
            "content_count": row.content_count,
            "socials_count": row.socials_count,
        }
        for row in rows
    ]


# ─── Activity Feed ──────────────────────────────────────────────────────────


@router.get("/api/dashboard/feed")
async def get_feed(
    limit: int = 20, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    log_stmt = (
        select(CollectionLog, Competitor.name)
        .join(Competitor, CollectionLog.competitor_id == Competitor.id)
        .order_by(CollectionLog.start_time.desc())
        .limit(limit)
    )
    log_result = await session.execute(log_stmt)
    logs = log_result.all()

    price_stmt = (
        select(CompetitorPricing, Competitor.name)
        .join(Competitor, CompetitorPricing.competitor_id == Competitor.id)
        .order_by(CompetitorPricing.collected_at.desc())
        .limit(limit)
    )
    price_result = await session.execute(price_stmt)
    prices = price_result.all()

    feed = []
    for log, comp_name in logs:
        feed.append({
            "type": "collection_success" if log.success else "collection_failure",
            "message": f"{comp_name} collection {'succeeded' if log.success else 'failed'}",
            "timestamp": log.start_time.isoformat() if log.start_time else "",
            "competitor_id": log.competitor_id,
            "duration_seconds": float(log.duration_seconds) if log.duration_seconds else None,
        })

    for price, comp_name in prices:
        feed.append({
            "type": "pricing_update",
            "message": f"{comp_name} updated pricing for {price.service_name}: {price.base_price} {price.currency}",
            "timestamp": price.collected_at.isoformat() if price.collected_at else "",
            "competitor_id": price.competitor_id,
        })

    feed.sort(key=lambda x: x["timestamp"], reverse=True)
    return feed[:limit]


# ─── Collection Logs ────────────────────────────────────────────────────────


@router.get("/api/dashboard/logs")
async def get_dashboard_logs(
    limit: int = 50,
    competitor_id: int | None = None,
    success: bool | None = None,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    stmt = select(CollectionLog)
    if competitor_id is not None:
        stmt = stmt.where(CollectionLog.competitor_id == competitor_id)
    if success is not None:
        stmt = stmt.where(CollectionLog.success.is_(success))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0

    stmt = stmt.order_by(CollectionLog.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    logs = result.scalars().all()

    enriched = []
    for log in logs:
        comp_stmt = select(Competitor.name).where(Competitor.id == log.competitor_id)
        comp_name = await session.scalar(comp_stmt) or "Unknown"
        enriched.append({
            "id": log.id,
            "competitor_id": log.competitor_id,
            "competitor_name": comp_name,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "success": log.success,
            "duration_seconds": float(log.duration_seconds) if log.duration_seconds else None,
            "records_collected": log.records_collected,
            "errors": log.errors or [],
            "retry_count": log.retry_count,
        })

    return {
        "logs": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ─── Collection Control ─────────────────────────────────────────────────────


@router.post("/api/dashboard/collect/{competitor_id}")
async def trigger_dashboard_collect(
    competitor_id: int, background_tasks: BackgroundTasks
) -> dict[str, str]:
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)
    return {"status": "accepted", "message": "Collection triggered"}


@router.post("/api/dashboard/collect/{competitor_id}/cancel")
async def cancel_dashboard_collect(competitor_id: int) -> dict[str, str]:
    async with collection_service._crawls_lock:
        collection_service._active_crawls.pop(competitor_id, None)
    return {"status": "cancelled", "message": f"Collection for competitor {competitor_id} cancelled"}


@router.post("/api/dashboard/collect/{competitor_id}/retry")
async def retry_dashboard_collect(
    competitor_id: int, background_tasks: BackgroundTasks
) -> dict[str, str]:
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)
    return {"status": "accepted", "message": "Retry collection triggered"}


# ─── Scheduler Control ──────────────────────────────────────────────────────


@router.get("/api/dashboard/scheduler/status")
async def get_scheduler_status() -> dict[str, Any]:
    return {
        "is_running": scheduler.is_running,
        "status": "running" if scheduler.is_running else "stopped",
        "interval_seconds": scheduler._interval_seconds,
    }


@router.post("/api/dashboard/scheduler/pause")
async def pause_scheduler() -> dict[str, str]:
    await scheduler.stop()
    return {"status": "paused", "message": "Scheduler paused"}


@router.post("/api/dashboard/scheduler/resume")
async def resume_scheduler() -> dict[str, str]:
    await scheduler.start()
    return {"status": "resumed", "message": "Scheduler resumed"}


# --- Config Re-sync ---

@router.post("/api/dashboard/config/resync")
async def resync_config() -> dict[str, Any]:
    from app.services.config_sync_service import config_sync_service
    result = config_sync_service.reload_config()
    synced = await config_sync_service.sync_competitors()
    return {"status": "success", "reloaded": len(result), "synced": synced}


@router.get("/api/dashboard/config")
async def get_config() -> dict[str, Any]:
    settings = get_settings()
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "queue_backend": settings.queue.backend,
        "webhooks_enabled": settings.webhook.enabled,
        "webhooks_slack": bool(settings.webhook.slack_webhook_url),
        "webhooks_teams": bool(settings.webhook.teams_webhook_url),
        "llm_enabled": settings.llm.enabled,
        "llm_provider": settings.llm.provider,
        "llm_model": settings.llm.model_name,
        "cache_enabled": settings.cache.enabled,
        "stealth_enabled": settings.stealth.enabled,
        "scheduler_enabled": settings.scheduler.enabled,
        "scheduler_interval": settings.scheduler.check_interval_seconds,
        "config_path": settings.competitors_config_path,
    }


# ─── Search ─────────────────────────────────────────────────────────────────


@router.get("/api/dashboard/search")
async def global_search(
    q: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    stmt = select(RawStorage).where(
        RawStorage.extracted_data.isnot(None),
        cast(RawStorage.extracted_data, String).ilike(f"%{q}%"),
    ).order_by(RawStorage.collected_at.desc()).limit(100)
    result = await session.execute(stmt)
    raw_storages = result.scalars().all()

    seen = set()
    latest_per_comp = []
    for r in raw_storages:
        if r.competitor_id not in seen:
            seen.add(r.competitor_id)
            latest_per_comp.append(r)

    matches = []
    q_lower = q.lower()
    for r in latest_per_comp:
        data_str = str(r.extracted_data).lower()
        if q_lower in data_str:
            comp_name = r.extracted_data.get("name", f"Competitor {r.competitor_id}")
            match_context = "Found in profile"
            if "services" in r.extracted_data:
                for srv in r.extracted_data["services"]:
                    if isinstance(srv, dict) and q_lower in str(srv).lower():
                        match_context = f"Service: {srv.get('name', 'Unknown')}"
                        break
            matches.append({
                "competitor_id": r.competitor_id,
                "name": comp_name,
                "context": match_context,
            })

    return {"query": q, "results": matches, "total": len(matches)}


# ─── Telemetry ──────────────────────────────────────────────────────────────


@router.get("/api/dashboard/telemetry")
async def get_dashboard_telemetry() -> dict[str, Any]:
    try:
        import psutil

        process = psutil.Process()
        mem_info = process.memory_info()
        mem_total = psutil.virtual_memory().total
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_mb": int(mem_info.rss / 1024 / 1024),
            "memory_total_gb": int(mem_total / 1024 / 1024 / 1024),
            "active_crawls": len(collection_service._active_crawls),
        }
    except ImportError:
        return {
            "cpu_percent": 0,
            "memory_mb": 0,
            "memory_total_gb": 0,
            "active_crawls": len(collection_service._active_crawls),
        }


# ─── Live Logs ──────────────────────────────────────────────────────────────


@router.get("/api/dashboard/live_logs/{competitor_id}")
async def get_dashboard_live_logs(competitor_id: int) -> list[dict[str, Any]]:
    from app.observability.log_buffer import global_log_buffer

    return global_log_buffer.get_logs_for_competitor(competitor_id)


# ─── Extracted Data ─────────────────────────────────────────────────────────


@router.get("/api/dashboard/extracted/{competitor_id}")
async def get_dashboard_extracted(
    competitor_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    stmt = (
        select(RawStorage)
        .where(RawStorage.competitor_id == competitor_id)
        .where(RawStorage.extracted_data.isnot(None))
        .order_by(RawStorage.collected_at.asc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    if not rows:
        return {"data": None}

    merged_data: dict[str, Any] = {}
    for raw in rows:
        if not raw.extracted_data:
            continue
        for k, v in raw.extracted_data.items():
            if isinstance(v, list):
                if k not in merged_data:
                    merged_data[k] = []
                merged_data[k].extend(v)
            elif isinstance(v, dict):
                if k not in merged_data:
                    merged_data[k] = {}
                merged_data[k].update(v)
            else:
                if v or k not in merged_data:
                    merged_data[k] = v

    return {"data": merged_data, "collected_at": rows[-1].collected_at.isoformat()}


# ─── Exports ────────────────────────────────────────────────────────────────


@router.get("/api/dashboard/compare/csv")
async def get_compare_csv(session: AsyncSession = Depends(get_session)):
    import csv
    import io

    stmt = select(Competitor).options(selectinload(Competitor.pricing)).order_by(Competitor.name)
    result = await session.execute(stmt)
    competitors = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Competitor", "Service/Tier", "Price", "Currency", "Billing", "Collected At"])

    for comp in competitors:
        if not comp.pricing:
            writer.writerow([comp.name, "No pricing found", "", "", "", ""])
            continue
        for p in comp.pricing:
            writer.writerow([
                comp.name,
                p.service_name or "N/A",
                p.base_price or "",
                p.currency or "",
                p.category or "",
                p.collected_at.isoformat() if p.collected_at else "N/A",
            ])

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=competitor_pricing_comparison.csv"
    return response


@router.get("/api/dashboard/raw/{competitor_id}")
async def get_raw_html(
    competitor_id: int, session: AsyncSession = Depends(get_session)
):
    stmt = (
        select(RawStorage)
        .where(RawStorage.competitor_id == competitor_id)
        .where(RawStorage.storage_uri.isnot(None))
        .order_by(RawStorage.collected_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    raw = result.scalar_one_or_none()

    if not raw or not raw.storage_uri or not os.path.exists(raw.storage_uri):
        raise HTTPException(status_code=404, detail="Raw HTML file not found")

    return FileResponse(raw.storage_uri, media_type="text/html", filename=f"competitor_{competitor_id}_raw.html")


@router.get("/api/dashboard/export/zip")
async def export_zip(session: AsyncSession = Depends(get_session)):
    import io
    import zipfile

    stmt = (
        select(RawStorage)
        .where(RawStorage.extracted_data.isnot(None))
        .order_by(RawStorage.collected_at.desc())
        .limit(100)
    )
    result = await session.execute(stmt)
    raw_storages = result.scalars().all()

    seen = set()
    latest_per_comp = []
    for r in raw_storages:
        if r.competitor_id not in seen:
            seen.add(r.competitor_id)
            latest_per_comp.append(r)

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
        for r in latest_per_comp:
            comp_name = (r.extracted_data or {}).get("name") or f"competitor_{r.competitor_id}"
            comp_name = str(comp_name).replace(" ", "_").replace("/", "_")

            json_str = json.dumps(r.extracted_data or {}, indent=2)
            zipf.writestr(f"{comp_name}_structured_data.json", json_str)

            if r.storage_uri and os.path.exists(r.storage_uri):
                with open(r.storage_uri, "rb") as f:
                    zipf.writestr(f"{comp_name}_raw.html", f.read())

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="application/zip")
    response.headers["Content-Disposition"] = "attachment; filename=competitor_intelligence_export.zip"
    return response


# ─── Health ─────────────────────────────────────────────────────────────────


@router.get("/api/dashboard/health")
async def get_system_health(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    try:
        start = time.monotonic()
        await session.scalar(select(func.count()).select_from(Competitor))
        db_latency = round((time.monotonic() - start) * 1000, 2)
        checks["database"] = {"status": "healthy", "latency_ms": db_latency}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    checks["scheduler"] = {
        "status": "healthy" if scheduler.is_running else "stopped",
        "running": scheduler.is_running,
    }

    try:
        from app.main import message_queue as mq

        q_stats = await mq.get_stats()
        checks["queue"] = {
            "status": "healthy",
            "queue_size": q_stats.get("queue_size", 0),
            "published": q_stats.get("stats", {}).get("published", 0),
            "consumed": q_stats.get("stats", {}).get("consumed", 0),
        }
    except Exception:
        checks["queue"] = {"status": "unknown"}

    active = len(collection_service._active_crawls)
    checks["collection"] = {"status": "healthy", "active_crawls": active}

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = round(usage.ru_maxrss / 1024, 1)
        checks["memory"] = {"status": "healthy", "rss_mb": rss_mb}
    except Exception:
        checks["memory"] = {"status": "unknown"}

    overall = all(c.get("status") == "healthy" for c in checks.values())
    return {"status": "healthy" if overall else "degraded", "checks": checks}
