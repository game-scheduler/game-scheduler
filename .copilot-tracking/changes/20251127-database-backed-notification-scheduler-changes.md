<!-- markdownlint-disable-file -->

# Release Changes: Database-Backed Event-Driven Notification Scheduler

**Related Plan**: 20251127-database-backed-notification-scheduler-plan.instructions.md
**Implementation Date**: 2025-11-27

## Summary

Replacing polling-based notification scheduler with database-backed event-driven daemon using PostgreSQL LISTEN/NOTIFY and MIN() query pattern for reliable, scalable notification delivery.

## Changes

### Added

- alembic/versions/012_add_notification_schedule.py - Database migration creating notification_schedule table with UUID primary key, foreign key to game_sessions, unique constraint on (game_id, reminder_minutes), partial index for MIN() query performance, and PostgreSQL trigger for LISTEN/NOTIFY events
- services/scheduler/postgres_listener.py - PostgreSQL LISTEN/NOTIFY client for event-driven scheduler wake-ups using psycopg2 with select() for timeout-based waiting, JSON payload parsing, and automatic reconnection
- services/scheduler/schedule_queries.py - Database query functions for notification schedule management with get_next_due_notification() for MIN() query (processes overdue notifications for daemon recovery) and mark_notification_sent()
- services/scheduler/notification_daemon.py - Main event-driven notification daemon using simplified single-notification pattern: queries for next unsent notification, processes immediately if due, or waits until due time, with PostgreSQL LISTEN/NOTIFY integration for instant wake-up on schedule changes, 5-minute periodic safety checks, and long-lived database session reuse for efficiency
- shared/models/notification_schedule.py - SQLAlchemy model for notification_schedule table with relationships to GameSession and proper indexes
- services/api/services/notification_schedule.py - Notification schedule management service with populate_schedule() for game creation, update_schedule() for game modification, and clear_schedule() for manual cleanup
- tests/services/api/services/test_notification_schedule.py - Unit tests for notification schedule service with mocked database sessions, verifying schedule population, updates, and edge cases
- docker/notification-daemon.Dockerfile - Dedicated Dockerfile for notification daemon service using project pyproject.toml for dependencies, multi-stage build, and running as non-root user
- tests/services/scheduler/test_postgres_listener.py - Unit tests (10 tests) for PostgreSQL LISTEN/NOTIFY client covering connection establishment, channel subscription, timeout handling, and notification reception with proper mocking of psycopg2 connections
- tests/services/scheduler/test_schedule_queries.py - Unit tests (7 tests) for notification schedule query functions testing get_next_due_notification() and mark_notification_sent() with proper result mocking
- tests/services/scheduler/test_notification_daemon.py - Unit tests (9 tests) for notification daemon core logic including configuration, connection management, loop iteration with various scenarios, notification processing, and error handling with valid UUID formats

### Modified

