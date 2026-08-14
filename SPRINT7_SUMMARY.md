# Sprint 7: Predictive Competitor Intelligence & Strategic Decision Support Engine

## Summary

Sprint 7 transformed the Utservio Competitor Intelligence Engine from a descriptive scraping platform into a predictive intelligence and strategic decision support ecosystem.

---

## 1. Database Schema & Migrations

### New Models (`app/database/models.py`)
- **`CompetitorChangeEvent`** — Granular delta tracking with event types: `PRICE_CHANGE`, `SERVICE_LAUNCH`, `SERVICE_DISCONTINUATION`, `REGIONAL_EXPANSION`, `CONTENT_UPDATE`, `STRATEGIC_SHIFT`
- **`PredictionEvaluation`** — Backtesting ground-truth validation with MAPE/RMSE scoring
- **`ChangeEventType`** enum (6 values)
- **`PredictionType`**, **`TrendDirection`**, **`RiskLevel`**, **`GrowthLevel`** enums

### Composite Indexes
- `ix_services_comp_date` — `(competitor_id, collected_at)` on `competitor_services`
- `ix_pricing_comp_date` — `(competitor_id, collected_at)` on `competitor_pricing`
- `ix_change_event_comp_date` — `(competitor_id, detected_at)` on `competitor_change_events`
- `ix_pred_eval_competitor_id`, `ix_pred_eval_prediction_type`, `ix_pred_eval_evaluated_at`

### Migration
- `migrations/versions/d4e5f6a7b8c9_add_predictive_analytics_tables.py`

---

## 2. Predictive Analytics Suite (`app/analytics/`)

### `time_series.py` — PriceForecaster
- Linear trend forecasting with OLS regression
- Exponential smoothing (alpha=0.3)
- Confidence intervals scaling by `σ · √h` (widens with forecast horizon)
- R² goodness-of-fit metric

### `growth_model.py` — GrowthAnalyzer
- Multi-window velocity: 30/60/90-day catalog velocity
- Digital footprint rate (pricing + content activity)
- Content publishing velocity
- Overall growth score (weighted average)
- Direction classification: growing / stable / declining

### `expansion_predictor.py` — RegionalExpansionPredictor
- URL-based geographic signal detection (15 Indian metros)
- Service gap detection per region
- Opportunity scoring and ranking

### `confidence.py` — ConfidenceScorer
- 5-factor weighted confidence: sample size, data freshness, completeness, historical accuracy, stability
- T-distribution correction for small samples (df < 30)
- Reliability classification: high / medium / low

---

## 3. Strategic Decision Support (`app/decision_support/`)

### `risk_evaluator.py` — StrategicRiskEvaluator
- 4 risk types: `price_war`, `market_share_erosion`, `expansion_collision`, `service_commoditization`
- Configurable thresholds per risk type
- Threat level classification: HIGH / MEDIUM / LOW
- Evidence tracking and mitigation recommendations

### `opportunity_miner.py` — OpportunityMiner
- Pricing gap detection (spread > 25% of average)
- Category gap detection (missing categories with competitor presence)
- Geographic gap detection (whitespace analysis)
- Combined mining with deduplication

### `recommendation.py` — StrategicRecommendationGenerator
- Growth response/opportunity recommendations
- Risk mitigation recommendations
- Pricing strategy recommendations
- Service expansion recommendations
- Impact rating and counter-action synthesis

---

## 4. API Endpoints (`app/api/endpoints/predictive.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/predictive/pricing/{competitor_id}` | GET | Pricing forecast with confidence scoring |
| `/api/predictive/growth/{competitor_id}` | GET | Growth velocity across 30/60/90-day windows |
| `/api/predictive/regional/opportunities` | GET | Geographic expansion opportunity detection |
| `/api/predictive/strategic-risks` | GET | Risk evaluation across all competitors |
| `/api/predictive/recommendations` | GET | Strategic recommendations synthesis |
| `/api/predictive/recommendations/briefing` | GET | LLM-narrated executive briefing |

All endpoints protected with `verify_credentials` (Basic Auth: `admin`/`admin123`).

---

## 5. LLM Narrative Synthesis

