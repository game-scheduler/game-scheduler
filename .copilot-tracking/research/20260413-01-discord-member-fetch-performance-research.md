<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Member Fetch Performance

## Research Executed

### File Analysis

- `shared/discord/client.py`
  - `get_guild_member` (line 764): fetches single member via bot token, uses `_get_or_fetch` with Redis cache key `discord_member:{guild_id}:{user_id}`
  - `get_guild_members_batch` (line 790): serial `for` loop over `get_guild_member` — the root cause of the delay
  - `_make_api_request` (line 198): calls `claim_global_slot()` or `claim_global_and_channel_slot()` before every HTTP dispatch; sleeps on non-zero return
- `shared/cache/client.py`
  - `_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA` (line 106): Lua script enforcing global sliding window; `global_max` hardcoded to `25` in script body
  - `claim_global_and_channel_slot(channel_id)` (line 414): passes ARGV[2] = `"5"` for per-channel max; does not pass global_max
  - `claim_global_slot()` (line 460): uses sentinel channel key with `999999` per-channel limit; does not pass global_max
- `services/api/routes/games.py`
  - `list_games` route (line 403): calls `_build_game_response(game)` for every authorized game
  - `get_game` route (line 456): calls `_build_game_response(game, can_manage=...)` for single game
  - `_build_game_response` (line 897): calls `_resolve_display_data` → `resolve_display_names_and_avatars` for ALL participants + host
- `services/api/services/display_names.py`
  - `_fetch_and_cache_display_names` (line 102): calls `get_guild_members_batch`; caches results under `CacheKeys.display_name(user_id, guild_id)`
  - `resolve_display_names_and_avatars` (line ~280): checks Redis cache first, then calls batch fetch for misses
- `shared/schemas/participant.py`
  - `ParticipantResponse.display_name`: `str | None` — already nullable, no schema change needed
  - `ParticipantResponse.avatar_url`: `str | None` — already nullable
- `frontend/src/components/GameCard.tsx`
  - Uses: `game.host.display_name`, `game.host.avatar_url`, `game.participant_count`
  - Does NOT use individual participant `display_name` or `avatar_url`
  - Uses `p.user_id` (UUID from DB) for `isParticipant` check — unaffected by display name resolution
- `frontend/src/pages/GameDetails.tsx`
  - Fetches `GET /api/v1/games/{gameId}` independently on mount
  - Does not reuse list response data

### Code Search Results

- `claim_global_and_channel_slot`
  - Called in `_make_api_request` when `channel_id is not None`
  - Called in `services/bot/bot.py` line 505 during orphaned-embed sweep
  - All callers pass only `channel_id`; no caller currently passes a `global_max`
- `global_max = 25` in Lua
  - Hardcoded in `_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA`; set to 25 to leave headroom for the background sweep not to saturate the 50 req/s Discord global limit
- Test coverage
  - `tests/unit/shared/cache/test_claim_global_and_channel_slot.py`: 17 tests covering both-available, global-full, channel-full, key naming, error backoff
  - `tests/unit/shared/discord/test_discord_api_client.py` `TestMakeAPIRequestRateLimit`: 3 tests covering global-only, channel+global, sleep-on-wait

### External Research

- #fetch:https://docs.discord.com/developers/topics/rate-limits
  - Global bot limit: 50 requests/second, shared across all routes and all processes using the same bot token
  - Per-route limits are independent per path+method; member endpoint showed `limit=1000, remaining=999, reset_after=0.001s` in log — not a constraint
  - Rate limit buckets scoped by top-level resource (guild_id); distinct user_id paths are distinct buckets
- #fetch:https://docs.discord.com/developers/resources/guild#list-guild-members
  - `GET /guilds/{guild.id}/members?limit=1000` exists but requires `GUILD_MEMBERS` privileged intent — not usable without bot portal configuration

### Project Conventions

- Standards referenced: existing Redis Lua pattern in `shared/cache/client.py`, `asyncio.gather` pattern standard in Python async, `asyncio` already imported in `client.py`
- Instructions followed: minimal change, no new abstractions

