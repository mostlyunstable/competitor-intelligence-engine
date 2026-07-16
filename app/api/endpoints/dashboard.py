import json
import os
import secrets
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import cast, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_session
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

# [SECURITY FIX] Apply Basic Auth globally to all endpoints in this router
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


router = APIRouter(tags=["dashboard"], dependencies=[Depends(verify_credentials)])


def _resolve_storage_path(storage_uri: str | None) -> str | None:
    """Strip file:// prefix from storage URIs for local file access."""
    if not storage_uri:
        return None
    return storage_uri.replace("file://", "") if storage_uri.startswith("file://") else storage_uri


@router.get("/dashboard", response_class=FileResponse)
async def get_dashboard(response: Response) -> str:
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return "app/static/dashboard.html"


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Computes aggregated database statistics and pipeline status."""
    competitors_count = await session.scalar(
        select(func.count()).select_from(Competitor).where(Competitor.enabled.is_(True))
    )
    urls_count = await session.scalar(select(func.count()).select_from(CompetitorSource))
    pages_count = await session.scalar(select(func.count()).select_from(CompetitorPage))
    services_count = await session.scalar(select(func.count()).select_from(CompetitorService))
    pricing_count = await session.scalar(select(func.count()).select_from(CompetitorPricing))
    content_count = await session.scalar(select(func.count()).select_from(CompetitorContent))
    social_count = await session.scalar(select(func.count()).select_from(CompetitorSocial))
    logs_count = await session.scalar(select(func.count()).select_from(CollectionLog))


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
        import importlib.util

        playwright_status = "ready" if importlib.util.find_spec("playwright") else "error"
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
    limit: int = 50, competitor_id: int | None = None, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    """Returns recent audit logs."""
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
        "active_crawls": len(collection_service._active_crawls),
    }


@router.post("/api/dashboard/collect/{competitor_id}/cancel")
async def cancel_dashboard_collect(competitor_id: int) -> dict[str, str]:
    async with collection_service._crawls_lock:
        collection_service._active_crawls.pop(competitor_id, None)
    return {
        "status": "cancelled",
        "message": f"Collection for competitor {competitor_id} cancelled",
    }



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


@router.get("/api/dashboard/extracted/{competitor_id}")
async def get_dashboard_extracted(
    competitor_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    from app.database.models import RawStorage

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
        extracted = raw.extracted_data or {}
        for k, v in extracted.items():
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
async def get_compare_csv(session: AsyncSession = Depends(get_session)) -> Any:
    import csv
    import io

    from fastapi.responses import StreamingResponse
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
            writer.writerow(
                [
                    comp.name,
                    p.service_name or "N/A",
                    p.base_price or "",
                    p.currency or "",
                    p.category or "",
                    p.collected_at.isoformat() if p.collected_at else "N/A",
                ]
            )

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = (
        "attachment; filename=competitor_pricing_comparison.csv"
    )
    return response


@router.get("/api/dashboard/raw/{competitor_id}")
async def get_raw_html(competitor_id: int, session: AsyncSession = Depends(get_session)) -> Any:
    import os

    from app.database.models import RawStorage

    stmt = (
        select(RawStorage)
        .where(RawStorage.competitor_id == competitor_id)
        .where(RawStorage.storage_uri.isnot(None))
        .order_by(RawStorage.collected_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    raw = result.scalar_one_or_none()

    storage_path = _resolve_storage_path(raw.storage_uri) if raw else None
    if not raw or not storage_path or not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="Raw HTML file not found")

    return FileResponse(
        storage_path, media_type="text/html", filename=f"competitor_{competitor_id}_raw.html"
    )



@router.get("/api/dashboard/export/zip")
async def export_zip(session: AsyncSession = Depends(get_session)) -> Any:
    import io
    import json
    import zipfile

    from fastapi.responses import StreamingResponse

    from app.database.models import RawStorage

    # [BUG FIX]: Removed text search on undefined 'q' to prevent crashes.
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
            extracted = r.extracted_data or {}
            comp_name = extracted.get("name") or f"competitor_{r.competitor_id}"
            comp_name = str(comp_name).replace(" ", "_").replace("/", "_")

            # Add JSON
            json_str = json.dumps(r.extracted_data, indent=2)
            zipf.writestr(f"{comp_name}_structured_data.json", json_str)

            # Add HTML if exists
            local_path = _resolve_storage_path(r.storage_uri) if r.storage_uri else None
            if local_path and os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    zipf.writestr(f"{comp_name}_raw.html", f.read())

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="application/zip")
    response.headers["Content-Disposition"] = (
        "attachment; filename=competitor_intelligence_export.zip"
    )
    return response


@router.get("/api/dashboard/search")
async def global_search(q: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    from sqlalchemy import String, cast

    from app.database.models import RawStorage

    escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    stmt = (
        select(RawStorage)
        .where(
            RawStorage.extracted_data.isnot(None),
            cast(RawStorage.extracted_data, String).ilike(f"%{escaped_q}%", escape="\\"),
        )
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

    matches = []
    q_lower = q.lower()
    for r in latest_per_comp:
        data_str = str(r.extracted_data).lower()
        if q_lower in data_str:
            extracted = r.extracted_data or {}
            comp_name = extracted.get("name", f"Competitor {r.competitor_id}")
            # Try to find exactly what matched
            match_context = "Found in profile"
            if "services" in extracted:
                for srv in extracted["services"]:
                    if isinstance(srv, dict) and q_lower in str(srv).lower():
                        match_context = f"Service: {srv.get('name', 'Unknown')}"
                        break
            matches.append(
                {"competitor_id": r.competitor_id, "name": comp_name, "context": match_context}
            )

    return {"query": q, "results": matches}


@router.get("/api/dashboard/feed")
async def get_feed(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    # Get last 20 collection logs
    log_stmt = (
        select(CollectionLog, Competitor.name)
        .join(Competitor, CollectionLog.competitor_id == Competitor.id)
        .order_by(CollectionLog.start_time.desc())
        .limit(20)
    )
    log_result = await session.execute(log_stmt)
    logs = log_result.all()

    # Get last 20 pricing changes
    price_stmt = (
        select(CompetitorPricing, Competitor.name)
        .join(Competitor, CompetitorPricing.competitor_id == Competitor.id)
        .order_by(CompetitorPricing.collected_at.desc())
        .limit(20)
    )
    price_result = await session.execute(price_stmt)
    prices = price_result.all()

    feed = []
    for log, comp_name in logs:
        feed.append(
            {
                "type": "collection_success" if log.success else "collection_failure",
                "message": f"{comp_name} collection {'succeeded' if log.success else 'failed'}",
                "timestamp": log.start_time.isoformat() if log.start_time else "",
                "competitor_id": log.competitor_id,
            }
        )

    for price, comp_name in prices:
        feed.append(
            {
                "type": "pricing_update",
                "message": f"{comp_name} updated pricing for {price.service_name}: {price.base_price} {price.currency}",
                "timestamp": price.collected_at.isoformat() if price.collected_at else "",
                "competitor_id": price.competitor_id,
            }
        )

    # Sort by timestamp desc
    feed.sort(key=lambda x: x["timestamp"], reverse=True)
    return feed[:20]
