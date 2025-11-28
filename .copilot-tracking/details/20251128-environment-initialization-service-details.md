<!-- markdownlint-disable-file -->

# Task Details: Environment Initialization Service

## Research Reference

**Source Research**: #file:../research/20251128-environment-initialization-service-research.md

## Phase 1: Enhance Migration Entrypoint Script

### Task 1.1: Replace docker/migrate-entrypoint.sh with enhanced version

Replace the current minimal migration script with a production-ready version that includes:
- Clear initialization phase logging with timestamps
- Database connection waiting with retry messages
- Migration execution with confirmation
- Schema verification for critical tables
- Success/failure status reporting

- **Files**:
  - docker/migrate-entrypoint.sh - Replace entire file with enhanced version
- **Success**:
  - Script includes timestamped initialization banner
  - PostgreSQL connection wait loop has status messages
  - Migration execution is clearly logged
  - Schema verification checks all critical tables (users, guild_configurations, channel_configurations, game_sessions, game_participants, notification_schedule)
  - Script exits with status 1 if any table verification fails
  - Completion message confirms successful initialization
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 164-198) - Enhanced entrypoint script implementation
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 82-98) - Current migration process and Alembic details
- **Dependencies**:
  - Existing docker/migrate.Dockerfile
  - PostgreSQL client tools (already in image)
  - Alembic configuration

## Phase 2: Add Init Service to Base Compose Configuration

### Task 2.1: Add init service definition to docker-compose.base.yml

Add a new init service after the redis service and before the bot service that:
- Uses the existing migrate.Dockerfile
- Depends on postgres, rabbitmq, and redis health checks
- Passes required database environment variables
- Uses restart: "no" policy to exit after completion
- Connects to the app-network

- **Files**:
  - docker-compose.base.yml - Add init service between redis and bot services
- **Success**:
  - Init service definition is properly formatted YAML
  - Service uses docker/migrate.Dockerfile
  - depends_on includes postgres, rabbitmq, redis with condition: service_healthy
  - environment includes DATABASE_URL, POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  - restart is set to "no"
  - Service is on app-network
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 143-163) - Init service configuration example
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 106-134) - Docker Compose dependency patterns
- **Dependencies**:
  - Phase 1 completion (enhanced entrypoint script)

## Phase 3: Update Application Service Dependencies

### Task 3.1: Update bot service to depend on init completion

Modify the bot service depends_on section to wait for init service completion instead of infrastructure health checks.

- **Files**:
  - docker-compose.base.yml (Lines 71-85) - bot service depends_on section
- **Success**:
  - depends_on section includes init with condition: service_completed_successfully
  - postgres, rabbitmq, redis health check dependencies are removed (inherited through init)
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 166-171) - Application service dependency pattern
- **Dependencies**:
  - Phase 2 completion (init service added)

### Task 3.2: Update api service to depend on init completion

Modify the api service depends_on section to wait for init service completion instead of infrastructure health checks.

- **Files**:
  - docker-compose.base.yml (Lines 106-120) - api service depends_on section
- **Success**:
  - depends_on section includes init with condition: service_completed_successfully
  - postgres, rabbitmq, redis health check dependencies are removed
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 166-171) - Application service dependency pattern
- **Dependencies**:
  - Phase 2 completion

### Task 3.3: Update scheduler service to depend on init completion

Modify the scheduler service depends_on section to wait for init service completion instead of infrastructure health checks.

- **Files**:
  - docker-compose.base.yml (Lines 137-151) - scheduler service depends_on section
- **Success**:
  - depends_on section includes init with condition: service_completed_successfully
  - postgres, rabbitmq, redis health check dependencies are removed
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 166-171) - Application service dependency pattern
- **Dependencies**:
  - Phase 2 completion

### Task 3.4: Update scheduler-beat service to depend on init completion

Modify the scheduler-beat service depends_on section to wait for init service completion instead of infrastructure health checks.

- **Files**:
  - docker-compose.base.yml (Lines 162-176) - scheduler-beat service depends_on section
- **Success**:
  - depends_on section includes init with condition: service_completed_successfully
  - postgres, rabbitmq, redis health check dependencies are removed
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 166-171) - Application service dependency pattern
- **Dependencies**:
  - Phase 2 completion

### Task 3.5: Update notification-daemon service to depend on init completion

Modify the notification-daemon service depends_on section to wait for init service completion instead of infrastructure health checks.

- **Files**:
  - docker-compose.base.yml (Lines 187-200) - notification-daemon service depends_on section
- **Success**:
  - depends_on section includes init with condition: service_completed_successfully
  - postgres, rabbitmq dependencies are removed
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 166-171) - Application service dependency pattern
- **Dependencies**:
  - Phase 2 completion

## Phase 4: Test in All Environments

### Task 4.1: Test initialization service in development environment

Verify the init service works correctly with persistent volumes in development environment.

- **Files**:
  - docker-compose.yml - Development environment configuration
- **Success**:
  - `docker compose up` starts init service first
  - Init service completes successfully and exits
  - Application services start after init completion
  - Logs show clear initialization progress
  - Database migrations are applied
  - All tables verified successfully
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 200-207) - Benefits and testing considerations
- **Dependencies**:
  - Phase 3 completion (all services updated)

### Task 4.2: Test initialization service in integration test environment

Verify the init service works correctly with tmpfs volumes in integration test environment.

- **Files**:
  - docker-compose.integration.yml - Integration test environment configuration
- **Success**:
  - `docker compose -f docker-compose.integration.yml up` starts init service
  - Init service completes quickly with tmpfs volumes
  - Integration tests run successfully after init
  - Schema is properly initialized for tests
  - No persistent data remains after cleanup
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 200-207) - Fast startup with tmpfs
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Test initialization service in e2e test environment

Verify the init service works correctly in e2e test environment with bot and notification-daemon.

- **Files**:
  - docker-compose.e2e.yml - E2E test environment configuration
- **Success**:
  - `docker compose -f docker-compose.e2e.yml up` starts init service
  - Bot and notification-daemon wait for init completion
  - E2E tests run successfully with initialized database
  - Notification triggers work correctly with initialized schema
  - Service startup order is correct (init → app services → tests)
- **Research References**:
  - #file:../research/20251128-environment-initialization-service-research.md (Lines 200-207) - All environment support
- **Dependencies**:
  - Task 4.2 completion

## Dependencies

- docker/migrate.Dockerfile - Existing image, no changes required
- Alembic migrations - Existing, no changes required
- PostgreSQL, RabbitMQ, Redis - Health checks already configured

## Success Criteria

- Init service runs and exits successfully in all three environments
- Application services consistently wait for init completion before starting
- Clear, actionable error messages if initialization fails
- Database schema is verified before applications start
- Fast startup maintained in test environments
- Idempotent: running multiple times produces same result
- Logs clearly show initialization phases and status
