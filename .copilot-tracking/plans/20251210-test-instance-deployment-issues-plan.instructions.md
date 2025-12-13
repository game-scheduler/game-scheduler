---
applyTo: ".copilot-tracking/changes/20251210-test-instance-deployment-issues-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Minimize Docker Port Exposure for Security

## Overview

Remove unnecessary port mappings from Docker Compose configurations to minimize attack surface and prevent port conflicts when running multiple environments simultaneously.

## Objectives

- Remove all infrastructure port mappings (postgres, rabbitmq, redis) from base configuration
- Expose only application ports (frontend, API) in development and test environments
- Maintain zero port exposure in production (reverse proxy handles routing)
- Document `docker exec` usage for infrastructure service debugging
- Ensure no regression in inter-service communication (all use internal Docker network)

## Research Summary

### Project Files

- docker-compose.base.yml (Lines 1-100) - Infrastructure services currently expose ports to host
- compose.override.yaml (Lines 1-50) - Development overrides for hot-reload
- docker-compose.test.yml (Lines 1-50) - Test environment configuration with tmpfs volumes
- compose.production.yaml (Lines 1-50) - Production configuration (no port exposure)
- .env.example (Lines 1-103) - Environment variable documentation

### External References

- #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 1-350) - Complete analysis of port exposure issues and security implications
- #fetch:https://docs.docker.com/compose/networking/ - Docker networking best practices
- #githubRepo:"docker/docs" container networking - Port exposure security patterns

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Security principle: minimize exposed ports
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding practices

## Implementation Checklist

### [x] Phase 1: Remove Infrastructure Ports from Base Configuration

- [x] Task 1.1: Remove postgres port mapping from docker-compose.base.yml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 15-28)

- [x] Task 1.2: Remove rabbitmq data port (5672) from docker-compose.base.yml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 30-43)

- [x] Task 1.3: Remove redis port mapping from docker-compose.base.yml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 45-58)

- [x] Task 1.4: Remove grafana-alloy OTLP ports from docker-compose.base.yml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 60-73)

### [x] Phase 2: Add Development Port Overrides

- [x] Task 2.1: Add frontend port to compose.override.yaml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 75-88)

- [x] Task 2.2: Add API port to compose.override.yaml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 90-103)

- [x] Task 2.3: Add RabbitMQ management UI port to compose.override.yaml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 105-118)

### [x] Phase 3: Add Test Environment Port Overrides

- [x] Task 3.1: Add frontend and API ports to docker-compose.test.yml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 120-133)

### [x] Phase 4: Update Documentation

- [x] Task 4.1: Update .env.example with port configuration guidance
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 135-163)

- [x] Task 4.2: Verify compose.production.yaml has no port mappings
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 165-178)

### [x] Phase 5: Fix Game Host Notifications

- [x] Task 5.1: Add is_host parameter to _send_reminder_dm method
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 190-205)

- [x] Task 5.2: Send reminder to game host in _handle_game_reminder_due
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 207-222)

### [x] Phase 6: Verify Notify Roles Functionality

- [x] Task 6.1: Verify notify_role_ids database storage and retrieval
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 224-239)

- [x] Task 6.2: Test role mentions in Discord announcements
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 241-256)

### [x] Phase 7: Remove Unused Environment Variables

- [x] Task 7.1: Remove DISCORD_REDIRECT_URI from all environment files
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 258-273)

- [x] Task 7.2: Remove DISCORD_REDIRECT_URI from compose.yaml
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 275-290)

- [x] Task 7.3: Remove DISCORD_REDIRECT_URI from documentation
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 292-307)

### [x] Phase 8: Fix Game Completion Status Transitions

- [x] Task 8.1: Add DEFAULT_GAME_DURATION_MINUTES constant
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 309-324)

- [x] Task 8.2: Create COMPLETED schedule entry in create_game method
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 326-341)

- [x] Task 8.3: Handle both IN_PROGRESS and COMPLETED schedules in update_game method
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 343-358)

- [x] Task 8.4: Create database migration for existing games
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 360-375)

### [x] Phase 9: Add Observability to Init Service

- [x] Task 9.1: Add telemetry to init_rabbitmq.py script
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 377-392)

- [x] Task 9.2: Add telemetry wrapper to database migrations
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 394-409)

### [ ] Phase 10: Add service.name to Infrastructure Metrics

- [ ] Task 10.1: Route infrastructure metrics through OTEL processors
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 411-426)

- [ ] Task 10.2: Add Docker log rotation to all services
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 428-443)

- [ ] Task 10.3: Configure Grafana Alloy to collect Docker logs
  - Details: .copilot-tracking/details/20251210-test-instance-deployment-issues-details.md (Lines 445-460)

## Dependencies

- Docker Compose with multi-file support (already in use)
- Existing layered compose configuration structure
- Docker network configuration (app-network)
- OpenTelemetry instrumentation (shared/telemetry.py)
- Grafana Cloud account with Mimir, Loki, Tempo

## Success Criteria

- Base configuration (docker-compose.base.yml) exposes zero ports
- Development (compose.override.yaml) exposes: frontend (3000), API (8000), RabbitMQ management (15672)
- Test (docker-compose.test.yml) exposes: frontend (3000), API (8000) only
- Production (compose.production.yaml) exposes: zero ports
- No observability ports exposed (Alloy collects via internal network)
- Documentation clearly explains `docker exec` usage for infrastructure debugging
- No port conflicts when running multiple environments simultaneously
- All services communicate successfully via internal Docker network
- Game hosts receive reminder notifications
- Notify roles properly trigger Discord pings
- Unused DISCORD_REDIRECT_URI removed from all files
- Games automatically transition to COMPLETED status
- Init service telemetry visible in Grafana Cloud
- Infrastructure metrics have service.name attribute
- Docker logs rotate properly
- Infrastructure logs collected in Grafana Cloud Loki
- No regression in functionality (all tests pass)
