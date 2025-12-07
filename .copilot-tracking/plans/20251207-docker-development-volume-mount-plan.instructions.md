---
applyTo: ".copilot-tracking/changes/20251207-docker-development-volume-mount-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Docker Development Volume Mount Strategy

## Overview

Enable instant hot-reload development workflow by adding development stages to
Dockerfiles and creating compose.override.yaml for automatic volume mounting of
source code.

## Objectives

- Enable instant code changes in development without container rebuilds
- Preserve existing optimized production build behavior
- Add hot-reload capability for all Python services (API, bot, daemons)
- Support frontend development with Vite dev server and hot module replacement
- Maintain security best practices with non-root users in development

## Research Summary

### Project Files

- `docker-compose.yml` and `docker-compose.base.yml` - Currently use
  production-style builds without development volume mounts
- `docker/api.Dockerfile`, `docker/bot.Dockerfile`,
  `docker/notification-daemon.Dockerfile`,
  `docker/status-transition-daemon.Dockerfile` - Multi-stage builds with only
  production targets
- `docker/frontend.Dockerfile` - Build-time compilation without development
  server support

### External References

- #file:../research/20251207-docker-development-volume-mount-research.md -
  Complete research on Docker development patterns
- #fetch:"https://docs.docker.com/compose/how-tos/production/" - Official Docker
  recommendations for dev/prod separation
- #githubRepo:"docker/awesome-compose nginx-golang-mysql react-express-mysql" -
  Industry-standard development stage patterns

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md -
  Multi-stage build and security conventions

## Implementation Checklist

### [x] Phase 1: Update Python Service Dockerfiles

- [x] Task 1.1: Add development stage to `docker/api.Dockerfile`

  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 15-50)

- [x] Task 1.2: Add development stage to `docker/bot.Dockerfile`

  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 52-87)

- [x] Task 1.3: Add development stage to `docker/notification-daemon.Dockerfile`

  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 89-124)

- [x] Task 1.4: Add development stage to
      `docker/status-transition-daemon.Dockerfile`
  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 126-161)

### [ ] Phase 2: Update Frontend Dockerfile

- [ ] Task 2.1: Add development stage to `docker/frontend.Dockerfile`
  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 165-200)

### [ ] Phase 3: Create Development Override Configuration

- [ ] Task 3.1: Create `compose.override.yaml` with development configurations

  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 204-260)

- [ ] Task 3.2: Create `compose.production.yaml` for explicit production
      deployment
  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 262-290)

### [ ] Phase 4: Update Documentation

- [ ] Task 4.1: Update README.md with development workflow instructions

  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 294-320)

- [ ] Task 4.2: Update DEPLOYMENT_QUICKSTART.md with production deployment
      changes
  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 322-345)

### [ ] Phase 5: Verification and Testing

- [ ] Task 5.1: Test development workflow with hot-reload

  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 349-380)

- [ ] Task 5.2: Verify production build behavior unchanged
  - Details:
    .copilot-tracking/details/20251207-docker-development-volume-mount-details.md
    (Lines 382-410)

## Dependencies

- Docker Compose with multi-file support (already in use)
- Existing multi-stage Dockerfiles with base and production stages
- uv for Python dependency management (already in use)
- Vite dev server configuration (already exists in frontend/vite.config.ts)

## Success Criteria

- Code changes in `shared/`, `services/`, and `frontend/src/` directories
  reflect immediately without rebuilds
- Running `docker compose up` automatically uses development configuration with
  volume mounts
- Production deployment with
  `docker compose -f compose.yml -f compose.production.yaml up` uses baked-in
  code
- All Python services support hot-reload via uvicorn --reload or python -m
  module
- Frontend supports hot module replacement via Vite dev server
- Production images remain small and secure with code copied in at build time
- All existing tests pass in both development and production modes
