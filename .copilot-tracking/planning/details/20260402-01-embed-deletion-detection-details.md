<!-- markdownlint-disable-file -->

# Task Details: Embed Deletion Detection and Auto-Cancellation

## Research Reference

**Source Research**: #file:../research/20260402-01-embed-deletion-detection-research.md

---

## Phase 1: Foundation (Shared Library Changes)

### Task 1.1: Add `EventType.EMBED_DELETED`

Add a new routing key constant to the shared event type enum so the bot and API
consumer can reference the same string without duplication.

- **Files**:
  - `shared/messaging/events.py` — add `EMBED_DELETED` after the last game lifecycle entry
- **Success**:
  - `EventType.EMBED_DELETED` resolves to `"game.embed_deleted"` (or similar value consistent with the `game.*` AMQP topic prefix)
  - Existing enum members are unchanged
  - Unit test: test that the new value is a member of `EventType` and has the expected string value
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 63-65) — `GAME_CANCELLED` at line 43 of `shared/messaging/events.py` is the model entry
- **Dependencies**:
  - None — this is the root dependency for phases 2 and 3

---

### Task 1.2: Add Combined Atomic Lua Rate Limit Script

Add a new Lua script and async wrapper to `shared/cache/client.py` that atomically
claims one global token AND one per-channel slot in a single round-trip. Returns 0
if both are available (claiming both), or the larger of the two wait durations
(claiming neither) if either limit is exhausted. This prevents the partial-claim
problem where one resource is held idle while waiting for the other.

The global budget is set at 25 req/sec (half of Discord's 50 req/sec hard limit)
to leave headroom for `discord.py` internal calls which are not routed through
`DiscordAPIClient`.

- **Files**:
  - `shared/cache/client.py` — add `_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA` constant and `claim_global_and_channel_slot(channel_id)` async method
- **Success**:
  - Script returns `0` and increments both counters when both budgets have capacity
  - Script returns the larger wait value and increments nothing when either budget is full
  - New Redis key: `discord:global_rate_limit` (leaky bucket, 25 tokens/1000ms window)
  - Existing `_CHANNEL_RATE_LIMIT_LUA` / `claim_channel_rate_limit_slot` are unchanged
  - Unit tests: mock Redis, test zero-wait path, test global-full path, test channel-full path, test both-full path (returns max)
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 110-134) — combined Lua design with KEYS/ARGV layout
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 56-62) — existing `_CHANNEL_RATE_LIMIT_LUA` at line 48, `claim_channel_rate_limit_slot` at line 306
- **Dependencies**:
  - None — pure Redis/Lua; no dependency on other tasks

---

### Task 1.3: Add Global Rate Limiting to `_make_api_request`

Call `claim_global_and_channel_slot` (or a global-only variant if no channel context
is available) at the top of `DiscordAPIClient._make_api_request` before every HTTP
call. This makes all explicitly-coded Discord API calls respect the global token
bucket automatically, including startup sweep calls.

For requests without a per-channel context (e.g., `get_guilds`), call a
global-only Lua path (the same script with a sentinel channel key that has a very
high per-channel limit, so it never constrains).

- **Files**:
  - `shared/discord/client.py` — modify `_make_api_request` at line 183 to acquire global rate limit slot before dispatching the HTTP call
  - `shared/cache/client.py` — (if needed) add a `claim_global_slot()` convenience wrapper that passes a no-op channel key
- **Success**:
  - Explicit HTTP calls queue behind the 25 req/sec global bucket
  - Sleep duration is derived from the Lua return value (0 = no sleep)
  - Existing 429 handling is unaffected
  - Unit tests: verify `_make_api_request` awaits the rate limit claim before issuing the HTTP call
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 66-72) — `_make_api_request` at line 183; no global limiting currently; note about `discord.py` internal calls not going through this client
- **Dependencies**:
  - Task 1.2 must be complete (provides `claim_global_and_channel_slot`)

---

## Phase 2: API Service Changes

### Task 2.1: Refactor `delete_game` to Extract `_delete_game_internal`

