# Version Information

## Current Version

**Utservio Intelligence Platform v1.0.0**

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-07-16 | Engineering Team | Initial production release |
| 0.9.0 | 2025-07-15 | Engineering Team | Dashboard + React frontend |
| 0.8.0 | 2025-07-14 | Engineering Team | API endpoints + auth |
| 0.7.0 | 2025-07-13 | Engineering Team | Collection pipeline |
| 0.6.0 | 2025-07-12 | Engineering Team | Parser engine |
| 0.5.0 | 2025-07-11 | Engineering Team | Database layer |
| 0.4.0 | 2025-07-10 | Engineering Team | Scheduler + queue |
| 0.3.0 | 2025-07-09 | Engineering Team | Collectors |
| 0.2.0 | 2025-07-08 | Engineering Team | Configuration |
| 0.1.0 | 2025-07-07 | Engineering Team | Initial scaffolding |

## Component Versions

| Component | Version | Last Updated |
|-----------|---------|--------------|
| FastAPI | 0.115+ | 2025-07-16 |
| SQLAlchemy | 2.0+ | 2025-07-16 |
| React | 18.3+ | 2025-07-16 |
| Vite | 6.3+ | 2025-07-16 |
| Tailwind CSS | 3.4+ | 2025-07-16 |
| TypeScript | 5.8+ | 2025-07-16 |
| Python | 3.11+ | 2025-07-16 |
| Docker | 24+ | 2025-07-16 |
| PostgreSQL | 15+ | 2025-07-16 |
| Redis | 7+ | 2025-07-16 |

## Release Notes

### v1.0.0 (2025-07-16)

**Production Release**

#### Features
- Complete React dashboard with 8 pages
- REST API with 25+ endpoints
- Basic Auth authentication
- Real-time polling for all data
- Competitor CRUD with bulk operations
- Collection pipeline with queue integration
- Scheduler with pause/resume controls
- Structured logging with JSON output
- Prometheus metrics export
- Alerting system with configurable rules
- Webhook notifications (Slack/Teams)
- CSV/JSON export functionality
- Global search across all entities
- System health monitoring
- Resource usage telemetry

#### Bug Fixes
- Fixed duplicated routes in dashboard API
- Fixed undefined `q` variable in search
- Fixed technographic collector upsert logic
- Fixed missing imports in API endpoints

#### Infrastructure
- Docker Compose with Redis
- Health checks for all services
- Database migrations (5 versions)
- Environment variable configuration

#### Documentation
- 15 comprehensive documentation files
- Architecture diagrams (Mermaid)
- API reference
- Deployment guide
- Acceptance criteria

### v0.9.0 (2025-07-15)

**Dashboard Release**

- React 18 + Vite 6 + Tailwind CSS
- 8 page components
- Layout with sidebar + topbar
- Authentication flow
- usePolling and useDebounce hooks
- API client with all endpoints
- TypeScript type definitions

### v0.8.0 (2025-07-14)

**API Release**

- Dashboard API endpoints
- Competitor CRUD API
- Collection trigger API
- Health check endpoints
- Authentication middleware
- Rate limiting middleware

### v0.7.0 (2025-07-13)

**Collection Release**

- Collection pipeline orchestrator
- HybridFetcher (httpx + Playwright)
- 7 data collectors
- Crawl frontier
- Budget enforcement

### v0.6.0 (2025-07-12)

**Parser Release**

- Strategy pattern parser
- 23 parsing strategies
- Entity deduplication
- Relationship linking
- Confidence scoring

### v0.5.0 (2025-07-11)

**Database Release**

- SQLAlchemy async ORM
- 13 database models
- Repository pattern
- Database migrations
- Connection pooling

### v0.4.0 (2025-07-10)

**Scheduler Release**

- APScheduler integration
- Collection scheduling
- Message queue (InMemory + Redis)
- Worker pool

### v0.3.0 (2025-07-09)

**Collector Release**

- Company information extraction
- Service listing extraction
- Pricing data extraction
- Content extraction
- Social profile extraction
- Technology detection
- URL discovery

### v0.2.0 (2025-07-08)

**Configuration Release**

- Pydantic Settings
- Environment variable support
- CI_ prefix for all config
- Secrets management

### v0.1.0 (2025-07-07)

**Scaffolding Release**

- Project structure
- FastAPI application factory
- Basic routing
- Dockerfile
- docker-compose.yml

## Known Issues

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| ISSUE-001 | No WebSocket for real-time updates | Low | Planned |
| ISSUE-002 | No dark mode | Low | Planned |
| ISSUE-003 | No data visualization charts | Medium | Planned |
| ISSUE-004 | No export scheduling | Low | Planned |
| ISSUE-005 | No notification center | Medium | Planned |

## Deprecations

| Component | Deprecated In | Removed In | Replacement |
|-----------|---------------|------------|-------------|
| `dashboard.html` | v0.8.0 | v1.0.0 | React SPA |
| InMemory Queue | v0.4.0 | N/A | Redis (production) |

## Upgrade Path

### From v0.9.0 to v1.0.0

1. Update dependencies: `uv sync`
2. Run migrations: `alembic upgrade head`
3. Update environment variables (add `CI_` prefix)
4. Rebuild frontend: `cd frontend && npm run build`
5. Restart services: `docker-compose restart`

### From v0.8.0 to v0.9.0

1. Update dependencies: `uv sync`
2. Run migrations: `alembic upgrade head`
3. Build frontend: `cd frontend && npm install && npm run build`

### From v0.7.0 to v0.8.0

1. Update dependencies: `uv sync`
2. Run migrations: `alembic upgrade head`
3. Update environment variables

## Roadmap

### v1.1.0 (Planned)

- WebSocket for real-time updates
- Dark mode toggle
- Data visualization charts
- Export scheduling
- Notification center

### v1.2.0 (Planned)

- Multi-user authentication (JWT)
- Role-based access control
- Audit logging
- SSO integration

### v2.0.0 (Planned)

- AI-powered insights
- Predictive analytics
- Automated reporting
- Mobile app

## Support

| Channel | Response Time |
|---------|---------------|
| GitHub Issues | 24 hours |
| Email | 48 hours |
| Documentation | Self-service |

## License

Proprietary - All rights reserved.
