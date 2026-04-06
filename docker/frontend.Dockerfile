# Multi-stage build for production-ready React frontend
FROM node:24-alpine AS base

WORKDIR /app

# Install dependencies first (better layer caching)
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# Development stage with Vite dev server
FROM base AS development

# Use existing node user (UID 1000)
# Note: Source files must be world-readable for volume mounts to work
RUN chown -R node:node /app

# Copy configuration files needed for Vite dev server
COPY frontend/vite.config.ts ./
COPY frontend/tsconfig.json ./
COPY frontend/tsconfig.node.json ./

# Source code NOT copied - will be mounted via volume in compose.override.yaml

USER node

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server with host binding for external access
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Builder stage for production compilation
FROM base AS builder

# Copy source code and configuration files
COPY frontend/src ./src
COPY frontend/index.html ./
COPY frontend/vite.config.ts ./
COPY frontend/tsconfig.json ./
COPY frontend/tsconfig.node.json ./
COPY frontend/vitest.config.ts ./

# Accept build arguments for environment variables
ARG VITE_API_URL

# Build the application with environment variables
RUN npm run build

# Production stage using Caddy
FROM caddy:2-alpine AS production

# Install curl for healthcheck; gettext provides envsubst used by the entrypoint
RUN apk add --no-cache curl gettext

# Copy built assets from builder stage
COPY --from=builder /app/dist /srv

# Copy config template and entrypoint script
COPY docker/frontend-config.template.js /srv/templates/config.template.js
COPY docker/frontend-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
