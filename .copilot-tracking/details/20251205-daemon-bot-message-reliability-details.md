<!-- markdownlint-disable-file -->
# Task Details: Daemon-Bot Message Reliability and Error Handling

## Research Reference

**Source Research**: #file:../research/20251205-daemon-bot-message-reliability-research.md

## Phase 1: Schema Enhancement

### Task 1.1: Create database migration for game_scheduled_at column

Add `game_scheduled_at` column to `notification_schedule` table to enable TTL calculation without JOINs.

- **Files**:
  - alembic/versions/XXX_add_game_scheduled_at_to_notification_schedule.py - New migration file
- **Success**:
  - Migration creates `game_scheduled_at` column as nullable DateTime with timezone
  - Backfill populates existing rows with values from joined game table
  - Column set to NOT NULL after backfill
  - Migration is reversible
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1854-1890) - Schema denormalization rationale
- **Dependencies**:
  - Alembic installed and configured
  - Database connection available

### Task 1.2: Update NotificationSchedule model

Add `game_scheduled_at` field to SQLAlchemy model.

- **Files**:
  - shared/models.py - NotificationSchedule class
- **Success**:
  - Model includes `game_scheduled_at` column definition
  - Field type matches migration (DateTime with timezone)
  - Field is non-nullable after migration
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1854-1890) - Denormalization justification
- **Dependencies**:
  - Task 1.1 migration completed

### Task 1.3: Update notification schedule population service

Update `populate_schedule()` to include `game_scheduled_at` when creating notifications.

- **Files**:
  - services/api/services/notification_schedule_service.py - populate_schedule() function
- **Success**:
  - Each NotificationSchedule created includes `game_scheduled_at=game.scheduled_at`
  - Full replacement pattern (delete all + recreate) maintains consistency
  - No additional queries needed (game object already loaded)
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 2220-2222) - Full replacement pattern confirmation
- **Dependencies**:
  - Task 1.2 model update completed

## Phase 2: Per-Message TTL Implementation

### Task 2.1: Enhance sync_publisher with expiration support

Add optional `expiration_ms` parameter to publisher for per-message TTL.

- **Files**:
  - shared/messaging/sync_publisher.py - publish() method
- **Success**:
  - publish() accepts optional `expiration_ms: int | None` parameter
  - When provided, sets `expiration` property on BasicProperties
  - Value converted to string representation of milliseconds
  - Backward compatible (None means use queue-level TTL)
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1735-1780) - Per-message TTL implementation
- **Dependencies**:
  - pika library (already installed)

### Task 2.2: Update event builders to return (Event, TTL) tuples

Modify event builders to calculate and return TTL for notifications.

- **Files**:
  - services/scheduler/event_builders.py - build_game_reminder_event(), build_status_transition_event()
- **Success**:
  - build_game_reminder_event() returns tuple[Event, int | None]
  - TTL calculated as milliseconds from now until game.scheduled_at
  - Minimum TTL of 60 seconds (don't expire immediately)
  - build_status_transition_event() returns tuple[Event, None] (no TTL)
  - Uses notification.game_scheduled_at field (no JOIN needed)
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1791-1844) - Event builder TTL calculation
- **Dependencies**:
  - Task 1.3 game_scheduled_at field populated
  - Task 2.1 publisher enhancement completed

### Task 2.3: Update daemon to handle tuple returns

Modify daemon to unpack (Event, TTL) tuples and pass TTL to publisher.

- **Files**:
  - services/scheduler/generic_scheduler_daemon.py - _process_item() method
- **Success**:
  - _process_item() unpacks tuple from event builder
  - Passes expiration_ms to publisher.publish()
  - Handles both tuple and Event returns (backward compatibility during transition)
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1851-1863) - Daemon tuple handling
- **Dependencies**:
  - Task 2.1 and 2.2 completed

## Phase 3: Fix Bot Consumer Auto-ACK

### Task 3.1: Replace message.process() with manual ACK/NACK

Fix critical auto-ACK bug by implementing manual message acknowledgment.

- **Files**:
  - shared/messaging/consumer.py - _process_message() method
- **Success**:
  - Remove `async with message.process()` context manager
  - On successful handler execution: call `await message.ack()`
  - On exception: call `await message.nack(requeue=False)` to send to DLQ
  - All failures go to DLQ (no instant retry loops)
  - Proper error logging with event type and exception
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 118-151) - Manual ACK implementation
- **Dependencies**:
  - aio_pika library (already installed)

### Task 3.2: Make bot handler defensive for stale notifications

Add staleness check to notification handler to skip expired notifications.

- **Files**:
  - services/bot/events/handlers.py - _handle_game_reminder_due() method
- **Success**:
  - Load game from database at start of handler
  - Check if game.scheduled_at < now() before processing
  - If stale, log skip message and return without sending notifications
  - Prevents sending notifications for already-started games
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 2046-2090) - Defensive handler pattern
- **Dependencies**:
  - Task 3.1 manual ACK completed

