"""Unit tests for Sprint 7.1: Enhanced Predictive Intelligence."""

import math

import pytest

from app.services.predictions.analytics import (
    clamp, linear_trend, direction_from_slope, moving_average,
    weighted_moving_average, volatility, momentum, growth_rate,
    trend_stability, seasonality_strength, prediction_interval,
    forecast_next, percentile, z_score, horizon_days,
)
from app.services.predictions.confidence import ConfidenceEngine
from app.services.predictions.explanations import ExplanationGenerator
from app.services.predictions.scoring import AdvancedScorer
from app.services.predictions.simulation import ScenarioSimulator
from app.services.predictions.data_quality import DataQualityEvaluator
from app.services.predictions.learning import ContinuousLearningFramework


# ─── Analytics Tests ────────────────────────────────────────────────────────


class TestClamp:
    def test_within_range(self):
        assert clamp(0.5) == 0.5

    def test_below(self):
        assert clamp(-1) == 0.0

    def test_above(self):
        assert clamp(2) == 1.0

    def test_custom(self):
        assert clamp(15, 10, 20) == 15
        assert clamp(5, 10, 20) == 10


class TestMovingAverage:
    def test_empty(self):
        assert moving_average([]) == []

    def test_single(self):
        assert moving_average([5.0]) == [5.0]

    def test_window_3(self):
        result = moving_average([1, 2, 3, 4, 5], window=3)
        assert len(result) == 5
        assert result[0] == 1.0
        assert result[2] == pytest.approx(2.0)
        assert result[4] == pytest.approx(4.0)


class TestWeightedMA:
    def test_empty(self):
        assert weighted_moving_average([]) == 0.0

    def test_single(self):
        assert weighted_moving_average([5.0]) == 5.0

    def test_converges_to_recent(self):
        values = [1.0] * 10 + [10.0] * 5
        result = weighted_moving_average(values, window=5)
        assert result > 5.0


class TestVolatility:
    def test_empty(self):
        assert volatility([]) == 0.0

    def test_single(self):
        assert volatility([5.0]) == 0.0

    def test_stable(self):
        assert volatility([5.0, 5.0, 5.0]) == 0.0

    def test_volatile(self):
        v = volatility([1.0, 10.0, 1.0, 10.0])
        assert v > 0.5


class TestMomentum:
    def test_empty(self):
        assert momentum([]) == 0.0

    def test_two_values(self):
        assert momentum([1.0, 2.0]) == 0.0

    def test_accelerating(self):
        m = momentum([1.0, 2.0, 4.0, 7.0])
        assert m > 0

    def test_decelerating(self):
        m = momentum([7.0, 4.0, 2.0, 1.0])
        assert m < 0


class TestGrowthRate:
    def test_empty(self):
        assert growth_rate([]) == 0.0

    def test_single(self):
        assert growth_rate([5.0]) == 0.0

    def test_positive(self):
        # (121/100)^(1/1) - 1 = 0.21
        assert growth_rate([100, 121]) == pytest.approx(0.21)

    def test_zero_start(self):
        assert growth_rate([0, 10]) == 0.0


class TestTrendStability:
    def test_empty(self):
        assert trend_stability([]) == 1.0

    def test_stable(self):
        assert trend_stability([5.0, 5.0, 5.0]) == 1.0

    def test_unstable(self):
        assert trend_stability([1.0, 10.0, 1.0, 10.0]) < 0.5


class TestSeasonality:
    def test_too_few(self):
        assert seasonality_strength([1, 2, 3]) == 0.0

    def test_seasonal(self):
        values = [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]
        s = seasonality_strength(values, period=4)
        assert s > 0.5


class TestPredictionInterval:
    def test_empty(self):
        lo, hi = prediction_interval([])
        assert lo == 0.0 and hi == 0.0

    def test_single(self):
        lo, hi = prediction_interval([5.0])
        assert lo == 5.0 and hi == 5.0

    def test_widens_with_variance(self):
        lo1, hi1 = prediction_interval([1, 1, 1])
        lo2, hi2 = prediction_interval([1, 5, 10])
        assert (hi2 - lo2) > (hi1 - lo1)


