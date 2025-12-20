<!-- markdownlint-disable-file -->

# Task Details: Delayed Join Notification with Conditional Signup Instructions

## Research Reference

**Source Research**: #file:../research/20251218-signup-instructions-dm-research.md

## Phase 1: Database Schema Extension

### Task 1.1: Create Alembic migration for notification_schedule table

Add notification_type and participant_id columns to support both game-wide reminders and participant-specific join notifications.

- **Files**:
  - alembic/versions/0XX_add_notification_type_participant_id.py - New migration file
- **Success**:
  - Migration creates notification_type column (String(50), default='reminder')
  - Migration creates participant_id column (nullable FK to game_participants.id with CASCADE delete)
  - Index created on participant_id column
  - Composite index created on (notification_type, notification_time)
  - Migration runs successfully on clean database
  - Downgrade reverts changes cleanly
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 295-327) - Migration schema and SQL
- **Dependencies**:
  - Alembic installed and configured
  - PostgreSQL database accessible

### Task 1.2: Update NotificationSchedule model with new columns

Extend SQLAlchemy model to match new database schema.

- **Files**:
  - shared/models/notification_schedule.py - Update model class
- **Success**:
  - notification_type: Mapped[str] field added with default='reminder'
  - participant_id: Mapped[str | None] field added with FK constraint
  - participant relationship added to GameParticipant
  - Model validates successfully with Alembic autogenerate
  - Type hints match column definitions
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 329-349) - Model definition
- **Dependencies**:
  - Task 1.1 completed (migration run)
  - GameParticipant model exists

## Phase 2: Event System Updates

### Task 2.1: Rename GAME_REMINDER_DUE to NOTIFICATION_DUE in events.py

Generalize event type to handle both reminders and join notifications.

- **Files**:
  - shared/messaging/events.py - Update EventType enum and NotificationDueEvent
- **Success**:
  - GAME_REMINDER_DUE renamed to NOTIFICATION_DUE
  - NotificationDueEvent includes notification_type field
  - NotificationDueEvent includes participant_id field (nullable)
  - Event validates with Pydantic
  - All existing references updated
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 351-365) - Event type definition
- **Dependencies**:
  - None (standalone update)

### Task 2.2: Update event builder for generalized notifications

Modify build_game_reminder_event to build_notification_event supporting both types.

- **Files**:
  - services/scheduler/event_builders.py - Rename and update function
- **Success**:
  - Function renamed to build_notification_event
  - Builds NotificationDueEvent with notification_type from schedule
  - Includes participant_id when present
  - TTL calculation maintained for game expiration
  - Returns (Event, expiration_ms) tuple
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 367-392) - Event builder implementation
- **Dependencies**:
  - Task 1.2 completed (model has new columns)
  - Task 2.1 completed (event type updated)

### Task 2.3: Update daemon wrapper event builder reference

Change daemon to use new event builder function name.

- **Files**:
  - services/scheduler/notification_daemon_wrapper.py - Update event_builder parameter
- **Success**:
  - event_builder changed from build_game_reminder_event to build_notification_event
  - Daemon starts successfully
  - Processes both reminder and join_notification types
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 394-402) - Wrapper update
- **Dependencies**:
  - Task 2.2 completed (function renamed)

## Phase 3: Schedule Creation on Participant Addition

### Task 3.1: Create notification schedule helper function

New service function to encapsulate schedule creation logic.

- **Files**:
  - services/api/services/notification_schedule.py - New file with helper function
- **Success**:
  - schedule_join_notification() function created
  - Takes db, game_id, participant_id, game_scheduled_at, delay_seconds parameters
  - Creates NotificationSchedule with notification_type='join_notification'
  - Sets notification_time to now + delay_seconds (default 60)
  - Flushes to database and returns schedule object
  - Function is async and uses AsyncSession
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 419-446) - Helper function implementation
- **Dependencies**:
  - Task 1.2 completed (model updated)
  - shared/models/base.py has utc_now() function

### Task 3.2: Update API games service for schedule creation

Modify join_game() and _add_new_mentions() to create schedules instead of immediate notifications.

- **Files**:
  - services/api/services/games.py - Update participant addition methods
- **Success**:
  - Import schedule_join_notification helper
  - join_game() creates schedule after participant commit
  - _add_new_mentions() creates schedule for each pre-filled participant
  - No immediate success messages sent
  - Schedules include game.scheduled_at for TTL
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 448-478) - API service updates
- **Dependencies**:
  - Task 3.1 completed (helper function exists)

### Task 3.3: Update bot join handler to remove immediate DM and create schedule

Replace immediate success DM in button handler with schedule creation.

- **Files**:
  - services/bot/handlers/join_game.py - Update handle_join_game function
- **Success**:
  - Remove or comment out immediate success DM code
  - Import NotificationSchedule, timedelta, utc_now
  - Create schedule after participant commit
  - Schedule has notification_type='join_notification'
  - notification_time set to utc_now() + 60 seconds
  - Button interaction response updates view (no DM mention)
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 480-512) - Bot handler updates
- **Dependencies**:
  - Task 1.2 completed (model updated)
  - Task 3.1 completed (can optionally use helper)

