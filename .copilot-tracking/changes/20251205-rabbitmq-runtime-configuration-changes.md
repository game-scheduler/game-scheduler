<!-- markdownlint-disable-file -->

# Release Changes: RabbitMQ Runtime Configuration

**Related Plan**: 20251205-rabbitmq-runtime-configuration-plan.instructions.md
**Implementation Date**: 2025-12-05

## Summary

Converting RabbitMQ from build-time credential baking to runtime environment
variable configuration, enabling the same container image to be used across all
environments (dev, test, prod). Expanded init container to handle RabbitMQ
infrastructure setup (exchanges, queues, bindings) alongside database
migrations.

## Changes

### Added

- scripts/init_rabbitmq.py - RabbitMQ infrastructure initialization script
  - Creates exchanges: game_scheduler (topic), game_scheduler.dlx (topic)
  - Creates queues: bot_events, api_events, scheduler_events, notification_queue
    (with 1-hour TTL and DLX configuration)
  - Creates DLQ queue (infinite TTL for failed message retention)
  - Establishes routing key bindings: bot.#, api.#, scheduler.#, notification.#
  - Implements connection retry logic with 30-attempt maximum
  - All operations are idempotent (safe to run multiple times)

### Modified

- docker-compose.base.yml

  - Replaced custom RabbitMQ build with official rabbitmq:4.2-management-alpine
    image
  - Added runtime environment variables: RABBITMQ_DEFAULT_USER,
    RABBITMQ_DEFAULT_PASS
  - Added RABBITMQ_URL environment variable to init service
  - Added rabbitmq dependency to init service with service_healthy condition

- rabbitmq/rabbitmq.conf

  - Removed load_definitions configuration line
  - Infrastructure now created at runtime instead of load-time

- docker/init-entrypoint.sh

  - Added RabbitMQ infrastructure initialization step after database migrations
  - Calls scripts/init_rabbitmq.py to create exchanges, queues, and bindings

- docker/init.Dockerfile
  - Added scripts/init_rabbitmq.py to container image
  - No additional dependencies needed (pika already in pyproject.toml)

### Removed

- docker/rabbitmq.Dockerfile - Custom Dockerfile with build-time credential
  hashing
- rabbitmq/definitions.json.template - Build-time template with credential
  substitution
- rabbitmq/definitions.json - Generated definitions file (if existed)