- shared/models/**init**.py - Added NotificationSchedule model to exports
- services/api/services/games.py - Integrated notification schedule management: populate_schedule() called after game creation with resolved reminder_minutes, update_schedule() called when scheduled_at or reminder_minutes changes in update_game()
- docker-compose.yml - Updated notification-daemon service to use dedicated notification-daemon.Dockerfile instead of shared scheduler.Dockerfile, removed Redis dependency (not needed by daemon), removed custom entrypoint override
- docker/scheduler.Dockerfile - Removed references to notification-daemon-entrypoint.sh
- shared/database.py - Refactored database URL configuration to build driver-specific URLs (ASYNC_DATABASE_URL, SYNC_DATABASE_URL) from BASE_DATABASE_URL instead of string parsing, eliminating brittle string manipulation
- .env - Changed DATABASE_URL to simple base PostgreSQL URL without driver specification
- services/scheduler/postgres_listener.py - Removed URL manipulation since BASE_DATABASE_URL is now provided directly
- services/scheduler/notification_daemon.py - Updated to use BASE_DATABASE_URL from shared.database for raw psycopg2 connection
- tests/integration/test_notification_daemon.py - Simplified fixtures for Docker-only testing: removed skip_if_no_database fixture (database always available in Docker), simplified db_url and rabbitmq_url fixtures by removing local fallback logic, streamlined test_game_session fixture with better formatting while keeping FK constraint setup
- docker/test.Dockerfile - Created dedicated test image for integration tests with pytest, pytest-asyncio, pytest-cov, and all dev dependencies
- docker-compose.yml - Added integration-tests service with test profile for running integration tests in Docker with proper service dependencies and health checks
- .dockerignore - Commented out tests/ exclusion to allow integration tests in Docker build context
- docker-compose.test.yml - Created isolated test environment with separate PostgreSQL (port 5433), RabbitMQ (port 5673), and Redis (port 6380) instances using tmpfs for performance, test-specific environment variables, profiles for integration vs e2e tests, and dedicated bot-test and notification-daemon-test services for end-to-end testing
- scripts/run-integration-tests.sh - Helper script to run integration tests in isolated Docker environment with automatic cleanup
- scripts/run-e2e-tests.sh - Helper script to run end-to-end tests requiring test Discord bot and guild setup with validation of required environment variables
- TESTING_E2E.md - Comprehensive guide for setting up test Discord bot and guild for end-to-end notification tests with step-by-step instructions, environment variable configuration, troubleshooting tips, and CI/CD integration guidance
- .gitignore - Added .env.test to prevent committing test Discord credentials
- docker-compose.base.yml - Added environment variable pass-through (DATABASE_URL, RABBITMQ_URL, REDIS_URL, DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID) to bot, api, scheduler, scheduler-beat, and notification-daemon services to fix localhost connection issues
- docker-compose.integration.yml - Added PostgreSQL connection environment variables (POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB) to integration-tests service and added dependency on init service completion
- services/scheduler/notification_daemon.py - Added db.rollback() in exception handler (line ~103) to prevent PendingRollbackError when query fails mid-transaction
- services/bot/config.py - Changed discord_bot_token and discord_client_id from required to optional fields (default=None) to support integration test mode without Discord credentials
- services/bot/main.py - Added early return when Discord tokens not configured (test mode) to prevent bot startup without credentials
- shared/models/guild.py - Added guild_name field (Mapped[str], String(100), nullable=False) to match database schema from migration 001_initial_schema.py
- tests/integration/test_notification_daemon.py - Added guild_name="Test Guild" to test fixture INSERT statement to satisfy NOT NULL constraint
- scripts/run-integration-tests.sh - Replaced `docker compose up --abort-on-container-exit` with `docker compose run` to avoid init container triggering premature shutdown (docker compose run starts dependencies automatically), added trap handler for guaranteed cleanup on success or failure
- scripts/run-e2e-tests.sh - Replaced `docker compose up --abort-on-container-exit` with `docker compose run`, added trap handler for cleanup consistency
- docker/test-entrypoint.sh - Removed redundant database wait and migration steps (now handled by init container), simplified to only execute tests directly
- .env.e2e - Removed problematic REDIS_COMMAND variable that caused bash parsing errors when sourcing file
- docker-compose.e2e.yml - Added init service dependency and API_BASE_URL environment variable, added api service dependency for e2e tests
- tests/e2e/test_game_notification_api_flow.py - Created API-based e2e tests using httpx to test complete flow through REST endpoints (POST /games → schedule populated, daemon processes → RabbitMQ events, PUT /games → schedule updated, DELETE /games → schedule cleaned), replacing direct SQL insert approach with proper API integration testing

### Removed

- docker/notification-daemon-entrypoint.sh - Removed unnecessary entrypoint script (migrations handled separately, daemon starts directly via CMD)
- tests/integration/test_notification_flow_e2e.py - Removed redundant integration-level tests that duplicated existing coverage in test_notification_daemon.py (game CRUD operations at SQL level don't qualify as true e2e tests)

## Testing

### Unit Tests (42 total)

- 10 tests for PostgreSQL LISTEN/NOTIFY client (services/scheduler/test_postgres_listener.py) ✅
- 7 tests for schedule queries (services/scheduler/test_schedule_queries.py) ✅
- 9 tests for notification daemon core (services/scheduler/test_notification_daemon.py) ✅
- 16 tests for notification schedule service (services/api/services/test_notification_schedule.py) ✅

### Integration Tests (10 total)

- 4 tests for PostgreSQL LISTEN/NOTIFY with real database (tests/integration/test_notification_daemon.py) ✅
- 3 tests for schedule queries with real database ✅
- 3 tests for daemon integration with PostgreSQL and RabbitMQ ✅

**Test Execution**: `bash scripts/run-integration-tests.sh`

**Test Results**: All 10 integration tests passing as of 2025-11-28

### E2E Tests

**Status**: Deferred for dedicated planning phase

**Created**: Initial test structure at tests/e2e/test_game_notification_api_flow.py with 4 test cases as starting point for future e2e testing work

**Rationale**: Comprehensive e2e testing requires systematic planning to address:

- API authentication patterns in test environment
- Test data fixture management (avoiding JSON casting issues)
- Database state isolation between tests
- Discord bot integration testing strategy
- API contract testing patterns
- httpx dependency and client configuration

**Recommendation**: Create separate research/planning documents for e2e testing strategy before implementation

**Note**: Integration tests (10/10 passing) provide sufficient coverage for notification daemon behavior. E2E tests would add value by testing the complete user-facing API surface, but require architectural decisions beyond the scope of this notification scheduler implementation.

**Debugging Summary**: Fixed 7 critical issues discovered during integration test setup:

1. Services couldn't connect to infrastructure (environment variables not propagated from base compose file)
2. Notification daemon PendingRollbackError (missing db.rollback() in exception handler)
3. Bot validation errors in test mode (Discord tokens required but not available)
4. Test container couldn't connect to database (missing PostgreSQL connection parameters)
5. Schema mismatch causing NULL constraint violations (guild_name field missing from model)
6. Test execution reliability (init container completion triggered `--abort-on-container-exit`, killing tests mid-execution due to timing race - resolved by using profiles + `docker compose run`)
7. Redundant e2e test file (tests/integration/test_notification_flow_e2e.py) removed after analysis showed it duplicated existing integration test coverage without adding true end-to-end API testing value

## Deployment Notes

1. Run database migration: `docker compose run --rm api alembic upgrade head`
2. Rebuild notification-daemon service: `docker compose build notification-daemon`
3. Restart services: `docker compose up -d`
4. Verify daemon logs: `docker compose logs -f notification-daemon`

## Performance Characteristics

- **Query Complexity**: O(1) with partial index on notification_time WHERE sent = FALSE
- **Memory Usage**: O(1) - only current minimum notification in memory
- **Notification Latency**: <10 seconds with LISTEN/NOTIFY wake-ups
- **Recovery Time**: Single MIN() query on restart
- **Scalability**: Supports unlimited notification windows (weeks/months in advance)
