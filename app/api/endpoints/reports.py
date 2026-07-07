"""API endpoints for reporting and analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.api.auth import verify_api_key
from app.database.connection import db_manager
from app.database.models import (
    CollectionLog,
    Competitor,
    CompetitorContent,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
)
from app.services.reporting_service import reporting_service

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/reports", tags=["reports"])


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session() as session:
        yield session


@router.get("/collection/{log_id}")
async def get_collection_report(
    log_id: int,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    log = await session.get(CollectionLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Collection log not found")

    competitor = await session.get(Competitor, log.competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    svc_res = await session.execute(
        select(CompetitorService).where(CompetitorService.competitor_id == log.competitor_id)
    )
    services = svc_res.scalars().all()

    price_res = await session.execute(
        select(CompetitorPricing).where(CompetitorPricing.competitor_id == log.competitor_id)
    )
    pricing = price_res.scalars().all()

    content_res = await session.execute(
        select(CompetitorContent).where(CompetitorContent.competitor_id == log.competitor_id)
    )
    content = content_res.scalars().all()

    social_res = await session.execute(
        select(CompetitorSocial).where(CompetitorSocial.competitor_id == log.competitor_id)
    )
    social = social_res.scalars().all()

    report = await reporting_service.get_collection_report(
        competitor, log, services, pricing, content, social
    )
    return _report_to_dict(report)


def _report_to_dict(report: Any) -> dict[str, Any]:
    return {
        "competitor_name": report.competitor_name,
        "competitor_id": report.competitor_id,
        "start_time": report.start_time,
        "duration_seconds": report.duration_seconds,
        "success": report.success,
        "errors": report.errors,
        "records_collected": report.records_collected,
        "services": report.services,
        "pricing": report.pricing,
        "content": report.content,
        "social": report.social,
    }


@router.get("/diff/{competitor_id}")
async def get_diff_report(
    competitor_id: int,
    before_id: int,
    after_id: int,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    competitor = await session.get(Competitor, competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    before_log = await session.get(CollectionLog, before_id)
    if not before_log or before_log.competitor_id != competitor_id:
        raise HTTPException(status_code=404, detail="Before log not found for this competitor")

    after_log = await session.get(CollectionLog, after_id)
    if not after_log or after_log.competitor_id != competitor_id:
        raise HTTPException(status_code=404, detail="After log not found for this competitor")

    async def _fetch(model: Any) -> Sequence[Any]:
        result = await session.execute(
            select(model).where(model.competitor_id == competitor_id)
        )
        return result.scalars().all()

    report = await reporting_service.compute_diff(
        competitor,
        before_log,
        after_log,
        await _fetch(CompetitorService),
        await _fetch(CompetitorService),
        await _fetch(CompetitorPricing),
        await _fetch(CompetitorPricing),
        await _fetch(CompetitorContent),
        await _fetch(CompetitorContent),
        await _fetch(CompetitorSocial),
        await _fetch(CompetitorSocial),
    )

    return {
        "competitor_name": report.competitor_name,
        "competitor_id": report.competitor_id,
        "before_time": report.before_time,
        "after_time": report.after_time,
        "total_changes": report.total_changes,
        "changes": {
            "services": [_diff_to_dict(d) for d in report.services],
            "pricing": [_diff_to_dict(d) for d in report.pricing],
            "content": [_diff_to_dict(d) for d in report.content],
            "social": [_diff_to_dict(d) for d in report.social],
        },
    }


def _diff_to_dict(d: Any) -> dict[str, Any]:
    return {
        "change_type": d.change_type,
        "field": d.field,
        "identifier": d.identifier,
        "before": d.before,
        "after": d.after,
    }


@router.get("/compare")
async def get_comparison_report(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    result = await session.execute(select(Competitor).where(Competitor.enabled.is_(True)))
    competitors = result.scalars().all()

    services_map: dict[int, int] = {}
    pricing_map: dict[int, int] = {}
    content_map: dict[int, int] = {}
    social_map: dict[int, int] = {}
    last_logs: dict[int, CollectionLog | None] = {}

    for comp in competitors:
        r = await session.execute(
            select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == comp.id
            )
        )
        services_map[comp.id] = r.scalar() or 0

        r = await session.execute(
            select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == comp.id
            )
        )
        pricing_map[comp.id] = r.scalar() or 0

        r = await session.execute(
            select(func.count()).select_from(CompetitorContent).where(
                CompetitorContent.competitor_id == comp.id
            )
        )
        content_map[comp.id] = r.scalar() or 0

        r = await session.execute(
            select(func.count()).select_from(CompetitorSocial).where(
                CompetitorSocial.competitor_id == comp.id
            )
        )
        social_map[comp.id] = r.scalar() or 0

        log_res = await session.execute(
            select(CollectionLog)
            .where(CollectionLog.competitor_id == comp.id)
            .order_by(CollectionLog.start_time.desc())
            .limit(1)
        )
        last_logs[comp.id] = log_res.scalar_one_or_none()

    report = await reporting_service.compute_comparison(
        competitors, services_map, pricing_map, content_map, social_map, last_logs
    )

    return {
        "competitors": [
            {
                "competitor_id": c.competitor_id,
                "competitor_name": c.competitor_name,
                "service_count": c.service_count,
                "pricing_count": c.pricing_count,
                "content_count": c.content_count,
                "social_count": c.social_count,
                "last_collected": c.last_collected,
                "last_collection_duration": c.last_collection_duration,
            }
            for c in report.competitors
        ]
    }


@router.get("/trends/{competitor_id}")
async def get_trend_report(
    competitor_id: int,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    competitor = await session.get(Competitor, competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    result = await session.execute(
        select(CollectionLog)
        .where(
            CollectionLog.competitor_id == competitor_id,
            CollectionLog.success.is_(True),
        )
        .order_by(CollectionLog.start_time.desc())
        .limit(limit)
    )
    logs = list(result.scalars().all())
    logs.reverse()

    report = await reporting_service.compute_trends(competitor, logs)
    return {
        "competitor_name": report.competitor_name,
        "competitor_id": report.competitor_id,
        "collection_history": [
            {
                "date": t.date,
                "services_added": t.services_added,
                "pricing_added": t.pricing_added,
                "content_added": t.content_added,
                "records_collected": t.records_collected,
                "duration_seconds": t.duration_seconds,
            }
            for t in report.collection_history
        ],
    }
