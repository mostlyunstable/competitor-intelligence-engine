"""Unit tests for Sprint 7 Predictive Analytics modules."""

import math
import pytest

from app.analytics.time_series import PriceForecaster, ForecastResult
from app.analytics.growth_model import GrowthAnalyzer, GrowthMetrics
from app.analytics.expansion_predictor import RegionalExpansionPredictor, ExpansionOpportunity
from app.analytics.confidence import ConfidenceScorer, ConfidenceResult


# ─── PriceForecaster Tests ────────────────────────────────────────────────


class TestPriceForecaster:
    def test_init(self):
        f = PriceForecaster()
        assert f is not None

    def test_linear_trend_empty(self):
        f = PriceForecaster()
        result = f.linear_trend_forecast([], steps=5)
        assert len(result.predictions) == 5
        assert all(p == 0.0 for p in result.predictions)
        assert result.model_name == "linear_trend"

    def test_linear_trend_single_value(self):
        f = PriceForecaster()
        result = f.linear_trend_forecast([5.0], steps=3)
        assert len(result.predictions) == 3
        assert all(p == 5.0 for p in result.predictions)

    def test_linear_trend_increasing(self):
        f = PriceForecaster()
        result = f.linear_trend_forecast([1.0, 2.0, 3.0, 4.0, 5.0], steps=3)
        assert len(result.predictions) == 3
        assert result.predictions[0] > 5.0
        assert result.metrics["slope"] > 0

    def test_linear_trend_decreasing(self):
        f = PriceForecaster()
        result = f.linear_trend_forecast([5.0, 4.0, 3.0, 2.0, 1.0], steps=3)
        assert result.predictions[0] < 1.0
        assert result.metrics["slope"] < 0

    def test_linear_trend_ci_widens(self):
        f = PriceForecaster()
        # Use noisy data so std > 0
        result = f.linear_trend_forecast([1.0, 2.5, 2.8, 4.2, 5.1], steps=5)
        ci = result.confidence_intervals
        # CI should widen with forecast horizon
        width_1 = ci[0][1] - ci[0][0]
        width_5 = ci[4][1] - ci[4][0]
        assert width_5 > width_1

    def test_linear_trend_r2(self):
        f = PriceForecaster()
        result = f.linear_trend_forecast([1.0, 2.0, 3.0, 4.0, 5.0], steps=3)
        assert 0.0 <= result.metrics["r2"] <= 1.0
        assert result.metrics["r2"] == pytest.approx(1.0, abs=0.01)

    def test_exp_smoothing_empty(self):
        f = PriceForecaster()
        result = f.exponential_smoothing_forecast([], steps=3)
        assert len(result.predictions) == 3
        assert all(p == 0.0 for p in result.predictions)

    def test_exp_smoothing_single(self):
        f = PriceForecaster()
        result = f.exponential_smoothing_forecast([5.0], steps=3)
        assert len(result.predictions) == 3

    def test_exp_smoothing_increasing(self):
        f = PriceForecaster()
        result = f.exponential_smoothing_forecast([1.0, 2.0, 3.0, 4.0, 5.0], steps=3)
        assert result.predictions[0] > 3.0

    def test_exp_smoothing_non_negative(self):
        f = PriceForecaster()
        result = f.exponential_smoothing_forecast([5.0, 4.0, 3.0, 2.0, 1.0], steps=5)
        assert all(p >= 0.0 for p in result.predictions)

    def test_forecast_linear_trend(self):
        f = PriceForecaster()
        result = f.forecast([1.0, 2.0, 3.0], steps=2, model="linear_trend")
        assert result.model_name == "linear_trend"

    def test_forecast_exp_smoothing(self):
        f = PriceForecaster()
        result = f.forecast([1.0, 2.0, 3.0], steps=2, model="exp_smoothing")
        assert result.model_name == "exp_smoothing"

    def test_forecast_unknown_model_defaults(self):
        f = PriceForecaster()
        result = f.forecast([1.0, 2.0, 3.0], steps=2, model="unknown")
        assert result.model_name == "linear_trend"


# ─── GrowthAnalyzer Tests ─────────────────────────────────────────────────


class TestGrowthAnalyzer:
    def test_init(self):
        a = GrowthAnalyzer()
        assert a is not None

    def test_analyze_empty(self):
        a = GrowthAnalyzer()
        result = a.analyze([], [], [])
        assert result.overall_growth_score == 0.0
        assert result.growth_direction == "stable"

    def test_analyze_growing(self):
        a = GrowthAnalyzer()
        services = list(range(1, 31))
        pricing = list(range(1, 31))
        content = list(range(1, 31))
        result = a.analyze(services, pricing, content)
        assert result.growth_direction == "growing"
        assert result.overall_growth_score > 0

    def test_analyze_declining(self):
        a = GrowthAnalyzer()
        services = list(range(30, 0, -1))
        pricing = list(range(30, 0, -1))
        content = list(range(30, 0, -1))
        result = a.analyze(services, pricing, content)
        assert result.growth_direction == "declining"
        assert result.overall_growth_score < 0

    def test_analyze_stable(self):
        a = GrowthAnalyzer()
        services = [5.0] * 30
        pricing = [3.0] * 30
        content = [2.0] * 30
        result = a.analyze(services, pricing, content)
        assert result.growth_direction == "stable"

    def test_velocity_single_point(self):
        a = GrowthAnalyzer()
        assert a._velocity([5.0], 30) == 0.0

    def test_velocity_two_points(self):
        a = GrowthAnalyzer()
        v = a._velocity([1.0, 2.0], 30)
        assert v > 0

    def test_metrics_fields(self):
        a = GrowthAnalyzer()
        result = a.analyze([1, 2, 3], [1, 2, 3], [1, 2, 3])
        assert hasattr(result, "catalog_velocity_30d")
        assert hasattr(result, "catalog_velocity_60d")
        assert hasattr(result, "catalog_velocity_90d")
        assert hasattr(result, "digital_footprint_rate")
        assert hasattr(result, "content_publishing_velocity")
        assert hasattr(result, "overall_growth_score")
        assert hasattr(result, "growth_direction")


