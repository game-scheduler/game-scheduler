---
applyTo: '.copilot-tracking/changes/20251205-daemon-bot-message-reliability-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: Daemon-Bot Message Reliability and Error Handling

## Overview

Fix critical message loss bug in bot consumer and implement daemon-based DLQ processing with per-message TTL for notifications to ensure reliable event delivery and data consistency.

## Objectives

- Eliminate message loss from auto-ACK bug in bot consumer
- Implement infinite retry for status transitions via daemon DLQ processing
- Add per-message TTL to notifications that expire when game starts
- Preserve architectural separation (daemons publish, bot consumes)
- Ensure status transitions always eventually succeed

## Research Summary

### Project Files
- shared/messaging/consumer.py - Consumer with auto-ACK bug
- services/scheduler/generic_scheduler_daemon.py - Generic daemon for scheduled items
- services/scheduler/event_builders.py - Event builder functions
- services/bot/events/handlers.py - Event handler implementations
- shared/messaging/sync_publisher.py - Synchronous RabbitMQ publisher
- shared/models.py - SQLAlchemy models including NotificationSchedule

### External References
- #file:../research/20251205-daemon-bot-message-reliability-research.md - Comprehensive research analysis
- #fetch:https://aio-pika.readthedocs.io/en/latest/rabbitmq-tutorial/2-work-queues.html - Manual acknowledgment patterns
- #fetch:https://www.rabbitmq.com/confirms.html - Publisher confirms and consumer acknowledgments

### Standards References
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding best practices

## Implementation Checklist

### [x] Phase 1: Schema Enhancement

- [x] Task 1.1: Create database migration for game_scheduled_at column
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 15-30)

- [x] Task 1.2: Update NotificationSchedule model
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 32-45)

- [x] Task 1.3: Update notification schedule population service
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 47-62)

### [x] Phase 2: Per-Message TTL Implementation

- [x] Task 2.1: Enhance sync_publisher with expiration support
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 64-80)

- [x] Task 2.2: Update event builders to return (Event, TTL) tuples
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 82-105)

- [x] Task 2.3: Update daemon to handle tuple returns
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 107-120)

### [ ] Phase 3: Fix Bot Consumer Auto-ACK

- [ ] Task 3.1: Replace message.process() with manual ACK/NACK
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 122-140)

- [ ] Task 3.2: Make bot handler defensive for stale notifications
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 142-158)

### [ ] Phase 4: Daemon DLQ Processing

- [ ] Task 4.1: Add DLQ processing configuration to SchedulerDaemon
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 160-178)

- [ ] Task 4.2: Implement DLQ message processing logic
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 180-210)

- [ ] Task 4.3: Enable DLQ processing in daemon wrappers
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 212-228)

### [ ] Phase 5: Testing and Validation

- [ ] Task 5.1: Add integration tests for manual ACK/NACK behavior
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 230-248)

- [ ] Task 5.2: Add integration tests for DLQ processing
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 250-268)

- [ ] Task 5.3: Add integration tests for per-message TTL
  - Details: .copilot-tracking/details/20251205-daemon-bot-message-reliability-details.md (Lines 270-285)

## Dependencies

- RabbitMQ with dead letter exchange (already configured)
- PostgreSQL with notification_schedule table (exists)
- aio_pika library for async RabbitMQ (installed)
- pika library for sync RabbitMQ (installed)
- SQLAlchemy for database operations (installed)

## Success Criteria

- Messages only ACKed after successful handler execution
- Failed messages go to DLQ for daemon republishing
- Daemon republishes from DLQ on startup and every 15 minutes
- Notifications expire when game starts (no stale reminders)
- Status transitions have infinite retry until success
- Bot remains purely event-driven consumer
- All integration tests pass
- No new services/containers required
