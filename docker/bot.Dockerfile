# Multi-stage build for Discord Bot Service
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

# Install Python dependencies
RUN uv pip install --system .

# Development stage
FROM base AS development

# Create non-root user for development
RUN addgroup --system appgroup && adduser --system --group appuser

# Set working directory ownership
RUN chown -R appuser:appgroup /app

# Create cache directory with proper permissions
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appgroup /home/appuser/.cache

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Use python -m for module execution in development
CMD ["python", "-m", "services.bot.main"]

# Production stage
FROM python:3.13-slim AS production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY shared/ ./shared/
COPY services/bot/ ./services/bot/

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Install shared package in editable mode
RUN pip install -e ./shared

# Set ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "services.bot.main"]
