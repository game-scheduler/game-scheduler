<!-- markdownlint-disable-file -->

# Release Changes: Daemon-Bot Message Reliability and Error Handling

**Related Plan**: 20251205-daemon-bot-message-reliability-plan.instructions.md
**Implementation Date**: 2025-12-05

## Summary

Fix critical message loss bug in bot consumer and implement daemon-based DLQ
processing with per-message TTL for notifications to ensure reliable event
delivery and data consistency.

## Changes

### Added

- alembic/versions/021_add_game_scheduled_at_to_notification_schedule.py -
  Database migration adding game_scheduled_at column to notification_schedule
  table with backfill
- tests/services/scheduler/test_event_builders.py - Comprehensive unit tests for
  event builder functions including TTL calculation and tuple returns
- tests/shared/messaging/test_sync_publisher.py - Unit tests for
  SyncEventPublisher expiration support
- tests/integration/test_rabbitmq_dlq.py - Comprehensive integration tests for
  RabbitMQ DLQ infrastructure (7 tests)
- docker/rabbitmq.Dockerfile - Multi-stage build for RabbitMQ with credential
  management and configuration injection
- rabbitmq/definitions.json.template - Template for RabbitMQ definitions with
  credential placeholders

### Modified

- shared/models/notification_schedule.py - Added game_scheduled_at field to
  NotificationSchedule model
- services/api/services/notification_schedule.py - Updated populate_schedule to
  include game_scheduled_at when creating notifications
- tests/services/api/services/test_notification_schedule.py - Enhanced test
  assertions to verify game_scheduled_at field
- tests/integration/test_notification_daemon.py - Updated test fixtures to
  include game_scheduled_at in INSERT statements
- scripts/run-integration-tests.sh - Added init container to rebuild list to
  ensure migrations run
- shared/messaging/sync_publisher.py - Added expiration_ms parameter to
  publish() method for per-message TTL support
- services/scheduler/event_builders.py - Updated build_game_reminder_event() to
  return (Event, TTL) tuple with calculated expiration time
- services/scheduler/event_builders.py - Updated build_status_transition_event()
  to return (Event, None) tuple (no TTL for critical transitions)
- services/scheduler/generic_scheduler_daemon.py - Updated \_process_item() to
  handle tuple returns from event builders and pass expiration_ms to publisher
- tests/services/scheduler/test_generic_scheduler_daemon.py - Updated
  mock_event_builder fixture and tests to support tuple returns and added
  comprehensive TTL handling tests
- shared/messaging/consumer.py - Replaced message.process() with manual ACK/NACK
  to prevent message loss on handler failures
- services/bot/events/handlers.py - Added staleness check to
  \_handle_game_reminder_due() to skip notifications for already-started games
- services/scheduler/generic_scheduler_daemon.py - Added process_dlq and
  dlq_check_interval parameters to **init**() for DLQ processing configuration
- services/scheduler/generic_scheduler_daemon.py - Updated run() method to call
  DLQ processing on startup and periodically every 15 minutes
- services/scheduler/generic_scheduler_daemon.py - Implemented
  \_process_dlq_messages() method to consume from DLQ and republish messages
  without TTL
- services/scheduler/notification_daemon_wrapper.py - Enabled DLQ processing
  with process_dlq=True and dlq_check_interval=900
- services/scheduler/status_transition_daemon_wrapper.py - Enabled DLQ
  processing with process_dlq=True and dlq_check_interval=900
- docker-compose.base.yml - Updated rabbitmq service to use custom Dockerfile
  instead of volume mounts for configuration
- docker-compose.integration.yml - Added RabbitMQ environment variables for test
  authentication and simplified test command
- docker/test.Dockerfile - Simplified to use pytest directly as ENTRYPOINT
  instead of bash script wrapper
- scripts/run-integration-tests.sh - Updated to handle both default and specific
  test runs with conditional argument passing
- rabbitmq/definitions.json - Removed guest user permissions (now managed via
  template)
- rabbitmq/rabbitmq.conf - Added load_definitions directive to load
  configuration from JSON file

### Removed

- docker/test-entrypoint.sh - Removed unused bash script (replaced by direct
  pytest ENTRYPOINT)

## Testing

### Unit Tests

