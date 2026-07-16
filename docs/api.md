# API Documentation

## Overview

The Utservio Competitor Intelligence API provides RESTful endpoints for managing competitors, triggering data collection, and monitoring system health.

## Authentication

All API endpoints require Bearer token authentication:

```bash
curl -H "Authorization: Bearer <your-api-token>" https://api.utservio.com/competitors
```

## Base URL

```
https://api.utservio.com
```

## Endpoints

### Health

#### GET /status

Quick status check.

**Response:**
```json
{
  "status": "running",
  "competitors": 5,
  "collection_logs": 150
}
```

#### GET /health

Comprehensive health check.

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy", "latency_ms": 5.23},
    "scheduler": {"status": "healthy", "running": true},
    "fetcher": {"status": "healthy", "http_client_ready": true, "cache_entries": 150},
    "collection": {"status": "healthy", "active_crawls": 3},
    "memory": {"status": "healthy", "rss_mb": 256.0}
  },
  "http_status": 200
}
```

#### GET /logs

Retrieve recent collection logs.

**Parameters:**
- `limit` (query, optional): Number of logs to retrieve (default: 50)

**Response:**
```json
[
  {
    "id": 1,
    "competitor_id": 1,
    "start_time": "2026-07-09T10:00:00Z",
    "end_time": "2026-07-09T10:00:25Z",
    "success": true,
    "duration_seconds": 25.5,
    "records_collected": 45,
    "errors": [],
    "retry_count": 0
  }
]
```

### Competitors

#### GET /competitors

List all competitors.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Example Corp",
    "website_url": "https://example.com",
    "enabled": true,
    "collection_frequency": "daily",
    "modules": ["services", "pricing", "content"],
    "tags": ["technology", "saas"],
    "notes": "Primary competitor",
    "created_at": "2026-07-09T10:00:00Z",
    "updated_at": "2026-07-09T10:00:00Z"
  }
]
```

#### GET /competitors/{id}

Get a specific competitor.

**Parameters:**
- `id` (path, required): Competitor ID

**Response:**
```json
{
  "id": 1,
  "name": "Example Corp",
  "website_url": "https://example.com",
  "enabled": true,
  "collection_frequency": "daily",
  "modules": ["services", "pricing", "content"],
  "tags": ["technology", "saas"],
  "notes": "Primary competitor",
  "created_at": "2026-07-09T10:00:00Z",
  "updated_at": "2026-07-09T10:00:00Z"
}
```

#### POST /competitors

Create a new competitor.

**Request Body:**
```json
{
  "name": "Example Corp",
  "website_url": "https://example.com",
  "enabled": true,
  "collection_frequency": "daily",
  "modules": ["services", "pricing", "content"],
  "tags": ["technology", "saas"],
  "notes": "Primary competitor"
}
```

**Response:** 201 Created
```json
{
  "id": 1,
  "name": "Example Corp",
  "website_url": "https://example.com",
  "enabled": true,
  "collection_frequency": "daily",
  "modules": ["services", "pricing", "content"],
  "tags": ["technology", "saas"],
  "notes": "Primary competitor",
  "created_at": "2026-07-09T10:00:00Z",
  "updated_at": "2026-07-09T10:00:00Z"
}
```

#### PUT /competitors/{id}

Update a competitor.

**Parameters:**
- `id` (path, required): Competitor ID

**Request Body:**
```json
{
  "name": "Updated Corp Name",
  "collection_frequency": "weekly",
  "enabled": false
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Updated Corp Name",
  "website_url": "https://example.com",
  "enabled": false,
  "collection_frequency": "weekly",
  "modules": ["services", "pricing", "content"],
  "tags": ["technology", "saas"],
  "notes": "Primary competitor",
  "created_at": "2026-07-09T10:00:00Z",
  "updated_at": "2026-07-09T11:00:00Z"
}
```

#### DELETE /competitors/{id}

Delete a competitor.

**Parameters:**
- `id` (path, required): Competitor ID

**Response:** 204 No Content

### Collection

#### POST /collection/collect

Trigger data collection for a competitor.

**Request Body:**
```json
{
  "competitor_id": 1
}
```

