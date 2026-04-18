<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Gateway Intent Redis Projection — Pre-Population Architecture

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - Current `Intents`: `guilds=True, guild_messages=True` only — `members` intent NOT enabled (line 121)
  - `on_ready` handler exists; calls `sync_all_bot_guilds` via `setup_hook` — no member write
  - No `on_member_add`, `on_member_update`, `on_member_remove` handlers present
  - Module-level `meter = metrics.get_meter(__name__)` + sweep counter/histogram instances at lines 62–88 — canonical OTel pattern for this codebase

- `services/bot/guild_sync.py`
  - `sync_all_bot_guilds`: uses Discord REST `get_guilds` + `get_guild_channels` — not gateway data
  - Syncs DB guild/channel records; does not write member/role data to Redis

- `services/bot/auth/role_checker.py`
  - `RoleChecker.get_user_role_ids`: checks Redis first (`user_roles:{user_id}:{guild_id}`), falls back to `discord_api.get_guild_member` REST call via bot token
  - Redis key written by `login_refresh.py` with `CacheTTL.USER_ROLES = 300` (5-min TTL)

- `services/api/services/login_refresh.py`
  - `refresh_display_name_on_login`: background task called after OAuth callback
  - Calls `get_user_guilds` (OAuth REST), then `client.get_current_user_guild_member` per guild
  - Writes `user_roles:{uid}:{gid}` to Redis with TTL; upserts `user_display_names` DB table via `UserDisplayNameService`

- `services/api/services/display_names.py`
  - `DisplayNameResolver`: on Redis miss, calls `discord_api.get_guild_members_batch` (REST)
  - Writes `display:{guild_id}:{user_id}` to Redis with `CacheTTL.DISPLAY_NAME = 300`
  - Root-cause of the serial REST loop identified in previous performance research

- `services/api/dependencies/permissions.py`
  - `_get_user_guilds` / `_check_guild_membership`: call `oauth2.get_user_guilds` (OAuth REST) on every authorization check
  - `verify_guild_membership`: FastAPI dependency; fires a REST call per route request — highest-frequency REST call in the API

- `shared/cache/keys.py`
  - Existing TTL-cache keys: `user_roles:{uid}:{gid}`, `display:{gid}:{uid}`, `display_avatar:{gid}:{uid}`, `discord_member:{gid}:{uid}`, `user_guilds:{uid}`
  - No projection keys exist yet — all `proj:*` keys are new

- `shared/cache/ttl.py`
  - `CacheTTL.DISPLAY_NAME = 300`, `USER_ROLES = 300`, `DISCORD_MEMBER = 300`, `USER_GUILDS = 300`
  - These remain until call sites are migrated; removed in the final cleanup step

- `shared/messaging/events.py`
  - `EventType` enum: game lifecycle, participant, and notification events only
  - No `MEMBER_CACHE_POPULATE` event — this is NOT added in the new design (no RabbitMQ member data path)

- `services/bot/message_refresh_listener.py`
  - Existing Postgres LISTEN/NOTIFY → bot action pattern — confirms bot infrastructure for async signals
  - Not used by the projection design but demonstrates bot async capability

### Code Search Results

- `guild_projection` — no matches anywhere in the codebase (file does not exist yet)
- `on_member_update` / `on_member_add` / `on_member_remove` — no matches in bot code (handlers do not exist yet)
- `proj:` Redis key prefix — no matches (projection namespace is entirely new)
- `bot:last_seen` — no matches (heartbeat key does not exist yet)
- `metrics.get_meter` in bot: line 62 of `bot.py` — module-level meter, counters and histogram follow immediately

### External Research

- discord.py `on_ready` timing
  - Fires AFTER `_delay_ready()` completes member chunking when `chunk_guilds_at_startup=True` AND `Intents.members=True`
  - At `on_ready`, `guild.members` is fully populated for all guilds — safe to iterate and write to Redis
  - Session resume (reconnect without IDENTIFY) does NOT re-fire `on_ready`; a reconnect after missed gateway events fires `on_ready` again

- `GUILD_MEMBERS` privileged intent
  - Enables: full member list in `GUILD_CREATE` on connect (chunking), real-time `GUILD_MEMBER_ADD/UPDATE/REMOVE` events
  - `discord.py`: `Intents.members = True` + `chunk_guilds_at_startup=True`
  - Discord Developer Portal toggle required; bot verification only required for 100+ server bots

