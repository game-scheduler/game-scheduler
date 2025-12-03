<!-- markdownlint-disable-file -->
# Task Details: Complete Celery Elimination and Notification System Consolidation

## Research Reference

**Source Research**: #file:../research/20251203-celery-elimination-notification-consolidation-research.md

## Phase 1: Create game_status_schedule Table

### Task 1.1: Create Alembic migration for game_status_schedule table

Create new database table with domain-specific schema for game status transitions.

- **Files**:
  - alembic/versions/020_add_game_status_schedule.py - New migration file
- **Success**:
  - Table created with id, game_id, target_status, transition_time, executed, created_at columns
  - Foreign key constraint to game_sessions with CASCADE delete
  - UNIQUE constraint on (game_id, target_status)
  - Partial index on transition_time WHERE executed = FALSE for performance
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 66-79) - Schema design
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 204-214) - Migration strategy
- **Dependencies**:
  - Alembic migration framework (existing)

### Task 1.2: Create PostgreSQL trigger for LISTEN/NOTIFY on status schedule changes

Implement trigger to notify status_transition_daemon when schedule records are inserted/updated.

- **Files**:
  - alembic/versions/020_add_game_status_schedule.py - Add trigger in same migration
- **Success**:
  - Trigger function notifies 'game_status_schedule_changed' channel
  - Trigger fires on INSERT and UPDATE of game_status_schedule
  - Payload includes schedule record ID and transition_time
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 98-101) - PostgreSQL LISTEN/NOTIFY pattern
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 204-214) - Trigger implementation
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Add GameStatusSchedule SQLAlchemy model

Create ORM model for game_status_schedule table.

- **Files**:
  - shared/models/__init__.py - Import new model
  - shared/models/game_status_schedule.py - New model file
- **Success**:
  - GameStatusSchedule model with all table columns mapped
  - Relationship to GameSession model
  - Type hints using Python types
  - Follows existing model patterns in shared/models/
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 66-79) - Schema specification
  - Existing models in shared/models/ for pattern reference
- **Dependencies**:
  - Task 1.1 completion
  - Alembic migration applied

## Phase 2: Implement Status Transition Daemon

### Task 2.1: Create status_transition_daemon.py based on notification_daemon.py pattern

Create new daemon service following proven notification_daemon architecture.

- **Files**:
  - services/scheduler/status_transition_daemon.py - New daemon implementation
- **Success**:
  - PostgreSQL LISTEN on 'game_status_schedule_changed' channel
  - MIN(transition_time) query pattern for next due transition
  - Sleep until next transition time with interruption on NOTIFY
  - Graceful shutdown handling with signal handlers
  - Logging configured following project standards
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 53-60) - notification_daemon architecture
  - services/scheduler/notification_daemon.py - Reference implementation
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 216-220) - Daemon creation strategy
- **Dependencies**:
  - Phase 1 completion
  - PostgreSQL LISTEN/NOTIFY infrastructure (existing)

### Task 2.2: Implement status transition processing with database transaction

Implement the core logic to update game status and publish events.

- **Files**:
  - services/scheduler/status_transition_daemon.py - Add _process_transition method
- **Success**:
  - Database transaction updates game.status to 'IN_PROGRESS'
  - game.updated_at set to current UTC time
  - game_status_schedule.executed set to TRUE
  - EventType.GAME_STARTED published to RabbitMQ after successful transaction
  - Transaction rollback on errors with proper logging
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 131-159) - Transaction pattern
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 161-175) - Differences from game reminders
  - services/scheduler/tasks/update_game_status.py - Current Celery implementation logic
- **Dependencies**:
  - Task 2.1 completion
  - shared.messaging event publisher (existing)

### Task 2.3: Add error handling and logging for status transitions

Implement comprehensive error handling and observability.

- **Files**:
  - services/scheduler/status_transition_daemon.py - Add error handling throughout
- **Success**:
  - Catch and log database connection errors without daemon crash
  - Retry logic for transient failures
  - Structured logging with game_id, transition_time, target_status
  - Metrics/counters for successful transitions and errors (if metrics framework exists)
  - Dead letter handling for permanently failed transitions
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 131-159) - Transaction error handling
  - services/scheduler/notification_daemon.py - Error handling patterns
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Integrate with API Layer

### Task 3.1: Update game creation to populate game_status_schedule

Ensure status transition schedule is created when games are scheduled.

- **Files**:
  - services/api/services/games.py - Update create_game function
- **Success**:
  - Insert game_status_schedule record when game created with SCHEDULED status
  - target_status set to 'IN_PROGRESS'
  - transition_time set to game.scheduled_at
  - Schedule creation in same transaction as game creation
  - No schedule created for games with non-SCHEDULED status
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 177-184) - Trigger points
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 222-226) - API integration strategy
- **Dependencies**:
  - Phase 1 completion
  - GameStatusSchedule model available

### Task 3.2: Update game scheduled_at changes to update status schedule

Handle updates to game scheduling time.

- **Files**:
  - services/api/services/games.py - Update update_game function
- **Success**:
  - Update game_status_schedule.transition_time when scheduled_at changes
  - Handle case where schedule doesn't exist (create it)
  - Handle case where game status changed to non-SCHEDULED (delete schedule)
  - Database trigger notifies daemon of schedule change
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 177-184) - Trigger points
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 222-226) - API integration
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Delete status schedule on game cancellation/deletion

Clean up schedule records when games are cancelled or deleted.

- **Files**:
  - services/api/services/games.py - Update cancel_game and delete_game functions