**Response:** 202 Accepted
```json
{
  "status": "accepted",
  "message": "Collection started in background",
  "competitor_id": 1
}
```

#### POST /collection/collect/{competitor_id}

Trigger data collection for a specific competitor.

**Parameters:**
- `competitor_id` (path, required): Competitor ID

**Response:** 202 Accepted
```json
{
  "status": "accepted",
  "message": "Collection started in background",
  "competitor_id": 1
}
```

### Metrics

#### GET /metrics

Prometheus metrics endpoint.

**Response:** Text plain (Prometheus format)
```
# HELP collections_total Total collections
# TYPE collections_total counter
collections_total 150

# HELP collection_duration_seconds Collection duration
# TYPE collection_duration_seconds histogram
collection_duration_seconds{quantile="0.5"} 25.5
collection_duration_seconds{quantile="0.95"} 45.2
```

#### GET /metrics/json

Metrics in JSON format.

**Response:**
```json
{
  "counters": {"collections_total": 150},
  "gauges": {"active_crawls": 3},
  "histograms": {
    "parse_time_ms": {
      "avg": 250,
      "min": 100,
      "max": 500,
      "p50": 200,
      "p95": 400,
      "p99": 480,
      "count": 500,
      "sum": 125000
    }
  },
  "timestamp": "2026-07-09T10:00:00Z"
}
```

### Monitoring

#### GET /monitoring/dashboard

Comprehensive monitoring dashboard.

**Response:**
```json
{
  "timestamp": "2026-07-09T10:00:00Z",
  "system_health": {
    "status": "healthy",
    "database": {"status": "healthy", "latency_ms": 5},
    "scheduler": {"status": "healthy", "running": true},
    "fetcher": {"status": "healthy", "cache_entries": 150},
    "memory": {"status": "healthy", "rss_mb": 256}
  },
  "collection_metrics": {
    "total_competitors": 5,
    "active_competitors": 4,
    "total_collections": 150,
    "successful_collections": 145,
    "failed_collections": 5,
    "success_rate": 0.967,
    "avg_duration_seconds": 25.5,
    "total_records_collected": 1250
  },
  "extraction_metrics": {
    "total_pages_parsed": 500,
    "avg_confidence": 0.85,
    "avg_parse_time_ms": 250,
    "total_entities_extracted": 2500,
    "total_entities_accepted": 2250,
    "rejection_rate": 0.1,
    "top_strategies": [
      {"name": "json_ld", "entities": 800, "confidence": 0.92},
      {"name": "card_extraction", "entities": 600, "confidence": 0.88}
    ]
  },
  "alerts": {
    "active_count": 0,
    "by_severity": {},
    "recent_alerts": []
  }
}
```

## Error Handling

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.utservio.com/errors/not-found",
  "title": "Competitor Not Found",
  "status": 404,
  "detail": "Competitor with id 999 does not exist"
}
```

### Error Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Rate Limiting

- **Global**: 300 requests per minute per IP
- **Per-domain**: Configurable per competitor
- **Crawl budget**: Per-competitor page/byte/time limits

## Pagination

List endpoints support pagination:

```bash
GET /competitors?limit=10&offset=0
```

## Filtering

List endpoints support filtering:

```bash
GET /competitors?enabled=true&collection_frequency=daily
```

## Sorting

List endpoints support sorting:

```bash
GET /competitors?sort=name&order=asc
```

## Webhooks

Configure webhooks for collection events:

```json
{
  "url": "https://your-webhook.com/endpoint",
  "events": ["collection.completed", "collection.failed"],
  "secret": "your-webhook-secret"
}
```

## SDKs

Official SDKs available for:

- Python
- JavaScript/TypeScript
- Go
- Ruby

## Postman Collection

Import our Postman collection for quick testing:

```
https://api.utservio.com/postman-collection.json
```

## OpenAPI Specification

Full OpenAPI specification available at:

```
https://api.utservio.com/openapi.json
```

## Support

- **Documentation**: https://docs.utservio.com
- **API Status**: https://status.utservio.com
- **Support Email**: api-support@utservio.com
- **GitHub Issues**: https://github.com/utservio/competitor-intelligence/issues
