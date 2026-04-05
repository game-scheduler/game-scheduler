# syntax=docker/dockerfile:1
# Multi-stage build for Scheduler Daemon Service
# Runs notification, status-transition, and participant-action schedulers as threads.
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
    pip install --no-cache-dir uv==0.11.3

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install only third-party dependencies (excluding the project itself and workspace
# members) so app code is never installed into site-packages. Python finds app code
# via PYTHONPATH=/app instead, which gives coverage correct relative paths.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --no-dev --no-emit-local --no-hashes -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

ENV PYTHONPATH=/app

# Install sitecustomize.py so coverage auto-starts when COVERAGE_PROCESS_START is set.
# This is a no-op in production because that env var is never set there.
RUN python -c "import site; open(site.getsitepackages()[0] + '/sitecustomize.py', 'w').write('import coverage\ncoverage.process_startup()\n')"

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
CMD ["python", "-m", "services.scheduler.scheduler_daemon_wrapper"]

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
COPY pyproject.toml ./
COPY shared/ ./shared/
COPY services/__init__.py ./services/__init__.py
COPY services/scheduler/generic_scheduler_daemon.py ./services/scheduler/generic_scheduler_daemon.py
COPY services/scheduler/daemon_runner.py ./services/scheduler/daemon_runner.py
COPY services/scheduler/event_builders.py ./services/scheduler/event_builders.py
COPY services/scheduler/participant_action_event_builder.py ./services/scheduler/participant_action_event_builder.py
COPY services/scheduler/scheduler_daemon_wrapper.py ./services/scheduler/scheduler_daemon_wrapper.py
COPY services/scheduler/postgres_listener.py ./services/scheduler/postgres_listener.py
COPY services/scheduler/__init__.py ./services/scheduler/__init__.py
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "services.scheduler.scheduler_daemon_wrapper"]
