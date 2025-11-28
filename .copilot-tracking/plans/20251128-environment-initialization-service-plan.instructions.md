---
applyTo: ".copilot-tracking/changes/20251128-environment-initialization-service-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Environment Initialization Service

## Overview

Create a dedicated initialization service that runs database migrations and verifies schema integrity before application services start in all environments.

## Objectives

- Ensure database migrations run before any application service starts
- Provide clear initialization progress logging and error reporting
- Support all environments (development, integration tests, e2e tests, production)
- Maintain fast startup times for test environments with tmpfs volumes
- Create idempotent initialization process safe for restarts

## Research Summary

### Project Files

- docker-compose.base.yml (Lines 1-223) - Base service definitions for all environments
- docker/migrate-entrypoint.sh (Lines 1-14) - Current minimal migration script
- docker/migrate.Dockerfile - Existing migration image with Alembic
- docker-compose.yml - Development environment with persistent volumes
- docker-compose.integration.yml - Integration test environment with tmpfs volumes
- docker-compose.e2e.yml - E2E test environment with tmpfs volumes

### External References

- #file:../research/20251128-environment-initialization-service-research.md (Lines 37-48) - Docker Compose startup order patterns
- #file:../research/20251128-environment-initialization-service-research.md (Lines 56-98) - Implementation patterns and migration details
- #file:../research/20251128-environment-initialization-service-research.md (Lines 106-134) - Docker Compose dependency patterns with health checks

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices for health checks and initialization
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Bash script commenting standards

## Implementation Checklist

### [ ] Phase 1: Enhance Migration Entrypoint Script

- [ ] Task 1.1: Replace docker/migrate-entrypoint.sh with enhanced version

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 12-38)

### [ ] Phase 2: Add Init Service to Base Compose Configuration

- [ ] Task 2.1: Add init service definition to docker-compose.base.yml

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 42-62)

### [ ] Phase 3: Update Application Service Dependencies

- [ ] Task 3.1: Update bot service to depend on init completion

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 66-74)

- [ ] Task 3.2: Update api service to depend on init completion

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 78-86)

- [ ] Task 3.3: Update scheduler service to depend on init completion

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 90-98)

- [ ] Task 3.4: Update scheduler-beat service to depend on init completion

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 102-110)

- [ ] Task 3.5: Update notification-daemon service to depend on init completion

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 114-122)

### [ ] Phase 4: Test in All Environments

- [ ] Task 4.1: Test initialization service in development environment

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 128-140)

- [ ] Task 4.2: Test initialization service in integration test environment

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 144-156)

- [ ] Task 4.3: Test initialization service in e2e test environment

  - Details: .copilot-tracking/details/20251128-environment-initialization-service-details.md (Lines 160-172)

## Dependencies

- Existing docker/migrate.Dockerfile (no changes required)
- Existing Alembic migrations (no changes required)
- PostgreSQL, RabbitMQ, Redis health checks (already configured)
- Docker Compose version supporting service_completed_successfully condition

## Success Criteria

- Init service runs successfully and exits in all environments
- Application services start only after init completes successfully
- Clear, timestamped log messages show initialization progress
- Schema verification catches missing tables and reports errors
- Fast startup maintained in test environments with tmpfs volumes
- Process is idempotent and safe to restart without side effects
- Failed initialization prevents application services from starting