- Redis SCAN performance
  - `SCAN MATCH proj:*:{old_gen}:*` iterates lazily; non-blocking; safe to run concurrently with reads
  - `redis-py` async: `redis.scan_iter(match=pattern)` — async generator, no blocking

### Project Conventions

- Standards referenced: OTel pattern from `bot.py` lines 62–88 (sweep metrics); Redis key namespacing from `shared/cache/keys.py`; existing phased cutover pattern (old and new namespaces coexist)
- TDD applicable: Python implementation — unit tests required before implementation
- No `MEMBER_CACHE_POPULATE` RabbitMQ event in this design — the bot writes autonomously, no API→bot coordination

## Key Discoveries

### Correct Write Ordering: Data First, Generation Flip Last

The generation pointer flip must happen **after** all data is written, not before. This invariant means: when the API reads a `proj:gen` value, all data under that generation is guaranteed to already exist. No per-user readiness signals, no waiting protocol.

Sequence:

1. Compute `new_gen = str(int(datetime.now(UTC).timestamp() * 1000))`
2. Pipeline-write all `proj:member:{new_gen}:*` and `proj:user_guilds:{new_gen}:*` keys for every member of every guild
3. `SET proj:gen = new_gen` — this single write atomically makes all new data visible
4. SCAN+DEL all `proj:*:{old_gen}:*` keys (cleanup; can be done immediately after flip)

### API Gen-Rotation Retry — 3 GETs, No Waiting

The only case where the API reads a nil for a projection key is:

- **Genuine absence**: the user is not in any monitored guild, OR
- **Gen rotation**: the generation pointer changed between the API's GET proj:gen and GET proj:member (only possible during a bot reconnect/repopulation — rare)

These two cases are disambiguated by re-reading `proj:gen`:

```python
_MAX_GEN_RETRIES = 3

async def _read_with_gen_retry(redis, key_fn, *key_args):
    gen = await redis.get(proj_gen())
    for _ in range(_MAX_GEN_RETRIES):
        if not gen:
            return None
        value = await redis.get(key_fn(gen, *key_args))
        if value is not None:
            return value
        gen2 = await redis.get(proj_gen())
        if gen == gen2:
            return None   # gen stable; key genuinely absent
        gen = gen2        # gen rotated under us; retry with new gen
    return None
```

Maximum 3 × 2 = 6 Redis GETs on the worst-case retry path. In normal operation (no concurrent reconnect): 2 GETs on hit, 3 GETs on genuine miss. No subscriptions, no waiting, no RabbitMQ.

### Repopulate-on-Any-Change Gives Consistent Snapshots

Every gateway member event (`on_ready`, `on_member_add`, `on_member_update`, `on_member_remove`) calls the same `repopulate_all()` function. Since each repopulation is a full snapshot written atomically before the gen pointer flips, every generation is always consistent. There is no partial-write window for nick/role mismatches.

Coalescing (de-duplicate rapid successive events) is not implemented initially. If `on_member_update` fires frequently and causes performance problems, that will be visible in the OTel metrics — add coalescing then. The correctness story is identical with or without coalescing.

### No RabbitMQ Member Data Path

The on-demand design used `MEMBER_CACHE_POPULATE` RabbitMQ messages for API→bot coordination. Pre-population eliminates this entirely: the bot writes autonomously on gateway events, the API reads. No message channel, no coupling between API availability and bot responsiveness.

### Memory Cost Is Not a Concern

5,000 members × 500 bytes/entry ≈ 2.5 MB per guild in Redis. The full member corpus is already in discord.py's in-process cache after `chunk_guilds_at_startup=True`. Writing it to Redis is a pipeline copy of data already in memory, not a net cost increase.

## Recommended Approach

### Redis Key Schema

```
proj:gen                               ← current generation pointer (UTC ms timestamp string)
proj:member:{gen}:{guild_id}:{uid}     ← hash: {roles, nick, global_name, username, avatar_url}
proj:user_guilds:{gen}:{uid}           ← JSON list of guild_id strings the bot monitors
bot:last_seen                          ← UTC ISO timestamp, TTL = heartbeat_interval × 3
```