## Key Discoveries

### Root Cause (from 442-line log)

~20 serial `GET /guilds/{guild_id}/members/{user_id}` calls during `GET /api/v1/games`, each ~1.5s RTT. Total: ~27s. The auth flow itself was ~2s. The delay is pure network latency, not rate limiting.

### Call Chain

```
list_games route
  → _build_game_response(game)          [for every game in list]
    → _resolve_display_data(game, ...)
      → resolve_display_names_and_avatars(guild_id, user_ids)
        → _fetch_and_cache_display_names(guild_id, uncached_ids)
          → get_guild_members_batch(guild_id, user_ids)
            → for user_id in user_ids:   ← SERIAL LOOP
                get_guild_member(...)    ← 1.5s each
```

### Existing Rate Limit Infrastructure

`_make_api_request` already calls `claim_global_slot()` before every HTTP request. The Lua sliding window enforces 25 req/1000ms globally, shared in Redis across all processes (bot + API workers). The 25 cap was deliberately set at half the Discord 50/s limit to leave headroom for the background orphaned-embed sweep.

With `asyncio.gather`: all N coroutines race to `claim_global_slot()`. The Lua script serializes them atomically — first 25 get `wait_ms=0` and fire immediately, subsequent callers get a wait and sleep. No semaphore needed; the existing machinery handles it correctly.

### Why global_max Should Be Parameterized

The sweep is background/non-interactive; 25 req/s is appropriate. Interactive member fetches (user waiting for page load) warrant a higher budget. With a parameterized `global_max`, interactive callers can claim up to 45/s while the sweep continues at 25/s. Both can safely co-exist as long as they don't simultaneously saturate the combined 50/s Discord limit — in practice the sweep completes once at startup and is then idle.

## Recommended Approach

### Fix 1: Parallelize `get_guild_members_batch`

Replace the serial loop with `asyncio.gather`. The existing Redis rate limiter handles throttling.

```python
# shared/discord/client.py
async def get_guild_members_batch(
    self, guild_id: str, user_ids: list[str], global_max: int = DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND
) -> list[dict[str, Any]]:
    results = await asyncio.gather(
        *[self.get_guild_member(guild_id, uid, global_max=global_max) for uid in user_ids],
        return_exceptions=True,
    )
    members = []
    for uid, result in zip(user_ids, results):
        if isinstance(result, DiscordAPIError) and result.status == HTTP_404_NOT_FOUND:
            logger.debug("User %s not found in guild %s", uid, guild_id)
        elif isinstance(result, Exception):
            raise result
        else:
            members.append(result)
    return members
```

Called from the detail view path with `global_max=DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE` (45).

### Fix 2: Parameterize global_max Through the Rate Limit Stack

**`_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA`**: change `local global_max = 25` to `local global_max = tonumber(ARGV[3] or '25')`.

**`claim_global_and_channel_slot(channel_id, global_max=25)`**: pass `str(global_max)` as ARGV[3].

**`claim_global_slot(global_max=25)`**: pass `str(global_max)` as ARGV[3].

**`_make_api_request(..., global_max=25)`**: pass `global_max` to whichever claim call is used.

**`get_guild_member(..., global_max=25)`**: pass `global_max` to `_make_api_request`.

Constants in `shared/cache/ttl.py` (or a new `shared/cache/limits.py`):

```python
DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND = 25   # sweep and other non-interactive calls
DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE = 45  # user-facing requests
```

The sweep in `bot.py` calls `claim_global_and_channel_slot(channel_id)` — default stays 25 with no caller change needed.

### Fix 3: Skip Participant Display Name Resolution in `list_games`

Add `resolve_participants: bool = True` parameter to `_build_game_response`. When `False`, skip `_resolve_display_data` for participants; still resolve host. Pass `resolve_participants=False` from `list_games` route only.

