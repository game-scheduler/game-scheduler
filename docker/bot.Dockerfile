# syntax=docker/dockerfile:1
# Multi-stage build for Discord Bot Service
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

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

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

# Health check waits for bot to complete guild sync on startup
HEALTHCHECK --interval=5s --timeout=3s --start-period=60s --retries=5 \
    CMD test -f /tmp/bot-ready || exit 1

# Use python -m for module execution in development
CMD ["python", "-m", "services.bot.main"]

# Production stage
FROM python:3.13-slim AS production

ARG CACHE_SHARING_MODE=private

# Install runtime dependencies only
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING_MODE} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING_MODE} \
    apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY pyproject.toml ./
COPY shared/ ./shared/
COPY services/bot/ ./services/bot/

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Install shared package in editable mode
RUN pip install -e ./shared

# Set ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Health check waits for bot to complete guild sync on startup
HEALTHCHECK --interval=5s --timeout=3s --start-period=60s --retries=5 \
    CMD test -f /tmp/bot-ready || exit 1

CMD ["python", "-m", "services.bot.main"]
