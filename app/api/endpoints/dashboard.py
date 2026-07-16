import os
import secrets
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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
    """Serves the live interactive dashboard UI from static file."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
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
        import importlib.util

        playwright_status = "ready" if importlib.util.find_spec("playwright") else "error"
    except Exception:
        pass

    return {
        "competitors_monitored": competitors_count or 0,
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
    limit: int = 50, competitor_id: int | None = None, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    """Returns recent audit logs."""
    stmt = select(CollectionLog)
    if competitor_id is not None:
        stmt = stmt.where(CollectionLog.competitor_id == competitor_id)
    stmt = stmt.order_by(CollectionLog.id.desc()).limit(limit)
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
        "active_crawls": len(collection_service._active_crawls),
    }


@router.post("/api/dashboard/collect/{competitor_id}/cancel")
async def cancel_dashboard_collect(competitor_id: int) -> dict[str, str]:
    """Cancels a running collection by removing it from the active crawls tracker."""
    async with collection_service._crawls_lock:
        collection_service._active_crawls.pop(competitor_id, None)
    return {
        "status": "cancelled",
        "message": f"Collection for competitor {competitor_id} cancelled",
    }


@router.get("/api/dashboard/live_logs/{competitor_id}")
async def get_dashboard_live_logs(competitor_id: int) -> list[dict[str, Any]]:
    """Returns real-time structlog events from the global buffer."""
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
                # Simple dedup for dicts in lists might be hard, but extending is fine for export
                merged_data[k].extend(v)
            elif isinstance(v, dict):
                if k not in merged_data:
                    merged_data[k] = {}
                merged_data[k].update(v)
            else:
                if v or k not in merged_data:
                    merged_data[k] = v

    return {"data": merged_data, "collected_at": rows[-1].collected_at.isoformat()}


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
