# End-to-End Sequence Diagrams

## Overview

This document provides detailed sequence diagrams for every major workflow in the Utservio Intelligence Platform.

## 1. User Login Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React SPA
    participant Auth as AuthContext
    participant LS as localStorage

    User->>UI: Enter username + password
    UI->>Auth: login(username, password)
    Auth->>Auth: btoa(username:password)
    Auth->>LS: Set "ci_credentials"
    Auth->>Auth: setIsAuthenticated(true)
    Auth->>UI: Redirect to /
    UI->>UI: Render Layout + OverviewPage
```

## 2. Dashboard Data Loading

```mermaid
sequenceDiagram
    participant UI as OverviewPage
    participant Hook as usePolling
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database

    UI->>Hook: usePolling(fetchStats, 15000)
    Hook->>API: GET /api/dashboard/stats
    API->>Server: GET /api/dashboard/stats
    Server->>DB: SELECT COUNT(*) FROM competitors
    DB-->>Server: 15
    Server-->>API: 200 {total_competitors: 15, ...}
    API-->>UI: {total_competitors: 15, ...}
    UI->>UI: Render StatCards

    Note over Hook: After 15 seconds...
    Hook->>API: GET /api/dashboard/stats
    API->>Server: GET /api/dashboard/stats
    Server->>DB: SELECT COUNT(*) FROM competitors
    DB-->>Server: 16
    Server-->>API: 200 {total_competitors: 16, ...}
    API-->>UI: {total_competitors: 16, ...}
    UI->>UI: Update StatCards
```

## 3. Competitor Creation

```mermaid
sequenceDiagram
    actor User
    participant UI as CompetitorsPage
    participant Modal as CompetitorModal
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database

    User->>UI: Click "Add Competitor"
    UI->>Modal: setOpen(true)
    Modal->>UI: Render form

    User->>Modal: Fill name, website_url, status, frequency
    Modal->>API: POST /api/dashboard/competitors
    API->>Server: POST /api/dashboard/competitors
    Server->>DB: INSERT INTO competitors (...)
    DB-->>Server: 16
    Server-->>API: 201 {id: 16, ...}
    API-->>Modal: {id: 16, ...}
    Modal->>UI: setOpen(false)
    UI->>UI: Refresh competitors list
```

## 4. Competitor Collection Pipeline

```mermaid
sequenceDiagram
    actor User
    participant UI as CompetitorProfilePage
    participant API as ApiClient
    participant Server as FastAPI
    participant MQ as MessageQueue
    participant Worker as CollectionWorker
    participant CS as CollectionService
    participant Collector as Fetcher
    participant Parser as StrategyParser
    participant DB as Database

    User->>UI: Click "Collect" button
    UI->>API: POST /api/collection/collect/16
    API->>Server: POST /api/collection/collect/16
    Server->>MQ: publish("collection_task", {competitor_id: 16})
    Server-->>API: 202 {status: "pending", task_id: "..."}
    API-->>UI: Collection started

    MQ->>Worker: consume(collection_task)
    Worker->>CS: collect_competitor(competitor_id=16)
    CS->>DB: INSERT INTO collection_logs (status='running')
    
    par Phase 1: Discovery
        CS->>Collector: discover_urls(website_url)
        Collector->>Collector: robots.txt + sitemap.xml
        Collector-->>CS: [url1, url2, url3]
    and Phase 2: Fetch
        CS->>Collector: fetch_page(url1)
        Collector->>Collector: httpx.get() / playwright.goto()
        Collector-->>CS: HTML content
    and Phase 3: Parse
        CS->>Parser: parse(html, url1)
        Parser->>Parser: select_strategy() → 23 parsers
        Parser->>Parser: extract_entities()
        Parser->>Parser: deduplicate()
        Parser->>Parser: resolve_references()
        Parser-->>CS: {services: [...], pricing: [...]}
    and Phase 4: Store
        CS->>DB: INSERT INTO services (...)
        CS->>DB: INSERT INTO pricing (...)
        CS->>DB: INSERT INTO tech_stacks (...)
    end

    CS->>DB: UPDATE collection_logs SET status='completed'
    Worker->>MQ: task_complete
```

## 5. Bulk Operations

```mermaid
sequenceDiagram
    actor User
    participant UI as CompetitorsPage
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database

    User->>UI: Select 3 competitors (checkboxes)
    UI->>UI: setSelected([1, 2, 3])

    User->>UI: Click "Delete Selected"
    UI->>API: POST /api/dashboard/competitors/bulk/delete
    API->>Server: POST /api/dashboard/competitors/bulk/delete {ids: [1, 2, 3]}
    Server->>DB: DELETE FROM competitors WHERE id IN (1, 2, 3)
    DB-->>Server: 3 rows deleted
    Server-->>API: 200 {deleted: 3}
    API-->>UI: {deleted: 3}
    UI->>UI: Refresh list, clear selection
```

## 6. Scheduler Management

```mermaid
sequenceDiagram
    actor User
    participant UI as AdminPage
    participant API as ApiClient
    participant Server as FastAPI
    participant Scheduler as CollectionScheduler
    participant DB as Database

    User->>UI: Click "Pause Scheduler"
    UI->>API: POST /api/dashboard/scheduler/pause
    API->>Server: POST /api/dashboard/scheduler/pause
    Server->>Scheduler: pause()
    Scheduler->>Scheduler: self.running = False
    Server-->>API: 200 {status: "paused", ...}
    API-->>UI: {status: "paused", ...}
    UI->>UI: Update status badge

    User->>UI: Click "Resume Scheduler"
    UI->>API: POST /api/dashboard/scheduler/resume
    API->>Server: POST /api/dashboard/scheduler/resume
    Server->>Scheduler: resume()
    Scheduler->>Scheduler: self.running = True
    Scheduler->>Scheduler: _run_collection_cycle()
    Server-->>API: 200 {status: "running", ...}
    API-->>UI: {status: "running", ...}
