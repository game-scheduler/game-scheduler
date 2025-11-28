#!/bin/bash
set -e

echo "=== Environment Initialization ==="
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "  PostgreSQL not ready, retrying..."
  sleep 1
done
echo "✓ PostgreSQL is ready"

echo "Running database migrations..."
alembic upgrade head
echo "✓ Migrations complete"

echo "Verifying database schema..."
TABLES="users guild_configurations channel_configurations game_sessions game_participants notification_schedule"
for table in $TABLES; do
  if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1 FROM $table LIMIT 0" >/dev/null 2>&1; then
    echo "  ✓ Table $table exists"
  else
    echo "  ✗ Table $table missing!"
    exit 1
  fi
done

echo "=== Initialization Complete ==="
