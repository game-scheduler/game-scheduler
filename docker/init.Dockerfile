FROM python:3.11-slim

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

# Install dependencies (alembic and database drivers)
RUN uv pip install --system -e .

# Copy migration files
COPY shared/ ./shared/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY docker/init-entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x init-entrypoint.sh

ENTRYPOINT ["./init-entrypoint.sh"]
