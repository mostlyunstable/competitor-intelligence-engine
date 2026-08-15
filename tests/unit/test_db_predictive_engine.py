"""Unit tests for Pure Database-Driven ML Prediction Engine, Persistence, and Feedback Loop."""

import pytest
from app.services.ml.db_predictive_engine import db_predictive_engine
from app.database.models import MLPredictionRecord, PriceObservation


@pytest.mark.asyncio
async def test_db_predictive_engine_generation_and_persistence(session):
    """Verify that predictions are engineered from DB tables and persisted into ml_predictions."""
    results = await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=90,
    )

    assert len(results) > 0
    first = results[0]

    # Verify structured fields
    assert first.competitor != ""
    assert first.service != ""
    assert first.utservio_current_price > 0
    assert first.prediction_horizon_days == 90
    assert first.model_version == "v2.0-db"
    assert first.training_data_size > 0
    assert 0.0 <= first.confidence_score <= 1.0
    assert len(first.contributing_factors) >= 3


@pytest.mark.asyncio
async def test_db_predictive_engine_horizon_sensitivity(session):
    """Verify that longer prediction horizons increase price uncertainty interval."""
    # First generate predictions once to ensure defaults are populated
    await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=30,
    )
    from app.database.models import CanonicalService
    from sqlalchemy import select
    res = await session.execute(select(CanonicalService))
    services = res.scalars().all()
    assert len(services) > 0
    service_id = services[0].id

    short_horizon = await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=30,
        canonical_service_id=service_id,
    )
    long_horizon = await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=180,
        canonical_service_id=service_id,
    )

    assert len(short_horizon) > 0
    assert len(long_horizon) > 0

    short_range = short_horizon[0].upper_bound - short_horizon[0].lower_bound
    long_range = long_horizon[0].upper_bound - long_horizon[0].lower_bound

    assert long_range > short_range


@pytest.mark.asyncio
async def test_db_predictive_engine_feedback_loop(session):
    """Verify continuous feedback loop evaluation comparing DB observations vs stored predictions."""
    # First generate predictions to seed ml_predictions table
    await db_predictive_engine.generate_and_persist_predictions(
        session=session,
        prediction_horizon_days=30,
    )

    feedback_res = await db_predictive_engine.evaluate_feedback_loop(session=session)

    assert "mean_absolute_percentage_error" in feedback_res
    assert "accuracy_score" in feedback_res
    assert feedback_res["accuracy_score"] >= 0.0
