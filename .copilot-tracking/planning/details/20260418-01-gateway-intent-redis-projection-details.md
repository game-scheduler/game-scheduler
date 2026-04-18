<!-- markdownlint-disable-file -->

# Task Details: Discord Gateway Intent Redis Projection

## Research Reference

**Source Research**: #file:../research/20260418-01-gateway-intent-redis-projection-research.md

---

## Phase 1: Foundation — Enable Intent and Add Key Constants

### Task 1.1: Enable GUILD_MEMBERS Privileged Intent

Set `Intents.members = True` and `chunk_guilds_at_startup = True` on the bot. This is a prerequisite for `guild.members` being populated at `on_ready`. No behavior change visible to users yet — it only enables gateway member data delivery.

Also requires toggling "Server Members Intent" in the Discord Developer Portal for the bot application.

- **Files**:
  - `services/bot/bot.py` — update `Intents` construction near line 121
- **Success**:
  - `Intents.members = True` and `chunk_guilds_at_startup = True` are set
  - Bot reconnects and logs `on_ready` without errors after the change
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 83–97) — external research on `GUILD_MEMBERS` intent behavior, chunking timing, and `on_ready` guarantees
- **Dependencies**:
  - Discord Developer Portal toggle must be enabled before the change is deployed

### Task 1.2: Add Projection Key Constants to shared/cache/keys.py

Add four new key-factory functions to `shared/cache/keys.py`:

- `proj_gen() -> str` — returns `"proj:gen"`
- `proj_member(gen: str, guild_id: str, uid: str) -> str` — returns `f"proj:member:{gen}:{guild_id}:{uid}"`
- `proj_user_guilds(gen: str, uid: str) -> str` — returns `f"proj:user_guilds:{gen}:{uid}"`
- `bot_last_seen() -> str` — returns `"bot:last_seen"`

No `proj_user_status` key. No changes to existing TTL constants in this step.

- **Files**:
  - `shared/cache/keys.py` — add four key functions after existing keys
- **Success**:
  - All four functions exist and return the documented key strings
  - No existing keys changed
  - Unit tests for all four functions pass
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 163–170) — Redis key schema section
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 23–29) — existing key patterns from `shared/cache/keys.py`
- **Dependencies**:
  - None — independent of Task 1.1

---

## Phase 2: Bot-side Writer

### Task 2.1: Create services/bot/guild_projection.py

Create a new module that implements the full repopulation writer. Follow the OTel pattern from `bot.py` lines 62–88 exactly — module-level meter, then named instrument instances.

**Module structure:**

```
module-level OTel meter and 3 instruments
  - bot.projection.repopulation.started (counter, unit="1", attribute: reason)
  - bot.projection.repopulation.duration (histogram, unit="s", attribute: reason)
  - bot.projection.repopulation.members_written (histogram, unit="1", attribute: reason)

repopulate_all(*, bot, redis, reason) -> None
  - compute new_gen = str(int(datetime.now(UTC).timestamp() * 1000))
  - read prev_gen = await redis.get(proj_gen())
  - increment started counter
  - for each guild in bot.guilds, for each member in guild.members:
      call write_member; accumulate user_guild_ids
  - for each uid, write_user_guilds
  - SET proj:gen = new_gen  (generation flip — completeness signal)
  - SCAN+DEL all proj:*:{prev_gen}:* keys
  - record duration and members_written histograms

write_member(*, redis, gen, guild_id, uid, member) -> None
  - SET proj:member:{gen}:{guild_id}:{uid} = JSON of {roles, nick, global_name, username, avatar_url}
  - no TTL

write_user_guilds(*, redis, gen, uid, guild_ids) -> None
  - SET proj:user_guilds:{gen}:{uid} = JSON list of guild_id strings
  - no TTL

write_bot_last_seen(*, redis) -> None
  - SET bot:last_seen = UTC ISO timestamp with TTL = heartbeat_interval * 3
```

The generation flip (`SET proj:gen`) must come **after** all data writes are complete. This invariant ensures any reader observing the new gen value will find all its data already present.

- **Files**:
  - `services/bot/guild_projection.py` — create new file
  - `tests/unit/bot/test_guild_projection.py` — create unit tests (TDD: stub + xfail first)