## Phase 4: Daemon DLQ Processing

### Task 4.1: Add DLQ processing configuration to SchedulerDaemon

Add configuration parameters for DLQ processing to daemon.

- **Files**:
  - services/scheduler/generic_scheduler_daemon.py - SchedulerDaemon.__init__() and run() methods
- **Success**:
  - __init__() accepts `process_dlq: bool = False` parameter
  - __init__() accepts `dlq_check_interval: int = 900` parameter (15 minutes)
  - run() calls DLQ processing on startup if process_dlq=True
  - run() calls DLQ processing every dlq_check_interval seconds
  - Configuration stored as instance attributes
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1610-1640) - Daemon configuration pattern
- **Dependencies**:
  - None (configuration only)

### Task 4.2: Implement DLQ message processing logic

Add method to consume from DLQ and republish messages.

- **Files**:
  - services/scheduler/generic_scheduler_daemon.py - _process_dlq_messages() method
- **Success**:
  - Method consumes all messages from dead_letter_queue
  - Republishes each message to primary queue WITHOUT TTL (let bot decide staleness)
  - Uses existing sync_publisher instance
  - Logs number of messages republished
  - Handles empty DLQ gracefully (no error)
  - Properly closes RabbitMQ connection after processing
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 2095-2148) - DLQ processing logic
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1605-1710) - Daemon-based DLQ architecture
- **Dependencies**:
  - Task 3.1 manual ACK (ensures messages reach DLQ)
  - Task 2.1 publisher enhancement (for republishing)

### Task 4.3: Enable DLQ processing in daemon wrappers

Configure both daemon wrappers to process DLQ.

- **Files**:
  - services/scheduler/notification_daemon_wrapper.py - main() function
  - services/scheduler/status_transition_daemon_wrapper.py - main() function
- **Success**:
  - Both wrappers pass process_dlq=True to SchedulerDaemon
  - Both wrappers pass dlq_check_interval=900 (15 minutes)
  - Configuration applied to daemon instances
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1629-1640) - Daemon wrapper configuration
- **Dependencies**:
  - Task 4.1 and 4.2 completed

## Phase 5: Testing and Validation

### Task 5.1: Add integration tests for manual ACK/NACK behavior

Create tests to verify consumer ACKs on success, NACKs on failure.

- **Files**:
  - tests/integration/messaging/test_consumer_ack_nack.py - New test file
- **Success**:
  - Test verifies successful handler results in ACK
  - Test verifies handler exception results in NACK to DLQ
  - Test verifies message not requeued (requeue=False)
  - Tests use real RabbitMQ (not mocked)
  - Tests verify DLQ receives NACKed messages
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 118-151) - Manual ACK specification
- **Dependencies**:
  - Task 3.1 completed
  - Integration test infrastructure exists

### Task 5.2: Add integration tests for DLQ processing

Create tests to verify daemon republishes from DLQ correctly.

- **Files**:
  - tests/integration/scheduler/test_daemon_dlq_processing.py - New test file
- **Success**:
  - Test verifies daemon consumes from DLQ on startup
  - Test verifies daemon republishes messages to primary queue
  - Test verifies TTL removed when republishing
  - Test verifies periodic DLQ check (every 15 minutes)
  - Tests use real RabbitMQ and PostgreSQL
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 2095-2148) - DLQ processing behavior
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1605-1710) - Architecture rationale
- **Dependencies**:
  - Task 4.2 and 4.3 completed

### Task 5.3: Add integration tests for per-message TTL

Create tests to verify notifications expire when game starts.

- **Files**:
  - tests/integration/scheduler/test_notification_ttl.py - New test file
- **Success**:
  - Test verifies notification messages have expiration property set
  - Test verifies TTL calculated correctly (ms until game.scheduled_at)
  - Test verifies status transitions have no TTL (None)
  - Test verifies bot handler skips stale notifications
  - Tests use real RabbitMQ to verify TTL behavior
- **Research References**:
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 1735-1844) - Per-message TTL implementation
  - #file:../research/20251205-daemon-bot-message-reliability-research.md (Lines 2046-2090) - Defensive handler behavior
- **Dependencies**:
  - Phase 2 and Phase 3 completed

## Dependencies

- RabbitMQ with dead letter exchange configured (already exists)
- PostgreSQL database with notification_schedule table
- aio_pika and pika libraries installed
- SQLAlchemy for ORM operations
- Alembic for migrations

## Success Criteria

- All migrations run successfully
- Bot consumer only ACKs after successful processing
- Failed messages accumulate in DLQ
- Daemon republishes from DLQ on startup and every 15 minutes
- Notifications have TTL that expires at game start
- Status transitions retry infinitely (no TTL)
- Bot handler skips stale notifications defensively
- All integration tests pass
- No message loss occurs during normal or failure scenarios
