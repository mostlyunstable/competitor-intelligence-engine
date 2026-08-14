"""Unit tests for Sprint 7: Predictive Intelligence Engine."""

import math
from datetime import UTC, datetime, timedelta

import pytest

from app.services.predictions.engine import PredictionEngine, _clamp, _linear_trend, _direction_from_slope
from app.services.predictions.trends import TrendAnalyzer
from app.services.predictions.growth import GrowthForecaster, _clamp as growth_clamp
from app.services.predictions.risks import RiskAnalyzer
from app.services.predictions.opportunities import OpportunityDetector
from app.services.predictions.recommendations import RecommendationEngine
from app.services.predictions.benchmarking import PredictiveBenchmarker
from app.services.predictions.expansion import ExpansionForecaster
from app.services.predictions.reports import ForecastReportGenerator


# ─── Utility Tests ──────────────────────────────────────────────────────────


class TestClamp:
    def test_within_range(self):
        assert _clamp(0.5) == 0.5

    def test_below_low(self):
        assert _clamp(-1.0) == 0.0

    def test_above_high(self):
        assert _clamp(2.0) == 1.0

    def test_custom_range(self):
        assert _clamp(15, 10, 20) == 15
        assert _clamp(5, 10, 20) == 10
        assert _clamp(25, 10, 20) == 20


class TestLinearTrend:
    def test_empty(self):
        assert _linear_trend([]) == 0.0

    def test_single_value(self):
        assert _linear_trend([5.0]) == 0.0

    def test_increasing(self):
        slope = _linear_trend([1.0, 2.0, 3.0, 4.0, 5.0])
        assert slope > 0

    def test_decreasing(self):
        slope = _linear_trend([5.0, 4.0, 3.0, 2.0, 1.0])
        assert slope < 0

    def test_flat(self):
        slope = _linear_trend([3.0, 3.0, 3.0, 3.0])
        assert abs(slope) < 0.001


class TestDirectionFromSlope:
    def test_increasing(self):
        assert _direction_from_slope(0.5) == "increasing"

    def test_decreasing(self):
        assert _direction_from_slope(-0.5) == "decreasing"

    def test_stable(self):
        assert _direction_from_slope(0.0) == "stable"

    def test_custom_threshold(self):
        assert _direction_from_slope(0.005, threshold=0.01) == "stable"
        assert _direction_from_slope(0.02, threshold=0.01) == "increasing"


# ─── PredictionEngine Tests ─────────────────────────────────────────────────


class TestPredictionEngine:
    def test_instance(self):
        engine = PredictionEngine()
        assert engine is not None


# ─── TrendAnalyzer Tests ────────────────────────────────────────────────────


class TestTrendAnalyzer:
    def test_instance(self):
        analyzer = TrendAnalyzer()
        assert analyzer is not None


# ─── GrowthForecaster Tests ─────────────────────────────────────────────────


class TestGrowthForecaster:
    def test_instance(self):
        forecaster = GrowthForecaster()
        assert forecaster is not None

    def test_clamp(self):
        assert growth_clamp(0.5) == 0.5
        assert growth_clamp(-1.0) == 0.0
        assert growth_clamp(2.0) == 1.0


# ─── RiskAnalyzer Tests ─────────────────────────────────────────────────────


class TestRiskAnalyzer:
    def test_instance(self):
        analyzer = RiskAnalyzer()
        assert analyzer is not None


# ─── OpportunityDetector Tests ──────────────────────────────────────────────


class TestOpportunityDetector:
    def test_instance(self):
        detector = OpportunityDetector()
        assert detector is not None


# ─── RecommendationEngine Tests ────────────────────────────────────────────


class TestRecommendationEngine:
    def test_instance(self):
        engine = RecommendationEngine()
        assert engine is not None


# ─── PredictiveBenchmarker Tests ────────────────────────────────────────────


class TestPredictiveBenchmarker:
    def test_instance(self):
        benchmarker = PredictiveBenchmarker()
        assert benchmarker is not None


# ─── ExpansionForecaster Tests ──────────────────────────────────────────────


class TestExpansionForecaster:
    def test_instance(self):
        forecaster = ExpansionForecaster()
        assert forecaster is not None


# ─── ForecastReportGenerator Tests ──────────────────────────────────────────


class TestForecastReportGenerator:
    def test_instance(self):
        generator = ForecastReportGenerator()
        assert generator is not None

    def test_build_summary_empty(self):
        generator = ForecastReportGenerator()
        summary = generator._build_summary(
            {"emerging_trends": []}, [], [], [], []
        )
        assert summary == "No significant findings at this time."

    def test_build_summary_with_data(self):
        generator = ForecastReportGenerator()
        summary = generator._build_summary(
            {"emerging_trends": [{"x": 1}]},
            [{"growth_level": "high"}],
            [{"risk_level": "critical"}],
            [{"opportunity_type": "pricing_gap"}],
            [{"title": "Test"}],
        )
        assert "1 competitor(s) showing high growth" in summary
        assert "1 high-priority risk(s)" in summary
        assert "1 business opportunity" in summary
        assert "1 strategic recommendation" in summary
        assert "1 emerging trend" in summary

    def test_extract_regional_empty(self):
        generator = ForecastReportGenerator()
        result = generator._extract_regional({}, [])
        assert result == []

    def test_extract_regional_with_opps(self):
        generator = ForecastReportGenerator()
        opps = [
            {"opportunity_type": "underserved_region", "title": "Chennai", "opportunity_score": 70, "recommended_action": "Expand"}
        ]
        result = generator._extract_regional({}, opps)
        assert len(result) == 1
        assert result[0]["region"] == "Chennai"

    def test_extract_actions_empty(self):
        generator = ForecastReportGenerator()
        result = generator._extract_actions([], [])
        assert result == []

    def test_extract_actions_with_data(self):
        generator = ForecastReportGenerator()
        recs = [{"title": "Rec 1", "recommendation": "Do X", "priority": "high", "expected_benefit": "Y"}]
        opps = [{"title": "Opp 1", "recommended_action": "Do Z", "priority": "medium", "roi_estimate": "20%"}]
        result = generator._extract_actions(recs, opps)
        assert len(result) == 2
        assert result[0]["type"] == "recommendation"
        assert result[1]["type"] == "opportunity"


# ─── Model Enum Tests ───────────────────────────────────────────────────────


class TestModelEnums:
    def test_prediction_type_values(self):
        from app.database.models import PredictionType
        assert PredictionType.GROWTH == "growth"
        assert PredictionType.PRICING == "pricing"
        assert PredictionType.SERVICE_LAUNCH == "service_launch"
        assert PredictionType.MARKET_MOVEMENT == "market_movement"
        assert PredictionType.EXPANSION == "expansion"

    def test_trend_direction_values(self):
        from app.database.models import TrendDirection
        assert TrendDirection.INCREASING == "increasing"
        assert TrendDirection.DECREASING == "decreasing"
        assert TrendDirection.STABLE == "stable"
        assert TrendDirection.EMERGING == "emerging"

    def test_risk_level_values(self):
        from app.database.models import RiskLevel
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"

    def test_growth_level_values(self):
        from app.database.models import GrowthLevel
        assert GrowthLevel.HIGH == "high"
        assert GrowthLevel.MEDIUM == "medium"
        assert GrowthLevel.LOW == "low"
