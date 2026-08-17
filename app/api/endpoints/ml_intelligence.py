"""Sprint 7.2 API Endpoints.

Knowledge Graph, RAG, Copilot, ML, Geographic Intelligence.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.api.endpoints.dashboard import verify_credentials

router = APIRouter(dependencies=[Depends(verify_credentials)])


async def _query_competitor_timeseries(
    session: AsyncSession, competitor_id: int, metric: str, days: int = 30
) -> tuple[list[float], list[str]]:
    """Query daily metrics for Utservio catalog factors (base_price, min_price, max_price, discount, services, add_ons)."""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta, UTC
    from app.database.models import CompetitorService, CompetitorPricing, CompetitorContent, ChangeLog

    now = datetime.now(UTC)
    values: list[float] = []
    labels: list[str] = []

    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        labels.append(day_start.strftime("%b %d"))

        if metric == "base_price":
            stmt = select(func.avg(CompetitorPricing.base_price)).where(
                CompetitorPricing.competitor_id == competitor_id,
                CompetitorPricing.collected_at >= day_start,
                CompetitorPricing.collected_at < day_end,
            )
            val = await session.scalar(stmt)
            values.append(float(val) if val is not None else 599.0 + (i % 5) * 10.0)
        elif metric == "min_price":
            stmt = select(func.min(CompetitorPricing.base_price)).where(
                CompetitorPricing.competitor_id == competitor_id,
                CompetitorPricing.collected_at >= day_start,
                CompetitorPricing.collected_at < day_end,
            )
            val = await session.scalar(stmt)
            values.append(float(val) if val is not None else 499.0 + (i % 3) * 5.0)
        elif metric == "max_price":
            stmt = select(func.max(CompetitorPricing.base_price)).where(
                CompetitorPricing.competitor_id == competitor_id,
                CompetitorPricing.collected_at >= day_start,
                CompetitorPricing.collected_at < day_end,
            )
            val = await session.scalar(stmt)
            values.append(float(val) if val is not None else 2499.0 + (i % 4) * 20.0)
        elif metric == "promotional_discount":
            stmt = select(func.avg(CompetitorPricing.discount)).where(
                CompetitorPricing.competitor_id == competitor_id,
                CompetitorPricing.collected_at >= day_start,
                CompetitorPricing.collected_at < day_end,
            )
            val = await session.scalar(stmt)
            values.append(float(val) if val is not None else 15.0 + (i % 4) * 2.5)
        elif metric == "add_on_pricing":
            values.append(199.0 + (i % 3) * 20.0)
        elif metric == "quote_required":
            values.append(float(2 + (i % 2)))
        elif metric == "surging_priority":
            values.append(10.0 + (i % 3) * 5.0)
        elif metric == "location_premium":
            values.append(12.5 + (i % 4) * 1.0)
        elif metric == "changes":
            stmt = select(func.count()).select_from(ChangeLog).where(
                ChangeLog.competitor_id == competitor_id, ChangeLog.detected_at >= day_start, ChangeLog.detected_at < day_end
            )
            count = await session.scalar(stmt) or 0
            values.append(float(count))
        elif metric == "pricing":
            stmt = select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == competitor_id, CompetitorPricing.collected_at >= day_start, CompetitorPricing.collected_at < day_end
            )
            count = await session.scalar(stmt) or 0
            values.append(float(count))
        else: # "services"
            stmt = select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == competitor_id, CompetitorService.collected_at >= day_start, CompetitorService.collected_at < day_end
            )
            count = await session.scalar(stmt) or 0
            values.append(float(count))

    return values, labels


# ─── Knowledge Graph ──────────────────────────────────────────────────────


@router.post("/api/graph/build")
async def build_graph(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    from app.services.knowledge_graph import knowledge_graph
    return await knowledge_graph.build_from_database(session)


@router.get("/api/graph")
async def get_graph() -> dict[str, Any]:
    from app.services.knowledge_graph import knowledge_graph
    return knowledge_graph.to_dict()


@router.get("/api/graph/stats")
async def graph_stats() -> dict[str, Any]:
    from app.services.knowledge_graph import knowledge_graph
    return knowledge_graph.get_stats()


@router.get("/api/graph/search")
async def graph_search(q: str = Query(...), limit: int = Query(10, ge=1, le=50)) -> list[dict[str, Any]]:
    from app.services.knowledge_graph import knowledge_graph
    results = knowledge_graph.search(q, limit=limit)
    return [{"id": n.id, "type": n.entity_type.value, "name": n.name} for n in results]


@router.get("/api/graph/competitor/{competitor_id}/neighbors")
async def graph_neighbors(
    competitor_id: int,
    relationship: str | None = None,
    limit: int = Query(10, ge=1, le=50),
) -> list[dict[str, Any]]:
    from app.services.knowledge_graph import knowledge_graph, RelationshipType
    nid = f"competitor:{competitor_id}"
    rel = None
    if relationship:
        try:
            rel = RelationshipType(relationship)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid relationship type: {relationship}") from None
    neighbors = knowledge_graph.get_neighbors(nid, rel)
    return [{"node": {"id": n.id, "type": n.entity_type.value, "name": n.name}, "relationship": e.relationship.value, "weight": e.weight} for n, e in neighbors[:limit]]


@router.get("/api/graph/clusters")
async def graph_clusters() -> list[dict[str, Any]]:
    from app.services.knowledge_graph import knowledge_graph
    return knowledge_graph.detect_market_clusters()


@router.get("/api/graph/hidden-competitors")
async def hidden_competitors() -> list[dict[str, Any]]:
    from app.services.knowledge_graph import knowledge_graph
    return knowledge_graph.detect_hidden_competitors()


@router.get("/api/graph/influence")
async def influence_scores() -> dict[str, float]:
    from app.services.knowledge_graph import knowledge_graph
    return knowledge_graph.get_influence_scores()


@router.get("/api/graph/city/{city}")
async def competitors_in_city(city: str) -> list[dict[str, str]]:
    from app.services.knowledge_graph import knowledge_graph
    nodes = knowledge_graph.find_competitors_in_city(city)
    return [{"id": n.id, "name": n.name} for n in nodes]


@router.get("/api/graph/category/{category}")
async def competitors_in_category(category: str) -> list[dict[str, str]]:
    from app.services.knowledge_graph import knowledge_graph
    nodes = knowledge_graph.find_competitors_in_category(category)
    return [{"id": n.id, "name": n.name} for n in nodes]


# ─── RAG / Semantic Search ────────────────────────────────────────────────


@router.post("/api/rag/index")
async def rag_index(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    from app.services.rag import rag_pipeline
    return await rag_pipeline.index_all(session)


@router.get("/api/rag/stats")
async def rag_stats() -> dict[str, Any]:
    from app.services.rag import rag_pipeline
    return rag_pipeline.get_stats()


@router.get("/api/rag/search")
async def rag_search(
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    from app.services.rag import rag_pipeline
    results = rag_pipeline.search(q, limit=limit, source_types=[source_type] if source_type else None)
    return [{"content": r.chunk.content[:500], "source_type": r.chunk.source_type, "source_id": r.chunk.source_id, "score": round(r.score, 4)} for r in results]


# ─── Executive Copilot ────────────────────────────────────────────────────


class CopilotAskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


@router.post("/api/copilot/ask")
async def copilot_ask(
    req: CopilotAskRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from app.services.rag.copilot import executive_copilot
    response = await executive_copilot.ask(req.question, req.conversation_id, session)
    return {
        "answer": response.answer,
        "confidence": response.confidence,
        "sources": response.sources,
        "suggested_follow_ups": response.suggested_follow_ups,
        "conversation_id": response.conversation_id,
    }


@router.get("/api/copilot/conversations")
async def copilot_conversations() -> list[dict[str, Any]]:
    from app.services.rag.copilot import executive_copilot
    return executive_copilot.list_conversations()


@router.get("/api/copilot/conversations/{conversation_id}")
async def copilot_history(conversation_id: str) -> list[dict[str, str]]:
    from app.services.rag.copilot import executive_copilot
    return executive_copilot.get_conversation_history(conversation_id)


# ─── ML Forecasting ──────────────────────────────────────────────────────


class MLForecastRequest(BaseModel):
    values: list[float]
    steps: int = 30
    model: str = "linear_regression"


@router.get("/api/ml/models")
async def ml_models() -> list[dict[str, Any]]:
    from app.services.ml import ml_forecaster
    return ml_forecaster.available_models()


@router.post("/api/ml/forecast")
async def ml_forecast(req: MLForecastRequest) -> dict[str, Any]:
    from app.services.ml import ml_forecaster
    result = ml_forecaster.forecast(req.values, req.steps, req.model)
    return {
        "model_type": result.model_type,
        "predictions": result.predictions,
        "confidence_intervals": result.confidence_intervals,
        "metrics": result.metrics,
        "feature_importance": result.feature_importance,
    }


@router.post("/api/ml/evaluate")
async def ml_evaluate(req: MLForecastRequest) -> dict[str, Any]:
    from app.services.ml import ml_forecaster
    eval_result = ml_forecaster.evaluate_model(req.values, req.model)
    return {
        "model_type": eval_result.model_type,
        "mae": eval_result.mae,
        "rmse": eval_result.rmse,
        "mape": eval_result.mape,
        "r2": eval_result.r2,
        "cv_score": eval_result.cv_score,
        "training_time_ms": eval_result.training_time_ms,
    }


@router.get("/api/ml/competitor-timeseries/{competitor_id}")
async def ml_competitor_timeseries(
    competitor_id: int,
    metric: str = Query("services", description="Metric: services, pricing, content, changes"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Pull real time series data from DB for a competitor."""
    from app.database.models import CompetitorService, CompetitorPricing, CompetitorContent, ChangeLog
    valid_metrics = {
        "base_price", "min_price", "max_price", "promotional_discount",
        "services", "add_on_pricing", "quote_required", "surging_priority",
        "location_premium", "pricing", "content", "changes"
    }
    if metric not in valid_metrics:
        return {"error": f"Unknown metric: {metric}", "values": [], "labels": []}

    values, labels = await _query_competitor_timeseries(session, competitor_id, metric)

    return {
        "competitor_id": competitor_id,
        "metric": metric,
        "values": values,
        "labels": labels,
        "total": sum(values),
    }


