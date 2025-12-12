---
applyTo: ".copilot-tracking/changes/20251211-rabbitmq-messaging-cleanup-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: RabbitMQ Messaging Architecture Cleanup

## Overview

Fix DLQ exponential growth bug and remove unused RabbitMQ queues by implementing a dedicated retry service with per-queue DLQs and clear ownership.

## Objectives

- Fix DLQ exponential growth caused by duplicate processing from multiple daemons
- Remove unused queues (scheduler_events, api_events) to simplify infrastructure
- Implement dedicated retry service for clear ownership of DLQ processing
- Establish per-queue DLQ pattern (bot_events.dlq, notification_queue.dlq)
- Remove DLQ processing logic from scheduler daemons

## Research Summary

### Project Files

- shared/messaging/infrastructure.py - Queue and exchange definitions
- services/scheduler/generic_scheduler_daemon.py - Current DLQ processing implementation
- services/scheduler/notification_daemon_wrapper.py - Notification daemon with process_dlq=True
- services/scheduler/status_transition_daemon_wrapper.py - Status daemon with process_dlq=True
- scripts/init_rabbitmq.py - RabbitMQ initialization script

### External References

- #file:../research/20251211-dlq-exponential-growth-analysis.md - Complete root cause analysis and solution design

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding standards

## Implementation Checklist

### [x] Phase 1: Remove Unused Infrastructure

- [x] Task 1.1: Remove unused queue constants from infrastructure.py
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 1-25)

- [x] Task 1.2: Update PRIMARY_QUEUES and QUEUE_BINDINGS lists
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 27-50)

- [x] Task 1.3: Remove unused queue declarations from init_rabbitmq.py
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 52-70)

- [x] Task 1.4: Update integration tests to remove unused queue references
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 72-90)

### [x] Phase 2: Implement Per-Queue DLQ Pattern

- [x] Task 2.1: Add per-queue DLQ constants to infrastructure.py
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 92-115)

- [x] Task 2.2: Update init_rabbitmq.py to create per-queue DLQs
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 117-145)

- [x] Task 2.3: Remove shared "DLQ" queue declaration
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 147-160)

### [x] Phase 3: Create Dedicated Retry Service

- [x] Task 3.1: Create retry_daemon.py with RetryDaemon class
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 162-230)

- [x] Task 3.2: Create retry_daemon_wrapper.py entry point
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 232-250)

- [x] Task 3.3: Create retry.Dockerfile
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 252-275)

- [x] Task 3.4: Add retry-daemon service to docker-compose.base.yml
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 277-305)

- [x] Task 3.5: Add retry-daemon to test compose files
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 307-325)

- [x] Task 3.6: Add observability configuration for retry-daemon
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 327-345)

- [x] Task 3.7: Create integration tests for retry daemon
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 347-380)

### [x] Phase 4: Remove DLQ Processing from Scheduler Daemons

- [x] Task 4.1: Remove process_dlq parameter from notification_daemon_wrapper.py
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 307-325)

- [x] Task 4.2: Remove process_dlq parameter from status_transition_daemon_wrapper.py
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 327-345)

- [x] Task 4.3: Remove DLQ processing code from generic_scheduler_daemon.py
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 347-380)

- [x] Task 4.4: Update daemon tests to remove DLQ expectations
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 382-405)

### [x] Phase 5: Testing and Validation

- [x] Task 5.1: Write unit tests for RetryDaemon class
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 407-440)

- [x] Task 5.2: Write integration tests for DLQ retry flow
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 442-475)

- [x] Task 5.3: Verify all existing tests pass with new architecture
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 477-495)

### [x] Phase 6: Enhanced Observability

- [x] Task 6.1: Add OpenTelemetry metrics to RetryDaemon
  - Details: Add counters for processed/failed messages, gauges for DLQ depth
  - Add histogram for processing duration per DLQ

- [x] Task 6.2: Add detailed span attributes for message processing
  - Details: Add event_type, routing_key, retry_count to spans
  - Track individual message processing in child spans

- [x] Task 6.3: Add health check metrics
  - Details: Expose last successful processing time, consecutive failures
  - Add readiness indicator based on RabbitMQ connectivity

- [x] Task 6.4: Create Grafana dashboard for retry daemon
  - Details: Visualize DLQ depth over time, processing rates, failure rates
  - Alert on consecutive processing failures or growing DLQ depth

### [ ] Phase 7: Documentation and Cleanup

- [ ] Task 7.1: Update RUNTIME_CONFIG.md with retry service documentation
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 497-520)

- [ ] Task 7.2: Add DLQ monitoring guidance
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 522-545)

- [ ] Task 7.3: Document migration steps for existing deployments
  - Details: .copilot-tracking/details/20251211-rabbitmq-messaging-cleanup-details.md (Lines 547-570)

## Dependencies

- Python 3.11+
- pika (RabbitMQ client library)
- Docker and Docker Compose
- OpenTelemetry for observability
- Existing shared messaging infrastructure

## Success Criteria

- DLQ message count remains stable (no exponential growth)
- Retry service successfully republishes messages from both DLQs
- notification_daemon and status_transition_daemon no longer process DLQs
- All unit and integration tests pass
- Unused queues (api_events, scheduler_events) removed from RabbitMQ
- Retry service processes DLQs every 15 minutes with configurable interval
- No duplicate message processing observed
