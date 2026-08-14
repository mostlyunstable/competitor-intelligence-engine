"""API Endpoints for Pure Database-Driven ML Predictions, Persistence, & Feedback Loops."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.services.ml.db_predictive_engine import db_predictive_engine

router = APIRouter(prefix="/api/ml/db-predictions", tags=["DB Predictive Intelligence"])


@router.get("", response_model=dict[str, Any])
async def get_database_predictions(
    prediction_horizon: int = Query(90, alias="prediction_horizon", description="Prediction horizon in days (30, 60, 90, 180, 365)"),
    competitor_id: int | None = Query(None, description="Optional competitor ID filter"),
    canonical_service_id: int | None = Query(None, description="Optional canonical service ID filter"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Generate and return database-driven predictions from historical DB observations."""
    predictions = await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=prediction_horizon,
        competitor_id=competitor_id,
        canonical_service_id=canonical_service_id,
    )

    preds_data = [asdict(p) for p in predictions]

    return {
        "source": "database_historical_observations",
        "horizon_days": prediction_horizon,
        "total_predictions": len(preds_data),
        "predictions": preds_data,
    }


@router.post("/generate", response_model=dict[str, Any])
async def generate_and_persist_db_predictions(
    prediction_horizon: int = Query(90, description="Prediction horizon in days"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Trigger feature extraction from DB, run ML predictions, and persist to ml_predictions table."""
    predictions = await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=prediction_horizon,
    )

    return {
        "status": "success",
        "message": f"Generated and persisted {len(predictions)} predictions to database table 'ml_predictions'.",
        "horizon_days": prediction_horizon,
        "total_persisted": len(predictions),
    }


@router.get("/feedback", response_model=dict[str, Any])
async def evaluate_prediction_feedback_loop(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Continuous Feedback Loop: Compares actual collected DB observations vs stored predictions."""
    feedback_result = await db_predictive_engine.evaluate_feedback_loop(session=session)
    return feedback_result
