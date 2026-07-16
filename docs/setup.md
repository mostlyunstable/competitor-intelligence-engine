# Installation & Setup Guide

## Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- PostgreSQL 14+
- Redis 7+ (optional, for production queue)
- Playwright browsers (for JavaScript rendering)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd competitor-intelligence-engine
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

### 3. Environment Configuration

Copy the `.env` file (already provided) and customize:

```bash
# Key settings to configure:
CI_ENVIRONMENT=development
CI_DEBUG=true
CI_DATABASE__URL=postgresql+asyncpg://utservio:changeme@localhost:5432/utservio_ci
ADMIN_USER=admin
ADMIN_PASSWORD=admin123
```

### 4. Database Setup

```bash
# Start PostgreSQL (using Docker)
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_USER=utservio \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=utservio_ci \
  postgres:16-alpine

# Run migrations
alembic upgrade head
```

Or use Docker Compose for everything:

```bash
docker compose up -d
```

### 5. Start Backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 7. Access the Application

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Prometheus Metrics**: http://localhost:8000/metrics

### 8. Default Login

- **Username**: admin
- **Password**: admin123

## Docker Setup

### Full Stack (Development)

```bash
docker compose up -d
```

This starts:
- App on port 8000
- PostgreSQL on port 5432
- Redis on port 6379

### Production Setup

```bash
# Build and run with staging compose
docker compose -f docker-compose.staging.yml up -d
```

## Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires PostgreSQL)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=app --cov-report=html
```

## Configuration

All configuration uses the `CI_` prefix. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `CI_ENVIRONMENT` | `development` | Environment name |
| `CI_DEBUG` | `false` | Debug mode |
| `CI_DATABASE__URL` | `postgresql+asyncpg://...` | Database URL |
| `CI_SCHEDULER__ENABLED` | `true` | Enable scheduler |
| `CI_SCHEDULER__CHECK_INTERVAL_SECONDS` | `60` | Scheduler interval |
| `CI_QUEUE__BACKEND` | `memory` | Queue backend (memory/redis) |
| `CI_QUEUE__REDIS_URL` | `redis://localhost:6379` | Redis URL |
| `ADMIN_USER` | `admin` | Dashboard admin username |
| `ADMIN_PASSWORD` | `admin123` | Dashboard admin password |

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U utservio -d utservio_ci
```

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium --force

# Install system dependencies
playwright install-deps
```

### Port Already in Use

```bash
# Find process on port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Redis Connection Issues

Redis is optional for development. The in-memory queue works without Redis.

```bash
# Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

## Verifying Subsystems

After starting, verify each subsystem:

1. **API**: `curl http://localhost:8000/status`
2. **Health**: `curl http://localhost:8000/health`
3. **Metrics**: `curl http://localhost:8000/metrics`
4. **Frontend**: Open http://localhost:3000
5. **Scheduler**: Check dashboard admin page
6. **Database**: Check dashboard stats page
