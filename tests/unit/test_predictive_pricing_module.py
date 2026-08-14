"""Unit tests for ML Predictive Pricing and Service Intelligence module."""

import pytest
from app.services.ml.predictive_pricing_service import (
    PredictivePricingEngine,
    predictive_pricing_engine,
    UTSERVIO_CATALOG_BASELINE,
)


@pytest.mark.asyncio
async def test_predictive_pricing_engine_structure(session):
    """Verify that predictive pricing engine generates structured predictions with Utservio baseline."""
    preds = await predictive_pricing_engine.predict_all_competitor_services(
        session=session,
        horizon_days=90,
    )

    assert len(preds) > 0
    first = preds[0]

    # Verify fields match PRD requirements
    assert first.service != ""
    assert first.utservio_price > 0
    assert first.competitor != ""
    assert first.current_competitor_price > 0
    assert first.predicted_service in ("Likely", "Unlikely", "Uncertain")
    assert 0.0 <= first.service_probability <= 1.0
    assert first.predicted_price > 0
    assert first.price_range["lower"] <= first.predicted_price <= first.price_range["upper"]
    assert isinstance(first.price_gap_percentage, float)
    assert 0.0 <= first.confidence <= 1.0
    assert first.confidence_level in ("High", "Medium", "Low")
    assert first.horizon_days == 90
    assert first.training_observations > 0
    assert first.data_quality_score > 0
    assert len(first.contributing_factors) >= 3


@pytest.mark.asyncio
async def test_predictive_pricing_horizon_sensitivity(session):
    """Verify that longer prediction horizons increase price uncertainty ranges."""
    short_preds = await predictive_pricing_engine.predict_all_competitor_services(
        session=session,
        horizon_days=30,
        target_service="AC General Service & Cleaning",
    )
    long_preds = await predictive_pricing_engine.predict_all_competitor_services(
        session=session,
        horizon_days=180,
        target_service="AC General Service & Cleaning",
    )

    assert len(short_preds) > 0
    assert len(long_preds) > 0

    short_range = short_preds[0].price_range["upper"] - short_preds[0].price_range["lower"]
    long_range = long_preds[0].price_range["upper"] - long_preds[0].price_range["lower"]

    # 180-day forecast horizon should have wider uncertainty interval than 30-day forecast horizon
    assert long_range > short_range
