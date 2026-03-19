---
applyTo: '.copilot-tracking/changes/20260319-01-discord-embed-rate-limit-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Embed Rate Limit Redesign

## Overview

Replace the fragile per-game in-memory throttle with a durable DB queue,
per-channel asyncio workers, and a Redis sorted-set rate limiter that correctly
accounts for Discord's per-channel 5-edits-per-5s bucket.

## Objectives

- Eliminate stale in-memory throttle state lost on bot crash
- Re-key rate limiting from per-game to per-channel to match Discord's actual bucket
- Ensure a first embed update after idle fires immediately (no artificial delay)
- Cap user-visible delay during bursts to ≤ 1.5 seconds per join
- Recover all pending updates automatically after a bot restart

## Research Summary

### Project Files

- `services/bot/events/handlers.py` — current `_handle_game_updated`, `_delayed_refresh`, `_set_message_refresh_throttle` to be replaced/removed
- `shared/cache/client.py` — `RedisClient` (line 36) to receive `claim_channel_rate_limit_slot`
- `shared/cache/ttl.py` — `MESSAGE_UPDATE_THROTTLE` constant to be removed
- `shared/cache/keys.py` — `message_update_throttle` key function to be removed
- `shared/models/` — new `MessageRefreshQueue` ORM model to be added
- `alembic/versions/c2135ff3d5cd_initial_schema.py` — reference `PGFunction` + trigger pattern
- `services/bot/bot.py` — `on_ready` / `on_resumed` to receive startup recovery query

### External References

- #file:../research/20260319-01-discord-embed-rate-limit-research.md — full architecture,
  DB schema, Lua script algorithm, worker pseudocode, and removal checklist

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style

## Implementation Checklist

### [x] Phase 1: Database Foundation

- [x] Task 1.1: Alembic migration for `message_refresh_queue` table and `pg_notify` trigger
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 13-41)

- [x] Task 1.2: `MessageRefreshQueue` SQLAlchemy ORM model with unit tests
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 42-67)

### [x] Phase 2: Redis Rate Limit Tracking — `claim_channel_rate_limit_slot` (TDD)

- [x] Task 2.1: Stub `claim_channel_rate_limit_slot` on `RedisClient` (NotImplementedError)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 68-83)

- [x] Task 2.2: Write xfail unit tests for `claim_channel_rate_limit_slot` (RED)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 84-102)

- [x] Task 2.3: Implement Lua script for `claim_channel_rate_limit_slot`; remove xfail (GREEN)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 103-125)

- [x] Task 2.4: Remove obsolete cache constants; add edge case tests (REFACTOR)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 126-149)

### [ ] Phase 3: asyncpg LISTEN Listener — `MessageRefreshListener` (TDD)

- [ ] Task 3.1: Stub `MessageRefreshListener` class (NotImplementedError)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 150-168)

- [ ] Task 3.2: Write xfail unit tests for `MessageRefreshListener` (RED)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 169-186)

- [ ] Task 3.3: Implement full `MessageRefreshListener`; remove xfail (GREEN)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 187-204)

- [ ] Task 3.4: Refactor and add edge case tests for `MessageRefreshListener` (REFACTOR)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 205-223)

### [ ] Phase 4: Per-Channel Worker — `_channel_worker` (TDD)

- [ ] Task 4.1: Stub `_channel_worker` in `EventHandlers` (NotImplementedError)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 224-239)

- [ ] Task 4.2: Write xfail unit tests for `_channel_worker` (RED)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 240-259)

- [ ] Task 4.3: Implement full `_channel_worker` loop; remove xfail (GREEN)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 260-282)

- [ ] Task 4.4: Refactor and add multi-game edge case tests (REFACTOR)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 283-303)

### [ ] Phase 5: Event Handler Replacement and Final Cleanup

- [ ] Task 5.1: Update `_handle_game_updated` tests to expect DB insert; remove old throttle tests (RED)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 304-325)

- [ ] Task 5.2: Replace throttle logic with DB insert; add startup recovery (GREEN)
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 326-350)

- [ ] Task 5.3: Delete obsolete methods and verify no regressions
  - Details: .copilot-tracking/planning/details/20260319-01-discord-embed-rate-limit-details.md (Lines 351-385)

### [ ] Phase 6: Integration Tests

- [ ] Task 6.1: Integration test — queue trigger fires correct `pg_notify` payload
  - Insert a row into `message_refresh_queue`; assert LISTEN connection receives `channel_id` as payload
  - Model: `tests/integration/test_notification_daemon.py`
  - Reference: #file:../research/20260319-01-discord-embed-rate-limit-research.md (Addendum section)

- [ ] Task 6.2: Integration test — `MessageRefreshListener` receives `channel_id` via asyncpg
  - Instantiate listener against real DB; insert row; assert callback fires with correct payload
  - Model: `test_listener_subscribes_to_channel` in `test_notification_daemon.py`
  - Reference: #file:../research/20260319-01-discord-embed-rate-limit-research.md (Addendum section)

- [ ] Task 6.3: Integration test — startup recovery query returns all pending channels
  - Insert rows for two distinct `channel_id`s; run recovery SELECT; assert both returned
  - Pure SQL, no async listener needed
  - Reference: #file:../research/20260319-01-discord-embed-rate-limit-research.md (Addendum section)

## Dependencies

- `asyncpg~=0.30.0` (already in `pyproject.toml`)
- `BOT_DATABASE_URL` environment variable (already configured)
- Redis sorted set commands: `ZADD`, `ZCARD`, `ZREMRANGEBYSCORE`, `PEXPIRE` (already available)
- `alembic-utils` `PGFunction` (already used in existing migrations)

## Success Criteria

- First join after idle: Discord embed updates immediately (no artificial delay)
- Burst of N joins on same game: edits fire at 0, 1, 2, 3.5, 5s (max 1.5s wait per user)
- Multiple games in same channel: correctly share the per-channel rate limit bucket
- Bot crash mid-burst: pending queue rows survive; workers restart on `on_ready` / `on_resumed`
- System idle: no background tasks, no Redis keys, no DB rows remain
- No 429 responses from Discord under normal operation
