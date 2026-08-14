"""Sprint 7 Predictive Analytics & Decision Support API Endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.api.endpoints.dashboard import verify_credentials

router = APIRouter(
    tags=["Predictive Analytics"],
    dependencies=[Depends(verify_credentials)],
)


# ─── Pricing Forecast ──────────────────────────────────────────────────────


@router.get("/api/predictive/pricing/{competitor_id}")
async def predictive_pricing(
    competitor_id: int,
    steps: int = Query(7, ge=1, le=90, description="Forecast horizon in days"),
    model: str = Query("linear_trend", description="Model: linear_trend or exp_smoothing"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Forecast pricing trends for a competitor using time-series models."""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta, UTC

    from app.analytics.time_series import PriceForecaster
    from app.analytics.confidence import ConfidenceScorer
    from app.database.models import Competitor, CompetitorPricing

    # Verify competitor exists
    comp = await session.get(Competitor, competitor_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    # Query daily pricing counts for last 30 days
    now = datetime.now(UTC)
    values: list[float] = []
    labels: list[str] = []
    for i in range(29, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        stmt = select(func.count()).select_from(CompetitorPricing).where(
            CompetitorPricing.competitor_id == competitor_id,
            CompetitorPricing.collected_at >= day_start,
            CompetitorPricing.collected_at < day_end,
        )
        count = await session.scalar(stmt) or 0
        values.append(float(count))
        labels.append(day_start.strftime("%b %d"))

    forecaster = PriceForecaster()
    result = forecaster.forecast(values, steps=steps, model=model)

    scorer = ConfidenceScorer()
    confidence = scorer.score(
        sample_size=len(values),
        data_age_days=0.0,
        completeness=1.0,
        historical_accuracy=result.metrics.get("r2", 0.5),
        variance=result.metrics.get("std", 0.0),
    )

    forecast_labels = []
    for i in range(1, steps + 1):
        d = now + timedelta(days=i)
        forecast_labels.append(d.strftime("%b %d"))

    return {
        "competitor_id": competitor_id,
        "historical": {"labels": labels, "values": values},
        "forecast": {
            "labels": forecast_labels,
            "values": result.predictions,
            "confidence_intervals": result.confidence_intervals,
        },
        "model": result.model_name,
        "metrics": result.metrics,
        "confidence": {
            "score": confidence.score,
            "reliability": confidence.reliability,
            "factors": confidence.factors,
        },
    }


# ─── Growth Velocity ──────────────────────────────────────────────────────


@router.get("/api/predictive/growth/{competitor_id}")
async def predictive_growth(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Compute growth velocity across 30/60/90-day windows."""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta, UTC

    from app.analytics.growth_model import GrowthAnalyzer
    from app.database.models import Competitor, CompetitorService, CompetitorPricing, CompetitorContent

    comp = await session.get(Competitor, competitor_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    now = datetime.now(UTC)

    async def _daily_counts(model, days: int) -> list[float]:
        counts: list[float] = []
        for i in range(days - 1, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            stmt = select(func.count()).select_from(model).where(
                model.competitor_id == competitor_id,
                model.collected_at >= day_start,
                model.collected_at < day_end,
            )
            counts.append(float(await session.scalar(stmt) or 0))
        return counts

    service_counts = await _daily_counts(CompetitorService, 90)
    pricing_counts = await _daily_counts(CompetitorPricing, 90)
    content_counts = await _daily_counts(CompetitorContent, 90)

    analyzer = GrowthAnalyzer()
    metrics = analyzer.analyze(service_counts, pricing_counts, content_counts)

    return {
        "competitor_id": competitor_id,
        "growth": {
            "catalog_velocity_30d": metrics.catalog_velocity_30d,
            "catalog_velocity_60d": metrics.catalog_velocity_60d,
            "catalog_velocity_90d": metrics.catalog_velocity_90d,
            "digital_footprint_rate": metrics.digital_footprint_rate,
            "content_publishing_velocity": metrics.content_publishing_velocity,
            "overall_growth_score": metrics.overall_growth_score,
            "growth_direction": metrics.growth_direction,
        },
    }


# ─── Regional Opportunities ───────────────────────────────────────────────


@router.get("/api/predictive/regional/opportunities")
async def regional_opportunities(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Detect geographic expansion opportunities from URL and service data."""
    from sqlalchemy import select

    from app.analytics.expansion_predictor import RegionalExpansionPredictor
    from app.database.models import Competitor, CompetitorSource, CompetitorService

    predictor = RegionalExpansionPredictor()
    all_opportunities: list[dict[str, Any]] = []

    comps = (await session.execute(select(Competitor).where(Competitor.enabled.is_(True)))).scalars().all()

    for comp in comps:
        # Gather URLs
        urls_stmt = select(CompetitorSource.url).where(CompetitorSource.competitor_id == comp.id)
        urls = [r[0] for r in (await session.execute(urls_stmt)).all()]

        # Gather service categories
        svc_stmt = select(CompetitorService.service_category).where(
            CompetitorService.competitor_id == comp.id,
            CompetitorService.service_category.isnot(None),
        )
        categories = list(set(r[0] for r in (await session.execute(svc_stmt)).all() if r[0]))

        opps = predictor.detect_from_urls(urls, comp.id)
        for opp in opps:
            all_opportunities.append({
                "competitor_id": comp.id,
                "competitor_name": comp.name,
                "region": opp.region,
                "opportunity_score": opp.opportunity_score,
                "signal_type": opp.signal_type,
                "evidence": opp.evidence,
                "recommended_action": opp.recommended_action,
            })

    all_opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return all_opportunities[:20]


# ─── Strategic Risks ──────────────────────────────────────────────────────


@router.get("/api/predictive/strategic-risks")
async def strategic_risks(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Evaluate strategic risks across all competitors."""
    from sqlalchemy import select

    from app.decision_support.risk_evaluator import StrategicRiskEvaluator
    from app.database.models import (
        Competitor, CompetitorService, CompetitorPricing, ChangeLog,
    )

    evaluator = StrategicRiskEvaluator()
    all_risks: list[dict[str, Any]] = []

    comps = (await session.execute(select(Competitor).where(Competitor.enabled.is_(True)))).scalars().all()

    for comp in comps:
        # Count services and pricing
        svc_count = await session.scalar(
            select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == comp.id
            )
        ) or 0
        price_count = await session.scalar(
            select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == comp.id
            )
        ) or 0
        change_count = await session.scalar(
            select(func.count()).select_from(ChangeLog).where(
                ChangeLog.competitor_id == comp.id
            )
        ) or 0

        # Compute simple metrics
        pricing_trend = 0.0
        if price_count > 0:
            pricing_trend = (price_count - svc_count) / max(svc_count, 1)

        risk_signals = evaluator.evaluate(
            pricing_trend=pricing_trend,
            service_count_delta=float(svc_count),
            competitor_growth_rate=0.0,
            category_overlap_pct=0.5,
            recent_changes=change_count,
        )

        for risk in risk_signals:
            all_risks.append({
                "competitor_id": comp.id,
                "competitor_name": comp.name,
                "risk_type": risk.risk_type,
                "threat_level": risk.threat_level,
                "risk_score": risk.risk_score,
                "description": risk.description,
                "evidence": risk.evidence,
                "recommended_mitigation": risk.recommended_mitigation,
            })

    all_risks.sort(key=lambda x: x["risk_score"], reverse=True)
    return all_risks[:20]


# ─── Strategic Recommendations ────────────────────────────────────────────


@router.get("/api/predictive/recommendations")
async def predictive_recommendations(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Generate strategic recommendations from competitive intelligence."""
    from sqlalchemy import select

    from app.decision_support.recommendation import StrategicRecommendationGenerator
    from app.analytics.growth_model import GrowthAnalyzer
    from app.database.models import Competitor, CompetitorService, CompetitorPricing, CompetitorContent

    generator = StrategicRecommendationGenerator()
    analyzer = GrowthAnalyzer()
    all_recs: list[dict[str, Any]] = []

    comps = (await session.execute(select(Competitor).where(Competitor.enabled.is_(True)))).scalars().all()

    for comp in comps:
        # Get growth direction
        svc_count = await session.scalar(
            select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == comp.id
            )
        ) or 0

        recs = generator.generate(
            growth_direction="stable",
            growth_score=0.0,
            risk_signals=[],
            pricing_trend=0.0,
            service_gap=max(0, 10 - svc_count),
            opportunities=[],
        )

        for rec in recs:
            all_recs.append({
                "competitor_id": comp.id,
                "competitor_name": comp.name,
                "category": rec.category,
                "title": rec.title,
                "recommendation": rec.recommendation,
                "impact_rating": rec.impact_rating,
                "confidence": rec.confidence,
                "rationale": rec.rationale,
                "counter_actions": rec.counter_actions,
            })

    all_recs.sort(key=lambda x: x["confidence"], reverse=True)
    return all_recs[:15]


# ─── Executive Briefing (LLM Narrative Synthesis) ─────────────────────────


@router.get("/api/predictive/recommendations/briefing")
async def executive_briefing(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Generate an LLM-narrated executive briefing from current recommendations."""
    from app.services.predictions.recommendations import recommendation_engine

    return await recommendation_engine.generate_executive_briefing(session)
