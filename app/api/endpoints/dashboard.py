from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.database.models import (
    CollectionLog,
    Competitor,
    CompetitorContent,
    CompetitorPage,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
    CompetitorSource,
)
from app.schedulers.scheduler import scheduler
from app.services.collection_service import collection_service

import os
import secrets
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import APIRouter, BackgroundTasks, Depends, Response, HTTPException, status

router = APIRouter(tags=["dashboard"])

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, os.getenv("ADMIN_USER", "admin"))
    correct_password = secrets.compare_digest(credentials.password, os.getenv("ADMIN_PASSWORD", "admin123"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@router.get("/dashboard", response_class=FileResponse)
async def get_dashboard(response: Response, username: str = Depends(verify_credentials)) -> str:
    """Serves the live interactive dashboard UI from static file."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return "app/static/dashboard.html"


@router.get("/api/dashboard/competitors")
async def get_dashboard_competitors(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.database.models import Competitor
    stmt = select(Competitor).order_by(Competitor.name)
    result = await session.execute(stmt)
    competitors = result.scalars().all()
    
    out = []
    for c in competitors:
        # Get the most recent successful collection time
        last_log_stmt = (
            select(CollectionLog.start_time)
            .where(CollectionLog.competitor_id == c.id)
            .where(CollectionLog.success.is_(True))
            .order_by(CollectionLog.start_time.desc())
            .limit(1)
        )
        last_collected = await session.scalar(last_log_stmt)
        out.append({
            "id": c.id,
            "name": c.name,
            "website_url": c.website_url,
            "last_collected": last_collected.isoformat() if last_collected else None,
        })
    return out

@router.post("/api/dashboard/competitors")
async def create_dashboard_competitor(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    from sqlalchemy.exc import IntegrityError
    from app.database.models import Competitor, CollectionFrequency
    
    comp = Competitor(
        name=payload["name"],
        website_url=payload["website_url"],
        enabled=True,
        collection_frequency=CollectionFrequency.DAILY,
        modules=[],
        tags=[]
    )
    session.add(comp)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="A competitor with this name or URL already exists.")
    await session.refresh(comp)
    return {"id": comp.id, "name": comp.name, "website_url": comp.website_url}

@router.delete("/api/dashboard/competitors/{competitor_id}")
async def delete_dashboard_competitor(
    competitor_id: int,
    session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    """Deletes a competitor and all associated data (CASCADE)."""
    from fastapi import HTTPException
    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await session.delete(comp)
    await session.commit()
    return {"status": "deleted", "message": f"Competitor {competitor_id} deleted"}


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Computes aggregated database statistics and pipeline status."""
    urls_count = await session.scalar(select(func.count()).select_from(CompetitorSource))
    pages_count = await session.scalar(select(func.count()).select_from(CompetitorPage))
    services_count = await session.scalar(select(func.count()).select_from(CompetitorService))
    pricing_count = await session.scalar(select(func.count()).select_from(CompetitorPricing))
    content_count = await session.scalar(select(func.count()).select_from(CompetitorContent))
    social_count = await session.scalar(select(func.count()).select_from(CompetitorSocial))
    logs_count = await session.scalar(select(func.count()).select_from(CollectionLog))

    # Calculate error count
    error_stmt = (
        select(func.count()).select_from(CollectionLog).where(CollectionLog.success.is_(False))
    )
    errors_count = await session.scalar(error_stmt)

    # Active collection
    active_collection = None
    if collection_service._active_crawls:
        import time
        # Get first active crawl ID
        active_id = next(iter(collection_service._active_crawls.keys()))
        start_time = collection_service._active_crawls[active_id]
        active_collection = {
            "competitor_id": active_id,
            "status": "active",
            "elapsed": time.time() - start_time,
        }

    # Check Playwright availability
    playwright_status = "error"
    try:
        import playwright
        playwright_status = "ready"
    except ImportError:
        pass

    return {
        "urls_discovered": urls_count or 0,
        "pages_crawled": pages_count or 0,
        "services_extracted": services_count or 0,
        "pricing_extracted": pricing_count or 0,
        "database_writes": (urls_count or 0)
        + (pages_count or 0)
        + (services_count or 0)
        + (pricing_count or 0)
        + (content_count or 0)
        + (social_count or 0)
        + (logs_count or 0),
        "errors": errors_count or 0,
        "scheduler_status": "active" if scheduler.is_running else "idle",
        "playwright_status": playwright_status,
        "db_status": "connected",
        "api_status": "healthy",
        "active_collection": active_collection,
    }


@router.get("/api/dashboard/summary")
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Generates counts of extracted modules per competitor in a single efficient query."""
    from sqlalchemy import outerjoin, literal_column
    from sqlalchemy.orm import aliased
    
    stmt = (
        select(
            Competitor.id,
            Competitor.name,
            func.count(func.distinct(CompetitorService.id)).label("services_count"),
            func.count(func.distinct(CompetitorPricing.id)).label("pricing_count"),
            func.count(func.distinct(CompetitorContent.id)).label("content_count"),
            func.count(func.distinct(CompetitorSocial.id)).label("socials_count"),
        )
        .outerjoin(CompetitorService, Competitor.id == CompetitorService.competitor_id)
        .outerjoin(CompetitorPricing, Competitor.id == CompetitorPricing.competitor_id)
        .outerjoin(CompetitorContent, Competitor.id == CompetitorContent.competitor_id)
        .outerjoin(CompetitorSocial, Competitor.id == CompetitorSocial.competitor_id)
        .group_by(Competitor.id, Competitor.name)
        .order_by(Competitor.name)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "services_count": row.services_count,
            "pricing_count": row.pricing_count,
            "content_count": row.content_count,
            "socials_count": row.socials_count,
        }
        for row in rows
    ]


@router.get("/api/dashboard/logs")
async def get_dashboard_logs(
    limit: int = 50, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    """Returns recent audit logs."""
    stmt = select(CollectionLog).order_by(CollectionLog.id.desc()).limit(limit)
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "competitor_id": log.competitor_id,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "success": log.success,
            "duration_seconds": float(log.duration_seconds) if log.duration_seconds else None,
            "records_collected": log.records_collected,
            "errors": log.errors or [],
            "retry_count": log.retry_count,
        }
        for log in logs
    ]


@router.post("/api/dashboard/collect/{competitor_id}")
async def trigger_dashboard_collect(
    competitor_id: int, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Triggers standard collection in the background."""
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)
    return {"status": "accepted", "message": "Collection triggered"}


@router.get("/api/dashboard/telemetry")
async def get_dashboard_telemetry() -> dict[str, Any]:
    """Returns actual system CPU and Memory metrics."""
    import psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_total = psutil.virtual_memory().total
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_mb": int(mem_info.rss / 1024 / 1024),
        "memory_total_gb": int(mem_total / 1024 / 1024 / 1024),
        "active_crawls": len(collection_service._active_crawls)
    }

