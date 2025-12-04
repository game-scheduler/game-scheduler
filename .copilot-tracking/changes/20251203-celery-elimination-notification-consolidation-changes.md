<!-- markdownlint-disable-file -->

# Release Changes: Complete Celery Elimination and Notification System Consolidation

**Related Plan**: 20251203-celery-elimination-notification-consolidation-plan.instructions.md
**Implementation Date**: 2025-12-03

## Summary

Eliminated Celery completely from the codebase by migrating game status transitions to database-backed scheduling using a separate game_status_schedule table and dedicated status_transition_daemon.

## Changes

### Added

- alembic/versions/020_add_game_status_schedule.py - Database migration creating game_status_schedule table with PostgreSQL LISTEN/NOTIFY trigger for status transition scheduling
- shared/models/game_status_schedule.py - SQLAlchemy model for game_status_schedule table (100% test coverage)
- services/scheduler/status_transition_daemon.py - Event-driven daemon for processing game status transitions using PostgreSQL LISTEN/NOTIFY pattern
- services/scheduler/status_schedule_queries.py - Database query functions for retrieving and updating game status schedule records (100% test coverage)
- tests/shared/models/test_game_status_schedule.py - Unit tests for GameStatusSchedule model (7 tests)
- tests/services/scheduler/test_status_schedule_queries.py - Unit tests for status schedule query functions (8 tests)
- docker/status-transition-daemon.Dockerfile - Multi-stage Docker build for status transition daemon service
- tests/integration/test_status_transitions.py - Integration tests for status transition daemon end-to-end functionality

### Modified

- shared/models/__init__.py - Added GameStatusSchedule model import and export
- shared/messaging/events.py - Added GameStartedEvent model for game.started event publishing
- shared/messaging/__init__.py - Added GameStartedEvent export
- services/api/services/games.py - Integrated game_status_schedule with game creation, updates, and cancellation (Task 3.1, 3.2, 3.3)
- docker-compose.base.yml - Added status-transition-daemon service definition with healthcheck and dependency configuration
- docker/test.Dockerfile - Updated uv pip install command to use --group dev for dependency groups
- scripts/run-integration-tests.sh - Added build step and argument passing with "$@" for selective test execution
- services/scheduler/status_transition_daemon.py - Removed buffer_seconds parameter and fixed NOTIFY channel name (bug fixes during Phase 4 validation)
- alembic/versions/020_add_game_status_schedule.py - Fixed trigger to always send NOTIFY regardless of time window, enabling true event-driven architecture

### Removed

## Notes

Phase 4 (Deploy and Validate) is complete:
- Task 4.1 ✅: status-transition-daemon service added to docker-compose.base.yml with healthcheck, DATABASE_URL, RABBITMQ_URL env vars
- Task 4.2 ✅: status-transition-daemon.Dockerfile created following multi-stage build pattern (base + production stages)
- Task 4.3 ✅: Integration tests created with 3 test classes and 6 tests - ALL PASSING:
  - TestPostgresListenerIntegration: PostgreSQL LISTEN/NOTIFY trigger validation (1 test)
  - TestStatusScheduleQueries: Database query function validation (2 tests)
  - TestStatusTransitionDaemonIntegration: Full daemon workflow validation (3 tests)
- Task 4.4 ✅: Integration tests pass successfully - 6/6 tests passing in 19.95 seconds
- Docker test infrastructure updated to support new uv dependency group syntax (--group dev)
- Test script enhanced to build before running and pass arguments for selective test execution

Phase 4 validation demonstrates:
- PostgreSQL LISTEN/NOTIFY trigger fires correctly on game_status_schedule changes
- Query functions correctly retrieve due transitions and mark them executed
- Daemon successfully processes transitions, updates game status, and publishes events
- Multi-transition handling works correctly
- Future transition scheduling and processing works as expected

Bug fixes applied during Phase 4 validation:
- Fixed daemon tight-loop issue by removing unnecessary buffer_seconds parameter - daemon now waits until exact transition time
- Fixed NOTIFY channel mismatch: daemon was listening on 'game_status_changed' but trigger sent to 'game_status_schedule_changed'
- Fixed trigger to always send NOTIFY (removed 10-minute window restriction) enabling true event-driven architecture without polling
- Updated logging levels from DEBUG to INFO for better monitoring visibility

