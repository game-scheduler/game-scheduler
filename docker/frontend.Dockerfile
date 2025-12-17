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
ARG VITE_DISCORD_CLIENT_ID
ARG VITE_API_URL

# Build the application with environment variables
RUN npm run build

# Production stage using nginx
FROM nginx:1.28-alpine AS production

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy custom nginx config
COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy config template and entrypoint script
COPY docker/frontend-config.template.js /etc/nginx/templates/config.template.js
COPY docker/frontend-entrypoint.sh /docker-entrypoint.d/40-generate-config.sh
RUN chmod +x /docker-entrypoint.d/40-generate-config.sh

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
