<!-- markdownlint-disable-file -->
# Task Details: RabbitMQ Runtime Configuration

## Research Reference

**Source Research**: #file:../research/20251205-rabbitmq-runtime-configuration-research.md

## Phase 1: Switch to Official RabbitMQ Image

### Task 1.1: Update docker-compose.base.yml rabbitmq service

Replace the custom build configuration with the official RabbitMQ image using runtime environment variables.

- **Files**:
  - docker-compose.base.yml - RabbitMQ service configuration
- **Success**:
  - Build section removed from rabbitmq service
  - Using official rabbitmq:4.2-management-alpine image
  - RABBITMQ_DEFAULT_USER and RABBITMQ_DEFAULT_PASS environment variables configured
  - All other settings (ports, volumes, healthcheck, networks) preserved
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 124-146) - Implementation guidance for Phase 1
  - #githubRepo:"docker-library/rabbitmq docker-entrypoint.sh" - Official image patterns
- **Dependencies**:
  - None

### Task 1.2: Update rabbitmq.conf to remove definitions import

Remove the load_definitions configuration line since we're no longer using definitions file for user creation.

- **Files**:
  - rabbitmq/rabbitmq.conf - RabbitMQ configuration file
- **Success**:
  - load_definitions line removed
  - management_agent.disable_metrics_collector setting preserved
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 147-153) - Configuration file updates
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Remove obsolete Docker build files

Delete files that are no longer needed after switching to official image.

- **Files**:
  - docker/rabbitmq.Dockerfile - Custom Dockerfile with build-time processing
  - rabbitmq/definitions.json.template - Template with build-time substitution
  - rabbitmq/definitions.json - Generated file if exists
- **Success**:
  - All three files deleted from repository
  - No references to deleted files remain
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 147-153) - File removal guidance
- **Dependencies**:
  - Task 1.1 completion

### Task 1.4: Verify RabbitMQ starts with runtime credentials

Test that RabbitMQ container starts successfully using environment variable credentials.

- **Files**:
  - None (verification only)
- **Success**:
  - docker compose up starts RabbitMQ successfully
  - Management UI accessible at localhost:15672
  - Login works with RABBITMQ_DEFAULT_USER and RABBITMQ_DEFAULT_PASS values
  - Health check passes
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 154-162) - Success criteria
- **Dependencies**:
  - Tasks 1.1, 1.2, 1.3 completion

## Phase 2: Expand Init Container for RabbitMQ Infrastructure

### Task 2.1: Create scripts/init_rabbitmq.py

Create Python script to initialize RabbitMQ infrastructure (exchanges, queues, bindings) with idempotent operations.

- **Files**:
  - scripts/init_rabbitmq.py - New infrastructure initialization script
- **Success**:
  - Script creates game_scheduler exchange (topic, durable)
  - Script creates game_scheduler.dlx exchange (topic, durable)
  - Script creates queues: bot_events, api_events, scheduler_events, notification_queue with DLX arguments
  - Script creates DLQ queue
  - Script creates bindings for routing keys
  - Wait logic with retries for RabbitMQ availability
  - All operations idempotent (safe to rerun)
  - Error handling and logging
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 166-236) - Complete script structure and logic
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 65-69) - Application code patterns
- **Dependencies**:
  - Phase 1 completion
  - pika library availability

### Task 2.2: Update docker/init-entrypoint.sh

Expand entrypoint script to include RabbitMQ infrastructure initialization after database migrations.

- **Files**:
  - docker/init-entrypoint.sh - Init container entrypoint
- **Success**:
  - Script runs database migrations (existing)
  - Script calls init_rabbitmq.py after database setup
  - Clear logging for each initialization step
  - Proper error handling with set -e
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 238-256) - Entrypoint script updates
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update docker-compose.base.yml init service

Add RabbitMQ dependency and RABBITMQ_URL environment variable to init service.

- **Files**:
  - docker-compose.base.yml - Init service configuration
- **Success**:
  - RABBITMQ_URL environment variable added
  - depends_on includes rabbitmq with service_healthy condition
  - All existing dependencies preserved
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 258-271) - Init service configuration
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Verify infrastructure initialization

Test that init container successfully creates all RabbitMQ infrastructure.

- **Files**:
  - None (verification only)
- **Success**:
  - Init container runs to completion without errors
  - All exchanges created in RabbitMQ
  - All queues created with correct DLX configuration
  - Bindings created correctly
  - Rerunning init container succeeds (idempotent)
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 273-284) - Success criteria
- **Dependencies**:
  - Tasks 2.1, 2.2, 2.3 completion

## Phase 3: Integration Testing and Validation

### Task 3.1: Run integration tests

Execute full integration test suite to verify messaging functionality.

- **Files**:
  - None (test execution)
- **Success**:
  - All integration tests pass
  - Message publishing works correctly
  - Message consumption works correctly
  - No errors or warnings in service logs
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 318-325) - Overall success criteria
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Validate multi-environment configuration

Test that same container image works with different credentials in different environments.

- **Files**:
  - None (validation only)
- **Success**:
  - Can start stack with test credentials
  - Can start stack with prod credentials
  - No rebuild required between environment changes
  - Only environment variables differ
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 6-9) - Problem statement about environment flexibility
- **Dependencies**:
  - Phase 2 completion

### Task 3.3: Update documentation

Update deployment and configuration documentation to reflect new runtime configuration approach.

- **Files**:
  - DEPLOYMENT_QUICKSTART.md - Deployment documentation
  - RUNTIME_CONFIG.md - Runtime configuration documentation
  - README.md - Main project documentation if needed
- **Success**:
  - Documentation explains runtime credential configuration
  - Documentation mentions removal of build-time processing
  - Documentation describes init container's expanded role
  - Environment variable requirements clearly stated
- **Research References**:
  - #file:../research/20251205-rabbitmq-runtime-configuration-research.md (Lines 118-122) - Recommended approach architecture
- **Dependencies**:
  - Phase 2 completion

## Dependencies

- Official RabbitMQ Docker image: rabbitmq:4.2-management-alpine
- Python pika library (already in pyproject.toml)
- Docker Compose with health check support

## Success Criteria

- Same RabbitMQ container image used across all environments
- No build-time credential processing
- RabbitMQ starts successfully with runtime credentials
- Init container creates all infrastructure before services start
- All integration tests pass
- Clear architecture: init creates, applications use
