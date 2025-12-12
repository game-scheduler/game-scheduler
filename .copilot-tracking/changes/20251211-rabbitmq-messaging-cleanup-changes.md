<!-- markdownlint-disable-file -->

# Release Changes: RabbitMQ Messaging Architecture Cleanup

**Related Plan**: 20251211-rabbitmq-messaging-cleanup-plan.instructions.md
**Implementation Date**: 2025-12-11

## Summary

Fix DLQ exponential growth bug and remove unused RabbitMQ queues by implementing a dedicated retry service with per-queue DLQs and clear ownership.

## Changes

### Added

### Modified

- shared/messaging/infrastructure.py - Removed unused queue constants (QUEUE_API_EVENTS, QUEUE_SCHEDULER_EVENTS, QUEUE_DLQ)
- shared/messaging/infrastructure.py - Updated PRIMARY_QUEUES and QUEUE_BINDINGS to only include bot_events and notification_queue
- scripts/init_rabbitmq.py - Removed unused queue declarations (api_events, scheduler_events, DLQ)
- tests/integration/test_rabbitmq_infrastructure.py - Removed tests for unused queues (api_events, scheduler_events, DLQ)
- shared/messaging/infrastructure.py - Added per-queue DLQ constants (QUEUE_BOT_EVENTS_DLQ, QUEUE_NOTIFICATION_DLQ)
- shared/messaging/infrastructure.py - Added DEAD_LETTER_QUEUES list and DLQ_BINDINGS list
- scripts/init_rabbitmq.py - Added imports for DEAD_LETTER_QUEUES and DLQ_BINDINGS
- scripts/init_rabbitmq.py - Added DLQ declaration and binding logic before primary queues
- tests/integration/test_rabbitmq_infrastructure.py - Added tests for per-queue DLQs (bot_events.dlq, notification_queue.dlq)
- tests/integration/test_rabbitmq_infrastructure.py - Added test_dlq_bindings_to_dlx to verify routing key-based bindings
- tests/integration/test_rabbitmq_infrastructure.py - Updated test_primary_queues_have_dlx_configured to verify messages route to correct per-queue DLQ
- shared/messaging/infrastructure.py - Updated DLQ_BINDINGS to use same routing keys as primary queues instead of catch-all pattern

### Removed

- tests/integration/test_rabbitmq_dlq.py - Removed tests for shared DLQ (will be replaced with per-queue DLQ tests in Phase 2)