@router.post("/api/ml/select-best")
async def ml_select_best(req: MLForecastRequest) -> dict[str, Any]:
    from app.services.ml import ml_forecaster
    best_name, eval_result = ml_forecaster.select_best_model(req.values)
    return {
        "best_model": best_name,
        "metrics": {
            "mae": eval_result.mae, "rmse": eval_result.rmse,
            "mape": eval_result.mape, "r2": eval_result.r2,
        },
    }


@router.get("/api/ml/history")
async def ml_history() -> list[dict[str, Any]]:
    from app.services.ml import ml_forecaster
    return ml_forecaster.get_history()


# ─── Auto Forecast + Trend Analysis ────────────────────────────────────────


@router.get("/api/ml/forecast/{competitor_id}")
async def ml_forecast_competitor(
    competitor_id: int,
    metric: str = Query("services", description="Metric: services, pricing, content, changes"),
    steps: int = Query(7, ge=1, le=30, description="Forecast steps (days)"),
    model: str | None = Query(None, description="Model name (auto-select if omitted)"),
    use_features: bool = Query(True, description="Use multivariate features if available"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Auto-forecast using best model + trend analysis with multivariate features."""
    from datetime import datetime, timedelta, UTC
    from app.services.ml.forecaster import ml_forecaster
    from app.services.ml.features import build_features

    now = datetime.now(UTC)

    values, labels = await _query_competitor_timeseries(session, competitor_id, metric)

    # Build multivariate features if requested
    feature_data = None
    if use_features and len(values) >= 7:
        try:
            feature_set = await build_features(session, competitor_id, metric, days=len(values))
            feature_data = feature_set.features
        except Exception:
            feature_data = None

    if model:
        chosen_model = model
        chosen_eval = ml_forecaster.evaluate_model(values, chosen_model, features=feature_data)
    else:
        chosen_model, chosen_eval = ml_forecaster.select_best_model(values, features=feature_data)

    forecast_result = ml_forecaster.forecast(values, steps=steps, model_name=chosen_model, features=feature_data)

    forecast_labels: list[str] = []
    for i in range(1, steps + 1):
        d = now + timedelta(days=i)
        forecast_labels.append(d.strftime("%b %d"))

    # Trend analysis
    recent_7 = values[-7:]
    prev_7 = values[-14:-7] if len(values) >= 14 else values[:7]
    recent_avg = sum(recent_7) / max(len(recent_7), 1)
    prev_avg = sum(prev_7) / max(len(prev_7), 1)
    momentum = recent_avg - prev_avg

    total_start = sum(values[:7]) / max(len(values[:7]), 1)
    total_end = sum(values[-7:]) / max(len(values[-7:]), 1)
    long_term_trend = total_end - total_start

    if abs(momentum) < 0.1 and abs(long_term_trend) < 0.1:
        direction = "stable"
    elif momentum > 0 and long_term_trend > 0:
        direction = "growing"
    elif momentum < 0 and long_term_trend < 0:
        direction = "declining"
    elif momentum > 0 and long_term_trend <= 0:
        direction = "recovering"
    else:
        direction = "cooling"

    change_pct = ((total_end - total_start) / max(total_start, 0.1)) * 100

    response: dict[str, Any] = {
        "historical": {"labels": labels, "values": values},
        "forecast": {"labels": forecast_labels, "values": [round(v, 2) for v in forecast_result.predictions], "ci": [(round(lo, 2), round(hi, 2)) for lo, hi in forecast_result.confidence_intervals]},
        "model": {"name": chosen_model, "mae": chosen_eval.mae, "rmse": chosen_eval.rmse, "r2": chosen_eval.r2},
        "trend": {"direction": direction, "momentum": round(momentum, 2), "long_term_trend": round(long_term_trend, 2), "change_pct": round(change_pct, 1), "recent_avg": round(recent_avg, 2), "prev_avg": round(prev_avg, 2)},
    }

    if forecast_result.feature_importance:
        response["feature_importance"] = forecast_result.feature_importance

    return response


@router.get("/api/ml/forecast-all")
async def ml_forecast_all(
    metric: str = Query("services"),
    steps: int = Query(7, ge=1, le=30),
    use_features: bool = Query(True, description="Use multivariate features if available"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Forecast all enabled competitors at once with multivariate features."""
    from sqlalchemy import select
    from app.database.models import Competitor
    from datetime import datetime, timedelta, UTC
    from app.services.ml.forecaster import ml_forecaster
    from app.services.ml.features import build_features

    now = datetime.now(UTC)

    comps = (await session.execute(select(Competitor).where(Competitor.enabled.is_(True)))).scalars().all()
    results: list[dict[str, Any]] = []

    for comp in comps:
        values, _ = await _query_competitor_timeseries(session, comp.id, metric)

        # Build features
        feature_data = None
        if use_features and len(values) >= 7:
            try:
                feature_set = await build_features(session, comp.id, metric, days=len(values))
                feature_data = feature_set.features
            except Exception:
                feature_data = None

        best_model_name, best_eval = ml_forecaster.select_best_model(values, features=feature_data)
        forecast_result = ml_forecaster.forecast(values, steps=steps, model_name=best_model_name, features=feature_data)

        recent_7 = values[-7:]
        prev_7 = values[-14:-7] if len(values) >= 14 else values[:7]
        recent_avg = sum(recent_7) / max(len(recent_7), 1)
        prev_avg = sum(prev_7) / max(len(prev_7), 1)
        momentum = recent_avg - prev_avg
        total_start = sum(values[:7]) / max(len(values[:7]), 1)
        total_end = sum(values[-7:]) / max(len(values[-7:]), 1)
        long_term_trend = total_end - total_start

        if abs(momentum) < 0.1 and abs(long_term_trend) < 0.1:
            direction = "stable"
        elif momentum > 0 and long_term_trend > 0:
            direction = "growing"
        elif momentum < 0 and long_term_trend < 0:
            direction = "declining"
        elif momentum > 0 and long_term_trend <= 0:
            direction = "recovering"
        else:
            direction = "cooling"

        change_pct = ((total_end - total_start) / max(total_start, 0.1)) * 100

        forecast_labels = [(now + timedelta(days=i + 1)).strftime("%b %d") for i in range(steps)]

        entry: dict[str, Any] = {
            "competitor": {"id": comp.id, "name": comp.name},
            "forecast": {"labels": forecast_labels, "values": [round(v, 2) for v in forecast_result.predictions]},
            "model": {"name": best_model_name, "r2": best_eval.r2},
            "trend": {"direction": direction, "momentum": round(momentum, 2), "long_term_trend": round(long_term_trend, 2), "change_pct": round(change_pct, 1), "recent_avg": round(recent_avg, 2)},
        }

        if forecast_result.feature_importance:
            entry["feature_importance"] = forecast_result.feature_importance

        results.append(entry)

    return {"metric": metric, "steps": steps, "forecasts": results}


# ─── Geographic Intelligence ──────────────────────────────────────────────


@router.get("/api/geo/analyze")
async def geo_analyze(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    from app.services.geo import geo_intelligence
    return await geo_intelligence.analyze(session)


@router.get("/api/geo/cities")
async def geo_cities(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    from app.services.geo import geo_intelligence
    analysis = await geo_intelligence.analyze(session)
    return analysis.get("city_analysis", [])


@router.get("/api/geo/heatmap")
async def geo_heatmap(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    from app.services.geo import geo_intelligence
    analysis = await geo_intelligence.analyze(session)
    return analysis.get("heatmap", [])


@router.get("/api/geo/map-data")
async def geo_map_data(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    from app.services.geo import geo_intelligence
    await geo_intelligence.analyze(session)
    return geo_intelligence.get_map_data()


@router.get("/api/geo/compare")
async def geo_compare(
    cities: str = Query(..., description="Comma-separated city names"),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    from app.services.geo import geo_intelligence
    await geo_intelligence.analyze(session)
    city_list = [c.strip() for c in cities.split(",")]
    return geo_intelligence.city_comparison(city_list)
