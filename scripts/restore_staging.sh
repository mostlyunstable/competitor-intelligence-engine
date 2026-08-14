#!/usr/bin/env bash
set -e

# Documented staging restore procedure
# This script uses PostgreSQL-native tools (pg_restore) to securely restore the staging database.

echo "Starting Staging Database Restore..."

if [ -z "$1" ]; then
  echo "Usage: ./restore_staging.sh <backup_file.sql>"
  exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: File $BACKUP_FILE not found."
  exit 1
fi

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
  echo "Error: POSTGRES_USER and POSTGRES_DB must be set in the environment."
  exit 1
fi

# Execute pg_restore against the postgres-staging container
cat "$BACKUP_FILE" | docker compose -f docker-compose.staging.yml exec -T postgres-staging \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" -1

echo "Restore completed from: $BACKUP_FILE"
