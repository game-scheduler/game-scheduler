<!-- markdownlint-disable-file -->

# Task Research Notes: Gateway-Driven Cache Enhancement

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - `on_ready` — fires after full reconnect; `self.guilds` is fully populated with channels and roles at this point; no REST calls needed to rebuild Redis
  - `on_resumed` — fires after session resume; discord.py has already replayed all missed gateway events (including `CHANNEL_CREATE/DELETE` and `GUILD_ROLE_CREATE/DELETE`) before this fires; no rebuild needed
  - `intents = discord.Intents(guilds=True, guild_messages=True)` — `GUILDS (1 << 0)` covers `CHANNEL_CREATE`, `CHANNEL_UPDATE`, `CHANNEL_DELETE`, `GUILD_ROLE_CREATE`, `GUILD_ROLE_UPDATE`, `GUILD_ROLE_DELETE` — no privileged intents required

- `services/bot/auth/role_checker.py`
  - `get_user_role_ids` — checks `user_roles` Redis cache, then falls back to `self.bot.fetch_guild()` (REST) + `guild.fetch_member()` (REST) — two uncached REST calls per cache miss
  - `get_guild_roles`, `check_manage_guild_permission`, `check_manage_channels_permission`, `check_administrator_permission`, `check_game_host_permission` — all call `self.bot.fetch_guild()` (REST); none use `self.get_guild()` (in-memory cache)
  - Does not import or use `DiscordAPIClient` at all — appears to predate the shared Discord client

- `services/bot/events/handlers.py`
  - `_validate_discord_channel` (line 189) — calls `discord_api.fetch_channel(channel_id)` (Redis → REST) purely for existence check, then `_get_bot_channel` immediately calls `self.bot.get_channel()` (in-memory) for the actual object
  - `_get_bot_channel` and the equivalent pattern in `_validate_channel_for_refresh` already use `self.bot.get_channel()` as primary, with `fetch_channel` as REST fallback — the correct pattern
  - The `discord_api.fetch_channel()` pre-validation step is redundant; `get_channel()` returning `None` already signals inaccessibility

- `shared/discord/client.py`
  - `fetch_channel` — Redis cache-backed (key: `discord:channel:{id}`, TTL: 300s)
  - `fetch_guild` — Redis cache-backed (key: `discord:guild:{id}`, TTL: 600s)
  - `get_guild_channels` — Redis cache-backed (key: `discord:guild_channels:{id}`, TTL: 300s)
  - `fetch_guild_roles` — Redis cache-backed (key: `discord:guild_roles:{id}`, TTL: 300s hardcoded)
  - `get_guild_member` — **no Redis caching**; goes through `_make_api_request` without `cache_key`/`cache_ttl`; rate-limit slot claimed but result not cached

- `shared/cache/ttl.py`
  - `DISCORD_CHANNEL = 300`, `DISCORD_GUILD = 600`, `DISCORD_GUILD_CHANNELS = 300` — 5-minute TTLs assume no push-based invalidation; safe to raise significantly once gateway events maintain freshness

- `shared/cache/keys.py`
  - Existing relevant keys: `discord_channel`, `discord_guild`, `discord_guild_channels`, `discord_guild_roles`, `discord_user`
  - No `discord_member` key exists — would need to be added for `get_guild_member` caching

- `services/api/routes/guilds.py` (line 297)
  - Only consumer of `fetch_guild_roles` — reads `id`, `name`, `color`, `position`, `managed` fields from each role dict

- `discord.py Role` object fields available without REST: `role.id`, `role.name`, `role.color.value`, `role.position`, `role.managed` — exact match to what `guilds.py` consumes

### Code Search Results

- `fetch_guild` calls in bot service
  - `role_checker.py` lines 78, 114, 151, 177, 203 — all `self.bot.fetch_guild()`, all bypassing in-memory cache
  - No uses of `self.get_guild()` anywhere in bot service

- `fetch_guild_roles` calls
  - Only in `services/api/routes/guilds.py` line 297 — API service, no gateway client available

- `get_guild_member` caching
  - `_make_api_request` called without `cache_key` — confirmed no caching
  - `display_names.py` uses `get_guild_members_batch` which calls `get_guild_member` in a loop — also uncached

