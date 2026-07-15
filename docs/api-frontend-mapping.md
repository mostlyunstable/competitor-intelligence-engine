# API ↔ Frontend Mapping

## Overview

This document maps every frontend page and component to the backend API endpoints it consumes.

## Endpoint Mapping by Page

### Login Page (`LoginPage.tsx`)

| Action | HTTP Method | Endpoint | Request | Response |
|--------|------------|----------|---------|----------|
| Authenticate | N/A | N/A | - | - |

> Authentication is client-side only. Credentials stored in localStorage as Base64.

### Overview Page (`OverviewPage.tsx`)

| Section | Endpoint | Method | Polling | Response Schema |
|---------|----------|--------|---------|-----------------|
| KPI Cards | `/api/dashboard/stats` | GET | 15s | `{total_competitors, total_services, total_prices, total_content, total_social, active_competitors, recent_updates, failed_collections}` |
| Activity Feed | `/api/dashboard/feed` | GET | 20s | `[{id, type, title, description, timestamp, status, metadata}]` |
| System Health | `/api/dashboard/health` | GET | 30s | `{database: {status, latency_ms}, scheduler: {status, active_jobs}, queue: {status, pending, processing}}` |
| System Metrics | `/api/dashboard/telemetry` | GET | 10s | `{uptime_seconds, cpu_percent, memory_percent, disk_percent, version}` |

### Competitors Page (`CompetitorsPage.tsx`)

| Action | Endpoint | Method | Request Body | Response |
|--------|----------|--------|-------------|----------|
| List | `/api/dashboard/competitors` | GET | Query: `page, page_size, search, status, sort_by, sort_order` | `{items, total, page, page_size, total_pages}` |
| Create | `/api/dashboard/competitors` | POST | `{name, website_url, status?, frequency?, tags?, notes?}` | `Competitor` |
| Update | `/api/dashboard/competitors/{id}` | PUT | `{name?, website_url?, status?, frequency?, tags?, notes?}` | `Competitor` |
| Delete | `/api/dashboard/competitors/{id}` | DELETE | - | `{success: true}` |
| Duplicate | `/api/dashboard/competitors/{id}/duplicate` | POST | - | `Competitor` |
| Bulk Delete | `/api/dashboard/competitors/bulk/delete` | POST | `{ids: [1,2,3]}` | `{deleted: 3}` |
| Bulk Enable | `/api/dashboard/competitors/bulk/enable` | POST | `{ids: [1,2,3]}` | `{enabled: 3}` |
| Bulk Disable | `/api/dashboard/competitors/bulk/disable` | POST | `{ids: [1,2,3]}` | `{disabled: 3}` |
| Bulk Freq | `/api/dashboard/competitors/bulk/update-frequency` | POST | `{ids: [1,2,3], frequency: "weekly"}` | `{updated: 3}` |

### Competitor Profile Page (`CompetitorProfilePage.tsx`)

| Section | Endpoint | Method | Polling |
|---------|----------|--------|---------|
| Header | `/api/dashboard/competitors/{id}` | GET | 30s |
| Services | `/api/dashboard/competitors/{id}/services` | GET | 30s |
| Pricing | `/api/dashboard/competitors/{id}/pricing` | GET | 30s |
| Tech Stack | `/api/dashboard/competitors/{id}/tech-stack` | GET | 30s |
| Content | `/api/dashboard/competitors/{id}/content` | GET | 30s |
| Social | `/api/dashboard/competitors/{id}/social` | GET | 30s |
| Teams | `/api/dashboard/competitors/{id}/teams` | GET | 30s |
| Collection Logs | `/api/dashboard/competitors/{id}/collection-logs` | GET | 30s |

| Action | Endpoint | Method | Response |
|--------|----------|--------|----------|
| Trigger Collection | `/api/collection/collect/{id}` | POST | `{status: "pending", task_id: "..."}` |
| Cancel Collection | `/api/collection/cancel/{task_id}` | DELETE | `{status: "cancelled"}` |
| Retry Collection | `/api/collection/retry/{log_id}` | POST | `{status: "pending", task_id: "..."}` |

### Collections Page (`CollectionsPage.tsx`)

| Action | Endpoint | Method | Polling |
|--------|----------|--------|---------|
| Logs | `/api/dashboard/logs` | GET | 10s |
| Scheduler Status | `/api/dashboard/scheduler/status` | GET | 10s |

