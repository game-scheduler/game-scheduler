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
PYTHONPATH=/app python3 -c "
from shared.telemetry import init_telemetry
from opentelemetry import trace
import subprocess
import sys

init_telemetry('init-service')
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span('init.database_migration') as span:
    result = subprocess.run(['alembic', 'upgrade', 'head'], capture_output=True, text=True)
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode != 0:
        span.set_status(trace.Status(trace.StatusCode.ERROR, 'Migration failed'))
        span.record_exception(Exception(result.stderr))
        sys.exit(result.returncode)
    span.set_status(trace.Status(trace.StatusCode.OK))
"
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

echo "Initializing RabbitMQ infrastructure..."
PYTHONPATH=/app python3 scripts/init_rabbitmq.py

echo "=== Initialization Complete ==="