Extract the non-auth portion of `delete_game` into a new private method
`_delete_game_internal(game)`. The caller `delete_game` retains the auth check and
calls through to `_delete_game_internal`. The new RabbitMQ consumer (Task 2.2) will
also call `_delete_game_internal` directly, bypassing HTTP auth.

Current `delete_game` body (line 1809):

1. `get_game` + null check
2. `can_manage_game` auth check
3. `release_image` × 2
4. `db.delete(game)`
5. `_publish_game_cancelled(game)`

Steps 3–5 move into `_delete_game_internal(game)`.

- **Files**:
  - `services/api/services/games.py` — extract lines 1853–1862 (image release, delete, publish) into `_delete_game_internal`; `delete_game` calls it after the auth check
- **Success**:
  - All existing `delete_game` behavior is preserved (images released, row deleted, `GAME_CANCELLED` published)
  - `_delete_game_internal` is callable without auth context
  - Existing `delete_game` tests pass without modification
  - New unit test: call `_delete_game_internal` directly and assert image release + publish occurred
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 29-34) — `delete_game` line 1809 flow, `_publish_game_cancelled` line 2104
- **Dependencies**:
  - None (pure refactor, no new constants or infrastructure required)

---

### Task 2.2: Add RabbitMQ Consumer for `EMBED_DELETED` in API Service

Add a new async consumer class in the API service that subscribes to
`EventType.EMBED_DELETED` events from RabbitMQ. When received, look up the game by
`game_id` from the event payload and call `_delete_game_internal(game)` using a
`get_bypass_db_session()` session. Model the class structure directly on
`services/api/services/sse_bridge.py`.

Wire the consumer into the API startup lifecycle (wherever `sse_bridge` is started).

- **Files**:
  - `services/api/services/embed_deletion_consumer.py` — new file; consumer class modeled on `sse_bridge.py`
  - `services/api/main.py` (or equivalent startup file) — register the new consumer alongside the SSE bridge
- **Success**:
  - Receiving an `EMBED_DELETED` RabbitMQ message with a valid `game_id` calls `_delete_game_internal` and the game is cancelled
  - Unknown `game_id` is logged and silently dropped (idempotent)
  - Uses `get_bypass_db_session()` — no HTTP auth check
  - Unit tests: mock RabbitMQ delivery, mock `_delete_game_internal`, assert it is called with the correct game
  - Integration test added to verify the end-to-end cancel flow via this path
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 37-42) — `sse_bridge.py` pattern; `get_bypass_db_session()` at line 111
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 87-97) — event-driven deletion path diagram
- **Dependencies**:
  - Task 1.1 (`EventType.EMBED_DELETED` constant)
  - Task 2.1 (`_delete_game_internal` method)

---

## Phase 3: Bot Service Changes

### Task 3.1: Add `guild_messages` Intent

Add the `guild_messages` Gateway intent flag so Discord delivers `MESSAGE_DELETE`
events to the bot. This is a non-privileged intent; no Discord developer portal
approval is required.

- **Files**:
  - `services/bot/bot.py` — line 79: change `discord.Intents(guilds=True)` to `discord.Intents(guilds=True, guild_messages=True)`
- **Success**:
  - Bot connects to Gateway with the `MESSAGE_INTENTS` bit set
  - No existing functionality is broken (test suite passes)
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 147-159) — intent change example, `guild_messages` non-privileged status
- **Dependencies**:
  - None

---

### Task 3.2: Implement `on_raw_message_delete` Handler in Bot

Add a new Gateway event handler `on_raw_message_delete` to the bot class. When
fired:

1. Look up the deleted `message_id` in `game_sessions` via `get_bypass_db_session()`
2. If a matching game is found, publish `EventType.EMBED_DELETED` to RabbitMQ with `game_id`, `channel_id`, and `message_id`
3. If no match, log at DEBUG and return

Use `discord.RawMessageDeleteEvent` payload: `.channel_id` (int), `.message_id`
(int, convert to str for DB lookup), `.guild_id`.

- **Files**:
  - `services/bot/bot.py` — add `on_raw_message_delete` method after `on_resumed`
