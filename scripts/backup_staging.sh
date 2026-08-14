#!/usr/bin/env bash
set -e

# Documented staging backup procedure
# This script uses PostgreSQL-native tools (pg_dump) to securely backup the staging database.

echo "Starting Staging Database Backup..."

# Validate environment variables
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
  echo "Error: POSTGRES_USER and POSTGRES_DB must be set in the environment."
  exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backup_staging_${TIMESTAMP}.sql"

# Execute pg_dump against the postgres-staging container
# Assuming execution via docker compose exec or similar context where env vars are available
docker compose -f docker-compose.staging.yml exec -T postgres-staging \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c > "$BACKUP_FILE"

echo "Backup completed: $BACKUP_FILE"
