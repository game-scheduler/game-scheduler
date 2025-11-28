# Multi-stage build for Celery Scheduler Service
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

# Install Python dependencies
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
COPY services/scheduler/ ./services/scheduler/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy entrypoint scripts
COPY docker/notification-daemon-entrypoint.sh ./docker/notification-daemon-entrypoint.sh
RUN chmod +x ./docker/notification-daemon-entrypoint.sh

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD celery -A services.scheduler.celery_app:app inspect ping || exit 1

CMD ["celery", "-A", "services.scheduler.celery_app:app", "worker", "--loglevel=info", "--pool=solo"]