- **Success**:
  - Deleting any message in a guild channel triggers the handler
  - Only game embed posts (matching `game_sessions.message_id`) produce a published event
  - DB lookup uses `get_bypass_db_session()`, not the HTTP auth path
  - Unit tests: mock DB lookup returning a game and assert publish occurs; mock returning None and assert no publish
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 139-158) — `on_raw_message_delete` payload, `discord.RawMessageDeleteEvent` fields
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 87-97) — event-driven path overview
- **Dependencies**:
  - Task 1.1 (`EventType.EMBED_DELETED`)
  - Task 3.1 (`guild_messages` intent, so the event actually arrives)

---

### Task 3.3: Implement Startup Sweep

On `on_ready` and `on_resumed`, after `_recover_pending_workers` runs (line 157/176),
trigger a startup sweep to find embed posts that were deleted while the services
were offline.

Sweep algorithm:

1. Query `game_sessions WHERE message_id IS NOT NULL ORDER BY scheduled_at ASC` via `get_bypass_db_session()`
2. Populate an `asyncio.PriorityQueue` with `(scheduled_at, game_id, channel_id, message_id)` tuples
3. Spawn ~60 asyncio coroutine workers
4. Each worker: `claim_global_and_channel_slot(channel_id)` → sleep if wait_ms > 0 and re-queue → `channel.fetch_message(message_id)` → on `discord.NotFound` publish `EMBED_DELETED`
5. `asyncio.gather(*workers)` to wait for completion before returning

~60 workers is intentionally higher than the 25 req/sec global cap; this ensures
the global token bucket is never left idle when one worker is mid-sleep on a
per-channel limit.

- **Files**:
  - `services/bot/bot.py` — add `_sweep_deleted_embeds()` coroutine; call it from `on_ready` and `on_resumed`
  - `services/bot/events/handlers.py` — the sweep worker follows the same pattern as `_fetch_message_for_refresh` at line 349
- **Success**:
  - Games with live embed posts are not disturbed
  - Games whose embed posts return 404 generate an `EMBED_DELETED` event
  - Sweep completes without rate-limit errors under normal conditions
  - Sweep runs concurrently with normal embed edit traffic without starvation
  - Unit tests: mock a queue with known games, mock `fetch_message` to raise `NotFound` for some, assert correct events published
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 98-109) — startup sweep path diagram, ~60 workers, PriorityQueue design
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 119-135) — sweep worker pseudocode
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 27-28) — `on_ready` / `on_resumed` insertion point (lines 138/173 in `bot.py`)
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 22-24) — `_fetch_message_for_refresh` at line 349 as pattern
- **Dependencies**:
  - Task 1.2 (`claim_global_and_channel_slot` Lua script and wrapper)
  - Task 1.1 (`EventType.EMBED_DELETED`)
  - Task 3.1 (`guild_messages` intent)

---

## Phase 4: Optional — DB Index

### Task 4.1: Add Migration for `message_id` Index

Add an Alembic migration that creates an index on `game_sessions.message_id`. This
table only holds active games so the index is not strictly required, but it removes
any future concern as game counts grow and makes `on_raw_message_delete` lookups
instantaneous.

Use `CREATE INDEX CONCURRENTLY` so the migration does not lock the table.

- **Files**:
  - `alembic/versions/<hash>_add_message_id_index.py` — new Alembic revision
- **Success**:
  - Migration applies cleanly against a running database
  - `alembic downgrade` removes the index without error
  - No existing tests broken
- **Research References**:
  - #file:../research/20260402-01-embed-deletion-detection-research.md (Lines 44-48) — `message_id` column at line 74 of `shared/models/game.py`; no existing index; table size note
- **Dependencies**:
  - No code dependency; can be done at any point

---

## Dependencies

- Python asyncio, RabbitMQ, Redis — all already present
- discord.py Gateway event system — already in use; only new intent flag needed
- Alembic — already in use for migrations

## Success Criteria

- Deleting a game embed post in Discord triggers game cancellation with no manual intervention
- Games deleted while services were offline are cancelled on next bot startup
- All existing `delete_game` HTTP API behavior is preserved
- Startup sweep completes without rate-limit errors or degrading live embed edits
- All new code has passing unit tests; integration test covers the end-to-end cancel path