class TestForecastNext:
    def test_empty(self):
        assert forecast_next([], steps=3) == [0.0, 0.0, 0.0]

    def test_linear(self):
        result = forecast_next([1, 2, 3, 4], steps=2)
        assert result[0] == pytest.approx(5.0)
        assert result[1] == pytest.approx(6.0)


class TestPercentile:
    def test_empty(self):
        assert percentile([], 50) == 0.0

    def test_median(self):
        assert percentile([1, 2, 3, 4, 5], 50) == 3.0

    def test_90th(self):
        assert percentile([1, 2, 3, 4, 5], 90) >= 4.0


class TestZScore:
    def test_empty(self):
        assert z_score(5, []) == 0.0

    def test_at_mean(self):
        assert z_score(5, [5, 5, 5]) == 0.0

    def test_above_mean(self):
        assert z_score(10, [1, 2, 3, 4, 5]) > 0


class TestHorizonDays:
    def test_7d(self):
        assert horizon_days("7d") == 7

    def test_30d(self):
        assert horizon_days("30days") == 30

    def test_90d(self):
        assert horizon_days("3months") == 90

    def test_1y(self):
        assert horizon_days("1year") == 365

    def test_unknown(self):
        assert horizon_days("unknown") == 30


# ─── Confidence Engine Tests ────────────────────────────────────────────────


class TestConfidenceEngine:
    def test_instance(self):
        engine = ConfidenceEngine()
        assert engine is not None

    def test_high_quality(self):
        engine = ConfidenceEngine()
        result = engine.calculate(
            data_points=20, data_age_days=1, completeness=1.0,
            historical_accuracy=0.9, trend_consistency=0.9,
        )
        assert result["confidence_score"] >= 0.7
        assert result["reliability_level"] == "high"

    def test_low_quality(self):
        engine = ConfidenceEngine()
        result = engine.calculate(
            data_points=1, data_age_days=90, completeness=0.1,
            historical_accuracy=0.1, trend_consistency=0.1,
            market_volatility=0.8, source_reliability=0.1,
        )
        assert result["confidence_score"] < 0.4
        assert result["reliability_level"] == "low"

    def test_batch(self):
        engine = ConfidenceEngine()
        preds = [
            {"confidence_score": 0.5, "metrics": {"successful_collections": 5}},
            {"confidence_score": 0.3, "metrics": {}},
        ]
        result = engine.calculate_batch(preds)
        assert len(result) == 2
        assert "confidence" in result[0]


# ─── Explanation Generator Tests ────────────────────────────────────────────


class TestExplanationGenerator:
    def test_growth_explanation(self):
        gen = ExplanationGenerator()
        result = gen.explain_growth(
            {"growth_level": "high", "growth_score": 75},
            {"services_last_30": 10, "pricing_last_30": 5, "content_last_30": 8, "changes_last_30": 12, "successful_collections": 10},
        )
        assert "why" in result
        assert "evidence" in result
        assert "feature_importance" in result
        assert "data_sources" in result

    def test_risk_explanation(self):
        gen = ExplanationGenerator()
        result = gen.explain_risk({"risk_type": "price_war", "risk_level": "high", "risk_score": 70, "likelihood": 0.8})
        assert "why" in result
        assert "price_war" in result["why"].lower() or "price" in result["why"].lower()

    def test_opportunity_explanation(self):
        gen = ExplanationGenerator()
        result = gen.explain_opportunity({"opportunity_type": "pricing_gap", "opportunity_score": 75, "description": "Test"})
        assert "why" in result

    def test_recommendation_explanation(self):
        gen = ExplanationGenerator()
        result = gen.explain_recommendation({"why": "test", "recommendation": "do X", "expected_benefit": "Y"})
        assert result["why"] == "test"

    def test_benchmark_explanation(self):
        gen = ExplanationGenerator()
        result = gen.explain_benchmark({"current_rank": 3, "predicted_rank": 2, "overall_prediction": "high_growth", "growth_score": 70, "innovation_score": 60, "expansion_score": 50})
        assert "improving" in result["why"]


# ─── Scenario Simulator Tests ───────────────────────────────────────────────


