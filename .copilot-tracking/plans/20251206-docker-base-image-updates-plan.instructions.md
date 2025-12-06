---
applyTo: ".copilot-tracking/changes/20251206-docker-base-image-updates-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Docker Base Image Version Updates

## Overview

Update all Docker base images to their most recent stable LTS versions to ensure
long-term support, security patches, and maintain best practices for
containerization.

## Objectives

- Update Python images from 3.11 to 3.13 across all services
- Update Nginx from 1.25 to 1.28 in frontend production stage
- Update Redis from generic 7 to specific 7.4 tag
- Update PostgreSQL from 15 to 17 (major version upgrade)
- Optionally update Node.js from 20 to 22 LTS
- Verify all services remain functional after updates
- Update documentation to reflect new versions

## Research Summary

### Project Files

- docker-compose.base.yml - Service image specifications for PostgreSQL,
  RabbitMQ, Redis
- docker/api.Dockerfile - Python 3.11-slim base image (2 stages)
- docker/bot.Dockerfile - Python 3.11-slim base image
- docker/init.Dockerfile - Python 3.11-slim base image
- docker/notification-daemon.Dockerfile - Python 3.11-slim base image
- docker/status-transition-daemon.Dockerfile - Python 3.11-slim base image
- docker/test.Dockerfile - Python 3.11-slim base image
- docker/frontend.Dockerfile - Node 20-alpine builder, Nginx 1.25-alpine
  production

### External References

- #file:../research/20251206-docker-base-image-versions-research.md - Complete
  version analysis and recommendations
- #fetch:https://hub.docker.com/_/python - Python 3.13 is latest LTS with bugfix
  support until Oct 2029
- #fetch:https://hub.docker.com/_/postgres - PostgreSQL 17 is latest stable with
  support until Nov 2029
- #fetch:https://hub.docker.com/_/redis - Redis 7.4 is latest in 7.x line
  (avoiding 8.x licensing changes)
- #fetch:https://hub.docker.com/_/nginx - Nginx 1.28 is current stable branch
- #fetch:https://hub.docker.com/_/node - Node 22 is Maintenance LTS until April
  2027

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md -
  Docker image best practices
- #file:../../.github/instructions/python.instructions.md - Python coding
  conventions

## Implementation Checklist

### [x] Phase 1: Update Python Base Images

- [x] Task 1.1: Update api.Dockerfile Python version

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 14-24)

- [x] Task 1.2: Update bot.Dockerfile Python version

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 26-36)

- [x] Task 1.3: Update init.Dockerfile Python version

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 38-48)

- [x] Task 1.4: Update notification-daemon.Dockerfile Python version

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 50-60)

- [x] Task 1.5: Update status-transition-daemon.Dockerfile Python version

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 62-72)

- [x] Task 1.6: Update test.Dockerfile Python version
  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 74-84)

### [x] Phase 2: Update Frontend Base Images

- [x] Task 2.1: Update Node.js version in frontend.Dockerfile

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 86-96)

- [x] Task 2.2: Update Nginx version in frontend.Dockerfile
  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 98-108)

### [x] Phase 3: Update Service Images in docker-compose.base.yml

- [x] Task 3.1: Update Redis version specification

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 110-120)

- [x] Task 3.2: Update PostgreSQL version specification
  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 122-135)

### [x] Phase 4: Testing and Validation

- [x] Task 4.1: Rebuild all Docker images

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 137-147)

- [x] Task 4.2: Run integration tests

  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 149-159)

- [x] Task 4.3: Verify PostgreSQL migration compatibility
  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 161-173)

### [x] Phase 5: Documentation Updates

- [x] Task 5.1: Update version references in documentation
  - Details:
    .copilot-tracking/details/20251206-docker-base-image-updates-details.md
    (Lines 175-185)

## Dependencies

- Docker and docker-compose installed
- Access to Docker Hub for pulling updated images
- PostgreSQL migration strategy for major version upgrade
- Test environment for validation

## Success Criteria

- All Dockerfiles updated to use latest LTS base images
- docker-compose.base.yml reflects new service versions
- All services build successfully without errors
- Integration tests pass with updated images
- PostgreSQL data migrates successfully to version 17
- Documentation updated with new version information
- No breaking changes in application functionality
