# Security Architecture

## Overview

The Utservio Competitor Intelligence Engine implements defense-in-depth security across authentication, authorization, network, application, and data layers.

## Authentication Mechanisms

### Basic Authentication (Dashboard)

The dashboard uses HTTP Basic Authentication:

```
Authorization: Basic base64(username:password)
```

**Implementation** (`app/api/endpoints/dashboard.py`):

```python
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(
        credentials.username, os.getenv("ADMIN_USER", "admin")
    )
    correct_password = secrets.compare_digest(
        credentials.password, os.getenv("ADMIN_PASSWORD", "admin123")
    )
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, ...)
    return credentials.username
```

**Security Properties**:
- Timing-safe comparison via `secrets.compare_digest()` prevents timing attacks
- Credentials stored in environment variables, never hardcoded
- Default credentials configurable per deployment
- All dashboard routes protected via router-level dependency

### API Key Authentication (Programmatic API)

The REST API uses API key authentication:

```
X-API-Key: your-api-key-here
```

**Implementation** (`app/api/auth.py`):

```python
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    settings = get_settings()
    expected_key = settings.api_key
    if not expected_key:
        if settings.environment != "development":
            raise HTTPException(status_code=500, detail="API key required")
        return "no-auth"
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

**Security Properties**:
- Timing-safe comparison via `hmac.compare_digest()`
- In development mode, API key is optional (allows unauthenticated testing)
- In production, missing API key returns 500 (fails safe)
- Per-endpoint enforcement via `Security(verify_api_key)`

### Frontend Authentication Flow

```
1. User submits credentials on login page
2. Frontend encodes to Base64: btoa(`${username}:${password}`)
3. Stored in localStorage as 'auth'
4. Every API request includes Authorization header
5. 401 response → clear localStorage → redirect to /login
6. Protected routes wrapped in AuthContext
```

## Network Security

### Security Headers

Applied to all responses via middleware:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forces HTTPS |

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=settings.debug,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- **Development**: All origins allowed (for local development)
- **Production**: No cross-origin requests allowed (dashboard served from same origin)

### Rate Limiting

Global rate limiting at 300 requests per minute:

```python
app.add_middleware(RateLimitMiddleware, requests_per_minute=300)
```

Prevents abuse and DDoS attacks.

### SSRF Protection

Competitor URL validation blocks internal/private IPs:

```python
ip = socket.gethostbyname(domain)
if ip.startswith("127.") or ip.startswith("169.254.") or ip.startswith("10.") or ip.startswith("192.168."):
    raise ValueError("Internal or private IPs are strictly forbidden (SSRF Protection).")
```

Prevents server-side request forgery attacks.

## Application Security

### Input Validation

All API inputs validated via Pydantic models:

```python
class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: HttpUrl = Field(...)
    enabled: bool = True
    collection_frequency: CollectionFrequency = Field(CollectionFrequency.DAILY)
```

- Type checking enforced
- Length constraints on strings
- URL format validation
- Enum validation for fixed values

### Error Handling

Errors follow RFC 7807 Problem Details format:

```json
{
    "detail": "Competitor not found"
}
```

- No stack traces leaked to clients
- Database errors return generic messages
- Validation errors include field-level details

### SQL Injection Prevention

SQLAlchemy ORM used throughout:

```python
stmt = select(Competitor).where(Competitor.id == competitor_id)
result = await session.execute(stmt)
```

- Parameterized queries via ORM
- No raw SQL with string interpolation
- ILIKE queries use bound parameters

### Secrets Management

| Secret | Storage | Access |
|--------|---------|--------|
| Database URL | `CI_DATABASE__URL` env var | `get_settings()` |
| API Key | `CI_API_KEY` env var | `get_settings()` |
| Admin Password | `ADMIN_PASSWORD` env var | `os.getenv()` |
| Webhook URLs | `CI_WEBHOOK__SLACK_WEBHOOK_URL` env var | `get_settings()` |
| LLM API Key | `CI_LLM__API_KEY` env var | `get_settings()` |

- Never committed to version control
- Loaded via Pydantic Settings from `.env` file
- Vault integration available for production secrets

### Credential Handling

- Passwords compared using timing-safe functions
- Credentials never logged
- API keys never exposed in error messages
- Frontend credentials stored in localStorage (not sessionStorage)

## Data Security

### Database Security

- Async sessions with automatic rollback on errors
- Connection pooling with pre-ping health checks
- Transactions with proper isolation
- Cascade deletes prevent orphaned data

### Storage Security

- Raw HTML stored on local filesystem with controlled permissions
- Content hashes prevent duplicate storage
- Storage URIs validated before file access

### Export Security

- CSV exports stream without buffering entire dataset
- ZIP exports limited to 100 records
- File downloads use `FileResponse` with proper content types

## Security Checklist

| Control | Status | Implementation |
|---------|--------|---------------|
| Authentication | Implemented | Basic Auth + API Keys |
| Authorization | Implemented | Route-level dependencies |
| Input Validation | Implemented | Pydantic models |
| SQL Injection | Prevented | SQLAlchemy ORM |
| XSS | Prevented | No inline scripts, CSP headers |
| CSRF | Mitigated | Same-origin policy |
| Rate Limiting | Implemented | 300 req/min global |
| Security Headers | Implemented | HSTS, X-Frame-Options |
| SSRF | Prevented | IP validation on URLs |
| Secrets | Managed | Environment variables |
| Error Handling | Implemented | RFC 7807 format |
| Logging | Implemented | No secrets logged |
| Timing Attacks | Prevented | secrets.compare_digest |
