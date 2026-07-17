# Utservio — System Architecture

## Overview

Utservio is a full-stack competitor intelligence platform that automatically scrapes, extracts, and monitors competitor data from home warranty companies. The system follows a pipeline architecture: discover → fetch → extract → store → detect changes → visualize.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPETITOR WEBSITES                         │
│              (5 home warranty companies scraped)                │
│  homewarranty.firstam.com │ choicehomewarranty.com │ ahs.com    │
│  totalhomeprotection.com │ cinchhomeservices.com                │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY ENGINE                             │
│                                                                 │
│  Sources:                                                       │
│  ├── sitemap.xml parsing                                        │
│  ├── robots.txt analysis                                        │
│  ├── HTML link extraction                                       │
│  └── Common path guessing (/plans, /pricing, /about)            │
│                                                                 │
│  Output: List of DiscoveredURL objects with source tracking     │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 HYBRID FETCHER (Playwright)                     │
│                                                                 │
│  Two modes:                                                     │
│  ├── HTTP (httpx) — fast, lightweight                           │
│  └── Headless Browser (Chromium) — JS-rendered pages            │
│                                                                 │
│  Features:                                                      │
│  ├── Stealth initialization (anti-detection)                    │
│  ├── 5 rotating user agents                                     │
│  ├── Anti-detection browser arguments                           │
│  ├── Response caching                                           │
│  └── Handles Akamai, Cloudflare, bot protection                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              SPECIALIZED COLLECTORS (5)                         │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Company  │ │ Service  │ │ Pricing  │ │ Content  │ │ Social │ │
│  │Collector │ │Collector │ │Collector │ │Collector │ │Collect.│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                                 │
│  Each collector:                                                │
│  ├── Fetches relevant URLs                                      │
│  ├── Parses HTML with BeautifulSoup                             │
│  ├── Extracts structured data                                   │
│  ├── Validates output (rejects nav/phone/questions)             │
│  └── Stores in database with content hashes                     │
│                                                                 │
│  + TechnographicCollector (detects tech stack, no DB write)     │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL (8 tables)                        │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐     │
│  │ competitors │  │   sources    │  │  competitor_services │    │
│  │ (config)    │  │  (URLs)      │  │  (plans/coverage)   │     │
│  └─────────────┘  └──────────────┘  └─────────────────────┘     │
│  ┌─────────────────────┐  ┌──────────────────────┐              │
│  │ competitor_pricing  │  │ competitor_content    │             │
│  │ (prices/offers)     │  │ (blogs/articles)      │             │
│  └─────────────────────┘  └──────────────────────┘              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐    │
│  │ competitor_social│  │  raw_storage     │  │collection_  │    │
│  │ (profiles)       │  │ (raw HTML)       │  │logs         │    │
│  └──────────────────┘  └──────────────────┘  └─────────────┘    │
│  ┌──────────────────┐                                           │
│  │  change_logs     │                                           │
│  │ (diff tracking)  │                                           │
│  └──────────────────┘                                           │
└───────────┬────────────────────────────────────┬────────────────┘
            ▼                                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│   CHANGE DETECTION       │    │        REST APIs (51)           │
│                          │    │                                 │
│  Compares current vs     │    │  Authentication:                │
│  previous collections    │    │  ├── Basic Auth (dashboard)     │
│  using content hashes    │    │  └── API Key (collection)       │
│                          │    │                                 │
│  Tracks:                 │    │  Endpoints:                     │
│  ├── Added records       │    │  ├── CRUD operations            │
│  ├── Removed records     │    │  ├── Stats & telemetry          │
│  └── Modified records    │    │  ├── Feed & activity            │
│                          │    │  ├── Trends & comparison        │
│  Stores in change_logs   │    │  ├── Export (PDF/CSV/ZIP)       │
│  with before/after values│    │  ├── Scheduler control          │
└───────────┬──────────────┘    │  └── System health              │
            ▼                   └──────────────┬──────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    REACT DASHBOARD (9 pages)                    │
