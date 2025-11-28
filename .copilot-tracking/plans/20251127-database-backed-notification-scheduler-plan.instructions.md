---
applyTo: ".copilot-tracking/changes/20251127-database-backed-notification-scheduler-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Database-Backed Event-Driven Notification Scheduler

## Overview

Replace polling-based notification scheduler with database-backed event-driven daemon using PostgreSQL LISTEN/NOTIFY and MIN() query pattern for reliable, scalable notification delivery.

## Objectives

- Eliminate Celery ETA unreliability and memory accumulation issues
- Support unlimited notification windows (weeks/months in advance)
- Achieve <10 second notification latency with event-driven wake-ups
- Ensure zero data loss on scheduler restart through database persistence
- Scale to millions of scheduled games with O(1) query performance

## Research Summary

### Project Files

- services/scheduler/tasks/check_notifications.py - Current polling implementation (to be replaced)
- services/scheduler/tasks/send_notification.py - Celery task that publishes to RabbitMQ (to be replaced with direct publish)
- services/scheduler/services/notification_service.py - RabbitMQ event publisher (reuse existing)
- shared/messaging/sync_publisher.py - Synchronous RabbitMQ publisher (reuse existing)
- shared/database.py - Database configuration with psycopg2 support (already configured)
- alembic/versions/011_add_expected_duration_minutes.py - Latest migration pattern reference

### External References

- #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 1-411) - Complete architecture research
- #fetch:"https://docs.celeryq.dev/en/stable/userguide/calling.html#eta-and-countdown" - Celery ETA limitations
- #fetch:"https://www.postgresql.org/docs/current/sql-notify.html" - PostgreSQL LISTEN/NOTIFY documentation
- #fetch:"https://www.postgresql.org/docs/current/sql-listen.html" - PostgreSQL LISTEN session management

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards
- #file:../../.github/instructions/taming-copilot.instructions.md - Code modification principles

## Implementation Checklist

### [x] Phase 1: Database Schema and Migration

- [x] Task 1.1: Create Alembic migration for notification_schedule table

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 15-35)

- [x] Task 1.2: Add PostgreSQL trigger for LISTEN/NOTIFY
  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 37-56)

### [x] Phase 2: Notification Daemon Core

- [x] Task 2.1: Create PostgreSQL LISTEN/NOTIFY client

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 58-78)

- [x] Task 2.2: Implement notification schedule queries

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 80-99)

- [x] Task 2.3: Create main notification daemon loop

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 101-123)

- [x] Task 2.4: Add daemon entry point and configuration
  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 125-144)

### [x] Phase 3: API Integration

- [x] Task 3.1: Add schedule population on game creation

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 15-35)

- [x] Task 3.2: Add schedule updates on game modification

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 37-56)

- [x] Task 3.3: Add schedule cleanup on game deletion
  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 188-204)

### [ ] Phase 4: Docker and Deployment

- [ ] Task 4.1: Create notification daemon Docker entrypoint

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 206-221)

- [ ] Task 4.2: Add daemon service to docker-compose.yml

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 223-242)

- [ ] Task 4.3: Update scheduler Dockerfile for daemon
  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 244-259)

### [ ] Phase 5: Testing

- [ ] Task 5.1: Create unit tests for daemon components

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 261-281)

- [ ] Task 5.2: Create integration tests with PostgreSQL LISTEN/NOTIFY

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 283-302)

- [ ] Task 5.3: Create end-to-end notification flow tests
  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 304-323)

### [ ] Phase 6: Cleanup and Documentation

- [ ] Task 6.1: Remove old Celery notification tasks

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 325-342)

- [ ] Task 6.2: Remove Redis deduplication code

  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 344-358)

- [ ] Task 6.3: Update documentation and README
  - Details: .copilot-tracking/details/20251127-database-backed-notification-scheduler-details.md (Lines 360-375)

## Dependencies

- psycopg2-binary>=2.9.0 (already installed)
- sqlalchemy[asyncio]>=2.0.0 (already installed)
- PostgreSQL 15+ with LISTEN/NOTIFY support
- RabbitMQ for event publishing (existing infrastructure)
- Existing shared.messaging.sync_publisher module

## Success Criteria

- Notification daemon starts successfully and connects to PostgreSQL
- Database migration creates notification_schedule table with proper indexes
- PostgreSQL trigger sends NOTIFY events on schedule changes
- Daemon wakes up within 1 second of schedule changes via LISTEN
- Notifications delivered with <10 second latency from due time
- Daemon survives restart without losing scheduled notifications
- MIN() query performs efficiently with partial index
- All tests pass with 100% coverage of core daemon logic
- Old Celery notification tasks completely removed
- Documentation updated with new architecture diagrams
