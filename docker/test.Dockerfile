# syntax=docker/dockerfile:1
# Dockerfile for running integration tests
FROM python:3.13-slim

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
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir uv==0.11.3

# Create coverage directory for mounted coverage files
RUN mkdir -p /app/coverage

# Copy dependency files including lock file for reproducible builds
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev dependencies (pytest, etc.)
# uv will use uv.lock for version resolution
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e . && uv pip install --system --group dev

# Copy application code
COPY shared/ ./shared/
COPY services/ ./services/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Create non-root user
RUN addgroup --system testgroup && adduser --system --group testuser
RUN chown -R testuser:testgroup /app

USER testuser

# ENTRYPOINT is pytest - pass pytest arguments only (not 'pytest' itself)
# Examples:
#   docker compose run integration-tests tests/integration/test_retry_daemon.py -v
#   docker compose run e2e-tests tests/e2e/test_game_announcement.py -v
#   docker compose run integration-tests tests/integration/ -k test_message
ENTRYPOINT ["pytest"]

# Default command runs all integration tests when service is 'integration-tests'
# or all e2e tests when service is 'e2e-tests'
CMD ["tests/integration/", "-q", "--tb=short"]
