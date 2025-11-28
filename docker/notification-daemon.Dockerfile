# Multi-stage build for Notification Daemon Service
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using project configuration
RUN uv pip install --system .

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY shared/ ./shared/
COPY services/scheduler/notification_daemon.py ./services/scheduler/notification_daemon.py
COPY services/scheduler/postgres_listener.py ./services/scheduler/postgres_listener.py
COPY services/scheduler/schedule_queries.py ./services/scheduler/schedule_queries.py
COPY services/scheduler/__init__.py ./services/scheduler/__init__.py
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "services.scheduler.notification_daemon"]