class TestScenarioSimulator:
    def test_available_scenarios(self):
        sim = ScenarioSimulator()
        scenarios = sim.available_scenarios()
        assert len(scenarios) == 5
        types = [s["type"] for s in scenarios]
        assert "competitor_price_cut" in types

    def test_price_cut_simulation(self):
        import asyncio
        sim = ScenarioSimulator()
        result = asyncio.run(sim.simulate("competitor_price_cut", params={"cut_percentage": 0.25}))
        assert result["scenario"] == "competitor_price_cut"
        assert "business_impact" in result
        assert "risk_analysis" in result
        assert "recommended_strategy" in result

    def test_unknown_scenario(self):
        import asyncio
        sim = ScenarioSimulator()
        result = asyncio.run(sim.simulate("nonexistent"))
        assert "error" in result


# ─── Continuous Learning Tests ──────────────────────────────────────────────


class TestContinuousLearning:
    def test_log_prediction(self):
        framework = ContinuousLearningFramework()
        framework.log_prediction("growth", 1, {"growth_score": 75}, 0.8)
        assert len(framework._prediction_log) == 1

    def test_record_outcome(self):
        framework = ContinuousLearningFramework()
        framework.log_prediction("growth", 1, {"growth_score": 75}, 0.8)
        result = framework.record_outcome("growth", 1, 70)
        assert result is not None
        assert result["accuracy"] is not None

    def test_accuracy_report_empty(self):
        framework = ContinuousLearningFramework()
        report = framework.get_accuracy_report()
        assert report["total_predictions"] == 0

    def test_accuracy_report_with_data(self):
        framework = ContinuousLearningFramework()
        framework.log_prediction("growth", 1, {"growth_score": 75}, 0.8)
        framework.record_outcome("growth", 1, 70)
        report = framework.get_accuracy_report()
        assert report["recorded_outcomes"] == 1
        assert report["average_accuracy"] > 0

    def test_confidence_drift_insufficient(self):
        framework = ContinuousLearningFramework()
        drift = framework.get_confidence_drift()
        assert drift["drift"] == "insufficient_data"

    def test_model_versions(self):
        framework = ContinuousLearningFramework()
        versions = framework.get_model_versions()
        assert len(versions) == 1
        assert versions[0]["version"] == "heuristic_v1"

    def test_feature_effectiveness(self):
        framework = ContinuousLearningFramework()
        features = framework.get_feature_effectiveness()
        assert len(features["features"]) == 5


# ─── Industry Benchmarker Tests ─────────────────────────────────────────────


# ─── Advanced Scorer Tests ──────────────────────────────────────────────────


class TestAdvancedScorer:
    def test_instance(self):
        scorer = AdvancedScorer()
        assert scorer is not None

    def test_grade(self):
        scorer = AdvancedScorer()
        # Absolute fallback (no all_scores): A>=65, B>=50, C>=35, D>=20, F<20
        assert scorer._grade(85) == "A"
        assert scorer._grade(70) == "A"
        assert scorer._grade(55) == "B"
        assert scorer._grade(40) == "C"
        assert scorer._grade(20) == "D"

        # Relative grading with all_scores
        scores = [80.0, 60.0, 40.0, 20.0, 10.0]
        assert scorer._grade(80.0, scores) == "A"
        assert scorer._grade(60.0, scores) == "B"
        assert scorer._grade(40.0, scores) == "C"
        assert scorer._grade(20.0, scores) == "D"
        assert scorer._grade(10.0, scores) == "F"


# ─── Data Quality Evaluator Tests ──────────────────────────────────────────


class TestDataQualityEvaluator:
    def test_instance(self):
        evaluator = DataQualityEvaluator()
        assert evaluator is not None

    def test_completeness_score(self):
        evaluator = DataQualityEvaluator()
        assert evaluator._score_completeness(5, 5, 3, 2) == 1.0
        assert evaluator._score_completeness(0, 0, 0, 0) < 0.1

    def test_freshness_score(self):
        from datetime import UTC, datetime, timedelta
        evaluator = DataQualityEvaluator()
        now = datetime.now(UTC)
        assert evaluator._score_freshness(now, now) == 1.0
        assert evaluator._score_freshness(now - timedelta(days=100), now) < 0.2
        assert evaluator._score_freshness(None, now) == 0.0
