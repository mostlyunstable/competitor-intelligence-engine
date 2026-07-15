# Deployment Architecture

## Overview

The Utservio Intelligence Platform supports multiple deployment configurations from single-container development to multi-service production setups.

## Deployment Modes

| Mode | Use Case | Services | Database | Queue |
|------|----------|----------|----------|-------|
| **Development** | Local development | 1 (all-in-one) | SQLite | InMemory |
| **Docker Compose** | Staging/testing | 3 | PostgreSQL | Redis |
| **Production** | Enterprise | 5+ | PostgreSQL | Redis |

## 1. Development Mode

```text
┌─────────────────────────────────────────────┐
│                 Developer Machine            │
│                                              │
│  ┌───────────────────────────────────────┐  │
│  │          FastAPI (uvicorn)             │  │
│  │  ┌─────────┐ ┌─────────┐ ┌────────┐ │  │
│  │  │ API     │ │ Worker  │ │Scheduler│ │  │
│  │  │ Server  │ │ Pool    │ │        │ │  │
│  │  └────┬────┘ └────┬────┘ └───┬────┘ │  │
│  │       │           │          │       │  │
│  │  ┌────┴───────────┴──────────┴────┐  │  │
│  │  │        SQLite (local file)      │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │                                       │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │        InMemory Queue            │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  ┌───────────────────────────────────────┐  │
│  │       Vite Dev Server (port 5173)     │  │
│  │       React SPA + HMR                 │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Commands:**
```bash
# Backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## 2. Docker Compose (Staging)

```text
┌─────────────────────────────────────────────────────┐
│                  Docker Host                         │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │              docker-compose.yml                │  │
│  │                                                │  │
│  │  ┌──────────────┐  ┌──────────────┐          │  │
│  │  │  app          │  │  redis        │          │  │
│  │  │  (FastAPI)    │  │  (port 6379)  │          │  │
│  │  │  port 8000    │  │              │          │  │
│  │  └──────┬───────┘  └──────────────┘          │  │
│  │         │                                       │  │
│  │  ┌──────┴───────┐  ┌──────────────┐          │  │
│  │  │  postgres     │  │  nginx        │          │  │
│  │  │  (port 5432)  │  │  (port 80)    │          │  │
│  │  │  volume: pg   │  │  reverse proxy│          │  │
│  │  └──────────────┘  └──────────────┘          │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Commands:**
```bash
docker-compose up -d
docker-compose logs -f app
docker-compose down
```

## 3. Production Mode

```text
                    ┌─────────────────┐
                    │   Load Balancer  │
                    │   (Nginx/HAProxy)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴────────┐    │    ┌────────┴────────┐
     │   App Server 1   │    │    │   App Server 2   │
     │   (FastAPI)       │    │    │   (FastAPI)       │
     │   port 8000       │    │    │   port 8000       │
     └────────┬────────┘    │    └────────┬────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴────────┐ ┌──┴───┐ ┌───────┴────────┐
     │   PostgreSQL     │ │Redis │ │   Object Store  │
     │   (Primary)      │ │(Queue│ │   (S3/MinIO)    │
     │   port 5432      │ │ 6379)│ │                 │
     └────────┬────────┘ └──────┘ └────────────────┘
              │
     ┌────────┴────────┐
     │   PostgreSQL     │
     │   (Replica)      │
     │   port 5433      │
     └─────────────────┘
```

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CI_DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/utservio
      - CI_REDIS_URL=redis://redis:6379/0
      - CI_AUTH__API_KEY=dev-key-change-in-production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: utservio
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d utservio"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app

volumes:
  pgdata:
```

## Environment Variables

| Variable | Development | Staging | Production |
|----------|------------|---------|------------|
| `CI_DATABASE_URL` | `sqlite+aiosqlite:///./utservio.db` | `postgresql+asyncpg://...` | `postgresql+asyncpg://...` |
| `CI_REDIS_URL` | N/A | `redis://redis:6379/0` | `redis://redis-cluster:6379/0` |
| `CI_AUTH__API_KEY` | `dev-key` | `staging-key` | Vault-managed |
| `CI_SCHEDULER__DEFAULT_FREQUENCY` | `daily` | `daily` | `daily` |
| `CI_LOGGING__LEVEL` | `DEBUG` | `INFO` | `INFO` |

## Network Architecture

```text
┌─────────────────────────────────────────────────────┐
│                  Public Network                      │
│                                                      │
│              ┌────────────────────┐                 │
│              │    :443 (HTTPS)    │                 │
│              └─────────┬──────────┘                 │
│                        │                             │
└────────────────────────┼─────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────┐
│                  DMZ                                  │
│              ┌─────────┴──────────┐                 │
│              │    Load Balancer    │                 │
│              │    :80 → :443       │                 │
│              └─────────┬──────────┘                 │
│                        │                             │
└────────────────────────┼─────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────┐
│                  Application Network                  │
│                        │                             │
│              ┌─────────┴──────────┐                 │
│              │    App Servers      │                 │
│              │    :8000            │                 │
│              └─────────┬──────────┘                 │
│                        │                             │
└────────────────────────┼─────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────┐
│                  Data Network                         │
│                        │                             │
│    ┌─────────┴──────────┬─────────┴──────────┐     │
│    │                    │                    │     │
│  ┌─┴──────┐      ┌──────┴──────┐      ┌─────┴───┐ │
│  │Postgres │      │    Redis     │      │   S3    │ │
│  │:5432    │      │    :6379     │      │  :443   │ │
│  └────────┘      └─────────────┘      └─────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Health Checks

| Service | Check | Interval | Timeout | Retries |
|---------|-------|----------|---------|---------|
| FastAPI | `GET /api/health` | 30s | 10s | 3 |
| PostgreSQL | `pg_isready` | 10s | 5s | 5 |
| Redis | `redis-cli ping` | 10s | 5s | 5 |
| Nginx | `curl localhost` | 30s | 10s | 3 |

## Scaling Strategy

| Component | Scaling Method | Trigger |
|-----------|---------------|---------|
| FastAPI | Horizontal (replicas) | CPU > 70% |
| PostgreSQL | Read replicas | Query latency > 100ms |
| Redis | Cluster mode | Memory > 80% |
| Workers | Horizontal (replicas) | Queue depth > 100 |

## Backup Strategy

| Component | Method | Frequency | Retention |
|-----------|--------|-----------|-----------|
| PostgreSQL | pg_dump | Daily | 30 days |
| PostgreSQL | WAL archiving | Continuous | 7 days |
| Redis | RDB snapshot | Hourly | 24 hours |
| Object Storage | S3 versioning | Continuous | 90 days |
| Configuration | Git | Every change | Indefinite |

## Monitoring Stack

```text
┌─────────────────────────────────────────┐
│              Prometheus                   │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │ FastAPI  │ │Postgres │ │   Redis   │ │
│  │ Metrics  │ │ Metrics │ │  Metrics  │ │
│  └─────────┘ └─────────┘ └───────────┘ │
└──────────────────┬──────────────────────┘
                   │
              ┌────┴────┐
              │ Grafana  │
              │ Dashboards│
              └─────────┘
```
