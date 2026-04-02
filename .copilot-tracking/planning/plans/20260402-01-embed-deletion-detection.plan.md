---
applyTo: '.copilot-tracking/changes/20260402-01-embed-deletion-detection-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Embed Deletion Detection and Auto-Cancellation

## Overview

Automatically cancel a game session when an admin deletes the Discord embed post,
and recover from missed deletions that occurred while services were offline.

## Objectives

- Add `on_raw_message_delete` Gateway handler to detect embed deletions in real time
- Propagate cancellation via RabbitMQ `EMBED_DELETED` event to the API service
- Add a startup sweep on `on_ready`/`on_resumed` to reconcile deletions missed while offline
- Add an atomic Redis Lua script governing both global and per-channel rate limits
- Refactor `delete_game` to expose `_delete_game_internal` for reuse by the new consumer
- (Optional) Index `game_sessions.message_id` for faster lookup

## Research Summary

### Project Files

- `shared/messaging/events.py` (line 37) — `EventType` enum; `GAME_CANCELLED` at line 43 is the pattern for `EMBED_DELETED`
- `services/api/services/games.py` (line 1809) — `delete_game`; `_publish_game_cancelled` at line 2104
- `services/api/services/sse_bridge.py` (line 111) — only existing RabbitMQ consumer in API; uses `get_bypass_db_session()`
- `shared/cache/client.py` (lines 48, 306) — `_CHANNEL_RATE_LIMIT_LUA` and `claim_channel_rate_limit_slot`
- `shared/discord/client.py` (line 183) — `_make_api_request`; no global rate limiting currently
- `services/bot/bot.py` (line 79) — `discord.Intents(guilds=True)`; `on_ready` line 138, `on_resumed` line 173
- `services/bot/events/handlers.py` (lines 349, 1398) — `_fetch_message_for_refresh` and `_channel_worker` as patterns
- `shared/models/game.py` (line 74) — `message_id` column; no index

### External References

- #file:../research/20260402-01-embed-deletion-detection-research.md — full feasibility and design research

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology

## Implementation Checklist

### [ ] Phase 1: Foundation (Shared Library Changes)

- [ ] Task 1.1: Add `EventType.EMBED_DELETED` to `shared/messaging/events.py`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 13-30)

- [ ] Task 1.2: Add combined atomic Lua script `claim_global_and_channel_slot` to `shared/cache/client.py`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 31-58)

- [ ] Task 1.3: Add global rate limiting call in `DiscordAPIClient._make_api_request`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 59-83)

### [ ] Phase 2: API Service Changes

- [ ] Task 2.1: Refactor `delete_game` to extract `_delete_game_internal`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 87-116)

- [ ] Task 2.2: Add RabbitMQ consumer for `EMBED_DELETED` in API service
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 117-143)

### [ ] Phase 3: Bot Service Changes

- [ ] Task 3.1: Add `guild_messages=True` to `discord.Intents(...)` in `services/bot/bot.py`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 147-163)

- [ ] Task 3.2: Implement `on_raw_message_delete` handler in bot
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 165-190)

- [ ] Task 3.3: Implement startup sweep from `on_ready` and `on_resumed`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 192-228)

### [ ] Phase 4: Optional — DB Index

- [ ] Task 4.1: Add Alembic migration for `CREATE INDEX CONCURRENTLY` on `game_sessions.message_id`
  - Details: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md (Lines 232-252)

## Dependencies

- Task 1.1 must precede Tasks 2.2, 3.2, and 3.3 (all use `EventType.EMBED_DELETED`)
- Task 1.2 must precede Tasks 1.3 and 3.3 (both need `claim_global_and_channel_slot`)
- Task 2.1 must precede Task 2.2 (`_delete_game_internal` is called by the new consumer)
- Task 3.1 must precede Task 3.2 (intent flag required for event delivery)
- Task 4.1 has no code dependencies; can be done at any time

## Success Criteria

- Deleting a game embed post in Discord triggers game cancellation with no manual intervention
- Games whose embed posts were deleted while services were offline are cancelled on next startup
- All existing `delete_game` HTTP API behavior is unchanged
- Startup sweep completes without Discord rate-limit errors or degrading live embed edits
- All new code has passing unit tests; integration test covers the end-to-end cancellation path