- **Success**:
  - `repopulate_all` writes all member and user_guilds keys before flipping gen
  - Old generation keys are deleted after the gen flip
  - OTel counters and histograms fire with correct attributes on each repopulation
  - Unit tests cover: normal repopulation, gen flip ordering, old-gen cleanup, empty guild list
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 101–130) — key discovery: correct write ordering, data-first / gen-flip-last invariant
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 171–213) — recommended approach: full module structure with code examples
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 60–66) — OTel pattern reference (bot.py lines 62–88)
- **Dependencies**:
  - Task 1.1 (intent enabled) and Task 1.2 (key constants) must be complete

### Task 2.2: Wire Bot Events and Heartbeat Task in bot.py

Add four gateway event handlers to `GameSchedulerBot` and a periodic heartbeat task:

```python
async def on_ready(self) -> None:
    # existing guild sync + new call:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="on_ready")

async def on_member_add(self, member: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_add")

async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_update")

async def on_member_remove(self, member: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_remove")
```

Add a background task (started in `setup_hook`) that calls `write_bot_last_seen` on a fixed interval (e.g., 30 s).

- **Files**:
  - `services/bot/bot.py` — add handlers and heartbeat task
  - `tests/unit/bot/test_bot.py` — unit tests for event handler dispatch (TDD: stub + xfail first)
- **Success**:
  - All four handlers call `repopulate_all` with the correct `reason` string
  - Heartbeat task writes `bot:last_seen` on each tick
  - Existing `on_ready` behavior (guild sync) is preserved; `repopulate_all` is called after it
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 214–237) — bot event wiring code examples
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 83–97) — on_ready timing and session-resume behavior
- **Dependencies**:
  - Task 2.1 (guild_projection.py) must be complete

---

## Phase 3: API-side Reader

### Task 3.1: Create services/api/services/member_projection.py

Create the API-side reader module. Uses `_read_with_gen_retry()` for all Redis reads.

**Module structure:**

```
module-level OTel meter and 2 instruments
  - api.projection.read.retries (counter, unit="1")
  - api.projection.read.not_found (counter, unit="1")

_MAX_GEN_RETRIES = 3

_read_with_gen_retry(redis, key_fn, *key_args) -> str | None
  - reads proj:gen
  - up to _MAX_GEN_RETRIES iterations:
      GET key_fn(gen, *key_args)
      if value: return value
      re-read gen2
      if gen == gen2: increment not_found counter; return None  (gen stable, key absent)
      gen = gen2; increment retries counter
  - return None

get_user_guilds(uid, *, redis) -> list[str] | None
  - calls _read_with_gen_retry with proj_user_guilds key
  - parses JSON list; returns None if absent

get_member(guild_id, uid, *, redis) -> dict | None
  - calls _read_with_gen_retry with proj_member key
  - parses JSON dict; returns None if absent

get_user_roles(guild_id, uid, *, redis) -> list[str]
  - calls get_member; returns member["roles"] or [] if absent

is_bot_fresh(*, redis) -> bool
  - GET bot:last_seen; returns True if key present and timestamp within acceptable age
```

- **Files**:
  - `services/api/services/member_projection.py` — create new file
  - `tests/unit/api/test_member_projection.py` — create unit tests (TDD: stub + xfail first)
- **Success**:
  - `_read_with_gen_retry` handles gen-rotation window correctly (max 6 GETs)
  - `_read_retry_counter` increments on each retry iteration; `_read_not_found_counter` on stable-gen miss
  - All public functions return correct types for present, absent, and gen-rotation cases
  - Unit tests cover: cache hit, genuine miss, gen-rotation mid-read, max retry exhaustion
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 101–131) — gen-rotation retry algorithm with annotated code example
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 218–230) — reader function signatures
- **Dependencies**:
  - Task 1.2 (key constants) must be complete
  - Can be developed in parallel with Phase 2

---

## Phase 4: Call Site Migration

Migrate each call site independently. Old TTL-cache keys and new projection keys coexist during this phase. Each migration is independently shippable.

### Task 4.1: Migrate permissions.py verify_guild_membership (Highest Priority)

Replace `_get_user_guilds` / `_check_guild_membership` OAuth REST calls with `member_projection.get_user_guilds()`.

`verify_guild_membership` fires on every protected API route — this is the single highest-frequency REST call elimination.

- **Files**:
  - `services/api/dependencies/permissions.py` — replace `_get_user_guilds` internals
  - `tests/unit/api/test_permissions.py` — update tests
- **Success**:
  - `verify_guild_membership` makes zero OAuth REST calls per request
  - Returns 403 correctly when user is not in the guild
  - Uses `is_bot_fresh()` to return a clear degraded response when bot:last_seen is absent
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 36–42) — current permissions.py behavior
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–246) — replacement table entry
- **Dependencies**:
  - Phase 2 and Phase 3 must be complete and deployed