@router.post("/api/dashboard/collect/{competitor_id}/cancel")
async def cancel_dashboard_collect(competitor_id: int) -> dict[str, str]:
    """Cancels a running collection by removing it from the active crawls tracker."""
    async with collection_service._crawls_lock:
        collection_service._active_crawls.pop(competitor_id, None)
    return {"status": "cancelled", "message": f"Collection for competitor {competitor_id} cancelled"}

@router.get("/api/dashboard/live_logs/{competitor_id}")
async def get_dashboard_live_logs(competitor_id: int) -> list[dict[str, Any]]:
    """Returns real-time structlog events from the global buffer."""
    from app.observability.log_buffer import global_log_buffer
    return global_log_buffer.get_logs_for_competitor(competitor_id)

@router.get("/api/dashboard/extracted/{competitor_id}")
async def get_dashboard_extracted(competitor_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    from sqlalchemy import select
    from app.database.models import RawStorage
    stmt = (
        select(RawStorage)
        .where(RawStorage.competitor_id == competitor_id)
        .where(RawStorage.extracted_data.isnot(None))
        .order_by(RawStorage.collected_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    raw = result.scalar_one_or_none()
    if not raw:
        return {"data": None}
    return {"data": raw.extracted_data, "collected_at": raw.collected_at.isoformat()}


@router.get("/api/dashboard/compare/csv")
async def get_compare_csv(session: AsyncSession = Depends(get_session)):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from app.database.models import Competitor, CompetitorPricing
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

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
                p.tier_name or p.service_name or "N/A",
                p.price or "N/A",
                p.currency or "N/A",
                p.billing_period or "N/A",
                p.collected_at.isoformat() if p.collected_at else "N/A"
            ])

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=competitor_pricing_comparison.csv"
    return response
