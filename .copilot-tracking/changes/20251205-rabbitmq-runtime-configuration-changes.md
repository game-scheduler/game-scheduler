<!-- markdownlint-disable-file -->

# Release Changes: RabbitMQ Runtime Configuration

**Related Plan**: 20251205-rabbitmq-runtime-configuration-plan.instructions.md
**Implementation Date**: 2025-12-05

## Summary

Converting RabbitMQ from build-time credential baking to runtime environment
variable configuration, enabling the same container image to be used across all
environments (dev, test, prod).

## Changes

### Added

### Modified

- docker-compose.base.yml - Replaced custom RabbitMQ build with official
  rabbitmq:4.2-management-alpine image using runtime environment variables
- rabbitmq/rabbitmq.conf - Removed load_definitions configuration line

### Removed

- docker/rabbitmq.Dockerfile - Removed custom Dockerfile with build-time
  credential hashing
- rabbitmq/definitions.json.template - Removed template with build-time
  substitution
- rabbitmq/definitions.json - Removed generated definitions file