- Gateway intent coverage (verified against Discord docs)
  - `GUILDS (1 << 0)`: `CHANNEL_CREATE`, `CHANNEL_UPDATE`, `CHANNEL_DELETE`, `GUILD_ROLE_CREATE`, `GUILD_ROLE_UPDATE`, `GUILD_ROLE_DELETE` — all covered by existing intent
  - `GUILD_MESSAGES (1 << 9)`: `MESSAGE_DELETE` — already used for embed deletion sweep
  - `GUILD_MEMBERS (1 << 1)`: required for member join/leave/update events — **privileged, not requested**

- Resume replay semantics (verified against Discord gateway docs)
  - On `RESUME`: Discord replays all missed events in sequence order before sending `RESUMED`; `on_resumed` fires after replay is complete
  - On full reconnect (`READY`): no replay; `on_ready` fires after `GUILD_CREATE` events populate the cache

### Project Conventions

- Standards referenced: `shared/discord/client.py` for Redis caching pattern (`cache_key` + `cache_ttl` via `_make_api_request`); `shared/cache/keys.py` for key naming; `shared/cache/ttl.py` for TTL constants

## Key Discoveries

### Gateway Cache is Always Consistent Post-Connect

After `on_ready`, `self.guilds` contains every guild the bot is a member of, with `.channels` and `.roles` fully populated — no REST calls needed. This is the authoritative source of truth for channels and roles at startup.

After `on_resumed`, gateway event replay has already updated the in-memory cache for any changes during the disconnection window. Both `CHANNEL_*` and `GUILD_ROLE_*` events are replayed.

### Five Independent Improvement Areas

#### 1. `on_ready` Redis Rebuild

Write all channel and role data into Redis from the in-memory gateway cache on startup. Eliminates the window where Redis has stale data after a full reconnect and avoids REST calls during startup.

Affected keys:

- `discord:channel:{id}` — write `{"name": channel.name}` per channel
- `discord:guild:{id}` — write `{"id": str(guild.id), "name": guild.name}` per guild
- `discord:guild_channels:{id}` — write list of channel dicts per guild
- `discord:guild_roles:{id}` — write list of role dicts per guild

Shape written to `discord:guild_roles:{id}` must match what `guilds.py` reads:

```python
{"id": str(role.id), "name": role.name, "color": role.color.value, "position": role.position, "managed": role.managed}
```

#### 2. Incremental Gateway Event Handlers

Handle `CHANNEL_CREATE`, `CHANNEL_UPDATE`, `CHANNEL_DELETE`, `GUILD_ROLE_CREATE`, `GUILD_ROLE_UPDATE`, `GUILD_ROLE_DELETE` to keep Redis current without waiting for TTL expiry.

For channel events: write/delete `discord:channel:{id}` and invalidate `discord:guild_channels:{guild_id}` (full list rebuild on next access).

For role events: write/delete individual entry within `discord:guild_roles:{guild_id}` list (read-modify-write pattern) or invalidate the key.

These events are already delivered via the `GUILDS` intent — no code changes to intents needed.

#### 3. Remove TTLs for Gateway-Maintained Keys

With `on_ready` rebuilding Redis from scratch and gateway events handling every incremental change, TTLs are not needed for channel, guild, or role keys — the cache is kept correct by push events, not by expiry. Setting a TTL would only cause unnecessary cache misses and REST fallback traffic.

The one exception is `discord:member`: member join/leave/update events require the privileged `GUILD_MEMBERS (1 << 1)` intent, which the project explicitly avoids. Member data must still use a TTL.

**Blocker**: `_make_api_request` at line 240 uses `if cache_key and cache_ttl:` to gate the Redis write. Because `None` is falsy, passing `cache_ttl=None` silently skips the write — the REST fallback result is never cached. The `redis.set()` wrapper at `shared/cache/client.py:224` already handles `ttl=None` correctly (uses plain `SET` without `SETEX`), so the only fix needed is changing the guard in `_make_api_request` from `if cache_key and cache_ttl:` to `if cache_key:`. Without this change, setting TTL constants to `None` would break caching through the REST path entirely.

#### 4. `role_checker.py` — Use In-Memory Cache

Replace `self.bot.fetch_guild()` (REST) with `self.get_guild()` (in-memory, free) in all five methods. This is the most impactful single-line change — eliminates at least one REST call per role check that misses the `user_roles` Redis cache.

The in-memory guild cache is always populated after `on_ready`, so `self.get_guild()` can only return `None` if the bot has genuinely left the guild — the same condition `fetch_guild` would raise `NotFound` for.

