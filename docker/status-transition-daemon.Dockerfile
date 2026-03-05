# syntax=docker/dockerfile:1
# Multi-stage build for Status Transition Daemon Service
FROM python:3.13-slim AS base

ARG CACHE_SHARING_MODE=private

# Configure apt to keep downloaded packages for cache mount
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING_MODE} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING_MODE} \
    apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using project configuration
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

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
CMD ["python", "-m", "services.scheduler.status_transition_daemon_wrapper"]

# Production stage
FROM python:3.13-slim AS production

ARG CACHE_SHARING_MODE=private

# Install runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING_MODE} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING_MODE} \
    apt-get update && apt-get install -y \
    postgresql-client \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY shared/ ./shared/
COPY services/__init__.py ./services/__init__.py
COPY services/scheduler/generic_scheduler_daemon.py ./services/scheduler/generic_scheduler_daemon.py
COPY services/scheduler/daemon_runner.py ./services/scheduler/daemon_runner.py
COPY services/scheduler/event_builders.py ./services/scheduler/event_builders.py
COPY services/scheduler/status_transition_daemon_wrapper.py ./services/scheduler/status_transition_daemon_wrapper.py
COPY services/scheduler/postgres_listener.py ./services/scheduler/postgres_listener.py
COPY services/scheduler/__init__.py ./services/scheduler/__init__.py
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "services.scheduler.status_transition_daemon_wrapper"]