```

## 7. Log Exploration

```mermaid
sequenceDiagram
    actor User
    participant UI as LogsPage
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database

    User->>UI: Navigate to /logs
    UI->>API: GET /api/dashboard/logs?page=1&page_size=20&status=completed
    API->>Server: GET /api/dashboard/logs?page=1&page_size=20&status=completed
    Server->>DB: SELECT * FROM collection_logs WHERE status='completed' LIMIT 20 OFFSET 0
    DB-->>Server: [log1, log2, ...]
    Server-->>API: 200 {items: [...], total: 45, ...}
    API-->>UI: {items: [...], total: 45, ...}
    UI->>UI: Render logs table

    User->>UI: Filter by competitor_id=16
    UI->>API: GET /api/dashboard/logs?competitor_id=16
    API->>Server: GET /api/dashboard/logs?competitor_id=16
    Server->>DB: SELECT * FROM collection_logs WHERE competitor_id=16
    DB-->>Server: [log16_1, log16_2]
    Server-->>API: 200 {items: [...], total: 2, ...}
    API-->>UI: {items: [...], total: 2, ...}
```

## 8. Report Export

```mermaid
sequenceDiagram
    actor User
    participant UI as ReportsPage
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database
    participant FS as FileSystem

    User->>UI: Select competitors + date range
    User->>UI: Click "Export CSV"
    UI->>API: GET /api/dashboard/export/csv?competitor_ids=1,2,3&start_date=2025-01-01&end_date=2025-12-31&export_type=all
    API->>Server: GET /api/dashboard/export/csv?competitor_ids=1,2,3&...
    Server->>DB: SELECT * FROM competitors WHERE id IN (1, 2, 3)
    DB-->>Server: [comp1, comp2, comp3]
    Server->>DB: SELECT * FROM services WHERE competitor_id IN (1, 2, 3)
    DB-->>Server: [services...]
    Server->>DB: SELECT * FROM pricing WHERE competitor_id IN (1, 2, 3)
    DB-->>Server: [pricing...]
    Server->>Server: generate CSV content
    Server-->>API: 200 Content-Type: text/csv
    API-->>UI: Blob
    UI->>UI: downloadBlob(blob, "report.csv")
```

## 9. Global Search

```mermaid
sequenceDiagram
    actor User
    participant UI as Layout TopBar
    participant Hook as useDebounce
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database

    User->>UI: Type "acme" in search box
    UI->>Hook: setValue("acme")
    Hook->>Hook: debounce(300ms)
    Hook->>API: GET /api/dashboard/search?q=acme
    API->>Server: GET /api/dashboard/search?q=acme
    Server->>DB: SELECT * FROM competitors WHERE name LIKE '%acme%'
    DB-->>Server: [acme_corp, acme_labs]
    Server-->>API: 200 [{id: 1, name: "Acme Corp"}, {id: 2, name: "Acme Labs"}]
    API-->>UI: [{id: 1, name: "Acme Corp"}, {id: 2, name: "Acme Labs"}]
    UI->>UI: Render search results dropdown
```

## 10. System Health Monitoring

```mermaid
sequenceDiagram
    participant UI as AdminPage
    participant Hook as usePolling
    participant API as ApiClient
    participant Server as FastAPI
    participant DB as Database
    participant Scheduler as CollectionScheduler
    participant MQ as MessageQueue
    participant PS as psutil

    Hook->>API: GET /api/dashboard/health
    API->>Server: GET /api/dashboard/health
    Server->>DB: SELECT 1
    DB-->>Server: OK (2ms)
    Server->>Scheduler: get_status()
    Scheduler-->>Server: {running: true, ...}
    Server->>MQ: get_stats()
    MQ-->>Server: {pending: 3, processing: 1, ...}
    Server-->>API: 200 {database: {status: "healthy", ...}, ...}
    API-->>UI: {database: {status: "healthy", ...}, ...}

    Hook->>API: GET /api/dashboard/telemetry
    API->>Server: GET /api/dashboard/telemetry
    Server->>PS: cpu_percent(), virtual_memory(), disk_usage()
    PS-->>Server: 45.2%, 68.5%, 42.3%
    Server-->>API: 200 {cpu_percent: 45.2, ...}
    API-->>UI: {cpu_percent: 45.2, ...}
```

## Component Interaction Diagram

```mermaid
graph TB
    subgraph Frontend["React SPA"]
        Login["LoginPage"]
        Layout["Layout"]
        Pages["Pages"]
    end

    subgraph Backend["FastAPI"]
        Auth["API Auth"]
        Dashboard["Dashboard API"]
        Collection["Collection API"]
        Reports["Reports API"]
    end

    subgraph Services["Service Layer"]
        CS["CollectionService"]
        RS["ReportingService"]
        WS["WebhookService"]
    end

    subgraph Data["Data Layer"]
        Scheduler["Scheduler"]
        Worker["Worker"]
        Queue["MessageQueue"]
        DB["Database"]
        Collectors["Collectors"]
        Parsers["Parsers"]
    end

    Login --> Auth
    Auth --> Layout
    Layout --> Pages
    Pages --> Dashboard
    Pages --> Collection
    Pages --> Reports
    Dashboard --> DB
    Collection --> CS
    CS --> Queue
    Queue --> Worker
    Worker --> Collectors
    Collectors --> Parsers
    Parsers --> DB
    Reports --> RS
    RS --> DB
    Scheduler --> Queue
    WS --> DB
```
