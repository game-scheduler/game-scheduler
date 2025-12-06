---
applyTo: ".copilot-tracking/changes/20251205-rabbitmq-runtime-configuration-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: RabbitMQ Runtime Configuration

## Overview

Convert RabbitMQ from build-time credential baking to runtime environment
variable configuration, enabling same container image across all environments.

## Objectives

- Eliminate build-time credential processing in RabbitMQ Dockerfile
- Use official RabbitMQ image with runtime environment variables
- Expand init container to create RabbitMQ infrastructure before services start
- Maintain idempotent operations and existing functionality

## Research Summary

### Project Files

- docker/rabbitmq.Dockerfile - Multi-stage build with build-time credential
  hashing
- rabbitmq/definitions.json.template - Template processed at build time
- docker-compose.base.yml - RabbitMQ service configuration with build args
- docker/init-entrypoint.sh - Database migration script to expand
- shared/messaging/publisher.py - Application code that declares exchanges
- shared/messaging/consumer.py - Application code that declares queues

### External References

- #file:../research/20251205-rabbitmq-runtime-configuration-research.md -
  Comprehensive research on RabbitMQ configuration patterns
- #fetch:https://www.rabbitmq.com/docs/configure - Environment variable
  interpolation support
- #fetch:https://www.rabbitmq.com/docs/definitions - Definition import patterns
  and idempotency
- #githubRepo:"docker-library/rabbitmq docker-entrypoint.sh" - Official Docker
  image patterns

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding
  conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md -
  Docker best practices
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md -
  Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Switch to Official RabbitMQ Image

- [x] Task 1.1: Update docker-compose.base.yml rabbitmq service

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 13-26)

- [x] Task 1.2: Update rabbitmq.conf to remove definitions import

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 28-38)

- [x] Task 1.3: Remove obsolete Docker build files

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 40-52)

- [x] Task 1.4: Verify RabbitMQ starts with runtime credentials
  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 54-65)

### [ ] Phase 2: Expand Init Container for RabbitMQ Infrastructure

- [ ] Task 2.1: Create scripts/init_rabbitmq.py

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 69-117)

- [ ] Task 2.2: Update docker/init-entrypoint.sh

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 119-135)

- [ ] Task 2.3: Update docker-compose.base.yml init service

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 137-150)

- [ ] Task 2.4: Verify infrastructure initialization
  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 152-163)

### [ ] Phase 3: Integration Testing and Validation

- [ ] Task 3.1: Run integration tests

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 167-177)

- [ ] Task 3.2: Validate multi-environment configuration

  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 179-191)

- [ ] Task 3.3: Update documentation
  - Details:
    .copilot-tracking/details/20251205-rabbitmq-runtime-configuration-details.md
    (Lines 193-204)

## Dependencies

- Official RabbitMQ Docker image: rabbitmq:4.2-management-alpine
- Python pika library (already in project dependencies)
- Docker Compose with health check support
- Environment variables: RABBITMQ_DEFAULT_USER, RABBITMQ_DEFAULT_PASS,
  RABBITMQ_URL

## Success Criteria

- Same RabbitMQ container image used across all environments
- No build-time credential processing
- RabbitMQ starts successfully with runtime credentials
- Init container creates all infrastructure before services start
- All integration tests pass
- Management UI accessible with runtime credentials
- Clear separation: init creates infrastructure, applications use it
