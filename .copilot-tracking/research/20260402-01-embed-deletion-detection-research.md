<!-- markdownlint-disable-file -->

# Task Research Notes: Embed Deletion Detection and Auto-Cancellation

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - `discord.Intents(guilds=True)` at line 79 — only guild (server structure) events subscribed; no message events
  - `on_ready` and `on_resumed` both call `_recover_pending_workers` — natural insertion point for startup sweep
  - No `on_raw_message_delete` handler exists anywhere in the codebase

- `services/bot/events/handlers.py`
  - `_fetch_message_for_refresh` (line 349) — returns `None` on `discord.NotFound`, logs warning only; provides the pattern the startup sweep should follow
  - `_channel_worker` (line 1398) — existing per-channel worker pattern; startup sweep worker pool should mirror this structure
  - `_edit_with_backoff` — handles 429 retry for embed edits; sweep should reuse or follow the same approach

- `services/api/services/games.py`
  - `delete_game` (line 1809) — flow: auth check → `release_image` × 2 → `db.delete(game)` → `_publish_game_cancelled`
  - `_publish_game_cancelled` (line 2104) — publishes `EventType.GAME_CANCELLED` with `game_id`, `message_id`, `channel_id`
  - Deletion business logic is currently inseparable from the HTTP auth check, preventing reuse by non-HTTP consumers

- `services/api/services/sse_bridge.py`
  - Only existing RabbitMQ consumer in the API service
  - Already imports and uses `get_bypass_db_session()` (line 111) — the exact pattern needed for the new consumer

- `shared/database.py`
  - `get_bypass_db_session()` / `BotAsyncSessionLocal` — uses the `gamebot_bot` DB user which has `BYPASSRLS` privilege
  - System-level operations that originate from trusted internal components (not user requests) use this session

- `shared/models/game.py`
  - `message_id: Mapped[str | None] = mapped_column(String(20), nullable=True)` (line 74)
  - No index on `message_id` — table only holds active games so lookup cost is acceptable, but adding an index is cheap and removes any future concern

- `shared/cache/client.py`
  - `_CHANNEL_RATE_LIMIT_LUA` (line 48): sliding window, 5 req per 5 sec per channel, returns wait_ms (0=proceed, positive=sleep that many ms)
  - `claim_channel_rate_limit_slot(channel_id)` (line 306): async wrapper; returns int milliseconds to wait
  - No global rate limiter exists

- `shared/discord/client.py`
  - `_make_api_request` (line 183): single chokepoint for all explicitly-coded HTTP calls to Discord — the correct place to add global rate limiting
  - Raises `DiscordAPIError` on 429; some callers handle it, most do not
  - Note: `discord.py` library's own internal REST calls (e.g., `channel.fetch_message`) do **not** go through `DiscordAPIClient`; they have their own internal rate limiter

### Code Search Results

- `on_raw_message_delete`
  - Not present anywhere in the codebase — this is net-new

- `EventType` definition
  - Lives in `shared/messaging/events.py` (or equivalent); `GAME_CANCELLED` exists and is the model for the new `EMBED_DELETED` entry

- `get_bypass_db_session`
  - Used in `services/api/services/sse_bridge.py` (line 111) — the exact import/usage pattern for the new API consumer to follow

- `_recover_pending_workers`
  - Called from both `on_ready` and `on_resumed` in `bot.py` — confirms the startup hook pattern

### Project Conventions

- Standards referenced: `shared/` library is the integration point between services; RabbitMQ is the async boundary between bot and API; Redis Lua scripts for atomic multi-key rate limit operations
- Instructions followed: TDD applies (Python); new consumer follows `sse_bridge.py` pattern exactly; no new auth mechanism for internal event consumers

## Key Discoveries

### Project Structure

The feature spans three layers:

1. **Bot layer** (`services/bot/`): Gateway event reception, DB lookup, publishing
2. **Messaging layer** (`shared/messaging/`): New `EventType` constant; event routing
3. **API layer** (`services/api/`): New RabbitMQ consumer; refactored deletion logic

Rate limiting infrastructure lives in `shared/cache/client.py` (Redis Lua scripts) and `shared/discord/client.py` (HTTP client).

### Implementation Patterns

**Event-driven deletion path:**

```
Discord Gateway → on_raw_message_delete (bot)
  → lookup message_id in game_sessions (bypass DB session)
  → publish EMBED_DELETED to RabbitMQ
  → API consumer receives event
  → _delete_game_internal(game) (bypass DB session)
  → GAME_CANCELLED published downstream (unchanged)
```

**Startup sweep path (missed deletions while services were down):**

```
on_ready / on_resumed
  → query game_sessions WHERE message_id IS NOT NULL ORDER BY scheduled_at ASC
  → populate asyncio.PriorityQueue
  → spawn ~60 coroutine workers
  → each worker: claim_global_and_channel_slot → fetch_message → NotFound → publish EMBED_DELETED
```

**Why bypass DB session, not HTTP auth:**
The new RabbitMQ consumer (`EMBED_DELETED` handler in API service) is a trusted internal component, not a user request. `sse_bridge.py` already uses this exact pattern. No HTTP auth token, no bot Discord ID auth, no new auth mechanism required.

### Complete Examples

**Existing per-channel rate limit Lua (model to extend):**

```lua
-- _CHANNEL_RATE_LIMIT_LUA in shared/cache/client.py
-- Sliding window 5 req / 5 sec per channel
-- Returns wait_ms: 0=proceed, positive=sleep
```

**Proposed combined global+channel Lua:**

