# Complete Data Flow

## Overview

This document traces data through every major pathway in the Utservio Competitor Intelligence Engine, from user interaction to database persistence and back.

## Dashboard Flow

The dashboard flow covers every interaction between the business user and the React frontend.

```mermaid
sequenceDiagram
    actor User as Business User
    participant FE as React Dashboard
    participant API as FastAPI
    participant Auth as Authentication
    participant Repo as Repository Layer
    participant DB as PostgreSQL

    User->>FE: Opens browser
    FE->>FE: Check localStorage for auth
    alt No credentials
        FE->>User: Show login page
        User->>FE: Enter admin/admin123
        FE->>API: GET /api/dashboard/stats (Basic Auth)
        API->>Auth: Verify credentials
        Auth-->>API: Authorized
        API->>Repo: Execute SQL queries
        Repo->>DB: SELECT counts, logs
        DB-->>Repo: Result sets
        Repo-->>API: Aggregated stats
        API-->>FE: JSON response
        FE->>FE: Store credentials in localStorage
        FE->>User: Redirect to dashboard
    end

    User->>FE: Navigates to Overview
    FE->>API: GET /api/dashboard/stats
    API->>Repo: Query competitors, logs, counts
    Repo->>DB: SELECT with aggregations
    DB-->>Repo: Statistics
    Repo-->>API: DashboardStats
    API-->>FE: JSON response
    FE->>User: Render KPI cards, charts

    User->>FE: Navigates to Competitors
    FE->>API: GET /api/dashboard/competitors?page=1&page_size=20
    API->>Repo: Query with pagination
    Repo->>DB: SELECT with OFFSET/LIMIT
    DB-->>Repo: Competitor list
    Repo-->>API: PaginatedCompetitors
    API-->>FE: JSON with total, page, total_pages
    FE->>User: Render table with pagination

    User->>FE: Clicks Add Competitor
    FE->>User: Show modal form
    User->>FE: Fill form, submit
    FE->>API: POST /api/dashboard/competitors
    API->>Repo: INSERT competitor
    Repo->>DB: INSERT with RETURNING
    DB-->>Repo: New competitor
    Repo-->>API: CompetitorResponse
    API-->>FE: 201 Created
    FE->>User: Close modal, refresh list
```

## Collection Flow

The collection flow traces how data moves from trigger to database persistence.

```mermaid
sequenceDiagram
    participant Sched as Scheduler
    participant MQ as MessageQueue
    participant Worker as WorkerPool
    participant CS as CollectionService
    participant DE as DiscoveryEngine
    participant HF as HybridFetcher
    participant SP as StrategyParser
    participant ER as EntityResolver
    participant Repo as Repository Layer
    participant DB as PostgreSQL
    participant WH as WebhookService
    participant PM as PrometheusMetrics

    Sched->>Sched: Check interval elapsed
    Sched->>DB: SELECT competitors WHERE enabled AND due
    DB-->>Sched: Due competitor list
    Sched->>MQ: Publish COLLECTION message {competitor_id}
    MQ->>Worker: Deliver message
    Worker->>CS: collect_competitor(competitor_id)

    CS->>DB: SELECT competitor config
    DB-->>CS: Competitor (name, url, modules, frequency)
    CS->>DE: discover(base_url)
    DE->>HF: Fetch robots.txt, sitemap
    HF-->>DE: URL list
    DE->>HF: Fetch navigation, footer links
    HF-->>DE: Additional URLs
    DE-->>CS: Discovered URLs (deduplicated, ranked)

    CS->>DB: INSERT discovered URLs (upsert)
    DB-->>CS: Sources saved

    loop For each module (company, services, pricing, content, social, technographic)
        CS->>CS: Select URLs matching module patterns
        loop For each URL
            CS->>HF: fetch(url, force_render=SPA?)
            HF->>HF: httpx (static) or Playwright (dynamic)
            HF-->>CS: FetchResult(html, headers, status)
            CS->>SP: parse(html, url)
            SP->>SP: Run 23 strategies in priority order
            SP->>ER: Resolve entities (dedup, normalize)
            ER->>ER: Fuzzy match, cluster
            SP->>SP: Link relationships
            SP->>SP: Score confidence per field
            SP-->>CS: ParsedResult(services, pricing, content, social)
            CS->>Repo: upsert per entity type
            Repo->>DB: INSERT ... ON CONFLICT UPDATE
            DB-->>Repo: Saved entities
        end
    end

    CS->>Repo: Create CollectionLog
    Repo->>DB: INSERT collection_log
    CS->>WH: notify_change(competitor, data_type, message)
    CS->>PM: counter(collection_total), histogram(duration)
    CS-->>Worker: CollectionResult
    Worker->>MQ: ACK message
```