No per-user status keys. No `proj:user:{gen}:{uid}:status`.

### New Files to Create

**`services/bot/guild_projection.py`** — bot-side writer:

```python
# Module-level OTel instruments
_meter = metrics.get_meter(__name__)
repopulation_started_counter = _meter.create_counter(
    name="bot.projection.repopulation.started",
    description="Number of full Redis projection repopulations triggered",
    unit="1",
)
repopulation_duration_histogram = _meter.create_histogram(
    name="bot.projection.repopulation.duration",
    description="Duration of full Redis projection repopulations in seconds",
    unit="s",
)
repopulation_members_written_histogram = _meter.create_histogram(
    name="bot.projection.repopulation.members_written",
    description="Number of member keys written per repopulation",
    unit="1",
)

# Core function
async def repopulate_all(*, bot: discord.Client, redis: Redis, reason: str) -> None:
    """Write all member data under a new generation, then flip the gen pointer."""
    new_gen = str(int(datetime.now(UTC).timestamp() * 1000))
    prev_gen = await redis.get(proj_gen())
    repopulation_started_counter.add(1, {"reason": reason})
    start = time.monotonic()
    members_written = 0

    # Collect guild membership per user across all guilds
    user_guild_ids: dict[str, list[str]] = {}
    for guild in bot.guilds:
        for member in guild.members:
            uid = str(member.id)
            guild_id = str(guild.id)
            await write_member(redis=redis, gen=new_gen, guild_id=guild_id, uid=uid, member=member)
            members_written += 1
            user_guild_ids.setdefault(uid, []).append(guild_id)

    for uid, guild_ids in user_guild_ids.items():
        await write_user_guilds(redis=redis, gen=new_gen, uid=uid, guild_ids=guild_ids)

    # Flip generation pointer — completeness signal
    await redis.set(proj_gen(), new_gen)

    # Retire old generation keys
    if prev_gen:
        async for key in redis.scan_iter(match=f"proj:*:{prev_gen}:*"):
            await redis.delete(key)

    repopulation_duration_histogram.record(time.monotonic() - start, {"reason": reason})
    repopulation_members_written_histogram.record(members_written, {"reason": reason})

# Supporting writers (no TTL on any projection key)
async def write_member(*, redis, gen, guild_id, uid, member: discord.Member) -> None: ...
async def write_user_guilds(*, redis, gen, uid, guild_ids) -> None: ...
async def write_bot_last_seen(*, redis) -> None: ...
```

**`services/api/services/member_projection.py`** — API-side reader:

```python
# Module-level OTel instruments
_meter = metrics.get_meter(__name__)
_read_retry_counter = _meter.create_counter(
    name="api.projection.read.retries",
    description="Gen-rotation retries during projection reads",
    unit="1",
)
_read_not_found_counter = _meter.create_counter(
    name="api.projection.read.not_found",
    description="Projection reads that returned absent after gen stabilized",
    unit="1",
)

_MAX_GEN_RETRIES = 3

async def get_user_guilds(uid: str, *, redis: Redis) -> list[str] | None: ...
async def get_member(guild_id: str, uid: str, *, redis: Redis) -> dict | None: ...
async def get_user_roles(guild_id: str, uid: str, *, redis: Redis) -> list[str]: ...
async def is_bot_fresh(*, redis: Redis) -> bool: ...
```

All read functions use `_read_with_gen_retry()` internally. `_read_retry_counter` incremented per retry iteration. `_read_not_found_counter` incremented when gen is stable but key is absent.

### Bot Event Wiring (changes to `services/bot/bot.py`)

Add to `GameSchedulerBot`:

```python
async def on_member_add(self, member: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_add")

async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_update")

async def on_member_remove(self, member: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_remove")
```

Update `on_ready` to call `repopulate_all(reason="on_ready")` and add bot heartbeat task.

### What This Replaces (Phased — Each Step Is Independently Shippable)

