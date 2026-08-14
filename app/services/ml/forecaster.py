"""Machine Learning Forecasting Pipeline.

Built-in models: Linear Regression, Moving Average,
Exponential Smoothing, Heuristic. Optional XGBoost support.
Feature engineering, model selection, cross-validation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ModelType(str, Enum):
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    MOVING_AVERAGE = "moving_average"
    ENSEMBLE = "ensemble"


@dataclass
class ForecastResult:
    model_type: str
    predictions: list[float]
    confidence_intervals: list[tuple[float, float]]
    metrics: dict[str, float]
    feature_importance: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelEvaluation:
    model_type: str
    mae: float
    rmse: float
    mape: float
    r2: float
    cv_score: float
    training_time_ms: float


def _linear_regression_forecast(values: list[float], steps: int) -> ForecastResult:
    n = len(values)
    if n < 2:
        return ForecastResult("linear_regression", [values[0]] * steps if values else [0.0] * steps, [(0, 0)] * steps, {})

    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0
    intercept = y_mean - slope * x_mean

    preds = [max(0.0, slope * (n + i) + intercept) for i in range(steps)]
    residuals = [values[i] - (slope * i + intercept) for i in range(n)]
    mse = sum(r * r for r in residuals) / max(n - 2, 1)
    std_err = math.sqrt(mse)

    ci = [(max(0, p - 1.96 * std_err * math.sqrt(i + 1)), p + 1.96 * std_err * math.sqrt(i + 1)) for i, p in enumerate(preds)]
    mae = sum(abs(r) for r in residuals) / n
    rmse = math.sqrt(sum(r * r for r in residuals) / n)

    return ForecastResult(
        model_type="linear_regression",
        predictions=preds, confidence_intervals=ci,
        metrics={"mae": round(mae, 4), "rmse": round(rmse, 4), "slope": round(slope, 4)},
        feature_importance={"time": 1.0},
    )


def _moving_average_forecast(values: list[float], steps: int, window: int = 3) -> ForecastResult:
    if len(values) < window:
        avg = sum(values) / max(len(values), 1)
        return ForecastResult("moving_average", [max(0, avg)] * steps, [(max(0, avg * 0.8), avg * 1.2)] * steps, {})

    preds = []
    recent = list(values[-window:])
    for _ in range(steps):
        pred = max(0.0, sum(recent[-window:]) / window)
        preds.append(pred)
        recent.append(pred)

    std = math.sqrt(sum((v - sum(values[-window:]) / window) ** 2 for v in values[-window:])) / window
    ci = [(max(0, p - 1.96 * std * math.sqrt(i + 1)), p + 1.96 * std * math.sqrt(i + 1)) for i, p in enumerate(preds)]

    return ForecastResult("moving_average", preds, ci, {"window": window})


def _exponential_smoothing_forecast(values: list[float], steps: int, alpha: float = 0.3) -> ForecastResult:
    if not values:
        return ForecastResult("exponential_smoothing", [0.0] * steps, [(0, 0)] * steps, {})

    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])

    trend = (smoothed[-1] - smoothed[max(0, len(smoothed) - 5)]) / min(5, len(smoothed))
    preds = [max(0.0, smoothed[-1] + trend * (i + 1)) for i in range(steps)]

    residuals = [values[i] - smoothed[i] for i in range(len(values))]
    std = math.sqrt(sum(r * r for r in residuals) / max(len(residuals), 1))
    ci = [(max(0, p - 1.96 * std * math.sqrt(i + 1)), p + 1.96 * std * math.sqrt(i + 1)) for i, p in enumerate(preds)]

    return ForecastResult("exponential_smoothing", preds, ci, {"alpha": alpha})


def _heuristic_forecast(values: list[float], steps: int) -> ForecastResult:
    if not values:
        return ForecastResult("heuristic", [0.0] * steps, [(0, 0)] * steps, {})

    avg = sum(values) / len(values)
    trend = (values[-1] - values[0]) / max(len(values) - 1, 1) if len(values) > 1 else 0
    preds = [max(0.0, values[-1] + trend * (i + 1)) for i in range(steps)]
    std = math.sqrt(sum((v - avg) ** 2 for v in values) / max(len(values), 1))
    ci = [(max(0, p - 1.96 * std * math.sqrt(i + 1)), p + 1.96 * std * math.sqrt(i + 1)) for i, p in enumerate(preds)]

    return ForecastResult("heuristic", preds, ci, {"avg": avg, "trend": trend})


def _croston_forecast(values: list[float], steps: int, alpha: float = 0.1) -> ForecastResult:
    """Croston's method for intermittent demand forecasting.

    Separates demand size and demand interval into two exponential smoothing streams.
    Ideal for sparse count data (90%+ zeros).
    """
    n = len(values)
    if n == 0:
        return ForecastResult("croston", [0.0] * steps, [(0, 0)] * steps, {})

    # Split into demand sizes (non-zero values) and inter-demand intervals
    demand_sizes: list[float] = []
    intervals: list[float] = []
    last_demand_idx = -1

    for i, v in enumerate(values):
        if v > 0:
            demand_sizes.append(v)
            if last_demand_idx >= 0:
                intervals.append(float(i - last_demand_idx))
            else:
                intervals.append(float(i + 1))
            last_demand_idx = i

    # If no demand at all, return zeros
    if not demand_sizes:
        return ForecastResult("croston", [0.0] * steps, [(0, 0)] * steps, {"demand_count": 0})

    # Exponential smoothing on demand sizes
    smoothed_demand = demand_sizes[0]
    for v in demand_sizes[1:]:
        smoothed_demand = alpha * v + (1 - alpha) * smoothed_demand

    # Exponential smoothing on intervals
    smoothed_interval = intervals[0]
    for iv in intervals[1:]:
        smoothed_interval = alpha * iv + (1 - alpha) * smoothed_interval

    # Croston's forecast = smoothed_demand / smoothed_interval
    if smoothed_interval > 0:
        forecast_value = smoothed_demand / smoothed_interval
    else:
        forecast_value = smoothed_demand

    # Demand probability
    demand_prob = len(demand_sizes) / max(n, 1)

    preds = [max(0.0, forecast_value) for _ in range(steps)]

    # CI based on demand variability
    if len(demand_sizes) > 1:
        demand_std = math.sqrt(sum((v - smoothed_demand) ** 2 for v in demand_sizes) / len(demand_sizes))
    else:
        demand_std = smoothed_demand * 0.5

    ci = [
        (max(0, forecast_value - 1.96 * demand_std * math.sqrt(i + 1)),
         forecast_value + 1.96 * demand_std * math.sqrt(i + 1))
        for i in range(steps)
    ]

    return ForecastResult(
        model_type="croston",
        predictions=preds,
        confidence_intervals=ci,
        metrics={
            "smoothed_demand": round(smoothed_demand, 4),
            "smoothed_interval": round(smoothed_interval, 4),
            "demand_prob": round(demand_prob, 4),
            "demand_count": len(demand_sizes),
        },
    )


def _sba_forecast(values: list[float], steps: int, alpha: float = 0.1) -> ForecastResult:
    """Syntetos-Boylan Approximation (SBA).

    Bias-corrected version of Croston's method. Multiplies Croston's
    forecast by (1 - alpha/2) to correct for systematic overestimation.
    """
    croston_result = _croston_forecast(values, steps, alpha)

    # SBA correction factor
    correction = 1.0 - alpha / 2.0
    sba_preds = [max(0.0, p * correction) for p in croston_result.predictions]

    return ForecastResult(
        model_type="sba",
        predictions=sba_preds,
        confidence_intervals=croston_result.confidence_intervals,
        metrics={
            **croston_result.metrics,
            "correction_factor": round(correction, 4),
        },
    )


def _ridge_regression_forecast(
    values: list[float], steps: int, features: list[list[float]] | None = None, alpha: float = 1.0
) -> ForecastResult:
    """Ridge regression with optional multivariate features.

    If features are provided, uses them. Otherwise falls back to time index.
    Uses closed-form solution: w = (X^T X + alpha I)^{-1} X^T y
    """
    n = len(values)
    if n < 2:
        v = values[0] if values else 0.0
        return ForecastResult("ridge", [v] * steps, [(v, v)] * steps, {})

    # Build design matrix X
    if features and len(features) == n:
        X = [row[:] for row in features]  # copy
    else:
        X = [[float(i)] for i in range(n)]

    # Add intercept column
    X_with_intercept = [[1.0] + row for row in X]
    p = len(X_with_intercept[0])

    # Solve via normal equations with L2 regularization: (X^T X + alpha * I) w = X^T y
    XtX = [[0.0] * p for _ in range(p)]
    Xty = [0.0] * p

    for i in range(n):
        for j in range(p):
            Xty[j] += X_with_intercept[i][j] * values[i]
            for k in range(p):
                XtX[j][k] += X_with_intercept[i][j] * X_with_intercept[i][k]

    # Add regularization (skip intercept)
    for j in range(1, p):
        XtX[j][j] += alpha

    # Solve via Gaussian elimination
    w = _solve_linear_system(XtX, Xty)

    # Predict: build future feature matrix
    future_X: list[list[float]] = []
    for i in range(steps):
        if features and len(features) == n:
            # Use last known feature row, extrapolate time-dependent features
            last_row = features[-1][:]
            if last_row:
                last_row[0] = float(n + i)  # update time_idx
            future_X.append([1.0] + last_row)
        else:
            future_X.append([1.0, float(n + i)])

    preds = [max(0.0, sum(w[j] * future_X[i][j] for j in range(p))) for i in range(steps)]

    # Residuals and metrics
    fitted = [max(0.0, sum(w[j] * X_with_intercept[i][j] for j in range(p))) for i in range(n)]
    residuals = [values[i] - fitted[i] for i in range(n)]
    mae = sum(abs(r) for r in residuals) / n
    rmse = math.sqrt(sum(r * r for r in residuals) / n)
    std = math.sqrt(sum(r * r for r in residuals) / max(n - p, 1))

    ci = [
        (max(0, p_ - 1.96 * std * math.sqrt(i + 1)), p_ + 1.96 * std * math.sqrt(i + 1))
        for i, p_ in enumerate(preds)
    ]

    # Feature importance (absolute weight, normalized)
    feat_names = ["intercept"] + (["time_idx"] if not features else [f"f{j}" for j in range(p - 1)])
    importance = {name: abs(w[j]) for j, name in enumerate(feat_names) if j < len(w)}
    total_imp = sum(importance.values()) or 1.0
    importance = {k: round(v / total_imp, 4) for k, v in importance.items()}

    return ForecastResult(
        model_type="ridge",
        predictions=preds,
        confidence_intervals=ci,
        metrics={"mae": round(mae, 4), "rmse": round(rmse, 4), "alpha": alpha, "features": p - 1},
        feature_importance=importance,
    )


def _solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve Ax = b via Gaussian elimination with partial pivoting."""
    n = len(b)
    # Augmented matrix
    M = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        # Partial pivoting
        max_row = col
        for row in range(col + 1, n):
            if abs(M[row][col]) > abs(M[max_row][col]):
                max_row = row
        M[col], M[max_row] = M[max_row], M[col]

        if abs(M[col][col]) < 1e-12:
            continue

        # Eliminate below
        for row in range(col + 1, n):
            factor = M[row][col] / M[col][col]
            for j in range(col, n + 1):
                M[row][j] -= factor * M[col][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = M[i][n]
        for j in range(i + 1, n):
            x[i] -= M[i][j] * x[j]
        x[i] /= M[i][i] if abs(M[i][i]) > 1e-12 else 1.0

    return x


def _ensemble_forecast(
    values: list[float], steps: int, features: list[list[float]] | None = None
) -> ForecastResult:
    """Ensemble: average predictions from best univariate + intermittent + multivariate models."""
    # Detect sparse data
    zero_ratio = sum(1 for v in values if v == 0) / max(len(values), 1)
    is_sparse = zero_ratio > 0.7

    if is_sparse:
        models = [
            ("croston", lambda v, s: _croston_forecast(v, s)),
            ("sba", lambda v, s: _sba_forecast(v, s)),
            ("ridge", lambda v, s: _ridge_regression_forecast(v, s, features=features)),
        ]
    else:
        models = [
            ("linear_regression", lambda v, s: _linear_regression_forecast(v, s)),
            ("ridge", lambda v, s: _ridge_regression_forecast(v, s, features=features)),
            ("exponential_smoothing", lambda v, s: _exponential_smoothing_forecast(v, s)),
        ]

    all_preds: list[list[float]] = []
    all_ci: list[list[tuple[float, float]]] = []

    for name, fn in models:
        try:
            result = fn(values, steps)
            all_preds.append(result.predictions)
            all_ci.append(result.confidence_intervals)
        except Exception:
            continue

    if not all_preds:
        return _heuristic_forecast(values, steps)

    # Average predictions
    n_models = len(all_preds)
    preds = [
        sum(all_preds[m][i] for m in range(n_models)) / n_models
        for i in range(steps)
    ]

    # CI: use widest from any model
    ci = [
        (
            min(all_ci[m][i][0] for m in range(n_models)),
            max(all_ci[m][i][1] for m in range(n_models)),
        )
        for i in range(steps)
    ]

    return ForecastResult(
        model_type="ensemble",
        predictions=[max(0.0, p) for p in preds],
        confidence_intervals=ci,
        metrics={"n_models": n_models, "model_names": [m[0] for m in models]},
    )


AVAILABLE_MODELS: dict[str, Any] = {
    "linear_regression": _linear_regression_forecast,
    "exponential_smoothing": _exponential_smoothing_forecast,
    "moving_average": _moving_average_forecast,
    "ridge": _ridge_regression_forecast,
    "heuristic": _linear_regression_forecast,
    "ensemble": _ensemble_forecast,
}


class MLForecaster:
    """Pluggable ML forecasting engine."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = dict(AVAILABLE_MODELS)
        self._model_history: list[dict[str, Any]] = []

    def available_models(self) -> list[dict[str, Any]]:
        descriptions = {
            "linear_regression": "Linear Pricing Trend — Mid-term price inflation & base pricing drift model",
            "exponential_smoothing": "Exponential Smoothing — Short-term pricing momentum & promotional markdown model",
            "moving_average": "Weighted Moving Average — Service catalog listing volume & baseline model",
            "ridge": "Ridge Regression — Regularized multivariate pricing trajectory model",
            "heuristic": "Heuristic Pricing Baseline — Rule-based market growth model",
            "ensemble": "Adaptive Pricing Ensemble — Multi-model hybrid with walk-forward validation",
        }
        display_names = {
            "linear_regression": "Linear Pricing Trend Model",
            "exponential_smoothing": "Exponential Smoothing Model",
            "moving_average": "Weighted Moving Average Model",
            "ridge": "Ridge Regression Model",
            "heuristic": "Heuristic Baseline Model",
            "ensemble": "Adaptive Pricing Ensemble Model",
        }
        return [
            {
                "name": name,
                "display_name": display_names.get(name, name),
                "description": descriptions.get(name, ""),
                "available": True,
                "type": "builtin",
            }
            for name in self._models
        ]

    def forecast(
        self,
        values: list[float],
        steps: int = 30,
        model_name: str = "linear_regression",
        features: list[list[float]] | None = None,
        **kwargs: Any,
    ) -> ForecastResult:
        if model_name in self._models:
            fn = self._models[model_name]
            if model_name in ("ensemble", "ridge"):
                result = fn(values, steps, features=features, **kwargs)
            else:
                result = fn(values, steps, **kwargs)
        else:
            logger.warning("model_unavailable", model=model_name, fallback="heuristic")
            result = _linear_regression_forecast(values, steps)
            result.model_type = "heuristic"

        self._model_history.append({
            "model": model_name, "steps": steps,
            "data_points": len(values),
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": result.metrics,
        })
        return result

    def _xgboost_forecast(self, values: list[float], steps: int, features: list[list[float]] | None = None) -> ForecastResult:
        try:
            import xgboost as xgb
            import numpy as np

            if features and len(features) == len(values):
                X = np.array(features)
            else:
                X = np.array(range(len(values))).reshape(-1, 1)
            y = np.array(values)

            model = xgb.XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, verbosity=0)
            model.fit(X, y)

            if features and len(features) == len(values):
                # Extrapolate last feature row
                future_X_list = [row[:] for row in features[-1:]]
                future_X = np.array(future_X_list)
                # Repeat for steps (simple extrapolation)
                future_X = np.tile(future_X, (steps, 1))
                future_X[:, 0] = np.arange(len(values), len(values) + steps)  # update time_idx
            else:
                future_X = np.array(range(len(values), len(values) + steps)).reshape(-1, 1)

            preds = model.predict(future_X).tolist()

            importance = dict(zip(
                [f"f{i}" for i in range(X.shape[1])],
                [float(v) for v in model.feature_importances_[:min(10, X.shape[1])]],
            ))

            residuals = [values[i] - float(model.predict(np.array([X[i]]))) for i in range(len(values))]
            std = math.sqrt(sum(r * r for r in residuals) / max(len(residuals), 1))
            ci = [(p - 1.96 * std * math.sqrt(i + 1), p + 1.96 * std * math.sqrt(i + 1)) for i, p in enumerate(preds)]

            return ForecastResult(
                model_type="xgboost", predictions=preds, confidence_intervals=ci,
                metrics={"n_estimators": 100, "max_depth": 3, "features": X.shape[1]},
                feature_importance=importance,
            )
        except Exception:
            return _heuristic_forecast(values, steps)

    def evaluate_model(
        self,
        values: list[float],
        model_name: str = "linear_regression",
        features: list[list[float]] | None = None,
    ) -> ModelEvaluation:
        import time
        start = time.monotonic()

        n = len(values)
        if n < 4:
            return self._simple_evaluate(values, model_name, start)

        # Walk-forward validation: train on first k points, predict k+1,
        # slide forward, repeat.
        min_train = max(3, n // 3)
        all_errors: list[float] = []
        all_sq_errors: list[float] = []
        all_pct_errors: list[float] = []
        all_actuals: list[float] = []
        all_preds: list[float] = []

        for split in range(min_train, n):
            train = values[:split]
            actual = values[split]
            train_features = features[:split] if features and len(features) >= split else None
            result = self.forecast(train, steps=1, model_name=model_name, features=train_features)
            pred = result.predictions[0] if result.predictions else 0.0

            err = abs(actual - pred)
            sq_err = (actual - pred) ** 2
            pct_err = abs(actual - pred) / max(abs(actual), 1e-10)

            all_errors.append(err)
            all_sq_errors.append(sq_err)
            all_pct_errors.append(pct_err)
            all_actuals.append(actual)
            all_preds.append(pred)

        mae = sum(all_errors) / len(all_errors)
        rmse = math.sqrt(sum(all_sq_errors) / len(all_sq_errors))
        mape = sum(all_pct_errors) / len(all_pct_errors) * 100

        # R² metric: for sparse data use naive baseline, for dense use mean baseline.
        # Sparse data (>70% zeros): naive = predict last value (usually 0).
        #   R² = 1 - SS_model / SS_naive. Naive gets 0, better → positive.
        # Dense data: standard R² = 1 - SS_res / SS_tot (relative to mean).
        zero_ratio = sum(1 for a in all_actuals if a == 0) / max(len(all_actuals), 1)

        if zero_ratio > 0.7:
            # Sparse: naive baseline (predict last value)
            naive_errors = []
            for split in range(min_train, n):
                train = values[:split]
                naive_pred = train[-1] if train else 0.0
                actual = values[split]
                naive_errors.append((actual - naive_pred) ** 2)
            total_naive_sq = sum(naive_errors)
            total_model_sq = sum(all_sq_errors)
            r2 = max(0.0, 1 - total_model_sq / total_naive_sq) if total_naive_sq > 0 else 0.0
        else:
            # Dense: standard R² (relative to mean)
            y_mean = sum(all_actuals) / len(all_actuals)
            ss_tot = sum((a - y_mean) ** 2 for a in all_actuals)
            total_model_sq = sum(all_sq_errors)
            r2 = max(0.0, 1 - total_model_sq / ss_tot) if ss_tot > 0 else 0.0

        elapsed = (time.monotonic() - start) * 1000

        return ModelEvaluation(
            model_type=model_name, mae=round(mae, 4), rmse=round(rmse, 4),
            mape=round(mape, 2), r2=round(r2, 4), cv_score=round(r2, 4),
            training_time_ms=round(elapsed, 2),
        )

    def _simple_evaluate(
        self, values: list[float], model_name: str, start: float
    ) -> ModelEvaluation:
        """Fallback for very short series."""
        import time
        if not values:
            return ModelEvaluation(model_name, 0, 0, 0, 0, 0, 0)

        result = self.forecast(values, steps=1, model_name=model_name)
        pred = result.predictions[0] if result.predictions else 0.0
        actual = values[-1]
        err = abs(actual - pred)
        sq_err = (actual - pred) ** 2
        pct_err = abs(actual - pred) / max(abs(actual), 1e-10)

        elapsed = (time.monotonic() - start) * 1000
        return ModelEvaluation(
            model_type=model_name, mae=round(err, 4), rmse=round(math.sqrt(sq_err), 4),
            mape=round(pct_err * 100, 2), r2=0.0, cv_score=0.0,
            training_time_ms=round(elapsed, 2),
        )

    def select_best_model(
        self, values: list[float], features: list[list[float]] | None = None
    ) -> tuple[str, ModelEvaluation]:
        """Select best model with penalties for count-data unfriendly predictions.

        Tries both univariate and multivariate models when features are provided.
        For sparse data (90%+ zeros), prioritizes intermittent demand models.
        """
        if not values or len(values) < 3:
            best_eval = self.evaluate_model(values or [0.0], model_name="linear_regression")
            return "linear_regression", best_eval

        candidates = ["linear_regression", "exponential_smoothing", "moving_average", "ensemble"]

        best_name = "linear_regression"
        best_score = float("inf")
        best_eval: ModelEvaluation | None = None

        for name in candidates:
            try:
                eval_result = self.evaluate_model(values, model_name=name, features=features)
                test_pred = self.forecast(
                    values[:max(3, len(values) // 2)],
                    steps=max(2, len(values) // 4),
                    model_name=name,
                    features=features,
                )
                neg_count = sum(1 for p in test_pred.predictions if p < 0)

                penalty = 0
                if neg_count > 0:
                    penalty += neg_count * 2.0
                score = eval_result.rmse + penalty

                if score < best_score:
                    best_score = score
                    best_name = name
                    best_eval = eval_result
            except Exception:
                continue

        if best_eval is None:
            best_eval = self.evaluate_model(values, model_name="linear_regression")
            best_name = "linear_regression"

        return best_name, best_eval

    def get_history(self) -> list[dict[str, Any]]:
        return self._model_history


ml_forecaster = MLForecaster()