Phase 2 implementation includes comprehensive unit test coverage:

- **test_event_builders.py**: 8 tests covering TTL calculation, tuple returns,
  and edge cases
- **test_sync_publisher.py**: 10 tests covering expiration parameter handling
  and message properties
- **test_generic_scheduler_daemon.py**: 33 tests including 3 new tests for tuple
  handling

All 51 unit tests pass successfully.

### Integration Tests

Added comprehensive RabbitMQ DLQ integration test suite:

- **tests/integration/test_rabbitmq_dlq.py**: 7 tests validating complete DLQ
  infrastructure
  - test_dlq_exchange_exists - Verifies game_scheduler.dlx exchange exists and
    is durable
  - test_dlq_queue_exists - Verifies DLQ queue exists and is durable
  - test_bot_events_queue_has_dlx_configured - Behavioral test proving DLX
    configuration by rejecting message
  - test_dlq_binding_exists - Verifies DLQ bound to DLX with catch-all routing
  - test_rejected_message_goes_to_dlq - Verifies NACKed messages route to DLQ
  - test_dlq_message_preserves_metadata - Verifies x-death headers preserved in
    DLQ
  - test_expired_message_goes_to_dlq - Verifies TTL expiration routes to DLQ

All 7 integration tests pass successfully.

### Test Coverage

- Event builders: TTL calculation logic, tuple returns, None handling
- Sync publisher: Expiration parameter, properties preservation, retry behavior
- Scheduler daemon: Tuple unpacking, backward compatibility, error handling
- RabbitMQ infrastructure: DLX/DLQ configuration, message routing, metadata
  preservation, TTL expiration

## Implementation Notes

### RabbitMQ Infrastructure Improvements

Implemented secure RabbitMQ credential management and configuration:

1. **Multi-stage Dockerfile**: Created docker/rabbitmq.Dockerfile that generates
   password hashes at build time and substitutes credentials into definitions
   template securely.

2. **Template-based configuration**: Split RabbitMQ definitions into a template
   (definitions.json.template) with placeholders for username and password hash,
   allowing dynamic credential injection without storing sensitive data in git.

3. **Simplified Docker configuration**: Removed volume mounts from
   docker-compose.base.yml in favor of configuration baked into the image,
   improving reproducibility and reducing external dependencies.

### RabbitMQ DLQ Test Fixes

Fixed several issues discovered during integration testing:

1. **Queue inspection API**: Pika's queue_declare(passive=True) returns
   DeclareOk without queue_arguments. Restructured
   test_bot_events_queue_has_dlx_configured to test behavior (reject message →
   verify in DLQ) instead of inspecting queue configuration directly.

2. **Routing key matching**: Updated test routing keys from three parts
   (game.reminder.due, game.test.ttl) to two parts (game.test, game.ttl) to
   match the game.\* binding pattern in definitions.json.

3. **Bytes vs string comparisons**: Fixed x-death header assertions to compare
   strings with strings (changed b"bot_events" to "bot_events", kept bytes like
   b"game_scheduler.dlx" as bytes where appropriate).

4. **Test isolation**: Added queue purging in rabbitmq_channel fixture (before
   and after each test) to prevent state contamination between tests.

### Docker Test Infrastructure Simplification

Simplified test execution infrastructure:

1. **Direct pytest ENTRYPOINT**: Replaced bash script wrapper with direct pytest
   ENTRYPOINT in docker/test.Dockerfile, following idiomatic Docker pattern.

2. **Flexible test execution**: Updated scripts/run-integration-tests.sh to
   handle both default test discovery (no arguments) and specific test paths,
   using conditional logic to pass arguments correctly.

3. **Cleaner command override**: Simplified docker-compose.integration.yml
   command to work with pytest ENTRYPOINT, removing complexity from bash script
   layer.

## Validation Results

All tests pass successfully:

- **Unit tests**: 51 tests passed (test_generic_scheduler_daemon.py: 33,
  test_event_builders.py: 8, test_sync_publisher.py: 10)
- **Integration tests**: 18 tests passed (7 RabbitMQ DLQ tests, 7 notification
  daemon tests, 4 status transition tests)

The implementation has been validated with comprehensive test coverage including
both unit tests and integration tests running against actual RabbitMQ
infrastructure.
