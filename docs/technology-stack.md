# Technology Stack

## Overview

The Utservio Intelligence Platform uses a modern, production-ready technology stack optimized for performance, scalability, and developer experience.

## Backend Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Core runtime |
| **Web Framework** | FastAPI | 0.115+ | Async HTTP server, API endpoints |
| **ASGI Server** | Uvicorn | 0.34+ | Production ASGI server |
| **ORM** | SQLAlchemy | 2.0+ | Database models, async queries |
| **Database** | SQLite | 3.45+ | Local development |
| | PostgreSQL | 15+ | Production database |
| **Migrations** | Alembic | 1.15+ | Schema versioning |
| **HTTP Client** | httpx | 0.28+ | External API calls, web scraping |
| **Browser Automation** | Playwright | 1.50+ | JavaScript-rendered page crawling |
| **Stealth** | playwright-stealth | 1.0+ | Bot detection bypass |
| **HTML Parsing** | BeautifulSoup4 | 4.13+ | DOM parsing |
| | lxml | 5.3+ | Fast HTML/XML parsing |
| **AI Integration** | OpenAI SDK | 1.82+ | LLM fallback parsing |
| **Async** | asyncio | stdlib | Concurrent operations |
| **Configuration** | Pydantic Settings | 2.8+ | Type-safe settings |
| **Validation** | Pydantic | 2.11+ | Data validation |
| **Logging** | structlog | 25.4+ | Structured JSON logging |
| **Metrics** | prometheus-client | 0.22+ | Prometheus metrics |
| **Rate Limiting** | slowapi | 0.1+ | API rate limiting |
| **Caching** | cachetools | 5.5+ | In-memory caching |
| **Scheduling** | APScheduler | 3.11+ | Background job scheduling |
| **Resilience** | tenacity | 9.1+ | Retry logic with backoff |
| **File Storage** | aiofiles | 24.1+ | Async file I/O |
| **System Metrics** | psutil | 7.0+ | CPU, memory, disk monitoring |
| **Containerization** | Docker | 24+ | Application packaging |
| | Docker Compose | 2.28+ | Multi-service orchestration |

## Frontend Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | TypeScript | 5.8+ | Type-safe JavaScript |
| **Framework** | React | 18.3+ | UI component system |
| **Build Tool** | Vite | 6.3+ | Fast dev server + bundler |
| **CSS Framework** | Tailwind CSS | 3.4+ | Utility-first styling |
| **Routing** | react-router-dom | 7.7+ | Client-side routing |
| **Linting** | ESLint | 9.25+ | Code quality |
| **Type Checking** | TypeScript Compiler | 5.8+ | Static analysis |
| **Package Manager** | npm | 10+ | Dependency management |

## Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Package Manager** | uv | 0.11+ | Python dependency management |
| **Testing** | pytest | 9.0+ | Test framework |
| **Mocking** | pytest-asyncio | 1.0+ | Async test support |
| **Coverage** | coverage | 7.10+ | Code coverage reporting |
| **Pre-commit** | pre-commit | 4.3+ | Git hooks |
| **Linting** | Ruff | 1.13+ | Fast Python linter |
| **Formatting** | Ruff Format | 1.13+ | Code formatting |
| **Type Checking** | mypy | 1.18+ | Static type analysis |
| **Documentation** | MkDocs | 1.9+ | Documentation site |
| | Material for MkDocs | 9.5+ | Documentation theme |

## Infrastructure Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Container Runtime** | Docker | Application isolation |
| **Orchestration** | Docker Compose | Multi-service management |
| **Reverse Proxy** | Nginx (optional) | Load balancing, SSL termination |
| **Message Queue** | Redis (optional) | Distributed job queue |
| **Storage** | Local FS / S3 | Raw HTML, screenshots, exports |
| **Monitoring** | Prometheus | Metrics collection |
| | Grafana (optional) | Metrics visualization |
| **Logging** | structlog → stdout | Centralized log aggregation |

## Version Pinning Strategy

| Category | Strategy | Rationale |
|----------|----------|-----------|
| Python | >=3.11,<4.0 | Access to modern async features |
| FastAPI | ~=0.115 | API stability, async support |
| SQLAlchemy | ~=2.0 | Async ORM, modern API |
| React | ~=18.3 | Stability, concurrent features |
| Vite | ~=6.3 | Fast builds, ESM support |
| Tailwind | ~=3.4 | Utility-first, JIT compilation |
| Docker | >=24.0 | Container features |
| Node.js | >=18.0 | LTS, npm compatibility |

## Dependency Count

| Category | Count |
|----------|-------|
| Python Backend | 35+ |
| Frontend | 12+ |
| Development | 15+ |
| **Total** | **62+** |

## Technology Decision Matrix

| Requirement | Choice | Alternative Considered | Decision Factor |
|------------|--------|----------------------|-----------------|
| Async HTTP | httpx | aiohttp | Better API, type hints |
| JS Rendering | Playwright | Selenium, Puppeteer | Async, Python native |
| ORM | SQLAlchemy | Tortoise, Prisma | Ecosystem, maturity |
| Database | SQLite → PostgreSQL | MongoDB | SQL for structured data |
| Frontend | React | Vue, Angular | Ecosystem, TypeScript |
| Styling | Tailwind | CSS Modules, styled-components | Speed, consistency |
| Build | Vite | Webpack | Speed, DX |
| Logging | structlog | logging | Structured output, JSON |
| Metrics | prometheus-client | statsd | Industry standard |
| Config | Pydantic Settings | python-dotenv | Type validation |
