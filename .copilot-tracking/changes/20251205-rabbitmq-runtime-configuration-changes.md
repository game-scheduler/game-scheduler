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
  - Establishes routing key bindings matching original
    definitions.json.template:
    - bot_events: game._, guild._, channel.\*
    - api_events: game.\*
    - scheduler_events: game.created, game.updated, game.cancelled
    - notification_queue: notification.send_dm
    - DLQ: # (catch-all from DLX)
  - Implements connection retry logic with 30-attempt maximum
  - All operations are idempotent (safe to run multiple times)

- tests/integration/test_rabbitmq_infrastructure.py - Comprehensive integration
  tests
  - Verifies all exchanges exist with correct types
  - Verifies all queues exist and are durable
  - Tests all 11 routing key bindings work correctly
  - Validates DLX configuration on primary queues
  - Confirms message routing isolation
  - Provides living documentation of expected infrastructure
    - DLQ: # (catch-all from DLX)
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
  - Increased RabbitMQ health check start_period to 60s for reliable startup

- rabbitmq/rabbitmq.conf

  - Removed load_definitions configuration line
  - Infrastructure now created at runtime instead of load-time

- docker/init-entrypoint.sh

  - Added RabbitMQ infrastructure initialization step after database migrations
  - Calls scripts/init_rabbitmq.py to create exchanges, queues, and bindings

- docker/init.Dockerfile

  - Added scripts/init_rabbitmq.py to container image
  - No additional dependencies needed (pika already in pyproject.toml)

- RUNTIME_CONFIG.md

  - Added comprehensive RabbitMQ runtime configuration section
  - Documented environment variable configuration for credentials
  - Explained infrastructure initialization process
  - Added guidance on changing RabbitMQ configuration

- DEPLOYMENT_QUICKSTART.md
  - Added RabbitMQ credentials to environment configuration example
  - Documented init container's expanded role in infrastructure setup
  - Added section on credentials and security best practices

### Removed

- docker/rabbitmq.Dockerfile - Custom Dockerfile with build-time credential
  hashing
- rabbitmq/definitions.json.template - Build-time template with credential
  substitution
- rabbitmq/definitions.json - Generated definitions file (if existed)

## Release Summary

**Total Files Affected**: 9

### Files Created (2)

- scripts/init_rabbitmq.py - RabbitMQ infrastructure initialization script that
  creates exchanges, queues, and bindings at runtime with connection retry logic
  and idempotent operations
- tests/integration/test_rabbitmq_infrastructure.py - Comprehensive test suite
  (16 tests) verifying all RabbitMQ infrastructure components created by init
  script

### Files Modified (5)

- docker-compose.base.yml - Switched to official RabbitMQ image with runtime
  environment variables, added init service dependencies, and increased health
  check start period
- rabbitmq/rabbitmq.conf - Removed load_definitions configuration to enable
  runtime infrastructure creation
- docker/init-entrypoint.sh - Added RabbitMQ infrastructure initialization step
  after database migrations
- docker/init.Dockerfile - Added init_rabbitmq.py script to container image
- RUNTIME_CONFIG.md - Added comprehensive RabbitMQ runtime configuration
  documentation including credential management, infrastructure initialization,
  and configuration change procedures
- DEPLOYMENT_QUICKSTART.md - Updated environment configuration examples,
  documented init container's expanded role, and added credentials and security
  best practices

### Files Removed (2)

- docker/rabbitmq.Dockerfile - Custom multi-stage Dockerfile with build-time
  credential processing
- rabbitmq/definitions.json.template - Build-time template for user and
  infrastructure definitions

### Dependencies & Infrastructure

- **New Dependencies**: None (pika already in project dependencies)
- **Updated Dependencies**: None
- **Infrastructure Changes**:
  - RabbitMQ now uses official rabbitmq:4.2-management-alpine image
  - Infrastructure (exchanges, queues, bindings) created by init container at
    runtime
  - User credentials provided via RABBITMQ_DEFAULT_USER and
    RABBITMQ_DEFAULT_PASS environment variables
  - Init container health check start period increased to 60s for reliable
    RabbitMQ startup
- **Configuration Updates**:
  - Removed build-time credential processing
  - Added runtime environment variable configuration for RabbitMQ credentials
  - Added RABBITMQ_URL environment variable to init service
  - Expanded init container to handle both database migrations and RabbitMQ
    infrastructure initialization

### Deployment Notes

**Migration from previous version:**

1. Remove old RabbitMQ volume if changing credentials:

   ```bash
   docker compose down rabbitmq
   docker volume rm <project>-rabbitmq-data
   ```

2. Update `.env` file with desired credentials:

   ```bash
   RABBITMQ_DEFAULT_USER=your_username
   RABBITMQ_DEFAULT_PASS=your_secure_password
   RABBITMQ_URL=amqp://your_username:your_secure_password@rabbitmq:5672/
   ```

3. Restart stack - init container will create infrastructure:
   ```bash
   docker compose up -d
   ```

**Benefits:**

- Same container image works across all environments (dev, test, prod)
- No build-time credential processing required
- Credentials can be changed without rebuilding images
- Clear separation: init creates infrastructure, applications use it
- All infrastructure operations are idempotent and safe to rerun
