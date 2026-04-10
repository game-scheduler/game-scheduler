---
applyTo: '.copilot-tracking/changes/20260408-01-embed-deletion-sweep-hardening-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Embed Deletion Sweep Hardening and Test Coverage

## Overview

Fix the concurrency bug in `_sweep_deleted_embeds`, add OTel metrics, add a `PYTEST_RUNNING`-gated test HTTP server, and add integration and e2e test coverage for the sweep and consumer paths.

## Objectives

- Eliminate concurrent sweep double-execution by cancel-and-restart via `_trigger_sweep`
- Add five OTel metrics for sweep observability following the `retry_daemon.py` pattern
- Provide a `POST /admin/sweep` test endpoint gated on `PYTEST_RUNNING` for e2e use
- Cover `EmbedDeletionConsumer._handle_embed_deleted` with a real-DB integration test
- Cover `_sweep_deleted_embeds` with a mocked-Discord integration test
- Cover real-time embed deletion and sweep-triggered cancellation with e2e tests

## Research Summary

### Project Files

- `services/bot/bot.py` — location of `_sweep_deleted_embeds`, `on_ready`, `on_resumed`; site of all production changes
- `services/retry/retry_daemon.py` — canonical OTel metrics pattern to replicate
- `services/api/services/embed_deletion_consumer.py` — consumer whose `_handle_embed_deleted` needs integration test coverage
- `tests/integration/test_participant_drop_event.py` — model for direct-call integration tests
- `tests/e2e/helpers/discord.py` — e2e helper requiring new `delete_message` method
- `shared/telemetry.py` — `PYTEST_RUNNING` gate pattern to follow

### External References

- #file:../research/20260408-01-embed-deletion-sweep-hardening-research.md — full research with code examples and specifications

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow (RED-GREEN cycle for new code; no xfail for retrofitting)

## Implementation Checklist

### [x] Phase 1: Concurrency Guard (TDD RED)

- [x] Task 1.1: Add `_trigger_sweep` stub with `NotImplementedError` and initialize `self._sweep_task = None`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 13-28)

- [x] Task 1.2: Write xfail unit tests for cancel-and-restart behaviour (4 tests)
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 29-47)

### [x] Phase 2: Concurrency Guard (TDD GREEN)

- [x] Task 2.1: Implement `_trigger_sweep` with cancel-and-restart logic
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 50-65)

- [x] Task 2.2: Update `on_ready` and `on_resumed` to call `await self._trigger_sweep()`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 66-80)

- [x] Task 2.3: Remove xfail markers from `test_trigger_sweep.py` and verify green
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 81-96)

### [x] Phase 3: OTel Metrics (TDD RED)

- [x] Task 3.1: Add module-level `meter` and five metric instruments to `bot.py`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 99-112)

- [x] Task 3.2: Write xfail unit tests for metric increments
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 113-127)

### [x] Phase 4: OTel Metrics (TDD GREEN)

- [x] Task 4.1: Add metric `.add()` calls in `_sweep_deleted_embeds`, `_run_sweep_worker`, and `_trigger_sweep`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 130-147)

- [x] Task 4.2: Remove xfail markers from `test_sweep_metrics.py` and verify green
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 148-163)

### [x] Phase 5: Test Server (TDD RED)

- [x] Task 5.1: Add `_start_test_server` and `_handle_sweep_request` stubs raising `NotImplementedError`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 166-179)

- [x] Task 5.2: Write xfail unit test for `_handle_sweep_request` calling `_trigger_sweep` and returning HTTP 200
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 180-195)

### [x] Phase 6: Test Server (TDD GREEN)

- [x] Task 6.1: Implement `_start_test_server` (aiohttp, port 8089) and `_handle_sweep_request`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 198-213)

- [x] Task 6.2: Gate test server launch on `PYTEST_RUNNING` in `on_ready`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 214-231)

- [x] Task 6.3: Remove xfail markers from `test_test_server.py` and verify green
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 232-246)

### [x] Phase 7: Integration Tests (Retrofitting — no xfail)

- [x] Task 7.1: Write integration test for `EmbedDeletionConsumer._handle_embed_deleted` (real DB + RabbitMQ)
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 249-266)

- [x] Task 7.2: ~~Write integration test for `_sweep_deleted_embeds` (mocked Discord, real DB + RabbitMQ)~~ — moved to e2e Phase 8 Case 2; sweep requires a live Discord connection, which provides no value over existing unit tests without a real bot
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 267-285)

### [x] Phase 8: E2E Tests

- [x] Task 8.1: Add `delete_message(channel_id, message_id)` to `DiscordTestHelper`
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 288-306)

- [x] Task 8.2: Write e2e test Case 1 — real-time Discord message deletion → game cancellation
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 307-322)

- [x] Task 8.3: Write e2e test Case 2 — fake `message_id` + `POST /admin/sweep` → game cancellation
  - Details: .copilot-tracking/planning/details/20260408-01-embed-deletion-sweep-hardening-details.md (Lines 323-341)

## Dependencies

- `aiohttp~=3.11.0` — already in `pyproject.toml`; no new packages required
- `opentelemetry-api` — already available in the bot service environment
- Phase 1 and 2 must complete before Phases 3+ and before e2e Case 2
- Task 3.1 must complete before Task 3.2 (metric instruments required before tests)
- Phase 5 and 6 must complete before Task 8.3 (test server required for Case 2)
- Task 8.1 must complete before Task 8.2 (`delete_message` required for Case 1)
- Tasks 7.1 and 7.2 are independent and may be done in any order

## Success Criteria

- Back-to-back `on_resumed` events produce exactly one active sweep; first is cancelled and logged
- Five OTel metrics exported: `bot.sweep.started`, `bot.sweep.interrupted`, `bot.sweep.messages_checked`, `bot.sweep.deletions_detected`, `bot.sweep.duration`
- Integration test confirms `_handle_embed_deleted` removes game row and publishes `GAME_CANCELLED`
- Integration test confirms `_sweep_deleted_embeds` publishes `EMBED_DELETED` with mocked Discord
- E2E Case 1 passes: real Discord delete → game row absent from DB
- E2E Case 2 passes: fake `message_id` + POST `/admin/sweep` → game row absent from DB
- No changes to `bot.Dockerfile`, healthcheck, or `compose.e2e.yaml`
