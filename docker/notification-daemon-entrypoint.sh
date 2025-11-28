#!/bin/bash
set -e

# Install shared package in editable mode if not already installed
if [ -d "/app/shared" ]; then
    pip install --user -e /app/shared --quiet
fi

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting notification daemon..."
# Execute the notification daemon
exec python -m services.scheduler.notification_daemon
