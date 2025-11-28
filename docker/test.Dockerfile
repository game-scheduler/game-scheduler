# Dockerfile for running integration tests
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install all dependencies including dev dependencies (pytest, etc.)
# Use brackets to install optional dependencies
RUN uv pip install --system -e ".[dev]"

# Copy application code
COPY shared/ ./shared/
COPY services/ ./services/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY tests/ ./tests/

# Create non-root user
RUN addgroup --system testgroup && adduser --system --group testuser
RUN chown -R testuser:testgroup /app

USER testuser

# Default command runs integration tests
CMD ["pytest", "tests/integration/", "-v"]
