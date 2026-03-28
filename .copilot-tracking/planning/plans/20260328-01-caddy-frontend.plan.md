---
applyTo: '.copilot-tracking/changes/20260328-01-caddy-frontend-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Replace nginx Frontend with Caddy (SSL Termination)

## Overview

Replace the existing `nginx:1.28-alpine` frontend container with Caddy, providing automatic Let's Encrypt SSL in production while operating as a plain HTTP server in staging (behind its existing reverse proxy).

## Objectives

- Replace the nginx production stage in `docker/frontend.Dockerfile` with a `caddy:2-alpine` stage
- Create environment-specific Caddyfiles: `:80` for staging, `{$DOMAIN}` with automatic HTTPS for production
- Update compose overlays so staging gets HTTP-only Caddy and production gets SSL-terminating Caddy with exposed ports
- Remove the now-unused `docker/frontend-nginx.conf`
- Zero net change in container count — same one frontend service, different image

## Research Summary

### Project Files

- [docker/frontend.Dockerfile](../../../docker/frontend.Dockerfile) - Multi-stage build; final `production` stage currently uses `nginx:1.28-alpine`, copies assets to `/usr/share/nginx/html`, copies `frontend-nginx.conf`
- [docker/frontend-nginx.conf](../../../docker/frontend-nginx.conf) - Nginx config covering: `config.js` no-cache, gzip, security headers, SSE streaming at `/api/v1/sse/`, standard API proxy at `/api/`, React Router catch-all, 1-year static asset caching
- [compose.yaml](../../../compose.yaml) - Base compose; frontend service has no ports (proxy handles external access); `NGINX_LOG_LEVEL` env var set on frontend
- [compose.staging.yaml](../../../compose.staging.yaml) - Staging overlay; sets `NGINX_LOG_LEVEL: debug` on frontend service
- [compose.prod.yaml](../../../compose.prod.yaml) - Prod overlay; no port mappings, `external: true` network, `build: target: production`
- [config/env/env.prod](../../../config/env/env.prod) - Prod environment file; needs `DOMAIN=` added

### External References

- #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md - Full research including Caddyfile examples, staging/prod pattern, nginx behavior requirements

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Multi-stage builds, minimal images

## Implementation Checklist

### [x] Phase 1: Update frontend.Dockerfile

- [x] Task 1.1: Replace `nginx:1.28-alpine` production stage with `caddy:2-alpine`
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 11-55)

### [x] Phase 2: Create Caddyfiles

- [x] Task 2.1: Create `docker/Caddyfile.staging` — HTTP-only, mirrors current nginx behavior
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 59-115)

- [x] Task 2.2: Create `docker/Caddyfile.prod` — automatic HTTPS via Let's Encrypt
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 117-155)

### [x] Phase 3: Update Compose Files

- [x] Task 3.1: Update `compose.yaml` frontend service
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 159-195)

- [x] Task 3.2: Update `compose.staging.yaml` frontend service
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 197-220)

- [x] Task 3.3: Update `compose.prod.yaml` frontend service and volumes
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 222-270)

- [x] Task 3.4: Add `DOMAIN` variable to `config/env/env.prod`
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 272-290)

### [x] Phase 4: Cleanup

- [x] Task 4.1: Remove `docker/frontend-nginx.conf`
  - Details: .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md (Lines 294-305)

## Dependencies

- `caddy:2-alpine` Docker image (official; no additional build tooling required)
- Domain DNS A/AAAA records must point to the production host before first cert issuance (operator responsibility, not a code change)
- Ports 80 and 443 open on the production host firewall (operator responsibility)

## Success Criteria

- `docker compose --env-file config/env/env.staging up -d` starts the frontend container serving HTTP on port 80 with no TLS errors
- `docker compose --env-file config/env/env.prod up -d` starts the frontend container, exposes ports 80 and 443, and obtains a Let's Encrypt certificate for `$DOMAIN`
- HTTP redirects to HTTPS automatically in production
- `/api/` and `/api/v1/sse/` proxy correctly to the `api` container
- React SPA routing works (deep links return `index.html`)
- `config.js` is served with no-cache headers
- `frontend-nginx.conf` is deleted and no references to it remain in Dockerfiles
