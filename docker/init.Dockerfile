# syntax=docker/dockerfile:1
FROM python:3.13-slim

ARG CACHE_SHARING_MODE=private

# Configure apt to keep downloaded packages for cache mount
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Install system dependencies with cache mount
# Note: gcc is needed for building psycopg2 from source
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING_MODE} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING_MODE} \
    apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (alembic, database drivers, messaging, observability)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# Install sitecustomize.py so coverage auto-starts when COVERAGE_PROCESS_START is set.
# This is a no-op in production because that env var is never set there.
RUN python -c "import site; open(site.getsitepackages()[0] + '/sitecustomize.py', 'w').write('import coverage\ncoverage.process_startup()\n')"

# Copy application files
COPY shared/ ./shared/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY services/init/ ./services/init/

ENTRYPOINT ["python3", "-u", "-m", "services.init.main"]
