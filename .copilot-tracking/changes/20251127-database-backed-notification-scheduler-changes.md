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

### Removed

- docker/notification-daemon-entrypoint.sh - Removed unnecessary entrypoint script (migrations handled separately, daemon starts directly via CMD)

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

**Test Execution**: `docker compose --profile test run --rm integration-tests`

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
