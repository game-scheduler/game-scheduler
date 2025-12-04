---
applyTo: '.copilot-tracking/changes/20251203-celery-elimination-notification-consolidation-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: Complete Celery Elimination and Notification System Consolidation

## Overview

Eliminate Celery completely from the codebase by migrating game status transitions to database-backed scheduling using a separate game_status_schedule table and dedicated daemon.

## Objectives

- Remove all Celery dependencies and infrastructure from the project
- Migrate game status transitions (SCHEDULED → IN_PROGRESS) to database-backed scheduling
- Create game_status_schedule table with domain-specific schema
- Implement status_transition_daemon.py following proven notification_daemon.py pattern
- Maintain <10 second latency for status transitions
- Preserve event-driven architecture for EventType.GAME_STARTED

## Research Summary

### Project Files
- services/scheduler/celery_app.py - Celery configuration to be removed
- services/scheduler/tasks/update_game_status.py - Status update task to be replaced
- services/scheduler/notification_daemon.py - Reference implementation pattern
- shared/messaging/events.py - Event types including GAME_STARTED
- docker-compose.base.yml - Service definitions for deployment

### External References
- #file:../research/20251203-celery-elimination-notification-consolidation-research.md - Comprehensive research on Celery elimination approach
- #file:../../.github/instructions/python.instructions.md - Python coding standards
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker deployment standards

### Standards References
- PostgreSQL LISTEN/NOTIFY pattern already proven with notification_daemon
- Separate tables approach selected for domain clarity and type safety
- Database-backed scheduling pattern replaces polling-based Celery beat

## Implementation Checklist

### [x] Phase 1: Create game_status_schedule Table

- [x] Task 1.1: Create Alembic migration for game_status_schedule table
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 11-30)

- [x] Task 1.2: Create PostgreSQL trigger for LISTEN/NOTIFY on status schedule changes
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 32-50)

- [x] Task 1.3: Add GameStatusSchedule SQLAlchemy model
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 52-70)

### [x] Phase 2: Implement Status Transition Daemon

- [x] Task 2.1: Create status_transition_daemon.py based on notification_daemon.py pattern
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 72-95)

- [x] Task 2.2: Implement status transition processing with database transaction
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 97-120)

- [x] Task 2.3: Add error handling and logging for status transitions
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 122-140)

### [x] Phase 3: Integrate with API Layer

- [x] Task 3.1: Update game creation to populate game_status_schedule
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 122-141)

- [x] Task 3.2: Update game scheduled_at changes to update status schedule
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 142-165)

- [x] Task 3.3: Delete status schedule on game cancellation/deletion
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 167-185)

### [x] Phase 4: Deploy and Validate

- [x] Task 4.1: Add status-transition-daemon service to docker-compose
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 202-225)

- [x] Task 4.2: Create Dockerfile for status-transition-daemon
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 227-245)

- [x] Task 4.3: Test status transitions end-to-end
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 247-270)

### [ ] Phase 5: Remove Celery Infrastructure

- [ ] Task 5.1: Remove Celery application and task files
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 272-285)

- [ ] Task 5.2: Remove scheduler and scheduler-beat services from docker-compose
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 287-300)

- [ ] Task 5.3: Remove Celery dependencies from pyproject.toml
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 302-315)

- [ ] Task 5.4: Update documentation to reflect architecture change
  - Details: .copilot-tracking/details/20251203-celery-elimination-notification-consolidation-details.md (Lines 317-335)

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