| Control | Endpoint | Method |
|---------|----------|--------|
| Pause Scheduler | `/api/dashboard/scheduler/pause` | POST |
| Resume Scheduler | `/api/dashboard/scheduler/resume` | POST |

### Logs Page (`LogsPage.tsx`)

| Action | Endpoint | Method | Polling |
|--------|----------|--------|---------|
| List | `/api/dashboard/logs` | GET | 15s |

Query Parameters: `page, page_size, status, competitor_id, collector_type, search`

### Reports Page (`ReportsPage.tsx`)

| Section | Endpoint | Method | Polling |
|---------|----------|--------|---------|
| Summary | `/api/dashboard/summary` | GET | 30s |
| Comparison | `/api/dashboard/comparison` | GET | 30s |
| Competitor | `/api/dashboard/reports/{id}` | GET | 30s |

| Action | Endpoint | Method | Query Params |
|--------|----------|--------|-------------|
| Export CSV | `/api/dashboard/export/csv` | GET | `competitor_ids, start_date, end_date, export_type` |
| Export JSON | `/api/dashboard/export/json` | GET | `competitor_ids, start_date, end_date, export_type` |

### Admin Page (`AdminPage.tsx`)

| Section | Endpoint | Method | Polling |
|---------|----------|--------|---------|
| System Health | `/api/dashboard/health` | GET | 20s |
| Scheduler Status | `/api/dashboard/scheduler/status` | GET | 15s |
| Telemetry | `/api/dashboard/telemetry` | GET | 10s |
| Prometheus | `/metrics/json` | GET | 30s |

### Search (`Layout.tsx` TopBar)

| Action | Endpoint | Method |
|--------|----------|--------|
| Search | `/api/dashboard/search` | GET |

Query Parameters: `q`

## Response Schemas

### Competitor

```typescript
interface Competitor {
  id: number
  name: string
  website_url: string
  status: "active" | "inactive"
  frequency: string
  tags: string[]
  notes: string
  last_collected_at: string | null
  created_at: string
  updated_at: string
}
```

### Service

```typescript
interface Service {
  id: number
  competitor_id: number
  name: string
  description: string
  category: string
  is_active: boolean
  url: string
  created_at: string
}
```

### Pricing

```typescript
interface Pricing {
  id: number
  competitor_id: number
  service_name: string
  plan_name: string
  price: string
  period: string
  features: string[]
  url: string
  created_at: string
}
```

### CollectionLog

```typescript
interface CollectionLog {
  id: number
  competitor_id: number
  status: "pending" | "running" | "completed" | "failed"
  started_at: string
  completed_at: string | null
  error_message: string | null
  pages_collected: number
  duration_seconds: number
}
```

### DashboardStats

```typescript
interface DashboardStats {
  total_competitors: number
  total_services: number
  total_prices: number
  total_content: number
  total_social: number
  active_competitors: number
  recent_updates: number
  failed_collections: number
}
```

### SystemHealth

```typescript
interface SystemHealth {
  database: { status: string; latency_ms: number }
  scheduler: { status: string; active_jobs: number }
  queue: { status: string; pending: number; processing: number }
}
```

### Telemetry

```typescript
interface Telemetry {
  uptime_seconds: number
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  version: string
}
```

## Authentication Flow

```
LoginPage
  ↓ (store credentials in localStorage)
Layout → ApiClient.setCredentials()
  ↓ (adds Authorization header)
All API calls → Authorization: Basic <base64>
  ↓ (on 401)
ApiClient → clearCredentials() → redirect to /login
```

## Error Handling

| HTTP Status | Frontend Behavior |
|-------------|-------------------|
| 200 | Process response |
| 400 | Show error toast |
| 401 | Clear credentials, redirect to login |
| 404 | Show "Not Found" message |
| 429 | Show "Rate Limited" message |
| 500 | Show "Server Error" message |
| Network Error | Show "Connection Failed" message |

## Polling Management

The `usePolling` hook manages data refresh:

```typescript
usePolling<T>(fetcher: () => Promise<T>, interval: number): T | null
```

- Fetches immediately on mount
- Re-fetches at specified interval
- Cleans up on unmount
- Returns null while loading
- Retries on error (next interval)
