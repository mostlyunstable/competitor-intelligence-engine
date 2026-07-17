# Utservio — Codebase Brain Map

A comprehensive guide to every important file in the project.

---

## Project Structure

```
competitor-intelligence-engine/
├── app/                    # Backend (FastAPI)
│   ├── api/               # API layer
│   ├── collectors/        # Data collection pipeline
│   ├── configuration/     # Settings & env vars
│   ├── database/          # Models, repos, connections
│   ├── messagequeue/      # In-memory message queue
│   ├── parsers/           # HTML parsing strategies
│   ├── schedulers/        # Automated collection scheduling
│   ├── services/          # Business logic
│   └── utilities/         # Helper functions
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # API client & utilities
│   │   └── pages/         # Page components
│   └── vite.config.ts     # Vite configuration
├── migrations/            # Alembic database migrations
├── docker-compose.yml     # Docker deployment
├── Dockerfile             # Backend container
├── pyproject.toml         # Python dependencies
└── competitors.json       # Competitor configurations (tracked in git)
```

---

## Backend Files

### Entry Point & Configuration

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app factory, lifespan, WebSocket endpoint `/ws`, queue worker, middleware setup. Imports all routers. |
| `app/configuration/settings.py` | Pydantic Settings class. All env vars use `CI_` prefix. DB URL, scheduler, stealth, webhook config. |
| `pyproject.toml` | Python dependencies: FastAPI, SQLAlchemy, Playwright, BeautifulSoup, structlog, etc. |

### API Layer

| File | Purpose |
|------|---------|
| `app/api/endpoints/dashboard.py` | **Main API file (1177 lines)** — stats, feed (paginated), health, telemetry, trends, compare, export PDF/CSV/ZIP, trigger collection. Uses Basic Auth. |
| `app/api/endpoints/collection.py` | Collection trigger endpoints. API key auth (`X-API-Key`). POST `/collect`, `/collect/{id}`. |
| `app/api/endpoints/competitors.py` | CRUD for competitors, extracted data retrieval, search endpoint. |
| `app/api/endpoints/health.py` | Health checks, system status, collection logs with filtering. |
| `app/api/endpoints/reports.py` | Reporting endpoints, CSV export, per-collection reports. |
| `app/api/auth.py` | API key authentication middleware. Checks `X-API-Key` header against `CI_API_KEY` env var. |
| `app/api/middleware.py` | Rate limiting middleware (300 req/min default). |

### Data Collection Pipeline

| File | Purpose |
|------|---------|
| `app/collectors/discovery.py` | URL discovery engine — sitemap.xml, robots.txt, HTML link extraction, common path guessing. Returns list of `DiscoveredURL` objects. |
| `app/collectors/fetcher.py` | **HybridFetcher (889 lines)** — HTTP (httpx) + Playwright headless browser. Stealth initialization, 5 user agents, anti-detection args, response caching. |
| `app/collectors/base.py` | Base collector class. Deduplication via content hashes. Shared fetcher instance. |
| `app/collectors/company.py` | Company data extraction — name, description, contact info, logo. |
| `app/collectors/service.py` | Service/plan extraction. `_is_valid_service()` filters out nav items, phone numbers, questions. Accepts coverage/plan patterns. |
| `app/collectors/pricing.py` | Price extraction. `_is_valid_pricing()` rejects nav, phone, URLs. Accepts real prices with currency detection. |
| `app/collectors/content.py` | Blog/article/news extraction from content pages. |
| `app/collectors/social.py` | Social media profile extraction — Facebook, Twitter, LinkedIn, Instagram. |
| `app/collectors/technographic.py` | Technology stack detection (simplified). Detects but doesn't write to DB. |

### Database Layer

| File | Purpose |
|------|---------|
| `app/database/connection.py` | SQLAlchemy async engine, session factory, connection pooling, table creation. |
| `app/database/models.py` | **All 8 active table models**: `Competitor`, `CompetitorSource`, `CompetitorService`, `CompetitorPricing`, `CompetitorContent`, `CompetitorSocial`, `RawStorage`, `CollectionLog`, `ChangeLog`. |
| `app/database/repositories/competitor_repository.py` | Competitor CRUD operations. |
| `app/database/repositories/competitor_source_repository.py` | URL source management, mark_crawled. |
| `app/database/repositories/collection_log_repository.py` | Collection history CRUD. |

### Services

| File | Purpose |
|------|---------|
| `app/services/collection_service.py` | **Core orchestration (431 lines)** — runs full collection pipeline: load config → discover URLs → save sources → collect per module → save collection log → detect changes → broadcast WebSocket events. Includes `_collect_with_retry()` with 3 retries, exponential backoff. |
| `app/services/change_detection_service.py` | Compares current vs previous collections using content hashes. Records added/removed/modified changes. Converts Decimal→float for JSON columns. |
| `app/services/websocket_manager.py` | `ConnectionManager` class. Tracks WebSocket connections. Broadcasts `collection_started`, `collection_completed`, `collection_failed`, `changes_detected` events. |
| `app/services/config_sync_service.py` | Reads `competitors.json` on startup and syncs to database. |
| `app/services/webhook_service.py` | Slack/Teams webhook notifications with retry logic. |
| `app/services/reporting_service.py` | Report generation for collections. |

### Message Queue

| File | Purpose |
|------|---------|
| `app/messagequeue/queue.py` | In-memory message queue with publish/subscribe, retry logic, handler registration. Used for async collection triggers. |

### Scheduling

| File | Purpose |
|------|---------|
| `app/schedulers/scheduler.py` | Automated collection scheduling. Triggers collections based on competitor frequency (daily, weekly, etc.). Pause/resume support. |