## Report Generation Flow

```mermaid
sequenceDiagram
    actor User as Business User
    participant FE as React Dashboard
    participant API as FastAPI
    participant RS as ReportingService
    participant Repo as Repository Layer
    participant DB as PostgreSQL

    User->>FE: Clicks Reports
    FE->>API: GET /reports/compare
    API->>Repo: SELECT competitors with counts
    Repo->>DB: Aggregate queries
    DB-->>Repo: Competitor comparison data
    Repo-->>API: ComparisonResult
    API-->>FE: JSON comparison
    FE->>User: Render comparison table

    User->>FE: Clicks Export CSV
    FE->>API: GET /api/dashboard/compare/csv
    API->>Repo: SELECT competitors with pricing
    Repo->>DB: JOIN queries
    DB-->>Repo: Pricing data
    API->>API: Generate CSV string
    API-->>FE: StreamingResponse (text/csv)
    FE->>User: Download competitor_pricing_comparison.csv

    User->>FE: Clicks Export ZIP
    FE->>API: GET /api/dashboard/export/zip
    API->>Repo: SELECT raw_storage with extracted_data
    Repo->>DB: Query with limits
    DB-->>Repo: Raw storage records
    API->>API: Create ZIP (JSON + HTML per competitor)
    API-->>FE: StreamingResponse (application/zip)
    FE->>User: Download competitor_intelligence_export.zip

    User->>FE: Clicks competitor in Reports
    FE->>API: GET /reports/trends/{competitor_id}
    API->>Repo: SELECT collection_logs for competitor
    Repo->>DB: Time-series query
    DB-->>Repo: Historical logs
    API->>RS: compute_trends(competitor, logs)
    RS-->>API: TrendReport
    API-->>FE: JSON trends
    FE->>User: Render trend chart
```

## Search Flow

```mermaid
sequenceDiagram
    actor User as Business User
    participant FE as React Dashboard
    participant API as FastAPI
    participant DB as PostgreSQL

    User->>FE: Types in search bar
    FE->>FE: Debounce (300ms)
    FE->>API: GET /api/dashboard/search?q=cloud
    API->>DB: SELECT raw_storage WHERE extracted_data::text ILIKE '%cloud%' LIMIT 100
    DB-->>API: Matching raw storage records
    API->>API: Deduplicate by competitor_id
    API->>API: Find match context (service, pricing, etc.)
    API-->>FE: {query, results: [{competitor_id, name, context}]}
    FE->>User: Show dropdown with results
    User->>FE: Clicks result
    FE->>User: Navigate to /competitors/{id}
```

## Authentication Flow

```mermaid
sequenceDiagram
    actor User as Business User
    participant FE as React Dashboard
    participant API as FastAPI
    participant Auth as HTTPBasic

    User->>FE: Opens /login
    FE->>User: Show login form
    User->>FE: Enter admin / admin123
    FE->>FE: Encode to Base64
    FE->>API: GET /api/dashboard/stats (Authorization: Basic YWRtaW46YWRtaW4xMjM=)
    API->>Auth: Extract credentials
    Auth->>Auth: secrets.compare_digest(username, ADMIN_USER)
    Auth->>Auth: secrets.compare_digest(password, ADMIN_PASSWORD)
    alt Credentials valid
        Auth-->>API: Authorized
        API->>API: Execute endpoint logic
        API-->>FE: 200 OK with stats
        FE->>FE: localStorage.setItem('auth', base64)
        FE->>User: Redirect to /
    else Credentials invalid
        Auth-->>API: 401 Unauthorized
        API-->>FE: 401 with WWW-Authenticate header
        FE->>User: Show "Invalid credentials"
    end

    Note over FE: Subsequent requests include auth header
    FE->>API: GET /api/dashboard/competitors (Authorization: Basic ...)
    API->>Auth: Verify
    Auth-->>API: Authorized
    API-->>FE: 200 OK
```
