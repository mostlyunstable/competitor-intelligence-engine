# Complete Installation & Run Guide

This guide covers every step from fresh clone to running application, including all subsystems.

## Prerequisites

| Software | Version | Purpose | Install |
|----------|---------|---------|---------|
| Python | 3.12+ | Backend runtime | `brew install python@3.12` |
| Node.js | 18+ | Frontend build | `brew install node` |
| PostgreSQL | 14+ | Primary database | `brew install postgresql@16` |
| Redis | 7+ | Queue backend | `brew install redis` |
| Docker | Latest | Containerized services | `brew install --cask docker` |
| Playwright | Latest | Browser automation | Installed via pip |
| Git | Latest | Version control | `brew install git` |

## Step 1: Clone Repository

```bash
git clone https://github.com/mostlyunstable/competitor-intelligence-engine.git
cd competitor-intelligence-engine
```

## Step 2: Backend Setup

### Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- FastAPI, uvicorn, SQLAlchemy, asyncpg, Alembic
- httpx, BeautifulSoup4, Playwright, lxml
- structlog, prometheus-client, pydantic
- tenacity, aiofiles, openai, psutil, playwright-stealth
- pytest, pytest-asyncio, pytest-cov, ruff, mypy, black (dev)

### Install Playwright Browsers

```bash
playwright install chromium
```

For system dependencies (Linux):

```bash
playwright install-deps
```

## Step 3: Environment Configuration

The `.env` file is provided with defaults. Customize as needed:

```bash
# Key settings to review:
CI_ENVIRONMENT=development          # development | staging | production
CI_DEBUG=true                       # Enable debug mode
CI_LOG_LEVEL=info                   # Logging level

# Database
CI_DATABASE__URL=postgresql+asyncpg://utservio:changeme@localhost:5432/utservio_ci

# Queue (memory for dev, redis for production)
CI_QUEUE__BACKEND=memory            # memory | redis
CI_QUEUE__REDIS_URL=redis://localhost:6379
CI_QUEUE__NUM_WORKERS=1

# Scheduler
CI_SCHEDULER__ENABLED=true
CI_SCHEDULER__CHECK_INTERVAL_SECONDS=60

# Dashboard credentials
ADMIN_USER=admin
ADMIN_PASSWORD=admin123
```

## Step 4: Database Setup

### Option A: Docker (Recommended)

```bash
docker run -d --name postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=utservio \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=utservio_ci \
  postgres:16-alpine
```

### Option B: Native PostgreSQL

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Create database
psql -U postgres -c "CREATE USER utservio WITH PASSWORD 'changeme';"
psql -U postgres -c "CREATE DATABASE utservio_ci OWNER utservio;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE utservio_ci TO utservio;"
```

### Run Migrations

```bash
alembic upgrade head
```

### Verify Database

```bash
psql -h localhost -U utservio -d utservio_ci -c "\dt"
```

Should show 13 tables.

## Step 5: Redis Setup (Optional for Development)

### Option A: Docker

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Option B: Native

```bash
brew install redis
brew services start redis
```

### Option C: Docker Compose (All Services)

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, and the app.

## Step 6: Backend Startup

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify Backend

```bash
# Health check
curl http://localhost:8000/status

# Comprehensive health
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Step 7: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Verify Frontend

```bash
# Open in browser
open http://localhost:3000
```

## Step 8: Authentication

### Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

### Login Flow

1. Navigate to `http://localhost:3000`
2. Redirected to login page
3. Enter credentials
4. Click "Sign In"
5. Redirected to dashboard

### API Authentication

For programmatic access:

```bash
# Using curl with Basic Auth
curl -u admin:admin123 http://localhost:8000/api/dashboard/stats

# Using API key (if configured)
curl -H "X-API-Key: your-key" http://localhost:8000/competitors
```

## Step 9: Access URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend Dashboard | http://localhost:3000 | React SaaS dashboard |
| Backend API | http://localhost:8000 | FastAPI REST API |
| Swagger UI | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | API documentation |
| Prometheus Metrics | http://localhost:8000/metrics | Metrics endpoint |
| Metrics JSON | http://localhost:8000/metrics/json | Metrics in JSON format |

## Step 10: Running Tests

### Backend Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires PostgreSQL)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=app --cov-report=html

# Type checking
mypy app

# Linting
ruff check app

# Formatting
ruff format app
```

### Frontend Tests

```bash
cd frontend

# Type checking
npx tsc --noEmit

# Build
npm run build
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres
# or
brew services list | grep postgresql

# Test connection
psql -h localhost -U utservio -d utservio_ci

# Check connection string
echo $CI_DATABASE__URL
```

### Redis Connection Issues

Redis is optional for development. If `CI_QUEUE__BACKEND=memory`, Redis is not needed.

```bash
# Check Redis is running
docker ps | grep redis
# or
redis-cli ping

# Test connection
redis-cli -h localhost -p 6379 ping
```

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium --force

# Install system dependencies
playwright install-deps

# Check installation
playwright --version
```

### Port Already in Use

```bash
# Find process on port 8000
lsof -i :8000
# or
netstat -an | grep 8000

# Kill process
kill -9 <PID>
```

### Migration Issues

```bash
# Check migration status
alembic current

# List migrations
alembic history

# Stamp database (if tables exist but no migration tracking)
alembic stamp head

# Reset migrations (WARNING: destroys data)
alembic downgrade base
alembic upgrade head
```

### Authentication Issues

```bash
# Check environment variables
echo $ADMIN_USER
echo $ADMIN_PASSWORD

# Test with curl
curl -u admin:admin123 http://localhost:8000/api/dashboard/stats
```

### Frontend Build Issues

```bash
cd frontend

# Clear node_modules
rm -rf node_modules package-lock.json

# Reinstall
npm install

# Check Node.js version
node --version  # Should be 18+
```

## Verification Checklist

After installation, verify each subsystem:

```bash
# 1. Backend Health
curl http://localhost:8000/status
# Expected: {"status":"running","competitors":0,"collection_logs":0}

# 2. Database Connection
curl http://localhost:8000/health
# Expected: {"status":"healthy","checks":{"database":{"status":"healthy",...}}}

# 3. Frontend Access
curl -o /dev/null -s -w "%{http_code}" http://localhost:3000
# Expected: 200

# 4. API Documentation
curl -o /dev/null -s -w "%{http_code}" http://localhost:8000/docs
# Expected: 200

# 5. Prometheus Metrics
curl http://localhost:8000/metrics
# Expected: Prometheus format text

# 6. Dashboard Authentication
curl -u admin:admin123 http://localhost:8000/api/dashboard/stats
# Expected: JSON with statistics

# 7. Scheduler Status
curl -u admin:admin123 http://localhost:8000/api/dashboard/scheduler/status
# Expected: {"is_running":true,"status":"running","interval_seconds":60}

# 8. Competitor CRUD
curl -u admin:admin123 -X POST http://localhost:8000/api/dashboard/competitors \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","website_url":"https://example.com"}'
# Expected: {"id":1,"name":"Test","website_url":"https://example.com","status":"created"}
```