### Parsers

| File | Purpose |
|------|---------|
| `app/parsers/` | 23 HTML parsing strategies for different website structures. Adaptive ordering based on success rates. |

---

## Frontend Files

### Entry & Configuration

| File | Purpose |
|------|---------|
| `frontend/src/App.tsx` | Router setup, auth context (`AuthContext`), protected routes. 10 routes defined. |
| `frontend/src/main.tsx` | React root mount point. |
| `frontend/vite.config.ts` | Vite config. Proxies `/api`, `/health`, `/status` to backend:8000. Proxies `/ws` with WebSocket support. |
| `frontend/tailwind.config.js` | Tailwind theme — `brand` = orange (#ff8811), `surface` = near-black grays. |
| `frontend/src/index.css` | Global styles, component classes (`.card`, `.btn-primary`, `.btn-secondary`, `.input`, `.badge-*`), consistent `cursor: default` everywhere. |

### Hooks

| File | Purpose |
|------|---------|
| `frontend/src/hooks/index.ts` | `usePolling` — generic polling hook with refresh function. `useDebounce` — input debounce. |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket React hook. Connects to `/ws`, auto-reconnects, filters pong messages. Uses `optionsRef` for stable callbacks. |

### API Client

| File | Purpose |
|------|---------|
| `frontend/src/lib/api.ts` | API client class. All endpoints: stats, feed (paginated), health, telemetry, trends, compare, export PDF/CSV/ZIP, search, CRUD. Handles Basic Auth, 401 detection. |
| `frontend/src/lib/utils.ts` | Utility functions: `formatDate`, `timeAgo`, `formatDuration`. |

### Components

| File | Purpose |
|------|---------|
| `frontend/src/components/Layout.tsx` | Main layout — dark sidebar with nav links, top bar with search and user menu. |
| `frontend/src/components/Charts.tsx` | `BarChart` and `LineChart` components for trend visualization. |

### Pages

| File | Purpose |
|------|---------|
| `frontend/src/pages/OverviewPage.tsx` | **Dashboard** — 8 KPI cards, trend charts (14 days), recent activity feed, system status panel. Refresh button dims cards + spins icon. |
| `frontend/src/pages/CompetitorsPage.tsx` | Competitor list with search, filters (enabled, frequency), pagination, bulk actions (delete, enable, disable), add/edit modal with URL validation. |
| `frontend/src/pages/CompetitorProfilePage.tsx` | Individual competitor view — stats, extracted data (services, pricing, social, content), collection history, collect trigger, refresh. |
| `frontend/src/pages/CompetitorComparePage.tsx` | Side-by-side comparison — select 2-4 competitors, table + bar charts, entity counts. |
| `frontend/src/pages/CollectionsPage.tsx` | Real-time collection monitoring — logs, pause/resume scheduler, retry failed collections. |
| `frontend/src/pages/LogsPage.tsx` | Paginated collection logs with filters (competitor, success/failure). |
| `frontend/src/pages/ReportsPage.tsx` | Summary stats, download buttons (CSV, PDF, ZIP). PDF opens in new tab. |
| `frontend/src/pages/ActivityPage.tsx` | Full paginated activity history — 30 items per page, prev/next navigation. Opened in new tab from dashboard. |
| `frontend/src/pages/AdminPage.tsx` | System health, scheduler control, config view, resync competitors. |
| `frontend/src/pages/LoginPage.tsx` | Login form — admin/admin123. Credentials stored in localStorage. |

---

## Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Backend container. Python 3.12, Playwright with Chromium at `/ms-playwright`. |
| `frontend/Dockerfile` | Frontend container. Node 20 build + nginx serve. |
| `docker-compose.yml` | 3 services: `db` (PostgreSQL 16:5432), `backend` (FastAPI:8000), `frontend` (React:3000). pgAdmin at :5050. |
| `.dockerignore` | Excludes node_modules, __pycache__, .git, tests from build context. |
| `.env` | Environment config. `CI_API_KEY=` (empty for dev), `CI_STEALTH__PROXY_URL=` (optional). |
| `competitors.json` | 5 competitor configurations — name, URL, modules, frequency. Tracked in git. |
| `migrations/env.py` | Alembic migration environment. |

---

## Data Flow

```
competitors.json → ConfigSyncService → PostgreSQL (competitors table)
                                              ↓
Dashboard API (trigger) → MessageQueue → CollectionService
                                              ↓
                              ┌─── DiscoveryEngine (find URLs)
                              ├─── CompanyCollector
                              ├─── ServiceCollector
                              ├─── PricingCollector
                              ├─── ContentCollector
                              ├─── SocialCollector
                              └─── TechnographicCollector
                                              ↓
                              PostgreSQL (services, pricing, content, social)
                                              ↓
                              ChangeDetectionService → change_logs table
                                              ↓
                              WebSocketManager → broadcast to all clients
                                              ↓
                              Frontend (Live Events panel)
```

---

## Key Patterns

1. **Short-lived sessions** — Every DB operation uses its own `async with db_manager.session()` block
2. **Deduplication** — Content hashes prevent duplicate records
3. **Retry with backoff** — `_collect_with_retry()` handles transient errors (timeout, 5xx, rate limits)
4. **Decimal handling** — `_record_to_dict()` converts Decimal→float before JSON serialization
5. **WebSocket cleanup** — Both `WebSocketDisconnect` and generic `Exception` trigger disconnect
6. **Options ref pattern** — `useWebSocket` uses `optionsRef.current` for stable callback references
