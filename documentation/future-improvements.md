# Future Improvements

## Worker Isolation

Replace APScheduler with Celery + Redis for independent worker processes, task retry with exponential backoff, and horizontal scaling.

Move rate limiting and caching to Redis for shared state across workers.

## Data Quality

- Post-collection validation (required fields, URL/price/date format checks)
- Data quality scoring (comteness, freshness, consistency)
- Incremental collection via ETag/If-Modified-Since headers

## Advanced Collection

- Playwright-based collectors for JavaScript-rendered SPAs
- Public API collection (REST, GraphQL)
- Improved sitemap parsing with recursive discovery

## Monitoring

- Prometheus metrics for collection duration, parser success rates, HTTP latencies
- Grafana dashboards for operational visibility
- Alerting on collection failures, parser errors, resource exhaustion

## API Enhancements

- Cursor-based pagination
- Filtering and sorting query parameters
- Webhook notifications for collection events

## Data Export

- JSON, CSV, Excel, PDF export formats
- Streaming for large datasets
- Scheduled export jobs

## Multi-Tenancy

- Team/workspace isolation
- Role-based access (admin, analyst, viewer)
- Per-team rate limits and data retention

## Compliance

- robots.txt crawl-delay support
- Per-competitor rate limits
- Configurable data retention policies
