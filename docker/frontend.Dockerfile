# Multi-stage build for production-ready React frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better layer caching)
COPY frontend/package*.json ./
RUN npm ci --only=production=false

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
FROM nginx:1.25-alpine

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
