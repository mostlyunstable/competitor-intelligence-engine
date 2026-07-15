# Known Limitations

## Current Limitations

The following are known limitations of the current implementation. These represent areas where the system functions but has constraints or where production hardening is needed.

### Infrastructure Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| No Kubernetes manifests | Cannot deploy to K8s clusters | Use Docker Compose for single-node |
| No CDN for frontend | Static assets served from FastAPI | Acceptable for internal use |
| No distributed scheduler | Single scheduler instance only | Sufficient for moderate workloads |
| No Redis Cluster | Single Redis instance | In-memory queue for development |
| No S3 storage | Raw HTML on local filesystem only | Sufficient for single-node |
| No Elasticsearch | Full-text search via SQL ILIKE | Acceptable for <10K records |

### Dashboard Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Polling instead of WebSockets | 10-30s data refresh delay | Acceptable for monitoring |
| No dark mode toggle | Single light theme | Can be added later |
| No mobile native app | Web-only access | Responsive design covers mobile |
| No export scheduling | Manual export only | Can be automated later |

### Pipeline Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| LLM Fallback requires API key | Extra cost for low-confidence extractions | Optional, configurable |
| Playwright memory usage | Higher memory per JS-rendered page | Crawl budget limits |
| Single-threaded Playwright | One browser instance per worker | Worker pool scaling |
| No proxy rotation | Single proxy or direct connection | Configurable proxy URLs |

### Data Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| No OCR | Cannot extract text from images | Future enhancement |
| No video analysis | Cannot process video content | Out of scope |
| No PDF parsing | Cannot extract from PDFs | Future enhancement |
| No API data collection | Web scraping only | Future enhancement |

### Security Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Basic Auth only | No OAuth2/OIDC | Sufficient for internal use |
| No RBAC | Single admin role | Can be extended |
| No audit logging | No compliance trail | Future enhancement |
| localStorage for credentials | XSS vulnerability if compromised | Acceptable for trusted environments |

## Implemented vs Future

### Fully Implemented

- 23 parsing strategies with adaptive ordering
- Entity resolution with fuzzy matching
- Relationship linking
- Dynamic confidence scoring
- Evidence metadata
- Incremental crawling
- Crawl budget enforcement
- Content hash deduplication
- Hybrid fetching (httpx + Playwright)
- Message queue with InMemory backend
- Worker pool with retry logic
- Async scheduler with pause/resume
- Prometheus metrics
- Structured logging
- Health checks
- Alerting system
- React dashboard with 8 modules
- Authentication (Basic + API Key)
- CRUD operations with validation
- Pagination, filtering, search
- Bulk operations
- CSV and ZIP export
- Docker deployment
- Alembic migrations

### Partially Implemented

- Redis queue backend (functional, needs production testing)
- S3 storage (stubbed, not functional)
- LLM fallback (requires external API key)
- Vault integration (wired, not configured)
- Webhook notifications (functional, needs Slack/Teams URLs)

### Not Implemented (Future Scope)

- Kubernetes deployment
- CDN for frontend
- WebSocket real-time updates
- Elasticsearch full-text search
- OAuth2/OIDC authentication
- RBAC with roles
- Audit logging
- OCR for images
- PDF parsing
- API data collection
- Multi-tenancy
- GraphQL API
- Auto scaling
- Distributed tracing
