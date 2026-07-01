# Known Limitations

## Current Limitations

### 1. Single-Server Architecture

The scheduler runs in the same process as the API. A slow collection can delay API responses.

**Mitigation**: Collection timeout (300s default) prevents indefinite hangs.

**Fix**: Move to Celery + Redis for worker isolation.

### 2. In-Memory Rate Limiting

Rate limiting uses an in-memory dict. Does not work across multiple workers or servers.

**Fix**: Use Redis-backed rate limiting for distributed environments.

### 3. No JavaScript Rendering by Default

Collectors use httpx (HTTP client). JavaScript-rendered content from SPAs returns empty HTML shells.

**Mitigation**: Playwright is installed but not used by default. The `HybridFetcher` can detect JS-heavy pages and fall back to Playwright rendering.

**Fix**: Enable Playwright per-competitor or per-module as needed.

### 4. Per-Competitor Deduplication Only

Duplicate detection is per-competitor, not across competitors. Two competitors with identical content are not deduplicated against each other.

### 5. No Incremental Collection

Every collection run fetches the full page. No delta detection via ETag or If-Modified-Since headers.

### 6. No Authentication for Competitor Sites

The system only collects public data. No login-based access to member-only content.

### 7. No Data Validation After Collection

Collected data is stored as-is. No validation that extracted data is meaningful or complete.

### 8. No Automatic Retry for Collection Failures

Failed collections are logged but not automatically retried. Temporary failures require manual re-collection.

### 9. No Webhook/Event System

No way to notify other systems when collection completes. External systems must poll.