```lua
-- Atomically claims one global token (25/sec leaky bucket)
-- AND one per-channel slot (5/5sec sliding window)
-- Returns 0 if both available (both claimed), else max(global_wait, channel_wait)
-- Claims nothing if either unavailable — no partial claim problem
local global_key = KEYS[1]        -- "discord:global_rate_limit"
local channel_key = KEYS[2]       -- "discord:channel_rate_limit:{channel_id}"
local now_ms = tonumber(ARGV[1])
local global_capacity = tonumber(ARGV[2])   -- 25
local global_window_ms = tonumber(ARGV[3])  -- 1000
-- ... per-channel parameters follow existing _CHANNEL_RATE_LIMIT_LUA structure
-- If global bucket full: return max(global_refill_wait, 0)
-- If channel window full: return max(channel_wait, 0)
-- Both available: increment both, return 0
```

**Startup sweep worker (pseudocode):**

```python
async def _sweep_worker(queue: asyncio.PriorityQueue, cache_client, discord_client, event_publisher):
    while True:
        try:
            scheduled_at, game_id, channel_id, message_id = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        wait_ms = await cache_client.claim_global_and_channel_slot(channel_id)
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)
            queue.put_nowait((scheduled_at, game_id, channel_id, message_id))
            continue
        try:
            await discord_client.fetch_message(channel_id, message_id)
        except discord.NotFound:
            await event_publisher.publish_embed_deleted(game_id, channel_id, message_id)
        queue.task_done()
```

### API and Schema Documentation

**`on_raw_message_delete`** is a discord.py Gateway event:

- Fires for any message deleted in any channel the bot can see
- Payload: `discord.RawMessageDeleteEvent` with `.channel_id`, `.message_id`, `.guild_id`
- Non-privileged — requires `guild_messages` intent only, which does not require Discord approval

**Required intent change:**

```python
# Before
intents = discord.Intents(guilds=True)
# After
intents = discord.Intents(guilds=True, guild_messages=True)
```

**`guild_messages` intent:** Non-privileged (no Discord developer portal approval needed). Receives `MESSAGE_DELETE`, `MESSAGE_DELETE_BULK` events. Does not expose message content (that requires `message_content`, a privileged intent we do not need).

### Technical Requirements

- Discord Gateway intent `guild_messages` required (non-privileged, no approval process)
- `message_id` is a string in Discord (snowflake); `game_sessions.message_id` is already `String(20)` — no schema type change needed
- `fetch_message` on a deleted message raises `discord.NotFound` (404) — no ambiguity with other errors
- Global rate limit budget: Discord allows 50 explicit API req/sec globally for bots; the startup sweep should use 25 req/sec to leave headroom for normal embed edits occurring concurrently
- Startup sweep may run concurrently with normal embed edit traffic — the shared rate limiter in `_make_api_request` (once added) naturally serializes both

## Recommended Approach

**Real-time detection:** Discord Gateway `on_raw_message_delete` event in the bot. When fired, look up `message_id` against `game_sessions.message_id` via `get_bypass_db_session()`. If found, publish `EMBED_DELETED` to RabbitMQ. API service consumes the event in a new consumer modeled on `sse_bridge.py`, calling a new `_delete_game_internal()` helper extracted from the existing `delete_game()` method.

**Missed-deletion reconciliation:** On `on_ready` and `on_resumed`, run a startup sweep. Query all games with a non-null `message_id` ordered by `scheduled_at ASC`. Spawn ~60 asyncio coroutine workers pulling from an `asyncio.PriorityQueue`. Each worker calls the new `claim_global_and_channel_slot(channel_id)` atomic Lua script, then attempts `fetch_message`. A `discord.NotFound` result publishes `EMBED_DELETED`. The 25 req/sec global budget and ~60 workers ensure the bucket is never left idle between channel-lock waits.

**Rate limiting:** New atomic Lua script `claim_global_and_channel_slot(channel_id)` in `shared/cache/client.py` replaces separate global+channel acquisition. Claims both or neither atomically, returning the larger of the two wait times if either limit is exhausted. This script is also called from `_make_api_request` in `shared/discord/client.py` to govern all explicitly-coded HTTP calls globally.

## Implementation Guidance

- **Objectives**:
  - Automatically cancel a game when an admin deletes its Discord embed post
  - Recover from missed deletions that occurred while services were offline
  - Do not degrade normal embed edit throughput

- **Key Tasks** (recommended order):
  1. Refactor `delete_game` → extract `_delete_game_internal(game, db)` in `services/api/services/games.py`
  2. Add `EventType.EMBED_DELETED` to `shared/messaging/events.py`
  3. Add `guild_messages=True` to `discord.Intents(...)` in `services/bot/bot.py`
  4. Implement `on_raw_message_delete` handler in bot
  5. Add new API RabbitMQ consumer for `EMBED_DELETED` (modeled on `sse_bridge.py`)
  6. Add combined atomic Lua script `claim_global_and_channel_slot` to `shared/cache/client.py`
  7. Add global rate limiting call in `DiscordAPIClient._make_api_request` in `shared/discord/client.py`
  8. Implement startup sweep called from `on_ready` and `on_resumed`
  9. (Optional) Add `CREATE INDEX CONCURRENTLY` migration on `game_sessions.message_id`

- **Dependencies**:
  - Step 1 must precede step 5 (consumer needs `_delete_game_internal`)
  - Step 6 must precede step 7 and step 8 (both need the combined Lua function)
  - Step 2 must precede steps 4 and 5 (both use the new event type constant)
  - All other steps are independent of each other

- **Success Criteria**:
  - Deleting a game embed post in Discord triggers game cancellation with no manual intervention
  - Games whose embed posts were deleted while the bot was offline are cancelled on next bot startup
  - Startup sweep completes within a reasonable time without exhausting Discord rate limits or degrading live embed edits
  - All existing `delete_game` behavior (image release, notification publishing) is preserved for both HTTP-triggered and embed-deletion-triggered cancellations