| Old Component                                                                          | New Replacement                      | Notes                                     |
| -------------------------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------- |
| `login_refresh.py` + `get_current_user_guild_member` REST calls                        | Bot `repopulate_all()` on `on_ready` | Entire file deleted eventually            |
| `DisplayNameResolver._fetch_and_cache_display_names*` (REST fallback)                  | `get_member()` projection read       | REST fallback removed per call site       |
| `permissions.py` `_get_user_guilds` / `_check_guild_membership` (OAuth REST per-route) | `get_user_guilds()` projection read  | Highest-frequency elimination             |
| `RoleChecker.get_guild_member` REST fallback                                           | `get_user_roles()` projection read   |                                           |
| `CacheTTL.DISPLAY_NAME / USER_ROLES / DISCORD_MEMBER / USER_GUILDS` (5-min TTLs)       | No TTL on projection keys            | Remove from `ttl.py` after full migration |
| `user_display_names` DB table + `UserDisplayNameService`                               | Redis projection                     | Becomes dead code; drop table migration   |
| `services/api/dependencies/discord.py` `DiscordAPIClient` in API                       | Unused after migration               | Delete once API has zero REST calls       |

## Implementation Guidance

- **Objectives**:
  - Eliminate all Discord REST calls from the per-request API path
  - Preserve phased cutover: old TTL-cache and new projection keys coexist; each call site migrated independently
  - Add OTel metrics to observe repopulation frequency, duration, and read retry rate before deciding whether coalescing is needed

- **Key Tasks** (in dependency order):
  1. **Enable `GUILD_MEMBERS` intent** in `services/bot/bot.py` (`Intents.members = True`, `chunk_guilds_at_startup=True`) and toggle in Discord Developer Portal. No behavior change yet; just enables gateway member data.

  2. **Add new Redis key constants** to `shared/cache/keys.py`: `proj_gen()`, `proj_member(gen, guild_id, uid)`, `proj_user_guilds(gen, uid)`, `bot_last_seen()`. No `proj_user_status()`.

  3. **Create `services/bot/guild_projection.py`**: module-level OTel meter + 3 instruments; `repopulate_all()`, `write_member()`, `write_user_guilds()`, `write_bot_last_seen()`.

  4. **Wire bot events**: update `on_ready` and add `on_member_add`, `on_member_update`, `on_member_remove` in `bot.py` — all call `repopulate_all(reason=...)`. Add bot heartbeat task writing `bot:last_seen`.

  5. **Create `services/api/services/member_projection.py`**: module-level OTel meter + 2 instruments; `_read_with_gen_retry()` helper; `get_user_guilds()`, `get_member()`, `get_user_roles()`, `is_bot_fresh()`. Can be developed in parallel with steps 3–4.

  6. **Migrate call sites one at a time** — in order of frequency:
     - `permissions.py` `verify_guild_membership` → `get_user_guilds()` (fires on every protected route)
     - `login_refresh.py` display name reads → `get_member()`
     - `RoleChecker.get_guild_member` REST fallback → `get_user_roles()`
     - `DisplayNameResolver` REST fallback → `get_member()`

  7. **Remove dead code** after all call sites migrated: `login_refresh.py`, REST fallback paths in `DisplayNameResolver` and `RoleChecker`, `_get_user_guilds` in `permissions.py`, TTL constants `DISPLAY_NAME / USER_ROLES / DISCORD_MEMBER / USER_GUILDS`. Verify zero Discord REST calls from the API before closing this step.

  8. **Drop `user_display_names` DB table**: add Alembic migration; delete `UserDisplayNameService` and `user_display_names.py`.
  - Steps 1–2 are independent and can ship together.
  - Steps 3–4 (bot side) must complete before any API call site migration (step 6).
  - Step 5 (API reader) can be developed in parallel with steps 3–4.
  - Step 6 is N independent PRs, each independently shippable.
  - Steps 7–9 are safe only after step 6 is 100% complete.

- **Dependencies**:
  - `Intents.members = True` + `chunk_guilds_at_startup=True` must be enabled before `repopulate_all()` has member data at `on_ready`
  - No `notify-keyspace-events` Redis configuration required (no keyspace subscriptions)
  - No RabbitMQ changes required (no new event types, no new consumers)

- **Success Criteria**:
  - `verify_guild_membership` fires zero OAuth REST calls per request after step 6
  - `list_games` display name resolution reads only Redis; no Discord API calls in the hot path
  - `api.projection.read.retries` counter is zero under normal operation
  - `bot:last_seen` absence causes a clear degraded response, not a silent error or hang
  - Zero Discord REST calls from the API server — verified before closing step 7
  - All steps pass the full unit + integration test suite before merging
