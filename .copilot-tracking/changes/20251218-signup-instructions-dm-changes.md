<!-- markdownlint-disable-file -->

# Release Changes: Delayed Join Notification with Conditional Signup Instructions

**Related Plan**: 20251218-signup-instructions-dm-plan.instructions.md
**Implementation Date**: 2025-12-20

## Summary

Replace immediate join confirmation DMs with single 60-second delayed notification that conditionally includes signup instructions when present, using existing notification_schedule infrastructure.

## Changes

### Added

#### Database Migration
- [alembic/versions/bcecd82ff82f_add_notification_type_participant_id.py](alembic/versions/bcecd82ff82f_add_notification_type_participant_id.py) - New migration adding notification_type and participant_id columns
  - Adds `notification_type` column (String(50), default='reminder') for distinguishing reminder vs join notifications
  - Adds `participant_id` column (nullable FK to game_participants.id) for participant-specific notifications
  - Creates CASCADE delete constraint on participant_id (auto-cancels notification when participant leaves)
  - Adds index on participant_id for efficient lookups
  - Adds composite index on (notification_type, notification_time) for efficient daemon queries
  - Both upgrade() and downgrade() paths tested

#### Integration Tests
- [tests/integration/test_database_infrastructure.py](tests/integration/test_database_infrastructure.py#L150-L262) - Added three new tests
  - `test_notification_schedule_schema()` - Verifies all columns exist with correct types, nullability, and defaults
  - `test_notification_schedule_indexes()` - Verifies all required indexes including new ones
  - `test_notification_schedule_foreign_keys()` - Verifies both game_id and participant_id FKs with CASCADE delete

### Modified

#### Database Models
- [shared/models/notification_schedule.py](shared/models/notification_schedule.py#L37-L52) - Extended NotificationSchedule model
  - Added `notification_type: Mapped[str]` field with default='reminder'
  - Added `participant_id: Mapped[str | None]` field with FK to game_participants.id
  - Added `participant` relationship to GameParticipant model
  - Added TYPE_CHECKING import for GameParticipant
  - Updated docstring to document both notification types

### Removed
