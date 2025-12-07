<!-- markdownlint-disable-file -->

# Release Changes: Docker Development Volume Mount Strategy

**Related Plan**: 20251207-docker-development-volume-mount-plan.instructions.md
**Implementation Date**: 2025-12-07

## Summary

Enable instant hot-reload development workflow by adding development stages to
Dockerfiles and creating compose.override.yaml for automatic volume mounting of
source code.

## Changes

### Added

- compose.override.yaml - Development overrides with volume mounts and
  hot-reload commands for all services
- compose.production.yaml - Production overrides with explicit production
  targets and restart policies

### Modified

- docker/api.Dockerfile - Added development stage with hot-reload support using
  uvicorn --reload; uses non-root user (UID 1000) for security
- docker/bot.Dockerfile - Added development stage with python -m execution for
  Discord bot service; uses non-root user (UID 1000) for security
- docker/notification-daemon.Dockerfile - Added development stage with python -m
  execution for notification daemon; uses non-root user (UID 1000) for security
- docker/status-transition-daemon.Dockerfile - Added development stage with
  python -m execution for status transition daemon; uses non-root user
  (UID 1000) for security
- docker/frontend.Dockerfile - Added development stage with Vite dev server for
  hot module replacement; uses non-root node user (UID 1000) for security
- README.md - Added comprehensive development workflow section with hot-reload
  instructions, permission requirements, and production build guidance
- DEPLOYMENT_QUICKSTART.md - Updated with production deployment workflow using
  compose.production.yaml
- compose.override.yaml - Added volume mounts for instant code changes;
  documented world-readable requirement for source files
- compose.production.yaml - Updated usage comment to reference correct
  docker-compose.yml filename

### Removed

## Release Summary

**Total Files Affected**: 11

### Files Created (2)

- compose.override.yaml - Development overrides enabling instant code changes
  with volume mounts and hot-reload
- compose.production.yaml - Production overrides ensuring optimized builds with
  code baked into images

### Files Modified (9)

- docker/api.Dockerfile - Added development stage with hot-reload support; fixed
  user UID to 1000 for volume mount permissions
- docker/bot.Dockerfile - Added development stage with hot-reload support; fixed
  user UID to 1000 for volume mount permissions
- docker/notification-daemon.Dockerfile - Added development stage with
  hot-reload support; fixed user UID to 1000 for volume mount permissions
- docker/status-transition-daemon.Dockerfile - Added development stage with
  hot-reload support; fixed user UID to 1000 for volume mount permissions
- docker/frontend.Dockerfile - Added development stage with Vite dev server for
  hot module replacement; added non-root user with UID 1000 for security and
  proper volume mount permissions
- README.md - Added comprehensive development workflow documentation
- DEPLOYMENT_QUICKSTART.md - Updated with production deployment workflow
- compose.override.yaml - Fixed volume mount permissions by removing read-only
  flags
- compose.production.yaml - Corrected usage comment to reference
  docker-compose.yml

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None - uses existing Docker Compose multi-file support
- **Updated Dependencies**: None
- **Infrastructure Changes**:
  - Development workflow now uses compose.override.yaml (automatically loaded)
  - Production workflow uses explicit
    `-f docker-compose.yml -f compose.production.yaml` flags
  - Multi-stage Dockerfiles with separate development and production targets
- **Configuration Updates**:
  - Development user UID set to 1000 to match typical host user permissions
  - Volume mounts configured for instant code reflection in development
  - Production containers use code baked into images at build time

### Deployment Notes

**Development Workflow (No changes to existing process)**:

- Run `docker compose up` to start services in development mode with hot-reload
- Code changes in `shared/`, `services/`, and `frontend/src/` reflect instantly
- No container rebuilds needed for code changes

**Production Workflow**:

- Build and deploy with:
  `docker compose -f docker-compose.yml -f compose.production.yaml up -d --build`
- Production images contain all code and dependencies (no volume mounts)
- All 43 integration tests pass with production configuration
- Image sizes remain reasonable (API: ~537MB)

**Verification Completed**:

- ✅ Hot-reload works for Python services (uvicorn --reload)
- ✅ Hot-reload works for frontend (Vite dev server)
- ✅ Production builds include code in images (no volumes)
- ✅ All 43 integration tests pass
- ✅ Services start and run successfully in both modes
- ✅ Permission issues resolved with UID 1000 for development user
