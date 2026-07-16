# Project Structure

## Overview

The Utservio Competitor Intelligence Engine follows a clean, modular architecture with clear separation between backend, frontend, and documentation.

## Complete Directory Tree

```text
competitor-intelligence-engine/
│
├── app/                              # Backend Python Application
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory, lifespan, middleware
│   │
│   ├── api/                          # API Layer
│   │   ├── __init__.py
│   │   ├── auth.py                   # API key authentication
│   │   ├── dependencies.py           # Dependency injection (get_session)
│   │   ├── middleware.py             # Rate limiting middleware
│   │   └── endpoints/               # Route handlers
│   │       ├── __init__.py
│   │       ├── dashboard.py          # Dashboard API (25+ endpoints)
│   │       ├── competitors.py        # Competitor CRUD API
│   │       ├── collection.py         # Collection trigger API
│   │       ├── health.py             # Health check endpoints
│   │       ├── metrics.py            # Prometheus metrics endpoint
│   │       └── reports.py            # Reporting endpoints
│   │
│   ├── collectors/                   # Data Collection Layer
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseCollector, shared fetcher
│   │   ├── company.py                # Company information extraction
│   │   ├── service.py                # Service listing extraction
│   │   ├── pricing.py                # Pricing data extraction
│   │   ├── content.py                # Blog/article extraction
│   │   ├── social.py                 # Social profile extraction
│   │   ├── technographic.py          # Technology stack detection
│   │   ├── discovery.py              # URL discovery (robots.txt, sitemaps)
│   │   ├── fetcher.py                # HybridFetcher (httpx + Playwright)
│   │   ├── budget_engine.py          # Legacy budget engine
│   │   └── crawl_budget.py           # Crawl budget enforcement
│   │
│   ├── parsers/                      # Data Parsing Layer
│   │   ├── __init__.py
│   │   ├── strategy_parser.py        # Main parser orchestrator
│   │   ├── entity_resolver.py        # Entity deduplication
│   │   ├── relationship_engine.py    # Entity relationship linking
│   │   ├── confidence.py             # Confidence scoring
│   │   ├── url_normalizer.py         # URL normalization
│   │   ├── content_hasher.py         # Content hashing
│   │   └── strategies/              # 23 parsing strategies
│   │       ├── __init__.py
│   │       ├── json_ld.py
│   │       ├── schema_org.py
│   │       ├── microdata.py
│   │       ├── table.py
│   │       ├── form.py
│   │       ├── faq.py
│   │       ├── breadcrumb.py
│   │       ├── semantic_html.py
│   │       ├── card.py
│   │       ├── list.py
│   │       ├── location.py
│   │       ├── team.py
│   │       ├── review.py
│   │       ├── trust_signal.py
│   │       ├── asset.py
│   │       ├── media.py
│   │       ├── generic_dom.py
│   │       ├── generic_css.py
│   │       ├── regex.py
│   │       ├── metadata.py
│   │       ├── multi_pass.py
│   │       └── llm_fallback.py
│   │
│   ├── configuration/                # Configuration Management
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic Settings (CI_ prefix)
│   │   └── secrets.py                # Vault/secrets integration
│   │
│   ├── database/                     # Database Layer
│   │   ├── __init__.py
│   │   ├── connection.py             # DatabaseManager, async engine
│   │   ├── models.py                 # 13 SQLAlchemy models
│   │   └── repositories/            # Repository pattern
│   │       ├── __init__.py
│   │       ├── base.py               # BaseRepository[T]
│   │       ├── competitor_repository.py
│   │       ├── competitor_source_repository.py
│   │       ├── page_repository.py
│   │       ├── service_repository.py
│   │       ├── pricing_repository.py
│   │       ├── content_repository.py
│   │       ├── social_repository.py
│   │       ├── collection_log_repository.py
│   │       ├── raw_storage_repository.py
│   │       ├── tech_stack_repository.py
│   │       ├── team_repository.py
│   │       ├── certification_repository.py
│   │       └── service_area_repository.py
│   │
│   ├── services/                     # Service Layer
│   │   ├── __init__.py
│   │   ├── collection_service.py     # Collection pipeline orchestrator
│   │   ├── reporting_service.py      # Report generation
│   │   ├── webhook_service.py        # Slack/Teams notifications
│   │   ├── config_sync_service.py    # Config → DB sync
│   │   └── visual_diff_service.py    # Screenshot comparison
│   │
│   ├── schedulers/                   # Scheduler
│   │   ├── __init__.py
│   │   └── scheduler.py              # CollectionScheduler
│   │
│   ├── workers/                      # Worker System
│   │   └── __init__.py               # CollectionWorker, WorkerPool
│   │
│   ├── messagequeue/                 # Message Queue
│   │   ├── __init__.py
│   │   └── queue.py                  # InMemory + Redis backends
│   │
│   ├── observability/                # Observability
│   │   ├── __init__.py
│   │   ├── alerting.py               # AlertManager, rules
│   │   ├── prometheus_metrics.py     # Metrics collection
│   │   ├── monitoring_dashboard.py   # Monitoring API
│   │   ├── apm_endpoint.py           # APM endpoint
│   │   ├── log_buffer.py             # Real-time log capture
│   │   └── parser_metrics.py         # Parser-specific metrics
│   │
│   ├── storage/                      # Storage
│   │   ├── __init__.py
│   │   └── provider.py               # Local + S3 storage
│   │
│   ├── crawlfrontier/                # Crawl Frontier
│   │   ├── __init__.py
│   │   └── frontier.py               # URL priority queue
│   │
│   ├── static/                       # Static Files
│   │   └── dashboard.html            # Legacy dashboard UI
│   │
│   └── templates/                    # Templates
│
├── frontend/                         # React Frontend Application
│   ├── index.html                    # HTML entry point
│   ├── package.json                  # Dependencies
│   ├── tsconfig.json                 # TypeScript config
│   ├── vite.config.ts                # Vite config + API proxy
│   ├── tailwind.config.js            # Tailwind config
│   ├── postcss.config.js             # PostCSS config
│   └── src/
│       ├── main.tsx                  # React entry point
│       ├── App.tsx                   # Root component + routing
│       ├── index.css                 # Global styles
│       ├── vite-env.d.ts             # Type declarations
│       ├── components/
│       │   └── Layout.tsx            # Main layout
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── OverviewPage.tsx
│       │   ├── CompetitorsPage.tsx
│       │   ├── CompetitorProfilePage.tsx
│       │   ├── CollectionsPage.tsx
│       │   ├── LogsPage.tsx
│       │   ├── ReportsPage.tsx
│       │   └── AdminPage.tsx
│       ├── hooks/
│       │   └── index.ts
│       ├── lib/
│       │   ├── api.ts
│       │   └── utils.ts
│       └── types/
│           └── index.ts
│
├── migrations/                       # Alembic Migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial.py
│       ├── 002_add_team_certs_areas.py
│       ├── 003_add_storage_uri_provenance.py
│       ├── 004_add_unique_constraints.py
│       └── 005_add_raw_storage_extracted_data.py
│
├── tests/                            # Test Suite
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/                         # Unit tests
│   │   ├── test_parsers.py
│   │   ├── test_hybrid_fetcher.py
│   │   ├── test_url_normalizer.py
│   │   ├── test_content_hasher.py
│   │   ├── test_resolution.py
│   │   ├── test_relationships.py
│   │   └── ... (25 files)
│   └── integration/                  # Integration tests
│       ├── test_competitor_repository.py
│       ├── test_parsing_pipeline.py
│       └── ... (13 files)
│
├── scripts/                          # Utility Scripts
│   ├── collect.py                    # CLI collection trigger
│   └── seed.py                       # Database seeding
│
├── docs/                             # Documentation
│   ├── architecture.md
│   ├── data-flow.md
│   ├── module-integration.md
│   ├── database.md
│   ├── api.md
│   ├── production-features.md
│   ├── security.md
│   ├── scalability-performance.md
│   ├── known-limitations.md
│   ├── future-scope.md
│   ├── installation-guide.md
│   ├── verification-checklist.md
│   ├── ui-guide.md
│   ├── project-structure.md
│   └── pipeline_architecture.md
│
├── documentation/                    # Legacy Documentation
│   ├── architecture.md
│   ├── future-improvements.md
│   └── known-limitations.md
│

│   └── competitors.json
│
├── storage/                          # Runtime Storage
│   ├── raw_html/
│   └── screenshots/
│
├── scratch/                          # Development Scratch
│   └── add_modal.py
│
├── .env                              # Environment Variables
├── .env.example                      # Environment Template
├── alembic.ini                       # Alembic Configuration
├── pyproject.toml                    # Python Project Config
├── Dockerfile                        # Docker Image
├── docker-compose.yml                # Docker Compose (dev)
├── docker-compose.staging.yml        # Docker Compose (staging)
├── docker-compose.test.yml           # Docker Compose (test)
├── entrypoint.sh                     # Docker Entrypoint
├── competitors.json                  # Competitor Configuration
├── README.md                         # Project README
├── CONTRIBUTING.md                   # Contribution Guidelines
├── SECURITY.md                       # Security Policy
└── LICENSE                           # License
```