- **Success**:
  - Delete game_status_schedule record on game cancellation
  - CASCADE delete handles game deletion automatically
  - No orphaned schedule records remain
  - Deletion in same transaction as status update
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 177-184) - Trigger points
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 66-79) - CASCADE constraint
- **Dependencies**:
  - Tasks 3.1 and 3.2 completion

## Phase 4: Deploy and Validate

### Task 4.1: Add status-transition-daemon service to docker-compose

Deploy new daemon alongside existing notification-daemon.

- **Files**:
  - docker-compose.base.yml - Add status-transition-daemon service
  - docker-compose.yml - Include in main compose (if needed)
- **Success**:
  - Service definition matches notification-daemon pattern
  - Depends on db and rabbitmq services
  - Uses status-transition.Dockerfile
  - Environment variables configured (DATABASE_URL, RABBITMQ_URL)
  - Restart policy set to unless-stopped
  - Healthcheck configured
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 240-247) - Deployment infrastructure
  - docker-compose.base.yml (Lines 210-236) - notification-daemon service for pattern
- **Dependencies**:
  - Phase 2 completion
  - Task 4.2 completion

### Task 4.2: Create Dockerfile for status-transition-daemon

Build container for status transition daemon.

- **Files**:
  - docker/status-transition.Dockerfile - New Dockerfile
  - docker/status-transition-entrypoint.sh - Entrypoint script
- **Success**:
  - Follows multi-stage build pattern from existing Dockerfiles
  - Includes only necessary dependencies (no Celery)
  - Runs status_transition_daemon.py as main process
  - Proper signal handling for graceful shutdown
  - User permissions configured correctly
- **Research References**:
  - #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker standards
  - docker/scheduler.Dockerfile - Reference for daemon containers
- **Dependencies**:
  - Phase 2 completion

### Task 4.3: Test status transitions end-to-end

Validate complete workflow from game creation to status transition.

- **Files**:
  - tests/integration/test_status_transitions.py - New integration test file
- **Success**:
  - Test creates game with scheduled_at in past, verifies status transitions to IN_PROGRESS
  - Test creates game with scheduled_at in future, waits, verifies transition
  - Test verifies EventType.GAME_STARTED published
  - Test verifies game_status_schedule.executed = TRUE after transition
  - Test verifies daemon recovery after restart
  - Test verifies multiple games transition correctly
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 349-363) - Success criteria
  - tests/integration/ - Existing integration test patterns
- **Dependencies**:
  - Tasks 4.1 and 4.2 completion
  - Docker services running

## Phase 5: Remove Celery Infrastructure

### Task 5.1: Remove Celery application and task files

Delete all Celery-related code files.

- **Files**:
  - services/scheduler/celery_app.py - DELETE
  - services/scheduler/tasks/update_game_status.py - DELETE
  - services/scheduler/tasks/__init__.py - DELETE (if now empty)
- **Success**:
  - No Celery configuration files remain
  - No task definitions remain
  - No imports of deleted modules in other files
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 7-14) - Current Celery usage
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 236-238) - Celery removal strategy
- **Dependencies**:
  - Phase 4 validation complete
  - Status transition daemon proven working

### Task 5.2: Remove scheduler and scheduler-beat services from docker-compose

Clean up Celery services from deployment configuration.

- **Files**:
  - docker-compose.base.yml - Remove scheduler and scheduler-beat services
  - docker-compose.yml - Remove references if present
- **Success**:
  - No scheduler or scheduler-beat service definitions
  - No depends_on references to removed services
  - Redis dependency removed if only used by Celery
  - Docker compose validates successfully
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 236-238) - Service removal
  - docker-compose.base.yml - Current service definitions
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Remove Celery dependencies from pyproject.toml

Remove Celery packages from project dependencies.

- **Files**:
  - pyproject.toml - Remove Celery dependencies
- **Success**:
  - celery package removed from dependencies
  - redis package removed if only used by Celery
  - Any Celery-related packages removed (celery-beat, flower, etc.)
  - uv lock file updated
  - No import errors when running tests
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 236-238) - Dependency removal
  - pyproject.toml - Current dependencies
- **Dependencies**:
  - Tasks 5.1 and 5.2 completion

### Task 5.4: Update documentation to reflect architecture change

Document new architecture without Celery.

- **Files**:
  - README.md - Update architecture section
  - DEPLOYMENT_QUICKSTART.md - Update service list
  - RUNTIME_CONFIG.md - Remove Celery configuration
- **Success**:
  - README reflects database-backed notification system
  - No mentions of Celery, scheduler service, or scheduler-beat
  - Status transition daemon documented
  - Architecture diagrams updated if present
  - Service list shows notification-daemon and status-transition-daemon
  - Configuration examples updated
- **Research References**:
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 236-238) - Documentation updates
  - #file:../research/20251203-celery-elimination-notification-consolidation-research.md (Lines 349-363) - Success criteria
- **Dependencies**:
  - All previous Phase 5 tasks complete

## Dependencies

- PostgreSQL with LISTEN/NOTIFY support (existing)
- RabbitMQ for event publishing (existing)
- shared.database synchronous session support (existing)
- notification_daemon.py as reference implementation (existing)

## Success Criteria

- Game status transitions from SCHEDULED to IN_PROGRESS within 10 seconds of scheduled_at
- EventType.GAME_STARTED events published correctly after status update
- Status transition daemon survives restart without losing scheduled transitions
- No Celery dependencies remain in codebase (pyproject.toml, docker-compose, code files)
- Both notification_daemon and status_transition_daemon run reliably in parallel
- All existing integration and e2e tests pass
- Documentation updated to reflect new architecture without Celery
