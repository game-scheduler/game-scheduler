# Multi-stage build for Notification Daemon Service
FROM python:3.13-slim AS base

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

# Development stage
FROM base AS development

# Create non-root user with UID 1000
# Note: Source files must be world-readable for volume mounts to work
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --gid 1000 appuser

# Set working directory ownership
RUN chown -R appuser:appgroup /app

# Create cache directory with proper permissions
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appgroup /home/appuser/.cache

USER appuser

# Use python -m for module execution in development
CMD ["python", "-m", "services.scheduler.notification_daemon_wrapper"]

# Production stage
FROM python:3.13-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY shared/ ./shared/
COPY services/scheduler/generic_scheduler_daemon.py ./services/scheduler/generic_scheduler_daemon.py
COPY services/scheduler/event_builders.py ./services/scheduler/event_builders.py
COPY services/scheduler/notification_daemon_wrapper.py ./services/scheduler/notification_daemon_wrapper.py
COPY services/scheduler/postgres_listener.py ./services/scheduler/postgres_listener.py
COPY services/scheduler/__init__.py ./services/scheduler/__init__.py
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "services.scheduler.notification_daemon_wrapper"]