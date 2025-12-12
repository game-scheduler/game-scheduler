<!-- markdownlint-disable-file -->

# Release Changes: RabbitMQ Messaging Architecture Cleanup

**Related Plan**: 20251211-rabbitmq-messaging-cleanup-plan.instructions.md
**Implementation Date**: 2025-12-11

## Summary

Fix DLQ exponential growth bug and remove unused RabbitMQ queues by implementing a dedicated retry service with per-queue DLQs and clear ownership.

## Changes

### Added

- services/retry/__init__.py - Created retry service package
- services/retry/retry_daemon.py - Implemented RetryDaemon class for dedicated DLQ processing
- services/retry/retry_daemon_wrapper.py - Created entry point with signal handling and config loading
- docker/retry.Dockerfile - Created multi-stage Dockerfile for retry service container
- tests/integration/test_retry_daemon.py - Created end-to-end integration tests verifying DLQ exponential growth bug fix (3/5 passing including critical bug fix test)
- tests/services/retry/__init__.py - Created unit test package for retry service
- tests/services/retry/test_retry_daemon.py - Created comprehensive unit tests for RetryDaemon class (18/18 passing with 100% coverage)
- grafana-alloy/dashboards/retry-daemon-dashboard.json - Created Grafana dashboard with 8 panels monitoring DLQ depth, processing rates, duration, failures, and health
- grafana-alloy/dashboards/README.md - Created comprehensive dashboard documentation with metrics overview, alert configuration, and troubleshooting guide
- tests/services/retry/test_retry_daemon_observability.py - Created observability tests for metrics, health checks, and span attributes (9/9 passing)

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
- docker-compose.base.yml - Added retry-daemon service with RabbitMQ dependency, OTEL config, and health check
- docker-compose.test.yml - Added retry-daemon dependency to e2e-tests
- docker-compose.integration.yml - Added retry-daemon dependency, fixed command, updated documentation for pytest entrypoint
- docker/test.Dockerfile - Added comments clarifying pytest ENTRYPOINT usage
- .env.integration - Added RETRY_INTERVAL_SECONDS=5 for fast integration testing
- services/scheduler/notification_daemon_wrapper.py - Set process_dlq=False and removed dlq_check_interval parameter
- services/scheduler/status_transition_daemon_wrapper.py - Set process_dlq=False and removed dlq_check_interval parameter
- services/scheduler/generic_scheduler_daemon.py - Removed process_dlq and dlq_check_interval parameters from __init__ (kept process_dlq as deprecated for backwards compatibility)
- services/scheduler/generic_scheduler_daemon.py - Removed last_dlq_check instance variable and DLQ check logic from main loop
- services/scheduler/generic_scheduler_daemon.py - Removed _process_dlq_messages method and pika import
- services/scheduler/generic_scheduler_daemon.py - Fixed _process_item to not re-raise exceptions after rollback (maintain daemon stability)
- tests/services/scheduler/test_generic_scheduler_daemon.py - Removed TestSchedulerDaemonDLQProcessing test class
- services/retry/retry_daemon.py - Added OpenTelemetry metrics (messages_processed_counter, messages_failed_counter, dlq_depth_gauge, processing_duration_histogram)
- services/retry/retry_daemon.py - Added detailed span attributes for message processing (routing_key, event_type, retry_count)
- services/retry/retry_daemon.py - Added health check metrics tracking (last_successful_processing_time, consecutive_failures)
- services/retry/retry_daemon.py - Added is_healthy() method with RabbitMQ connectivity check and failure threshold detection
- services/retry/retry_daemon.py - Moved pika import to module level (removed inline imports from methods)

### Removed

- tests/integration/test_rabbitmq_dlq.py - Removed tests for shared DLQ (will be replaced with per-queue DLQ tests in Phase 2)
- tests/services/scheduler/test_dlq_processing.py - Removed unit tests for DLQ processing (functionality moved to dedicated retry service)

