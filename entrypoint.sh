#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-utservio}" -q; do
    sleep 1
done
echo "PostgreSQL is ready."

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head || echo "Warning: Migrations failed (database may not be initialized yet)"
fi

if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
    echo "Creating multiprocess directory: $PROMETHEUS_MULTIPROC_DIR"
    mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
fi

echo "Starting application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${CI_APP_PORT:-${APP_PORT:-8000}}" \
    --workers "${CI_WORKERS:-${WORKERS:-1}}" \
    --log-level "${CI_LOG_LEVEL:-${LOG_LEVEL:-info}}" \
    --access-log