```python
async def _build_game_response(
    game: game_model.GameSession,
    can_manage: bool = False,
    resolve_participants: bool = True,
) -> game_schemas.GameResponse:
    ...
    display_data_map, host_discord_id = await _resolve_display_data(
        game, partitioned, resolve_participants=resolve_participants
    )
```

`get_game` route continues calling `_build_game_response(game, can_manage=can_manage)` — no change. The detail endpoint calls `get_guild_members_batch` with `global_max=DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE`.

## Implementation Guidance

- **Objectives**: eliminate 27s cold-cache page load on game list; parallelize remaining Discord member fetches; allow interactive requests to use more of the Discord global rate budget
- **Key Tasks**:
  1. Add constants `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND = 25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE = 45`
  2. Add `ARGV[3]` to Lua script for `global_max`; update `claim_global_and_channel_slot` and `claim_global_slot` to accept and pass it
  3. Thread `global_max` parameter through `_make_api_request` → `get_guild_member` → `get_guild_members_batch`
  4. Replace serial loop in `get_guild_members_batch` with `asyncio.gather`
  5. Add `resolve_participants` flag to `_build_game_response`; pass `False` from `list_games`
  6. In `get_game` route, pass `global_max=DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE` when calling through to member fetches
  7. Update unit tests for `claim_global_and_channel_slot`, `claim_global_slot`, `_make_api_request`, `get_guild_members_batch`
- **Dependencies**: `asyncio` already imported in `shared/discord/client.py`; no new packages
- **Files touched**: `shared/cache/client.py`, `shared/discord/client.py`, `services/api/routes/games.py`, `services/api/services/display_names.py`, plus test files for each
- **Success Criteria**:
  - `GET /api/v1/games` cold-cache completes in ~2s (host resolution only, no participant Discord calls)
  - `GET /api/v1/games/{id}` cold-cache completes in ~1.5s (parallel gather, 45 req/s budget)
  - No 429s from Discord under normal load
  - All existing unit tests pass; new tests cover `global_max` threading and gather error handling

## Addendum: Parallel Host Fetch in list_games (2026-04-13)

### Problem

After Fixes 1–3 were implemented, `list_games` was still making individual host Discord fetches sequentially — one `_build_game_response` awaited at a time. With `resolve_participants=False`, each game still called `_resolve_display_data` → `resolve_display_names_and_avatars` for the single host ID, serially across all games in the list.

### Solution: Pre-batch All Host IDs, Then Gather

Before building any responses, collect all unique host Discord IDs grouped by guild, issue one `resolve_display_names_and_avatars` call per guild (gathered in parallel if multiple guilds), then pass the resulting map into each `_build_game_response` call as `prefetched_display_data`. Response builds are themselves gathered so per-game Redis reads (channel/guild names) are also concurrent.

**Key properties:**

- A host appearing in N games is fetched exactly once — `get_guild_members_batch` deduplicates since host IDs are collected into a set per guild
- `get_guild_members_batch` fires all host fetches concurrently via `asyncio.gather` in a single call, maximally parallelizing the Discord member fetches within the existing rate limit budget
- `asyncio` import added to `services/api/routes/games.py`; `collections.defaultdict` used for grouping
- `_build_game_response` gains `prefetched_display_data: dict[str, dict[str, str | None]] | None = None`; when provided it branches before `_resolve_display_data` so no Discord call is made per-game
- All existing callers (`get_game`, `join_game`, etc.) are unaffected — `prefetched_display_data` defaults to `None`

**Call chain after fix:**

```
list_games route
  → collect unique host_discord_ids per guild
  → asyncio.gather(
      resolve_display_names_and_avatars(guild_id, [all_host_ids])  ← 1 call per guild
        → get_guild_members_batch(...)
          → asyncio.gather(get_guild_member for each host)  ← all parallel
    )
  → asyncio.gather(
      _build_game_response(game, prefetched_display_data=prefetched)  ← for every game
        [no Discord call; uses prefetched map directly]
    )
```

**Files changed:** `services/api/routes/games.py` only.
