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
- docker/notification-daemon-entrypoint.sh - Docker entrypoint script for notification daemon that runs Alembic migrations before starting the daemon process

### Modified

- shared/models/**init**.py - Added NotificationSchedule model to exports
- services/api/services/games.py - Integrated notification schedule management: populate_schedule() called after game creation with resolved reminder_minutes, update_schedule() called when scheduled_at or reminder_minutes changes in update_game()
- docker-compose.yml - Added notification-daemon service using scheduler image with custom entrypoint, depends on postgres and rabbitmq, includes healthcheck with pgrep
- docker/scheduler.Dockerfile - Added procps package for process monitoring, copied alembic files and alembic.ini for migrations, copied notification-daemon-entrypoint.sh with executable permissions

### Removed
