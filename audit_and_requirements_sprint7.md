# Sprint 7 Audit & Requirements

## Objective
Transform the Competitor Intelligence System from descriptive/real-time insights into a **predictive intelligence ecosystem** with forecasting, trend detection, risk assessment, opportunity analysis, and strategic decision support.

---

## Audit Summary

| Category | Status | Score |
|---|---|---|
| Predictive Analytics & Forecasting | ✅ Partial | 7/10 |
| Trend Detection | ✅ Done | 8/10 |
| Growth Trajectory Forecasting | ✅ Done | 8/10 |
| Pricing/Service Strategy Prediction | ✅ Done | 7/10 |
| Regional Expansion | ⚠️ Partial | 4/10 |
| Risk Assessment | ✅ Done | 7/10 |
| Opportunity Analysis | ✅ Done | 8/10 |
| Confidence Scoring | ⚠️ Partial | 5/10 |
| Multi-factor Models | ✅ Done | 7/10 |
| Business Recommendations | ✅ Done | 8/10 |
| Accuracy/Scalability/Explainability | ⚠️ Partial | 5/10 |
| Testing | ⚠️ Partial | 6/10 |
| Production-Readiness | ⚠️ Partial | 5/10 |
| **Overall** | **⚠️ Partial** | **6.5/10** |

---

## P0 — Critical Crashes (Must Fix)

### 1. `predictions.py:274` — NameError: datetime not imported
- **File:** `app/api/endpoints/predictions.py`
- **Line:** 274 (`datetime.now(UTC).isoformat()`)
- **Bug:** `datetime` imported at line 504 (bottom of file), but used at line 274
- **Impact:** `POST /api/predictions/generate` crashes with `NameError`
- **Fix:** Move `from datetime import UTC, datetime` to top of file

### 2. `sprint_7_2.py:169,274` — Duplicate function name
- **File:** `app/api/endpoints/sprint_7_2.py`
- **Bug:** Two `async def ml_forecast()` — POST at line 169, GET at line 274
- **Impact:** POST `/api/ml/forecast` is shadowed/broken
- **Fix:** Rename GET endpoint to `ml_forecast_competitor`

### 3. `confidence.py:198` — TypeError on ORM objects
- **File:** `app/services/predictions/confidence.py`
- **Bug:** `statistics.mean(recent_prices)` and `statistics.stdev(recent_prices)` called on ORM `BasePrice` objects
- **Impact:** `GET /api/predictions/growth/{id}/confidence` crashes
- **Fix:** Extract `.base_price` float values before calling statistics

### 4. `copilot.py:40-50` — Provider permanent failure
- **File:** `app/services/rag/copilot.py`
- **Bug:** `_provider` cached as `None` on first failure, never retried
- **Impact:** Copilot permanently broken after one API hiccup
- **Fix:** Don't cache `None`; retry on next call

---

## P1 — Wrong Data (Must Fix)

### 5. `IndustryBenchmarksPage.tsx:99-105` — Hardcoded text
- **File:** `frontend/src/pages/IndustryBenchmarksPage.tsx`
- **Bug:** "Strongest Dimension: Growth, Avg 91st percentile" is hardcoded string
- **Impact:** Always shows wrong data regardless of actual benchmarks
- **Fix:** Compute from actual data

### 6. `scoring.py:187` — Tied score ranking bug
- **File:** `app/services/predictions/scoring.py`
- **Bug:** `sorted_scores.index(score)` returns first occurrence — tied scores get wrong grades
- **Fix:** Use enumerated index with tie-breaking

### 7. `benchmarking.py:88-120` — Dead current_rank
- **File:** `app/services/predictions/benchmarking.py`
- **Bug:** `current_rank` computed at line 88, overwritten at line 120
- **Fix:** Remove dead computation

---

## P2 — Statistical Correctness

