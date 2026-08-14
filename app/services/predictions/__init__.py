"""Sprint 7.1: Enhanced Predictive Intelligence Engine."""

from app.services.predictions.engine import prediction_engine
from app.services.predictions.trends import trend_analyzer
from app.services.predictions.expansion import expansion_forecaster
from app.services.predictions.growth import growth_forecaster
from app.services.predictions.risks import risk_analyzer
from app.services.predictions.opportunities import opportunity_detector
from app.services.predictions.recommendations import recommendation_engine
from app.services.predictions.benchmarking import predictive_benchmarker
from app.services.predictions.reports import forecast_report_generator
from app.services.predictions.analytics import (
    clamp, linear_trend, direction_from_slope, moving_average,
    weighted_moving_average, volatility, momentum, growth_rate,
    trend_stability, seasonality_strength, prediction_interval,
    forecast_next, percentile, z_score, horizon_days,
)
from app.services.predictions.confidence import confidence_engine
from app.services.predictions.explanations import explanation_engine
from app.services.predictions.scoring import advanced_scorer
from app.services.predictions.simulation import scenario_simulator
from app.services.predictions.data_quality import data_quality_evaluator
from app.services.predictions.learning import continuous_learner
from app.services.predictions.industry_benchmarking import industry_benchmarker

__all__ = [
    "prediction_engine",
    "trend_analyzer",
    "expansion_forecaster",
    "growth_forecaster",
    "risk_analyzer",
    "opportunity_detector",
    "recommendation_engine",
    "predictive_benchmarker",
    "forecast_report_generator",
    "confidence_engine",
    "explanation_engine",
    "advanced_scorer",
    "scenario_simulator",
    "data_quality_evaluator",
    "continuous_learner",
    "industry_benchmarker",
]
