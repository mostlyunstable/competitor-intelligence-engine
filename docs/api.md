# API Documentation

## Authentication

All API endpoints (except health) require Basic Authentication.

```
Authorization: Basic base64(username:password)
```

Default credentials: `admin` / `admin123`

## Base URLs

- **Backend API**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`
- **API Documentation**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Quick system status |
| GET | `/health` | Comprehensive health check |
| GET | `/logs` | Collection logs |

### Competitors (API)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/competitors` | List all competitors |
| GET | `/competitors/{id}` | Get competitor by ID |
| POST | `/competitors` | Create competitor |
| PUT | `/competitors/{id}` | Update competitor |
| DELETE | `/competitors/{id}` | Delete competitor |

### Collection

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/collection/collect` | Trigger collection (body: `{competitor_id}`) |
| POST | `/collection/collect/{id}` | Trigger collection by ID |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/collection/{log_id}` | Collection report |
| GET | `/reports/diff/{id}` | Diff report |
| GET | `/reports/compare` | Comparison report |
| GET | `/reports/trends/{id}` | Trend report |

### Dashboard API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/dashboard/summary` | Competitor summary |
| GET | `/api/dashboard/feed` | Activity feed |
| GET | `/api/dashboard/health` | System health |
| GET | `/api/dashboard/search?q=` | Global search |
| GET | `/api/dashboard/telemetry` | System telemetry |
| GET | `/api/dashboard/scheduler/status` | Scheduler status |
| POST | `/api/dashboard/scheduler/pause` | Pause scheduler |
| POST | `/api/dashboard/scheduler/resume` | Resume scheduler |

### Dashboard Competitors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/competitors` | List competitors (with search, filter, pagination) |
| GET | `/api/dashboard/competitors/{id}` | Competitor detail |
| POST | `/api/dashboard/competitors` | Create competitor |
| PUT | `/api/dashboard/competitors/{id}` | Update competitor |
| DELETE | `/api/dashboard/competitors/{id}` | Delete competitor |
| POST | `/api/dashboard/competitors/{id}/duplicate` | Duplicate competitor |
| POST | `/api/dashboard/competitors/bulk/delete` | Bulk delete |
| POST | `/api/dashboard/competitors/bulk/enable` | Bulk enable |
| POST | `/api/dashboard/competitors/bulk/disable` | Bulk disable |
| POST | `/api/dashboard/competitors/bulk/frequency` | Bulk update frequency |

### Dashboard Collections

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dashboard/collect/{id}` | Trigger collection |
| POST | `/api/dashboard/collect/{id}/cancel` | Cancel collection |
| POST | `/api/dashboard/collect/{id}/retry` | Retry collection |

### Dashboard Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/logs` | Collection logs (with filters) |
| GET | `/api/dashboard/extracted/{id}` | Extracted data |
| GET | `/api/dashboard/live_logs/{id}` | Live logs |
| GET | `/api/dashboard/raw/{id}` | Raw HTML download |
| GET | `/api/dashboard/compare/csv` | CSV export |
| GET | `/api/dashboard/export/zip` | ZIP export |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/metrics` | Prometheus metrics |
| GET | `/metrics/json` | Metrics in JSON |

## Query Parameters

### GET /api/dashboard/competitors
- `search` (string): Search by name
- `enabled` (boolean): Filter by enabled status
- `frequency` (string): Filter by collection frequency
- `page` (int): Page number (default: 1)
- `page_size` (int): Results per page (default: 50)

### GET /api/dashboard/logs
- `competitor_id` (int): Filter by competitor
- `success` (boolean): Filter by success status
- `page` (int): Page number
- `page_size` (int): Results per page

## Error Responses

All errors follow RFC 7807 Problem Details format:

```json
{
  "detail": "Error message"
}
```

Status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict
- `500`: Internal Server Error
