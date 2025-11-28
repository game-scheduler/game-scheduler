<!-- markdownlint-disable-file -->

# Release Changes: Database-Backed Event-Driven Notification Scheduler

**Related Plan**: 20251127-database-backed-notification-scheduler-plan.instructions.md
**Implementation Date**: 2025-11-27

## Summary

Replacing polling-based notification scheduler with database-backed event-driven daemon using PostgreSQL LISTEN/NOTIFY and MIN() query pattern for reliable, scalable notification delivery.

## Changes

### Added

- alembic/versions/012_add_notification_schedule.py - Database migration creating notification_schedule table with UUID primary key, foreign key to game_sessions, unique constraint on (game_id, reminder_minutes), partial index for MIN() query performance, and PostgreSQL trigger for LISTEN/NOTIFY events

### Modified

### Removed