## Directory Responsibilities

### `app/` - Backend Application

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| `app/api/` | HTTP request handling, routing, authentication | `dashboard.py`, `competitors.py`, `auth.py` |
| `app/collectors/` | Web scraping, data extraction | `fetcher.py`, `discovery.py`, `company.py` |
| `app/parsers/` | HTML parsing, entity extraction | `strategy_parser.py`, `strategies/` |
| `app/configuration/` | Settings, secrets management | `settings.py`, `secrets.py` |
| `app/database/` | ORM models, repository pattern | `models.py`, `repositories/` |
| `app/services/` | Business logic orchestration | `collection_service.py`, `reporting_service.py` |
| `app/schedulers/` | Periodic job scheduling | `scheduler.py` |
| `app/workers/` | Queue consumption, background processing | `__init__.py` |
| `app/messagequeue/` | Message pub/sub, queue backends | `queue.py` |
| `app/observability/` | Metrics, logging, alerting | `prometheus_metrics.py`, `alerting.py` |
| `app/storage/` | File storage (local/S3) | `provider.py` |
| `app/crawlfrontier/` | URL priority scheduling | `frontier.py` |

### `frontend/` - React Application

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| `frontend/src/components/` | Reusable UI components | `Layout.tsx` |
| `frontend/src/pages/` | Page-level components | `OverviewPage.tsx`, `CompetitorsPage.tsx` |
| `frontend/src/hooks/` | Custom React hooks | `usePolling`, `useDebounce` |
| `frontend/src/lib/` | Utilities, API client | `api.ts`, `utils.ts` |
| `frontend/src/types/` | TypeScript type definitions | `index.ts` |

