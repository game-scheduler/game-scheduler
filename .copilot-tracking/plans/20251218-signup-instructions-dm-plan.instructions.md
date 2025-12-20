---
applyTo: ".copilot-tracking/changes/20251218-signup-instructions-dm-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Delayed Join Notification with Conditional Signup Instructions

## Overview

Replace immediate join confirmation DM with single 60-second delayed notification that conditionally includes signup instructions when present, using existing notification_schedule infrastructure.

## Objectives

- Remove immediate "You've joined" DMs from all participant addition paths
- Extend notification_schedule table to support participant-specific notifications
- Send single delayed notification 60 seconds after join with conditional signup instructions
- Leverage CASCADE delete for automatic cancellation when participant removed
- Maintain backward compatibility with existing game reminder notifications

## Research Summary

### Project Files

- services/bot/handlers/join_game.py - Currently sends immediate success DM, needs removal and schedule creation
- services/api/services/games.py - Has join_game() and _add_new_mentions() methods for participant creation
- services/bot/events/handlers.py - Handles game.reminder_due events, needs extension for join_notification
- services/scheduler/notification_daemon_wrapper.py - Existing daemon for scheduled notifications
- shared/models/notification_schedule.py - Current schedule model needs notification_type and participant_id columns
- shared/messaging/events.py - Event types, needs NOTIFICATION_DUE to replace GAME_REMINDER_DUE

### External References

- #file:../research/20251218-signup-instructions-dm-research.md - Complete implementation research with schema changes
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - General best practices

## Implementation Checklist

### [ ] Phase 1: Database Schema Extension

- [ ] Task 1.1: Create Alembic migration for notification_schedule table
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 15-45)

- [ ] Task 1.2: Update NotificationSchedule model with new columns
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 47-70)

### [ ] Phase 2: Event System Updates

- [ ] Task 2.1: Rename GAME_REMINDER_DUE to NOTIFICATION_DUE in events.py
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 72-95)

- [ ] Task 2.2: Update event builder for generalized notifications
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 97-120)

- [ ] Task 2.3: Update daemon wrapper event builder reference
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 122-140)

### [ ] Phase 3: Schedule Creation on Participant Addition

- [ ] Task 3.1: Create notification schedule helper function
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 142-175)

- [ ] Task 3.2: Update API games service for schedule creation
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 177-210)

- [ ] Task 3.3: Update bot join handler to remove immediate DM and create schedule
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 212-245)

### [ ] Phase 4: Bot Event Handler Extension

- [ ] Task 4.1: Rename and extend notification handler for routing
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 247-280)

- [ ] Task 4.2: Implement join notification handler with conditional message
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 282-330)

- [ ] Task 4.3: Update handler registration mapping
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 332-350)

### [ ] Phase 5: Testing and Validation

- [ ] Task 5.1: Update existing notification tests for renamed event type
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 352-375)

- [ ] Task 5.2: Add tests for join notification with signup instructions
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 377-410)

- [ ] Task 5.3: Add tests for join notification without signup instructions
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 412-445)

- [ ] Task 5.4: Add integration tests for schedule creation and cancellation
  - Details: .copilot-tracking/details/20251218-signup-instructions-dm-details.md (Lines 447-480)

## Dependencies

- PostgreSQL with LISTEN/NOTIFY support (existing)
- RabbitMQ message broker (existing)
- SQLAlchemy async (existing)
- Alembic for migrations (existing)
- Existing notification daemon infrastructure (existing)
- discord.py library (existing)

## Success Criteria

- Migration successfully adds notification_type and participant_id columns
- No immediate DM sent when user joins game
- Single delayed notification sent 60 seconds after join
- Notification includes signup instructions when game.signup_instructions exists
- Notification uses generic message when game.signup_instructions is None
- Schedule automatically deleted when participant removed (CASCADE)
- Existing game reminder notifications continue working unchanged
- All tests pass including new join notification tests
- No Docker changes required (reuses existing notification-daemon service)