### 8. `forecaster.py` — CI doesn't widen with horizon
- All forecast models produce constant-width confidence intervals
- Multi-step forecasts should widen CI proportionally to horizon
- **Fix:** Scale CI by `sqrt(step)` for each forecast step

### 9. `analytics.py:113` — z=1.96 always
- `prediction_interval` uses z=1.96 regardless of sample size
- Small samples (<30) should use t-distribution
- **Fix:** Use `scipy.stats.t.ppf` or approximate t-value

### 10. `forecaster.py` — Unused `test_split` parameter
- `evaluate_model` accepts `test_split` but walk-forward always starts at `n//3`
- **Fix:** Remove unused parameter

---

## P3 — Performance

### 11. `sprint_7_2.py` — 3x duplicated time-series query
- Lines 222-240, 291-302, 370-379 are copy-pasted
- **Fix:** Extract to shared `_query_time_series()` helper

### 12. N+1 query patterns
- `trends.py:57-63` — per-category query in `analyze_pricing_trends`
- `data_quality.py:135-138` — per-competitor in `evaluate_all`
- `benchmarking.py:83` — linear scan per competitor
- **Fix:** Batch queries where possible

### 13. `sprint_7_2.py` — Zero auth on endpoints
- Unlike `predictions.py`, sprint_7_2 has no `verify_credentials`
- **Fix:** Add `Depends(verify_credentials)` to all endpoints

### 14. `reports.py`, `engine.py` — No error handling
- If any sub-service fails, entire report/prediction crashes
- **Fix:** Wrap each sub-call in try/except

---

## P4 — Code Quality

### 15. Duplicate utility functions
- `_clamp` duplicated in: `risks.py`, `trends.py`, `benchmarking.py`, `growth.py`
- `_linear_trend` duplicated in `trends.py`
- `_direction_from_slope` duplicated in `trends.py`
- **Fix:** Import from `analytics.py`, remove local copies

### 16. Dead code
- `benchmarking.py:_compute_metrics` — never called
- `growth.py:_clamp` — never used
- `industry_benchmarking.py:categories` — computed but never filtered on
- `engine.py:_linear_trend` — imported but never used
- **Fix:** Remove all dead code

### 17. Magic numbers
- Growth thresholds: 0.15, 0.0, -0.15
- Risk thresholds: 70/50/30, 2.0, -0.05, 0.4, 0.7
- Scoring denominators: /10, /20, /15, /5
- Confidence weights: 0.15, 0.15, 0.15, 0.20, 0.10, 0.15, 0.10
- **Fix:** Extract to named constants or config

### 18. REST violations
- `GET /api/graph/build` — mutates state (builds graph)
- `GET /api/rag/index` — mutates state (indexes data)
- **Fix:** Change to `POST`

---

## Files Changed Summary

| File | Changes |
|---|---|
| `app/api/endpoints/predictions.py` | Fix datetime import |
| `app/api/endpoints/sprint_7_2.py` | Rename function, add auth, extract helper, fix REST |
| `app/services/predictions/confidence.py` | Fix ORM stdev bug |
| `app/services/rag/copilot.py` | Fix provider caching |
| `app/services/predictions/scoring.py` | Fix tied-score ranking |
| `app/services/predictions/benchmarking.py` | Remove dead code |
| `app/services/predictions/trends.py` | Remove duplicate functions, fix N+1 |
| `app/services/predictions/risks.py` | Remove duplicate _clamp |
| `app/services/predictions/growth.py` | Remove dead _clamp |
| `app/services/predictions/reports.py` | Add error handling |
| `app/services/predictions/engine.py` | Add error handling, remove dead import |
| `app/services/predictions/analytics.py` | Add t-distribution support |
| `app/services/ml/forecaster.py` | CI widening, remove unused param |
| `app/services/predictions/data_quality.py` | Fix N+1 queries |
| `frontend/src/pages/IndustryBenchmarksPage.tsx` | Fix hardcoded text |
