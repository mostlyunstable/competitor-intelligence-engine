# Architecture

## Overview

The Utservio Competitor Intelligence Engine is a production-grade data collection system for competitor analysis. It extracts structured data from competitor websites using generic HTML parsing strategies, with no company-specific selectors.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Health     │  │ Competitors │  │ Collection  │            │
│  │   Status     │  │    CRUD     │  │   Trigger   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Collection Service                             ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │ Discover │  │ Collect  │  │  Parse   │  │  Store   │  ││
│  │  │   URLs   │  │  Pages   │  │  HTML    │  │  Data    │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Collector Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Company  │  │ Service  │  │ Pricing  │  │ Content  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Social  │  │ Discovery│  │Technogr. │  │  Crawl   │      │
│  └──────────┘  └──────────┘  └──────────┘  │  Budget  │      │
│                                             └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Parser Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Strategy Parser (Orchestrator)                 ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │   JSON-LD│  │ Schema   │  │Microdata │  │  Table   │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │   FAQ    │  │ Breadcrumb│  │ Semantic │  │   Card   │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │   List   │  │ Location │  │   Team   │  │  Review  │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │  Trust   │  │  Asset   │  │  Media   │  │  LLM     │  ││
│  │  │  Signal  │  │          │  │          │  │ Fallback │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           Post-Processing Pipeline                          ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │  Entity  │  │Relations │  │  Merge   │  │Evidence  │  ││
│  │  │Resolution│  │  Linking │  │ Results  │  │Metadata  │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Competitor│  │  Source  │  │   Page   │  │ Service  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Pricing  │  │ Content  │  │  Social  │  │   Log    │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │   Team   │  │  Certif. │  │Service   │                    │
│  │          │  │          │  │  Area    │                    │
│  └──────────┘  └──────────┘  └──────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Database Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    PostgreSQL                               ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │competitors│  │sources   │  │  pages   │  │ services │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │ pricing  │  │ content  │  │  social  │  │   logs   │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 ││
│  │  │   team   │  │  certs   │  │  areas   │                 ││
│  │  └──────────┘  └──────────┘  └──────────┘                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Parser Layer

The parser layer is the heart of the system, implementing 23 extraction strategies with dynamic confidence scoring.

#### Strategy Pattern

All strategies implement the `ParsingStrategy` ABC:

```python
class ParsingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def weight(self) -> float: ...

    @abstractmethod
    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult: ...
```

#### Strategy Execution Order

1. **MultiPassStrategy** - 6-pass combined extraction
2. **JsonLdStrategy** - JSON-LD structured data
3. **SchemaOrgStrategy** - Schema.org microdata
4. **MicrodataStrategy** - HTML5 microdata
5. **TableExtractionStrategy** - HTML tables
6. **FormExtractionStrategy** - Forms and inputs
7. **FaqExtractionStrategy** - FAQ sections
8. **BreadcrumbExtractionStrategy** - Navigation breadcrumbs
9. **SemanticHtmlStrategy** - Semantic HTML elements
10. **CardExtractionStrategy** - Card-based layouts
11. **ListExtractionStrategy** - List-based content
12. **LocationExtractionStrategy** - Office locations
13. **TeamExtractionStrategy** - Team members
14. **ReviewExtractionStrategy** - Reviews and testimonials
15. **TrustSignalExtractionStrategy** - Awards, certifications
16. **AssetExtractionStrategy** - Documents, downloads
17. **MediaExtractionStrategy** - Images, videos
18. **GenericDomHeuristicStrategy** - DOM structure analysis
19. **GenericCssPatternStrategy** - CSS pattern matching
20. **RegexPatternStrategy** - Regex extraction
21. **MetadataStrategy** - HTML meta tags
22. **LLMFallbackStrategy** - LLM extraction (when confidence < threshold)

#### Confidence Scoring

Each extraction receives a dynamic confidence score based on:

- **Base score** (0.25-0.85): Strategy-specific baseline
- **Completeness bonus** (+0.10): All expected fields present
- **Consistency bonus** (+0.10 per match, capped +0.30): Cross-strategy agreement
- **Validation bonus** (+0.05): Passes validation rules

#### Entity Resolution

Extracted entities are deduplicated using:

- **Normalization**: Lowercase, strip whitespace, remove special characters
- **Abbreviation expansion**: "St" → "Street", "Ave" → "Avenue"
- **Fuzzy matching**: Token Jaccard + containment (threshold 0.55)
- **Greedy clustering**: Groups similar entities together
- **Canonicalization**: Selects best representative

#### Relationship Linking

Entities are connected using:

- **Name matching**: Exact and fuzzy name comparison
- **Text overlap**: Shared text between entities
- **DOM proximity**: HTML element distance
- **Plan-feature dereferencing**: Links features to plans