## Phase 4: Bot Event Handler Extension

### Task 4.1: Rename and extend notification handler for routing

Generalize _handle_game_reminder_due to route based on notification_type.

- **Files**:
  - services/bot/events/handlers.py - Rename and add routing logic
- **Success**:
  - _handle_game_reminder_due renamed to _handle_notification_due
  - Parses NotificationDueEvent from data
  - Routes to _handle_game_reminder for type='reminder'
  - Routes to _handle_join_notification for type='join_notification'
  - Logs error for unknown notification types
  - Existing reminder logic moved to _handle_game_reminder method
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 519-555) - Handler routing implementation
- **Dependencies**:
  - Task 2.1 completed (event type updated)

### Task 4.2: Implement join notification handler with conditional message

New handler sends delayed join notification with conditional signup instructions.

- **Files**:
  - services/bot/events/handlers.py - Add _handle_join_notification method
- **Success**:
  - Queries game and participant by IDs from event
  - Returns early if participant no longer exists
  - Checks if participant is on waitlist, skips notification if so
  - Formats message with signup instructions if game.signup_instructions exists
  - Uses generic "You've joined" message if no signup instructions
  - Calls _send_dm() with formatted message
  - Logs success/failure appropriately
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 557-602) - Join notification handler implementation
- **Dependencies**:
  - Task 4.1 completed (routing in place)
  - _send_dm() helper exists in handlers.py

### Task 4.3: Update handler registration mapping

Update event type mapping in __init__ to use renamed handler.

- **Files**:
  - services/bot/events/handlers.py - Update handlers dict in __init__
- **Success**:
  - EventType.NOTIFICATION_DUE mapped to self._handle_notification_due
  - Old GAME_REMINDER_DUE reference removed or updated
  - Handler registration validates successfully
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 604-613) - Handler registration
- **Dependencies**:
  - Task 4.1 completed (handler renamed)

## Phase 5: Testing and Validation

### Task 5.1: Update existing notification tests for renamed event type

Ensure existing reminder tests work with renamed event type.

- **Files**:
  - tests/services/bot/events/test_handlers.py - Update test names and assertions
  - tests/services/scheduler/test_event_builders.py - Update builder tests
- **Success**:
  - Test method names updated to reference notification_due
  - Event type assertions changed to NOTIFICATION_DUE
  - notification_type field added to test data with value='reminder'
  - All existing reminder tests pass
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 615-620) - Test update notes
- **Dependencies**:
  - Task 2.1 completed (event type renamed)
  - Task 4.1 completed (handler renamed)

### Task 5.2: Add tests for join notification with signup instructions

Test that join notification includes signup instructions when present.

- **Files**:
  - tests/services/bot/events/test_handlers.py - Add new test method
- **Success**:
  - test_handle_join_notification_with_signup_instructions created
  - Sets game.signup_instructions to sample text
  - Creates test participant
  - Calls _handle_notification_due with type='join_notification'
  - Asserts _send_dm called once
  - Verifies message contains "✅ **You've joined"
  - Verifies message contains "📋 **Signup Instructions**"
  - Verifies message contains actual signup instructions text
  - Test passes
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 622-645) - Test with signup instructions
- **Dependencies**:
  - Task 4.2 completed (handler implemented)

### Task 5.3: Add tests for join notification without signup instructions

Test that generic message sent when no signup instructions.

- **Files**:
  - tests/services/bot/events/test_handlers.py - Add new test method
- **Success**:
  - test_handle_join_notification_without_signup_instructions created
  - Sets game.signup_instructions to None
  - Creates test participant
  - Calls _handle_notification_due with type='join_notification'
  - Asserts _send_dm called once
  - Verifies message equals "✅ You've joined **{game.title}**!"
  - Verifies "Signup Instructions" not in message
  - Test passes
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 647-669) - Test without signup instructions
- **Dependencies**:
  - Task 4.2 completed (handler implemented)

### Task 5.4: Add integration tests for schedule creation and cancellation

Test end-to-end flow of schedule creation and CASCADE cancellation.

- **Files**:
  - tests/integration/test_join_notification_scheduling.py - New integration test file
- **Success**:
  - Test creates game with signup instructions
  - Calls join_game() or simulates button click
  - Verifies NotificationSchedule created with correct fields
  - Verifies notification_type='join_notification'
  - Verifies notification_time ~60 seconds in future
  - Test removes participant
  - Verifies schedule deleted via CASCADE
  - All integration tests pass
- **Research References**:
  - #file:../research/20251218-signup-instructions-dm-research.md (Lines 681-697) - Success criteria and testing strategy
- **Dependencies**:
  - Task 3.2 and 3.3 completed (schedule creation implemented)
  - Integration test infrastructure exists