│                                                                 │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌────────────────┐   │
│  │Overview  │ │Competitors │ │ Competitor│ │   Competitor   │   │
│  │(KPIs,    │ │(List,      │ │  Profile  │ │    Compare     │   │
│  │ charts,  │ │ Search,    │ │ (Detail,  │ │  (2-4 side by  │   │
│  │ activity)│ │ Filter)    │ │ Extract)  │ │    side)       │   │
│  └──────────┘ └────────────┘ └───────────┘ └────────────────┘   │
│  ┌────────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐   │
│  │Collections │ │ Logs │ │Reports  │ │ Activity │ │  Admin  │   │ 
│  │(Monitor,   │ │(Filter││(Summary,│ │ (Full    │ │(Health, │   │
│  │ Pause)     │ │ Pagin.)│ │ Export) │ │ history) │Config)  │   │
│  └────────────┘ └──────┘ └─────────┘ └──────────┘ └─────────┘   │
│                                                                 │
│  Tech: React 18 + TypeScript + Tailwind CSS                     │
│  Theme: Orange (#ff8811) + Dark sidebar                         │
│  Features: Refresh buttons, loading states, new-tab links       │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               WEBSOCKET LIVE UPDATES                            │
│                                                                 │
│  Events broadcast to all connected clients:                     │
│  ├── collection_started     (competitor name, id)               │
│  ├── collection_completed   (records, duration, changes)        │
│  ├── collection_failed      (error message)                     │
│  └── changes_detected       (change list)                       │
│                                                                 │
│  Auto-reconnect with 3s delay                                   │
│  Ping/pong keepalive every 30s                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow (Detailed)

```
1. TRIGGER
   Dashboard API or Scheduler
        │
        ▼
2. MESSAGE QUEUE (in-memory)
   Publishes COLLECTION message
        │
        ▼
3. COLLECTION SERVICE
   ├── Load competitor config from DB
   ├── Broadcast: collection_started
   ├── Discovery Engine → find URLs
   ├── Save URLs to competitor_sources
   ├── For each module (company, services, pricing, content, social):
   │   ├── Select relevant URLs (pattern matching)
   │   ├── Fetch page (HTTP or Playwright)
   │   ├── Parse HTML (BeautifulSoup)
   │   ├── Extract structured data
   │   ├── Validate (reject noise)
   │   ├── Store in DB (upsert by content hash)
   │   └── Retry on failure (3x, exponential backoff)
   ├── Save collection_log entry
   ├── Detect changes (compare with previous snapshot)
   ├── Broadcast: collection_completed or changes_detected
   └── Broadcast: collection_failed (on error)
        │
        ▼
4. FRONTEND
   Receives WebSocket event → updates UI
   Polling refreshes stats, feed, health
```

---

## Authentication

| Endpoint Group | Auth Method | Header |
|---------------|-------------|--------|
| Dashboard API (`/api/dashboard/*`) | Basic Auth | `Authorization: Basic base64(admin:admin123)` |
| Collection API (`/collection/*`) | API Key | `X-API-Key: <key>` |
| WebSocket (`/ws`) | None | Direct connection |

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│                  DOCKER COMPOSE                     │
│                                                     │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐ │
│  │  PostgreSQL  │  │  FastAPI   │  │    React     │ │
│  │  Port: 5432  │  │  Port: 8000│  │  Port: 3000  │ │
│  │              │  │            │  │              │ │
│  │  Database:   │  │  Backend:  │  │  Frontend:   │ │
│  │  utservio_ci │  │  API + WS  │  │  Vite proxy  │ │
│  └──────────────┘  └────────────┘  └──────────────┘ │
│                                                     │
│  ┌──────────────┐                                   │
│  │   pgAdmin    │                                   │
│  │  Port: 5050  │                                   │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

1. **Short-lived DB sessions** — Every operation uses its own `async with db_manager.session()` to avoid connection leaks
2. **Content hash deduplication** — Prevents duplicate records across collections
3. **Retry with backoff** — `_collect_with_retry()` handles transient errors (timeout, 5xx, rate limits)
4. **Decimal→float conversion** — `_record_to_dict()` converts before JSON serialization to prevent crashes
5. **Options ref pattern** — WebSocket hook uses `optionsRef.current` for stable callback references
6. **Paginated feed** — API returns `{ items, total, has_more }` for infinite scroll
7. **Separate auth layers** — Dashboard uses Basic Auth, collection triggers use API keys
