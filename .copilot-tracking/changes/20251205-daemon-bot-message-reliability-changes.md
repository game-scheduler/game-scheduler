<!-- markdownlint-disable-file -->

# Release Changes: Daemon-Bot Message Reliability and Error Handling

**Related Plan**: 20251205-daemon-bot-message-reliability-plan.instructions.md
**Implementation Date**: 2025-12-05

## Summary

Fix critical message loss bug in bot consumer and implement daemon-based DLQ processing with per-message TTL for notifications to ensure reliable event delivery and data consistency.

## Changes

### Added

- alembic/versions/021_add_game_scheduled_at_to_notification_schedule.py - Database migration adding game_scheduled_at column to notification_schedule table with backfill
- tests/services/scheduler/test_event_builders.py - Comprehensive unit tests for event builder functions including TTL calculation and tuple returns
- tests/shared/messaging/test_sync_publisher.py - Unit tests for SyncEventPublisher expiration support

### Modified

- shared/models/notification_schedule.py - Added game_scheduled_at field to NotificationSchedule model
- services/api/services/notification_schedule.py - Updated populate_schedule to include game_scheduled_at when creating notifications
- tests/services/api/services/test_notification_schedule.py - Enhanced test assertions to verify game_scheduled_at field
- tests/integration/test_notification_daemon.py - Updated test fixtures to include game_scheduled_at in INSERT statements
- scripts/run-integration-tests.sh - Added init container to rebuild list to ensure migrations run
- shared/messaging/sync_publisher.py - Added expiration_ms parameter to publish() method for per-message TTL support
- services/scheduler/event_builders.py - Updated build_game_reminder_event() to return (Event, TTL) tuple with calculated expiration time
- services/scheduler/event_builders.py - Updated build_status_transition_event() to return (Event, None) tuple (no TTL for critical transitions)
- services/scheduler/generic_scheduler_daemon.py - Updated _process_item() to handle tuple returns from event builders and pass expiration_ms to publisher
- tests/services/scheduler/test_generic_scheduler_daemon.py - Updated mock_event_builder fixture and tests to support tuple returns and added comprehensive TTL handling tests
- shared/messaging/consumer.py - Replaced message.process() with manual ACK/NACK to prevent message loss on handler failures
- services/bot/events/handlers.py - Added staleness check to _handle_game_reminder_due() to skip notifications for already-started games
- services/scheduler/generic_scheduler_daemon.py - Added process_dlq and dlq_check_interval parameters to __init__() for DLQ processing configuration
- services/scheduler/generic_scheduler_daemon.py - Updated run() method to call DLQ processing on startup and periodically every 15 minutes
- services/scheduler/generic_scheduler_daemon.py - Implemented _process_dlq_messages() method to consume from DLQ and republish messages without TTL
- services/scheduler/notification_daemon_wrapper.py - Enabled DLQ processing with process_dlq=True and dlq_check_interval=900
- services/scheduler/status_transition_daemon_wrapper.py - Enabled DLQ processing with process_dlq=True and dlq_check_interval=900

### Removed

## Testing

### Unit Tests

Phase 2 implementation includes comprehensive unit test coverage:

- **test_event_builders.py**: 8 tests covering TTL calculation, tuple returns, and edge cases
- **test_sync_publisher.py**: 10 tests covering expiration parameter handling and message properties
- **test_generic_scheduler_daemon.py**: 33 tests including 3 new tests for tuple handling

All 51 unit tests pass successfully.

### Test Coverage

- Event builders: TTL calculation logic, tuple returns, None handling
- Sync publisher: Expiration parameter, properties preservation, retry behavior
- Scheduler daemon: Tuple unpacking, backward compatibility, error handling

## Validation Results

All unit tests pass successfully:
- **test_generic_scheduler_daemon.py**: 33 tests passed
- **test_event_builders.py**: 8 tests passed  
- **test_sync_publisher.py**: 10 tests passed

The implementation has been validated with comprehensive unit test coverage. Integration tests for manual ACK/NACK behavior, DLQ processing, and per-message TTL would require a full RabbitMQ environment and are recommended as follow-up work during system integration testing.