### `migrations/` - Database Schema

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| `migrations/versions/` | Schema migration scripts | `001_initial.py` through `005_*.py` |

### `tests/` - Test Suite

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| `tests/unit/` | Isolated component tests | `test_parsers.py`, `test_hybrid_fetcher.py` |
| `tests/integration/` | Database + pipeline tests | `test_parsing_pipeline.py`, `test_*_repository.py` |

### `docs/` - Documentation

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| `docs/` | Complete project documentation | 14 markdown files covering architecture, API, security, etc. |

## Key File Relationships

```
main.py
  ├── imports api/endpoints/*.py (routers)
  ├── imports configuration/settings.py (config)
  ├── imports database/connection.py (DB)
  ├── imports messagequeue/queue.py (queue)
  ├── imports schedulers/scheduler.py (scheduler)
  ├── imports observability/alerting.py (alerts)
  └── imports observability/log_buffer.py (logging)

collection_service.py
  ├── imports collectors/*.py (scraping)
  ├── imports parsers/strategy_parser.py (parsing)
  ├── imports database/repositories/*.py (storage)
  └── imports services/webhook_service.py (notify)

scheduler.py
  ├── imports database/connection.py (DB queries)
  ├── imports messagequeue/queue.py (publish jobs)
  └── imports configuration/settings.py (intervals)

worker.py
  ├── imports messagequeue/queue.py (consume jobs)
  └── imports collection_service.py (execute pipeline)
```