#### 5. `DiscordAPIClient.get_guild_member` — Add Redis Caching

Add `cache_key` and `cache_ttl` to the `_make_api_request` call in `get_guild_member`. New key: `discord:member:{guild_id}:{user_id}`. This benefits both the API service (`display_names.py`, `participant_resolver.py`, `roles.py`) and bot usage.

Wire `role_checker.get_user_role_ids` to use `DiscordAPIClient.get_guild_member()` instead of `fetch_guild()` + `fetch_member()`, collapsing two uncached REST calls to one cached call.

#### 6. Remove Redundant `fetch_channel` in `handlers.py`

`_validate_discord_channel` calls `discord_api.fetch_channel()` then immediately `self.bot.get_channel()`. The first call is redundant within the bot service — `get_channel()` returning `None` is the definitive answer. Remove `_validate_discord_channel` or replace its body with the same `get_channel()` pattern used in `_get_bot_channel`.

## Recommended Approach

Implement all six areas independently — they have no interdependencies and each delivers value on its own. Suggested order by risk/reward:

1. **`on_ready` rebuild** — highest value, isolated to `bot.py`, no API changes
2. **`role_checker.py` `get_guild()` fix** — one-liner per method, eliminates REST calls
3. **Remove redundant `fetch_channel`** — simplifies `handlers.py`, no behaviour change
4. **Gateway event handlers** — enables TTL increases, moderate scope
5. **Remove TTLs on gateway-maintained keys** — depends on #4 being in place; set `DISCORD_CHANNEL`, `DISCORD_GUILD`, `DISCORD_GUILD_CHANNELS`, `DISCORD_GUILD_ROLES` to `None` (no expiry)
6. **`get_guild_member` caching** — requires new cache key, touches shared client and multiple callers

## Implementation Guidance

- **Objectives**:
  - Replace REST calls with in-memory gateway cache lookups within the bot service
  - Rebuild Redis from the gateway cache on startup rather than letting it cold-start
  - Add caching to the one `DiscordAPIClient` method that currently lacks it

- **Key Tasks**:
  1. In `bot.py` `on_ready`: loop over `self.guilds`, write `discord:channel`, `discord:guild`, `discord:guild_channels`, `discord:guild_roles` keys to Redis
  2. In `bot.py`: add `on_guild_channel_create`, `on_guild_channel_update`, `on_guild_channel_delete` handlers that write/invalidate Redis
  3. In `bot.py`: add `on_guild_role_create`, `on_guild_role_update`, `on_guild_role_delete` handlers that update `discord:guild_roles:{id}`
  4. In `shared/discord/client.py` `_make_api_request` (line 240): change `if cache_key and cache_ttl:` to `if cache_key:` — the `redis.set()` wrapper already handles `ttl=None` correctly via plain `SET`; without this fix, `cache_ttl=None` silently skips the write
     4b. In `shared/cache/ttl.py`: set `DISCORD_CHANNEL`, `DISCORD_GUILD`, `DISCORD_GUILD_CHANNELS`, `DISCORD_GUILD_ROLES` to `None` (no expiry); `DISCORD_MEMBER` retains a TTL since member events require the privileged `GUILD_MEMBERS` intent
  5. In `role_checker.py`: replace `self.bot.fetch_guild()` with `self.bot.get_guild()` in all five methods
  6. In `role_checker.py`: replace `fetch_guild()` + `fetch_member()` in `get_user_role_ids` with `DiscordAPIClient.get_guild_member()`
  7. In `shared/discord/client.py`: add `cache_key` and `cache_ttl` to `get_guild_member`; add `discord_member` key to `shared/cache/keys.py` and TTL to `shared/cache/ttl.py`
  8. In `handlers.py`: remove or replace `_validate_discord_channel` body

- **Dependencies**:
  - Tasks 2–3 should follow Task 1 (rebuild establishes baseline before incremental updates)
  - Task 4 should follow Tasks 2–3
  - Tasks 5–8 are independent of Tasks 1–4

- **Success Criteria**:
  - `on_ready` writes Redis cache without any REST calls to Discord
  - `role_checker.py` role fetches call `get_guild()` not `fetch_guild()`
  - `get_guild_member` results are cached in Redis
  - Channel and role changes in Discord are reflected in Redis immediately via gateway events; no TTL-driven expiry occurs
  - `discord:member` cache entries expire on their TTL since member events are privileged
