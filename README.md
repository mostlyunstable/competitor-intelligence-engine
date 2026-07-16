# Competitor Intelligence Engine

[![CI](https://github.com/mostlyunstable/competitor-intelligence-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/mostlyunstable/competitor-intelligence-engine/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)

An advanced, adaptive data collection engine that crawls competitor websites and stores structured data in PostgreSQL. Built for high-coverage extraction without the use of brittle CSS selectors.

## Features

- **23 Adaptive Extraction Strategies** - DOM-level parsing with zero CSS selectors
- **Hybrid Fetching** - Static HTML (httpx) + JavaScript rendering (Playwright)
- **Entity Resolution** - Automatic deduplication with fuzzy matching
- **Relationship Linking** - Connect extracted entities into graphs
- **Dynamic Confidence Scoring** - Per-field confidence with cross-strategy consistency
- **Evidence Metadata** - DOM path, XPath, and HTML snippet for every extraction
- **Incremental Crawling** - ETag/Last-Modified conditional requests
- **Crawl Budget** - Per-competitor page/byte/time limits
- **Message Queue** - In-memory or Redis-backed with DLQ support
- **Workers** - Background queue consumers for horizontal scaling
- **Scheduler** - Async scheduler with hourly/daily/weekly frequencies
- **Observability** - Prometheus metrics, structured logging, alerting
- **React Dashboard** - Professional SaaS frontend with all modules

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- PostgreSQL 14+

### Installation

```bash
# Clone
git clone <repo-url>
cd competitor-intelligence-engine

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# Frontend
cd frontend && npm install && cd ..
```

### Start

```bash
# Database (Docker)
docker run -d --name pg -p 5432:5432 -e POSTGRES_USER=utservio -e POSTGRES_PASSWORD=changeme -e POSTGRES_DB=utservio_ci postgres:16-alpine

# Backend
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend && npm run dev
```

- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Default login: `admin` / `admin123`

## Architecture

```
Frontend (React + Tailwind)
    ↓ HTTP
API Layer (FastAPI)
    ↓
Service Layer (CollectionService, ReportingService, WebhookService)
    ↓
Collector Layer (Company, Service, Pricing, Content, Social, Technographic)
    ↓
Parser Layer (23 Strategies + Entity Resolution + Relationship Linking)
    ↓
Repository Layer (13 Repositories with Native Upsert)
    ↓
Database Layer (PostgreSQL via SQLAlchemy Async)
```

## Documentation

> **New to the project?** Start with the [Documentation Index](docs/README.md) for a guided tour.

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture, components, lifecycles |
| [Data Flow](docs/data-flow.md) | Complete data flow diagrams |
| [Module Integration](docs/module-integration.md) | How all modules connect |
| [Database](docs/database.md) | ER diagram, tables, relationships |
| [API Reference](docs/api.md) | Complete API endpoint documentation |
| [Production Features](docs/production-features.md) | Production-ready feature matrix |
| [Security](docs/security.md) | Authentication, authorization, hardening |
| [Scalability & Performance](docs/scalability-performance.md) | Scaling architecture, optimizations |
| [Known Limitations](docs/known-limitations.md) | Current constraints and workarounds |
| [Future Scope](docs/future-scope.md) | Planned enhancements and extension points |
| [Installation Guide](docs/installation-guide.md) | Complete setup from fresh clone |
| [Verification Checklist](docs/verification-checklist.md) | Component verification matrix |
| [UI Guide](docs/ui-guide.md) | React frontend architecture, components, routing |
| [Project Structure](docs/project-structure.md) | Complete directory tree with responsibilities |
| [Technology Stack](docs/technology-stack.md) | All technologies, versions, and decisions |
| [API ↔ Frontend Mapping](docs/api-frontend-mapping.md) | Endpoint to page mapping |
| [End-to-End Flow](docs/end-to-end-flow.md) | Complete sequence diagrams |
| [Feature Traceability](docs/feature-traceability.md) | Requirements to implementation matrix |
| [Deployment Architecture](docs/deployment-architecture.md) | Docker, scaling, networking |
| [Acceptance Criteria](docs/acceptance-criteria.md) | All acceptance criteria with status |
| [Version Information](docs/version-information.md) | Release history and roadmap |

## Testing

```bash
pytest tests/ -v
mypy app
ruff check app
```

## License

See [LICENSE](LICENSE)