# ─── RegionalExpansionPredictor Tests ─────────────────────────────────────


class TestRegionalExpansionPredictor:
    def test_init(self):
        p = RegionalExpansionPredictor()
        assert len(p.TARGET_REGIONS) > 0
        assert "chennai" in p.TARGET_REGIONS

    def test_detect_from_urls_empty(self):
        p = RegionalExpansionPredictor()
        opps = p.detect_from_urls([], 1)
        assert len(opps) == len(p.TARGET_REGIONS)

    def test_detect_from_urls_with_region(self):
        p = RegionalExpansionPredictor()
        opps = p.detect_from_urls(["https://example.com/chennai/services"], 1)
        regions = [o.region for o in opps]
        assert "chennai" not in regions
        assert "mumbai" in regions

    def test_detect_from_services(self):
        p = RegionalExpansionPredictor()
        opps = p.detect_from_services(["plumbing"], {"chennai": 1, "mumbai": 5})
        assert len(opps) >= 1
        chennai_opp = next((o for o in opps if o.region == "chennai"), None)
        assert chennai_opp is not None
        assert chennai_opp.signal_type == "service_gap"

    def test_compute_opportunities(self):
        p = RegionalExpansionPredictor()
        opps = p.compute_opportunities(
            urls=["https://example.com/chennai"],
            service_categories=["plumbing"],
            region_mentions={"chennai": 1},
            competitor_id=1,
        )
        assert len(opps) > 0
        assert len(opps) <= 10

    def test_deduplication(self):
        p = RegionalExpansionPredictor()
        opps = p.compute_opportunities(
            urls=[],
            service_categories=[],
            region_mentions={"chennai": 1},
            competitor_id=1,
        )
        keys = [(o.region, o.signal_type) for o in opps]
        assert len(keys) == len(set(keys))


# ─── ConfidenceScorer Tests ───────────────────────────────────────────────


class TestConfidenceScorer:
    def test_init(self):
        s = ConfidenceScorer()
        assert s is not None

    def test_score_defaults(self):
        s = ConfidenceScorer()
        result = s.score()
        assert 0.0 <= result.score <= 1.0
        assert result.reliability in ("high", "medium", "low")
        assert "sample_size" in result.factors
        assert "data_freshness" in result.factors
        assert "completeness" in result.factors
        assert "historical_accuracy" in result.factors
        assert "stability" in result.factors

    def test_high_confidence(self):
        s = ConfidenceScorer()
        result = s.score(
            sample_size=30,
            data_age_days=0,
            completeness=1.0,
            historical_accuracy=0.9,
            variance=0.05,
        )
        assert result.score >= 0.7
        assert result.reliability == "high"

    def test_low_confidence(self):
        s = ConfidenceScorer()
        result = s.score(
            sample_size=1,
            data_age_days=100,
            completeness=0.2,
            historical_accuracy=0.1,
            variance=0.9,
        )
        assert result.score < 0.4
        assert result.reliability == "low"

    def test_sample_size_scoring(self):
        s = ConfidenceScorer()
        assert s._score_sample_size(30) == 1.0
        assert s._score_sample_size(20) == 0.9
        assert s._score_sample_size(10) == 0.7
        assert s._score_sample_size(5) == 0.5
        assert s._score_sample_size(2) == 0.3
        assert s._score_sample_size(0) == 0.1

    def test_freshness_scoring(self):
        s = ConfidenceScorer()
        assert s._score_freshness(0) == 1.0
        assert s._score_freshness(1) == 1.0
        assert s._score_freshness(7) == 0.9
        assert s._score_freshness(30) == 0.7
        assert s._score_freshness(90) == 0.5
        assert s._score_freshness(100) == 0.3

    def test_t_adjusted_interval(self):
        s = ConfidenceScorer()
        lo, hi = s.t_adjusted_interval(mean=100.0, std=10.0, df=10)
        assert lo < 100.0 < hi
        # t-distribution should be wider than z=1.96 for small df
        assert (hi - lo) > 2 * 1.96 * 10.0

    def test_t_value_large_df(self):
        s = ConfidenceScorer()
        assert s._t_value(30) == 1.96
        assert s._t_value(100) == 1.96

    def test_t_value_small_df(self):
        s = ConfidenceScorer()
        t = s._t_value(5)
        assert t > 1.96