### `app/services/predictions/recommendations.py` — `generate_executive_briefing()`
- Gathers all current recommendations from `generate_all()`
- Formats into structured prompt for `gpt-4o-mini` via Utservio proxy
- Generates executive briefing with: Critical Actions, Strategic Themes, Risk Summary, Next Steps
- Graceful fallback to raw text if LLM unavailable
- Exposed via `GET /api/predictive/recommendations/briefing`

---

## 6. Automated Weekly Backtest Cron

### `app/schedulers/scheduler.py` — `_backtest_loop()`
- Runs weekly (604800s interval) after 60s initial startup delay
- Queries `competitor_predictions` older than 30 days
- Compares predicted values against actual DB counts (services/pricing/content)
- Computes MAPE and RMSE accuracy statistics
- Writes results to `prediction_evaluations` table
- Graceful cancellation on scheduler shutdown
- Mapped by prediction type: `growth` → service count, `pricing` → pricing count, `market_movement` → content count

---

## 7. Scheduler Enhancements

### Startup Tasks (`_initial_setup`)
- Auto-builds knowledge graph from DB
- Auto-generates predictions (growth, risks, recommendations, benchmarks, trends)
- Auto-runs initial backtest

### Periodic Tasks
- Collection scheduling per competitor frequency
- Prediction regeneration every 3 collections
- Weekly backtest cron

---

## 8. Bug Fixes & Improvements

- **`CompetitorService` index** — Fixed `ix_services_comp_date` referencing non-existent `created_at` → corrected to `collected_at`
- **`predictions.py`** — Fixed datetime import moved to top-level
- **`sprint_7_2.py`** — Renamed duplicate `ml_forecast` → `ml_forecast_competitor`; extracted `_query_competitor_timeseries()` helper; added auth
- **`copilot.py`** — Provider permanent-failure fix (sentinel `_UNSET` pattern)
- **`confidence.py`** — ORM stdev bug fixed (extract `.base_price` floats)
- **`analytics.py`** — Added `_t_value()` for t-distribution approximation
- **`scoring.py`** — Tied-score ranking fixed (enumerate)
- **`benchmarking.py`** — Dead `_compute_metrics` removed
- **`forecaster.py`** — CI widening with `sqrt(step)` in all 5 models; walk-forward validation; R² relative to naive baseline [0,1]

---

## 9. Tests

### New Test Files
| File | Tests | Coverage |
|------|-------|----------|
| `test_predictive_analytics.py` | 34 | PriceForecaster, GrowthAnalyzer, RegionalExpansionPredictor, ConfidenceScorer |
| `test_decision_support.py` | 37 | StrategicRiskEvaluator, OpportunityMiner, StrategicRecommendationGenerator |
| `test_predictive_api.py` | 9 | 5 endpoint tests + 2 auth tests + 404 handling |

### Total: 662 tests passing, 0 TypeScript errors

---

## 10. Competitor Configuration

### `competitors.json` — 11 Active Competitors
| # | Name | Frequency | Status |
|---|------|-----------|--------|
| 1 | Urban Company | daily | active |
| 2 | HomeFix Smart Services | daily | active |
| 3 | Servi | daily | active |
| 4 | Vijay Home Services | daily | active |
| 5 | Sparkle Cleaning Services | daily | active |
| 6 | IndiaMART | weekly | active |
| 7 | Chennai Home Service | daily | active |
| 8 | NoBroker | daily | active |
| 9 | Justdial | daily | active |
| 10 | Sulekha | daily | active |
| 11 | CallSevai | daily | active |

---

## Architecture

```
API Layer (FastAPI + /api/predictive/*)
    ↓
Analytics Layer (time_series, growth_model, expansion_predictor, confidence)
    ↓
Decision Support Layer (risk_evaluator, opportunity_miner, recommendation)
    ↓
Service Layer (recommendations with LLM briefing, learning, explanations)
    ↓
Repository Layer (competitor_change_events, prediction_evaluations)
    ↓
Database Layer (PostgreSQL + composite indexes + async)
    ↓
Scheduler (weekly backtest cron + prediction regeneration)
```
