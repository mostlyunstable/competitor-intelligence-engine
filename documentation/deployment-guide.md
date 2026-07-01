# Deployment Guide

## Prerequisites

- Docker 24+
- Docker Compose v2
- PostgreSQL 16+ (if running outside Docker)
- Python 3.12+ (for local development)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database username | `utservio` |
| `POSTGRES_PASSWORD` | Database password | Must change |
| `POSTGRES_DB` | Database name | `utservio_ci` |
| `DATABASE_URL` | Full async connection string | Constructed from above |
| `COMPETITORS_CONFIG_PATH` | Path to competitors JSON | `./competitors.json` |

## Docker Deployment

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f app
docker compose down
```

## Local Development

```bash
docker compose up -d postgres redis
pip install -e ".[dev]"
export CI_DATABASE__URL="postgresql+asyncpg://utservio:changeme@localhost:5432/utservio_ci"
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

## Database Migrations

```bash
alembic revision --autogenerate -m "description"  # Generate
alembic upgrade head                              # Apply
alembic downgrade -1                              # Rollback
```

## Production Checklist

- [ ] Change `POSTGRES_PASSWORD` from default
- [ ] Set `CI_ENVIRONMENT=production`
- [ ] Configure `WORKERS` based on CPU cores
- [ ] Set up log aggregation
- [ ] Set up backup for PostgreSQL volume
- [ ] Review rate limiting settings