### Task 4.2: Migrate login_refresh.py Display Name Reads

Replace `get_current_user_guild_member` REST calls with `member_projection.get_member()`.

- **Files**:
  - `services/api/services/login_refresh.py` — replace REST calls
  - `tests/unit/api/test_login_refresh.py` — update tests
- **Success**:
  - `refresh_display_name_on_login` reads from Redis projection; makes zero REST calls
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 29–35) — current login_refresh.py behavior
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–246) — replacement table
- **Dependencies**:
  - Phase 2 and Phase 3 complete

### Task 4.3: Migrate RoleChecker REST Fallback

Replace `discord_api.get_guild_member` REST fallback in `RoleChecker.get_user_role_ids` with `member_projection.get_user_roles()`.

- **Files**:
  - `services/bot/auth/role_checker.py` — replace REST fallback
  - `tests/unit/bot/test_role_checker.py` — update tests
- **Success**:
  - `get_user_role_ids` reads from Redis projection; REST fallback removed
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 22–27) — current role_checker.py behavior
- **Dependencies**:
  - Phase 2 and Phase 3 complete

### Task 4.4: Migrate DisplayNameResolver REST Fallback

Replace `discord_api.get_guild_members_batch` REST fallback in `DisplayNameResolver` with `member_projection.get_member()`.

- **Files**:
  - `services/api/services/display_names.py` — replace REST fallback
  - `tests/unit/api/test_display_names.py` — update tests
- **Success**:
  - `DisplayNameResolver` resolves display names from Redis projection; zero REST calls
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 43–49) — current display_names.py behavior
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–246) — replacement table
- **Dependencies**:
  - Phase 2 and Phase 3 complete

---

## Phase 5: Cleanup

### Task 5.1: Remove Dead Code

After all Phase 4 call sites are migrated and verified, delete or gut the following:

- `services/api/services/login_refresh.py` — delete entirely (or gut REST call paths if any non-REST logic remains)
- REST fallback paths in `DisplayNameResolver` and `RoleChecker` already removed in Phase 4
- `_get_user_guilds` and `_check_guild_membership` helper functions in `permissions.py`
- TTL constants `DISPLAY_NAME`, `USER_ROLES`, `DISCORD_MEMBER`, `USER_GUILDS` from `shared/cache/ttl.py`
- Old TTL-cache key functions in `shared/cache/keys.py` if no longer referenced

Verify zero Discord REST calls from the API service before closing this task.

- **Files**:
  - `services/api/services/login_refresh.py`
  - `services/api/dependencies/permissions.py`
  - `shared/cache/ttl.py`
  - `shared/cache/keys.py`
- **Success**:
  - `grep -r "discord_api\|get_guild_member\|get_user_guilds.*oauth\|get_current_user_guild_member" services/api/` returns no matches
  - All TTL constants removed; no references remain
  - Full test suite passes
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–258) — full dead-code removal list
- **Dependencies**:
  - All Phase 4 tasks complete

### Task 5.2: Drop user_display_names Table

Add an Alembic migration to drop the `user_display_names` table and delete `UserDisplayNameService` and its associated model/data-access files.

- **Files**:
  - `alembic/versions/<new_revision>.py` — drop table migration
  - `services/api/services/display_names.py` — delete or reduce to projection reader only
  - Any `user_display_names` model and data-access files
- **Success**:
  - Migration applies cleanly in dev and staging
  - No import references to `UserDisplayNameService` remain
  - Integration tests pass after migration
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–258) — user_display_names in the replacement table
- **Dependencies**:
  - Task 5.1 complete

---

## Dependencies

- `discord.py` `GUILD_MEMBERS` intent toggle in Discord Developer Portal
- `redis-py` async (`redis.asyncio`) — already present in codebase
- No new RabbitMQ events or consumers
- No `notify-keyspace-events` Redis configuration required

## Success Criteria

- `verify_guild_membership` fires zero OAuth REST calls per request after Phase 4
- `list_games` display name resolution reads only Redis; no Discord API calls in the hot path
- `api.projection.read.retries` OTel counter is zero under normal operation
- `bot:last_seen` absence causes a clear degraded response, not a silent error
- Zero Discord REST calls from the API server — confirmed by grep before closing Phase 5
- All unit tests pass at each phase boundary before merging
