"""Unit tests for ML feature engineering and multivariate models."""

import math
import pytest

from app.services.ml.features import (
    build_features_simple, FeatureSet,
    _rolling_sum, _rolling_mean, _rolling_std,
)
from app.services.ml.forecaster import (
    MLForecaster, _ridge_regression_forecast, _ensemble_forecast,
    _solve_linear_system, _linear_regression_forecast, _exponential_smoothing_forecast,
)


# ─── Feature Engineering Tests ────────────────────────────────────────────


class TestRollingFunctions:
    def test_rolling_sum(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _rolling_sum(values, 4, 3) == 12.0  # 3+4+5
        assert _rolling_sum(values, 0, 3) == 1.0
        assert _rolling_sum(values, 2, 7) == 6.0  # 1+2+3

    def test_rolling_mean(self):
        values = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert _rolling_mean(values, 4, 3) == 8.0  # (6+8+10)/3
        assert _rolling_mean(values, 0, 3) == 2.0

    def test_rolling_std(self):
        values = [1.0, 1.0, 1.0, 1.0, 1.0]
        assert _rolling_std(values, 4, 3) == 0.0

    def test_rolling_std_single(self):
        values = [5.0]
        assert _rolling_std(values, 0, 7) == 0.0


class TestBuildFeaturesSimple:
    @pytest.mark.asyncio
    async def test_basic(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = await build_features_simple(values)
        assert len(result.target) == 5
        assert len(result.features) == 5
        assert len(result.feature_names) == 4
        assert result.metadata["days"] == 5

    @pytest.mark.asyncio
    async def test_time_index(self):
        values = [10.0, 20.0, 30.0]
        result = await build_features_simple(values)
        assert result.features[0][0] == 0.0
        assert result.features[1][0] == 1.0
        assert result.features[2][0] == 2.0

    @pytest.mark.asyncio
    async def test_lag_1d(self):
        values = [10.0, 20.0, 30.0]
        result = await build_features_simple(values)
        assert result.features[0][1] == 10.0  # lag_1d = values[0]
        assert result.features[1][1] == 10.0  # lag_1d = values[0]
        assert result.features[2][1] == 20.0  # lag_1d = values[1]

    @pytest.mark.asyncio
    async def test_lag_7d(self):
        values = list(range(10))
        result = await build_features_simple(values)
        assert result.features[7][2] == 0.0  # lag_7d = values[0]
        assert result.features[9][2] == 2.0  # lag_7d = values[2]

    @pytest.mark.asyncio
    async def test_rolling_mean_7d(self):
        values = [1.0] * 10
        result = await build_features_simple(values)
        assert result.features[5][3] == 1.0  # all ones

    @pytest.mark.asyncio
    async def test_empty(self):
        result = await build_features_simple([])
        assert len(result.target) == 0
        assert len(result.features) == 0

    @pytest.mark.asyncio
    async def test_single_value(self):
        result = await build_features_simple([5.0])
        assert len(result.target) == 1
        assert result.features[0][0] == 0.0


# ─── Ridge Regression Tests ───────────────────────────────────────────────


class TestRidgeRegression:
    def test_empty(self):
        result = _ridge_regression_forecast([], 5)
        assert len(result.predictions) == 5
        assert result.model_type == "ridge"

    def test_single_value(self):
        result = _ridge_regression_forecast([5.0], 3)
        assert len(result.predictions) == 3
        assert all(p == 5.0 for p in result.predictions)

    def test_linear_trend(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _ridge_regression_forecast(values, 3)
        assert len(result.predictions) == 3
        assert result.predictions[0] > 4.0
        assert "mae" in result.metrics
        assert "rmse" in result.metrics
        assert "alpha" in result.metrics

    def test_with_features(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        features = [[float(i), float(i) * 2] for i in range(5)]
        result = _ridge_regression_forecast(values, 3, features=features)
        assert len(result.predictions) == 3
        assert result.metrics["features"] == 2

    def test_feature_importance(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _ridge_regression_forecast(values, 3)
        assert "feature_importance" in dir(result)
        assert len(result.feature_importance) > 0

    def test_no_negative_predictions(self):
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        result = _ridge_regression_forecast(values, 5)
        assert all(p >= 0.0 for p in result.predictions)

    def test_alpha_effect(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        r1 = _ridge_regression_forecast(values, 3, alpha=0.1)
        r2 = _ridge_regression_forecast(values, 3, alpha=10.0)
        # Higher alpha should produce different (smoother) predictions
        assert r1.predictions != r2.predictions


class TestSolveLinearSystem:
    def test_simple(self):
        A = [[2.0, 1.0], [1.0, 3.0]]
        b = [5.0, 7.0]
        x = _solve_linear_system(A, b)
        assert abs(2 * x[0] + x[1] - 5.0) < 1e-6
        assert abs(x[0] + 3 * x[1] - 7.0) < 1e-6

    def test_diagonal(self):
        A = [[2.0, 0.0], [0.0, 3.0]]
        b = [4.0, 6.0]
        x = _solve_linear_system(A, b)
        assert abs(x[0] - 2.0) < 1e-6
        assert abs(x[1] - 2.0) < 1e-6


# ─── Ensemble Tests ───────────────────────────────────────────────────────


class TestEnsemble:
    def test_empty(self):
        result = _ensemble_forecast([], 5)
        assert len(result.predictions) == 5
        assert result.model_type == "ensemble"

    def test_basic(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _ensemble_forecast(values, 3)
        assert len(result.predictions) == 3
        assert result.metrics["n_models"] >= 2

    def test_with_features(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        features = [[float(i)] for i in range(5)]
        result = _ensemble_forecast(values, 3, features=features)
        assert len(result.predictions) == 3

    def test_ci_widens(self):
        values = [1.0, 2.5, 2.8, 4.2, 5.1]
        result = _ensemble_forecast(values, 5)
        width_1 = result.confidence_intervals[0][1] - result.confidence_intervals[0][0]
        width_5 = result.confidence_intervals[4][1] - result.confidence_intervals[4][0]
        assert width_5 >= width_1


# ─── MLForecaster Integration Tests ───────────────────────────────────────


class TestMLForecasterMultivariate:
    def test_ridge_forecast(self):
        f = MLForecaster()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        result = f.forecast(values, steps=3, model_name="ridge")
        assert result.model_type == "ridge"
        assert len(result.predictions) == 3

    def test_ensemble_forecast(self):
        f = MLForecaster()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        result = f.forecast(values, steps=3, model_name="ensemble")
        assert result.model_type == "ensemble"
        assert len(result.predictions) == 3

    def test_ridge_with_features(self):
        f = MLForecaster()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        features = [[float(i), float(i) * 0.5] for i in range(7)]
        result = f.forecast(values, steps=3, model_name="ridge", features=features)
        assert result.model_type == "ridge"
        assert result.metrics["features"] == 2

    def test_select_best_with_features(self):
        f = MLForecaster()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        features = [[float(i), float(i) * 0.5] for i in range(10)]
        best_name, best_eval = f.select_best_model(values, features=features)
        assert best_name in ["linear_regression", "ridge", "ensemble", "exponential_smoothing", "heuristic"]
        assert best_eval.r2 >= 0.0

    def test_evaluate_ridge(self):
        f = MLForecaster()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        eval_result = f.evaluate_model(values, "ridge")
        assert eval_result.mae >= 0
        assert eval_result.rmse >= 0
        assert eval_result.r2 >= 0.0

    def test_available_models_includes_new(self):
        f = MLForecaster()
        models = f.available_models()
        names = [m["name"] for m in models]
        assert "ridge" in names
        assert "ensemble" in names

    def test_fallback_to_heuristic(self):
        f = MLForecaster()
        result = f.forecast([1.0], steps=2, model_name="nonexistent")
        assert result.model_type == "heuristic"
