"""Sprint 7: Predictive Intelligence API Endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.api.endpoints.dashboard import verify_credentials

logger = structlog.get_logger(__name__)

router = APIRouter(
    tags=["Predictions"],
    dependencies=[Depends(verify_credentials)],
)


# ─── Market Trends ───────────────────────────────────────────────────────────


@router.get("/api/predictions/trends")
async def get_market_trends(
    days: int = 90,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.trends import trend_analyzer

    days = min(max(days, 7), 365)
    trends = await trend_analyzer.get_all_trends(session, days)
    return trends


@router.get("/api/predictions/trends/emerging")
async def get_emerging_trends(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.trends import trend_analyzer

    return await trend_analyzer.detect_emerging_trends(session)


# ─── Growth Forecasting ─────────────────────────────────────────────────────


@router.get("/api/predictions/growth")
async def get_growth_forecasts(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.growth import growth_forecaster

    return await growth_forecaster.forecast_all(session)


@router.get("/api/predictions/growth/{competitor_id}")
async def get_competitor_growth(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.growth import growth_forecaster

    result = await growth_forecaster.forecast(competitor_id, session)
    if not result:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return result


# ─── Regional Expansion ─────────────────────────────────────────────────────


@router.get("/api/predictions/expansion/{competitor_id}")
async def get_expansion_forecast(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.expansion import expansion_forecaster

    return await expansion_forecaster.forecast(competitor_id, session)


# ─── Risk Analysis ──────────────────────────────────────────────────────────


@router.get("/api/predictions/risks")
async def get_all_risks(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.risks import risk_analyzer

    return await risk_analyzer.analyze_all(session)


@router.get("/api/predictions/risks/{competitor_id}")
async def get_competitor_risks(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.risks import risk_analyzer

    return await risk_analyzer.analyze(competitor_id, session)


# ─── Opportunity Detection ──────────────────────────────────────────────────


@router.get("/api/predictions/opportunities")
async def get_opportunities(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.opportunities import opportunity_detector

    return await opportunity_detector.detect(session)


# ─── Strategic Recommendations ──────────────────────────────────────────────


@router.get("/api/predictions/recommendations")
async def get_all_recommendations(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.recommendations import recommendation_engine

    return await recommendation_engine.generate_all(session)


@router.get("/api/predictions/recommendations/{competitor_id}")
async def get_competitor_recommendations(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.recommendations import recommendation_engine

    return await recommendation_engine.generate(competitor_id, session)


# ─── Predictive Benchmarking ────────────────────────────────────────────────


@router.get("/api/predictions/benchmarks")
async def get_predictive_benchmarks(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.benchmarking import predictive_benchmarker

    return await predictive_benchmarker.benchmark_all(session)


@router.get("/api/predictions/benchmarks/{competitor_id}")
async def get_competitor_benchmark(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.benchmarking import predictive_benchmarker

    result = await predictive_benchmarker.benchmark_competitor(competitor_id, session)
    if not result:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return result


# ─── Forecast Reports ───────────────────────────────────────────────────────


@router.get("/api/predictions/report")
async def get_forecast_report(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.reports import forecast_report_generator

    return await forecast_report_generator.generate(session)


# ─── Full Prediction (per competitor) ──────────────────────────────────────


@router.get("/api/predictions/full/{competitor_id}")
async def get_full_predictions(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.engine import prediction_engine

    return await prediction_engine.generate_all_predictions(competitor_id, session)


# ─── Save/Trigger ──────────────────────────────────────────────────────────


@router.post("/api/predictions/generate")
async def generate_and_save_predictions(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.database.models import (
        CompetitorPrediction,
        MarketTrend,
        PredictiveBenchmark,
        PredictionType,
        TrendDirection,
    )
    from app.services.predictions.growth import growth_forecaster
    from app.services.predictions.trends import trend_analyzer
    from app.services.predictions.benchmarking import predictive_benchmarker

    saved_predictions = 0
    saved_trends = 0
    saved_benchmarks = 0

    growth_data = await growth_forecaster.forecast_all(session)
    for g in growth_data:
        pred = CompetitorPrediction(
            competitor_id=g["competitor_id"],
            prediction_type=PredictionType.GROWTH,
            prediction_data=g,
            confidence_score=g.get("confidence_score", 0.5),
        )
        session.add(pred)
        saved_predictions += 1

    trends = await trend_analyzer.get_all_trends(session)
    for t in trends.get("pricing_trends", []) + trends.get("service_trends", []):
        direction_str = t.get("direction", "stable")
        try:
            direction = TrendDirection(direction_str)
        except ValueError:
            direction = TrendDirection.STABLE

        trend = MarketTrend(
            category=t.get("category", "unknown"),
            direction=direction,
            strength=t.get("strength", 0.5),
            description=t.get("description", ""),
            evidence=[],
            affected_competitors=[],
        )
        session.add(trend)
        saved_trends += 1

    benchmarks = await predictive_benchmarker.benchmark_all(session)
    for b in benchmarks:
        from app.database.models import GrowthLevel

        overall = b.get("overall_prediction", "stable")
        try:
            growth_level = GrowthLevel(overall.replace("_growth", ""))
        except ValueError:
            growth_level = GrowthLevel.MEDIUM

        bench = PredictiveBenchmark(
            competitor_id=b["competitor_id"],
            current_rank=b.get("current_rank", 0),
            predicted_rank=b.get("predicted_rank", 0),
            growth_score=b.get("growth_score", 0),
            innovation_score=b.get("innovation_score", 0),
            expansion_score=b.get("expansion_score", 0),
            risk_score=b.get("risk_score", 0),
            overall_prediction=overall,
            benchmark_data=b.get("benchmark_data", {}),
        )
        session.add(bench)
        saved_benchmarks += 1

    await session.commit()

    return {
        "status": "success",
        "saved_predictions": saved_predictions,
        "saved_trends": saved_trends,
        "saved_benchmarks": saved_benchmarks,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ─── Sprint 7.1: Enhanced Endpoints ─────────────────────────────────────────


# ─── Advanced Scoring ──────────────────────────────────────────────────────


@router.get("/api/predictions/scores")
async def get_advanced_scores(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.scoring import advanced_scorer
    return await advanced_scorer.score_all(session)


# ─── Data Quality ──────────────────────────────────────────────────────────


@router.get("/api/predictions/data-quality")
async def get_data_quality_all(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.data_quality import data_quality_evaluator
    return await data_quality_evaluator.evaluate_all(session)


@router.get("/api/predictions/data-quality/{competitor_id}")
async def get_data_quality(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.data_quality import data_quality_evaluator
    return await data_quality_evaluator.evaluate(competitor_id, session)


# ─── Scenario Simulation ──────────────────────────────────────────────────


@router.get("/api/predictions/scenarios")
async def list_scenarios() -> list[dict[str, str]]:
    return [
        {"id": "price_war", "name": "Price War", "description": "Simulate 10-30% market price reduction"},
        {"id": "new_competitor", "name": "New Competitor", "description": "Simulate entry of a new competitor"},
        {"id": "category_expansion", "name": "Category Expansion", "description": "Simulate entering a new service category"},
        {"id": "market_decline", "name": "Market Decline", "description": "Simulate market demand decline"},
    ]


@router.post("/api/predictions/scenarios/{scenario_type}")
async def run_scenario(
    scenario_type: str,
    params: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.simulation import scenario_simulator
    return await scenario_simulator.simulate(scenario_type, params or {}, session)


# ─── Continuous Learning ──────────────────────────────────────────────────


@router.get("/api/predictions/learning/accuracy")
async def get_accuracy_report() -> dict[str, Any]:
    from app.services.predictions.learning import continuous_learner
    return await continuous_learner.get_accuracy_stats()


@router.get("/api/predictions/learning/drift")
async def get_confidence_drift() -> dict[str, Any]:
    from app.services.predictions.learning import continuous_learner
    should = await continuous_learner.should_recalibrate()
    summary = await continuous_learner.get_learning_summary()
    return {"should_recalibrate": should, **summary}


@router.get("/api/predictions/learning/features")
async def get_feature_effectiveness() -> dict[str, Any]:
    from app.services.predictions.learning import continuous_learner
    return await continuous_learner.get_learning_summary()


@router.get("/api/predictions/learning/models")
async def get_model_versions() -> list[dict[str, Any]]:
    from app.services.predictions.learning import continuous_learner
    summary = await continuous_learner.get_learning_summary()
    return [{"type": k, "adjustment": v} for k, v in summary.get("weight_adjustments", {}).items()]


# ─── Enhanced Growth with Confidence ──────────────────────────────────────


@router.get("/api/predictions/growth/{competitor_id}/confidence")
async def get_growth_with_confidence(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.growth import growth_forecaster
    from app.services.predictions.explanations import explanation_engine

    result = await growth_forecaster.forecast(competitor_id, session)
    if not result:
        raise HTTPException(status_code=404, detail="Competitor not found")

    explanation = await explanation_engine.explain_forecast(competitor_id, "services", session)

    result["explanation"] = explanation
    return result


# ─── Enhanced Risks with Explanation ──────────────────────────────────────


@router.get("/api/predictions/risks/{competitor_id}/explained")
async def get_risks_explained(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.risks import risk_analyzer
    from app.services.predictions.explanations import explanation_engine

    risks = await risk_analyzer.analyze(competitor_id, session)
    for risk in risks:
        risk["explanation"] = await explanation_engine.explain_recommendation_async(risk, session)
    return risks


# ─── Enhanced Opportunities with Explanation ─────────────────────────────


@router.get("/api/predictions/opportunities/explained")
async def get_opportunities_explained(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.opportunities import opportunity_detector
    from app.services.predictions.explanations import explanation_engine

    opps = await opportunity_detector.detect(session)
    for opp in opps:
        opp["explanation"] = await explanation_engine.explain_recommendation_async(opp, session)
    return opps


# ─── Enhanced Recommendations with Explanation ───────────────────────────


@router.get("/api/predictions/recommendations/explained")
async def get_recommendations_explained(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.recommendations import recommendation_engine
    from app.services.predictions.explanations import explanation_engine

    recs = await recommendation_engine.generate_all(session)
    for rec in recs:
        rec["explanation"] = await explanation_engine.explain_recommendation_async(rec, session)
    return recs


# ─── Enhanced Benchmarks with Explanation ─────────────────────────────────


@router.get("/api/predictions/benchmarks/explained")
async def get_benchmarks_explained(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.predictions.benchmarking import predictive_benchmarker
    from app.services.predictions.explanations import explanation_engine

    benchmarks = await predictive_benchmarker.benchmark_all(session)
    for b in benchmarks:
        b["explanation"] = await explanation_engine.explain_recommendation_async(b, session)
    return benchmarks


# ─── Full Enhanced Report ──────────────────────────────────────────────────


@router.get("/api/predictions/report/enhanced")
async def get_enhanced_report(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.predictions.reports import forecast_report_generator
    from app.services.predictions.data_quality import data_quality_evaluator
    from app.services.predictions.learning import continuous_learner

    report = await forecast_report_generator.generate(session)

    quality = await data_quality_evaluator.evaluate_all(session)
    report["data_quality"] = quality
    report["learning"] = {
        "accuracy_report": await continuous_learner.get_accuracy_stats(),
        "should_recalibrate": await continuous_learner.should_recalibrate(),
    }

    return report


# ─── Competitor Service & Pricing Predictions Module ────────────────────────


@router.get("/api/predictions/competitors")
async def get_competitor_service_pricing_predictions(
    service: str | None = None,
    competitor: str | None = None,
    prediction_horizon: int = 90,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Predict competitor service adoption, price trajectories, uncertainty ranges, and gap vs Utservio."""
    from app.services.ml.predictive_pricing_service import predictive_pricing_engine
    from dataclasses import asdict

    prediction_horizon = min(max(prediction_horizon, 7), 365)
    raw_preds = await predictive_pricing_engine.predict_all_competitor_services(
        session=session,
        horizon_days=prediction_horizon,
        target_service=service,
        target_competitor=competitor,
    )

    return [asdict(p) for p in raw_preds]