### 2. Collector Layer

Collectors orchestrate data collection from competitor websites.

#### Hybrid Fetcher

The `HybridFetcher` supports:

- **Static pages**: httpx with connection pooling
- **JS-heavy pages**: Playwright with headless Chromium
- **Framework detection**: React, Vue, Angular, Next.js, Nuxt, Svelte
- **Conditional requests**: ETag/Last-Modified headers
- **Rate limiting**: Per-domain token bucket

#### Crawl Budget

Per-competitor budgets prevent over-crawling:

- **Page limit**: Maximum pages per collection
- **Byte limit**: Maximum data download
- **Time limit**: Maximum collection duration

### 3. Database Layer

#### Schema Design

13 tables with proper constraints:

- **Foreign keys**: Cascade delete from root entity
- **Unique constraints**: Enable native upsert
- **Content deduplication**: SHA-256 hashes
- **Provenance tracking**: JSON columns for data lineage

#### Repository Pattern

Each entity has a dedicated repository:

```python
class CompetitorServiceRepository(BaseRepository[CompetitorService]):
    async def get_by_hash(self, content_hash: str) -> CompetitorService | None: ...
    async def upsert(self, competitor_id: int, **kwargs) -> CompetitorService: ...
```

#### Native Upsert

PostgreSQL native upsert eliminates double-query anti-pattern:

```sql
INSERT INTO competitor_services (competitor_id, name, content_hash, ...)
VALUES ($1, $2, $3, ...)
ON CONFLICT (competitor_id, content_hash)
DO UPDATE SET name = EXCLUDED.name, ...
```

### 4. Observability Layer

#### Structured Logging

All logs use structlog with consistent fields:

```python
logger.info(
    "collection_started",
    competitor_id=1,
    url="https://example.com",
    modules=["services", "pricing"],
)
```

#### Prometheus Metrics

Key metrics exposed:

- `collections_total`: Total collections
- `collection_duration_seconds`: Collection duration
- `entities_extracted_total`: Entities extracted
- `parse_duration_seconds`: Parse time
- `confidence_score`: Extraction confidence

#### Alerting

Automated alerts for:

- High error rates
- Low extraction confidence
- Memory usage > 512MB
- Database connection failures
- Crawl budget exceeded

## Design Decisions

### 1. Zero CSS Selectors

All strategies use DOM semantics, not CSS selectors. This ensures:

- **Generality**: Works on any website
- **Maintainability**: No selector updates needed
- **Reliability**: Less breakage from website changes

### 2. Strategy Pattern

New extraction logic requires only:

1. Create a new file in `app/parsers/strategies/`
2. Implement `ParsingStrategy` ABC
3. Register in `DEFAULT_STRATEGIES`

No existing code modification required.

### 3. Dynamic Confidence

Confidence is per-field, not per-page. This enables:

- **Granular filtering**: Keep high-confidence fields
- **Debugging**: Identify low-confidence extractions
- **Quality tracking**: Monitor extraction quality over time

### 4. Evidence Metadata

Every extraction includes:

- **DOM path**: CSS selector to source element
- **XPath**: XML path to source element
- **HTML snippet**: Original HTML content

This enables debugging and validation without re-parsing.

## Scaling Considerations

### Current Capacity

- **10 competitors**: Comfortable
- **100 competitors**: With tuning
- **1000+ competitors**: Requires fundamental changes

### Scaling Roadmap

1. **Message queue**: Redis/RabbitMQ for task distribution
2. **Crawl frontier**: Intelligent page prioritization
3. **Distributed workers**: Horizontal scaling
4. **Database partitioning**: Sharding by competitor
5. **Read replicas**: Separate read/write paths

## Security

### Authentication

API endpoints require Bearer token authentication.

### Rate Limiting

- **Global**: 60 requests per minute
- **Per-domain**: Configurable per competitor
- **Crawl budget**: Per-competitor limits

### Input Validation

All inputs validated via Pydantic models.

### Secrets Management

Environment variables for sensitive configuration.

## Deployment

### Docker

Multi-stage build with:

- Python 3.12-slim base
- Playwright + Chromium for JS rendering
- Non-root user
- Health checks

### Kubernetes

Ready for deployment with:

- Liveness/readiness probes
- Resource limits
- Horizontal pod autoscaling

## Monitoring

### Health Checks

Composite health endpoint checking:

- Database connectivity + latency
- Scheduler status
- Fetcher/http client status
- Active crawl count
- Memory usage

### Dashboards

Pre-built dashboards for:

- System health
- Collection metrics
- Extraction quality
- Alert status

### Alerting

Automated alerts via:

- Prometheus Alertmanager
- Webhook notifications
- Email alerts (configurable)
