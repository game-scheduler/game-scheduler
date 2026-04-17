<!-- markdownlint-disable-file -->

# Task Details: Discord Gateway Intent Redis Projection Architecture

## Research Reference

**Source Research**: #file:../research/20260417-01-gateway-intent-redis-projection-research.md

## Phase 1: Foundation (Steps 1–3)

### Task 1.1: Enable GUILD_MEMBERS Privileged Intent

Enable the Discord `members` privileged gateway intent in `services/bot/bot.py`. Set `Intents.members = True` and `chunk_guilds_at_startup = True`. Toggle the intent in the Discord Developer Portal. The system continues operating identically — no new behavior until the handlers in Phase 2 are wired.

- **Files**:
  - `services/bot/bot.py` — add `members=True, chunk_guilds_at_startup=True` to `Intents` setup
- **Success**:
  - Bot connects and fires `on_ready` without error after the Discord Portal toggle
  - `Intents.members` is `True` at runtime
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 90–96) — `GUILD_MEMBERS` privileged intent requirements
- **Dependencies**:
  - None; independent of all other tasks

### Task 1.2: Add Redis Projection Key Constants

Add projection-namespace key functions to `shared/cache/keys.py`:

- `proj_gen() -> str` → `"proj:gen"`
- `proj_member(gen, guild_id, uid) -> str` → `"proj:member:{gen}:{guild_id}:{uid}"`
- `proj_user_guilds(gen, uid) -> str` → `"proj:user_guilds:{gen}:{uid}"`
- `proj_user_complete(gen, uid) -> str` → `"proj:user:{gen}:{uid}:complete"`
- `bot_populate_lock(gen, uid) -> str` → `"bot:populate:{gen}:{uid}"`
- `bot_last_seen() -> str` → `"bot:last_seen"`

TDD: stub each function with `raise NotImplementedError`, write `xfail` tests in `tests/unit/shared/cache/test_keys.py`, then implement.

- **Files**:
  - `shared/cache/keys.py` — add the six projection key functions
  - `tests/unit/shared/cache/test_keys.py` — unit tests for all new key functions
- **Success**:
  - All new key functions return the expected string patterns
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 135–141) — Redis projection schema
- **Dependencies**:
  - None; independent of all other tasks

### Task 1.3: Add MEMBER_CACHE_POPULATE Event Type and Payload

Add `MEMBER_CACHE_POPULATE = "member_cache_populate"` to the `EventType` enum in `shared/messaging/events.py`. Add a `MemberCachePopulateEvent` Pydantic model with fields `user_discord_id: str`, `guild_ids: list[str]`, `gen: str`.

TDD: write `xfail` tests in `tests/unit/shared/messaging/test_events.py`, then implement.

- **Files**:
  - `shared/messaging/events.py` — add `MEMBER_CACHE_POPULATE` enum value, add `MemberCachePopulateEvent` model
  - `tests/unit/shared/messaging/test_events.py` — unit tests
- **Success**:
  - `EventType.MEMBER_CACHE_POPULATE` resolves to `"member_cache_populate"`
  - `MemberCachePopulateEvent` validates correct field types
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 285–290) — `MEMBER_CACHE_POPULATE` in implementation guidance
- **Dependencies**:
  - None; independent of all other tasks

## Phase 2: Bot Projection Writer

### Task 2.1: Implement Bot Projection Writer Module

Create `services/bot/guild_projection.py` with:

- `write_member(redis, gen, guild_id, member)` — writes `proj:member:{gen}:{guild_id}:{uid}` as JSON (`roles`, `nick`, `global_name`, `username`, `avatar_url`)
- `write_user_guilds(redis, gen, uid, guild_ids)` — writes `proj:user_guilds:{gen}:{uid}` as JSON list
- `write_user_complete(redis, gen, uid)` — writes `proj:user:{gen}:{uid}:complete = "ready"`
- `delete_user_projection(redis, gen, guild_id, uid)` — deletes all three keys for the user (member, user_guilds, complete); preserves the marker contract by ensuring the complete marker is never left set after a partial write
- `new_generation() -> str` — returns `str(int(datetime.now(UTC).timestamp() * 1000))`

TDD: stub all functions, write `xfail` tests in `tests/unit/bot/test_guild_projection.py`, then implement.

- **Files**:
  - `services/bot/guild_projection.py` — new module
  - `tests/unit/bot/test_guild_projection.py` — unit tests using a fake Redis client
- **Success**:
  - All functions tested against a fake Redis; all unit tests pass
  - `new_generation()` returns a millisecond-precision timestamp string
  - `delete_user_projection` deletes all three keys atomically
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 135–141) — Redis projection schema
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 153–180) — per-user completion marker contract and delete-all rationale
- **Dependencies**:
  - Task 1.2 must be complete

### Task 2.2: Wire on_ready and Reconnect (Generation Bump)

Update the `on_ready` handler in `services/bot/bot.py` (currently at line 180) to:

1. Read `proj:gen` to obtain the previous generation value
2. Compute `new_gen = new_generation()`
3. SET `proj:gen = new_gen`
4. SCAN+DEL all `proj:*:{prev_gen}:*` keys (clean up previous generation)
5. Write `bot:last_seen`

discord.py fires `on_ready` again after a full reconnect (IDENTIFY), so this same handler covers both the initial connect and reconnect-after-invalidation cases.

TDD: write `xfail` tests in `tests/unit/bot/test_bot_on_ready.py` mocking the Redis client to assert the correct operation sequence, then implement.

- **Files**:
  - `services/bot/bot.py` — update `on_ready` at line 180
  - `tests/unit/bot/test_bot_on_ready.py` — unit tests
- **Success**:
  - `proj:gen` is updated to a new generation value on `on_ready`
  - Previous generation keys are deleted
  - `bot:last_seen` is written
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 143–160) — generation bump sequence
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 162–185) — generation retirement strategy
- **Dependencies**:
  - Tasks 1.2 and 2.1 must be complete

### Task 2.3: Add on_member_update and on_member_remove Handlers

Add event handlers to `services/bot/bot.py`. Both call `delete_user_projection(redis, gen, guild_id, uid)`. `on_member_add` is an intentional no-op; new members are demand-faulted in by the API.

TDD: write `xfail` tests in `tests/unit/bot/test_bot_member_events.py`, then implement.

- **Files**:
  - `services/bot/bot.py` — add `on_member_update` and `on_member_remove` handlers
  - `tests/unit/bot/test_bot_member_events.py` — unit tests
- **Success**:
  - Both handlers delete all three projection keys for the affected user
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 150–160) — incremental gateway event invalidation
- **Dependencies**:
  - Tasks 1.2 and 2.1 must be complete

### Task 2.4: Add Bot Heartbeat Task

Create a background task (in `services/bot/bot.py` or `services/bot/heartbeat.py`) that writes `bot:last_seen = <utc_iso>` with `TTL = heartbeat_interval × 3` every N minutes. Start the task in `setup_hook`.

TDD: write `xfail` tests verifying the key is written with the correct TTL, then implement.

- **Files**:
  - `services/bot/bot.py` or `services/bot/heartbeat.py` — heartbeat background task
  - Corresponding unit test file
- **Success**:
  - `bot:last_seen` is written with the correct TTL on every interval tick
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 247–251) — bot freshness signal specification
- **Dependencies**:
  - Task 1.2 must be complete

### Task 2.5: Add MEMBER_CACHE_POPULATE Consumer in Bot

Add a RabbitMQ consumer for `MEMBER_CACHE_POPULATE` events. Handler logic:

1. Check `proj:user:{gen}:{uid}:complete` — if `ready`, return immediately (data already present)
2. Attempt `SET bot:populate:{gen}:{uid} 1 NX EX 30`
3. If NX wins: call `write_member` for each specified guild, call `write_user_guilds`, call `write_user_complete`, then DELETE `bot:populate:{gen}:{uid}`
4. If NX loses: return immediately (concurrent handler is doing the work)

The lock must be deleted immediately after writing `ready` — leaving it to expire would block re-populate after `on_member_update` invalidation until the TTL expires.

TDD: write `xfail` tests in `tests/unit/bot/test_member_cache_populate.py` covering: already complete, NX wins (full write path), NX loses (early return), and lock deletion after write. Then implement.

- **Files**:
  - `services/bot/handlers.py` (or relevant handler file) — `MEMBER_CACHE_POPULATE` consumer
  - `tests/unit/bot/test_member_cache_populate.py` — unit tests
- **Success**:
  - Dedup lock prevents duplicate populate work
  - Lock is deleted immediately after writing the complete marker
  - All four test cases pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 195–220) — on-demand populate flow, bot side
- **Dependencies**:
  - Tasks 1.2, 1.3, and 2.1 must be complete

## Phase 3: API Projection Reader

### Task 3.1: Implement API Projection Reader Module

Create `services/api/services/member_projection.py` with:

- `get_current_gen(redis) -> str | None`
- `get_user_guilds(redis, uid) -> list[str] | None`
- `get_member(redis, guild_id, uid) -> dict | None`
- `get_user_roles(redis, guild_id, uid) -> list[str] | None`
- `is_bot_fresh(redis) -> bool`
- `wait_for_user_complete(redis, uid, timeout) -> bool` — subscribes to keyspace notifications, re-checks after subscription to close the TOCTOU window, publishes `MEMBER_CACHE_POPULATE`, blocks until notification or timeout; implements max-3-attempt retry loop for generation rotation

TDD: stub all functions, write `xfail` tests in `tests/unit/api/services/test_member_projection.py`, then implement.

- **Files**:
  - `services/api/services/member_projection.py` — new module
  - `tests/unit/api/services/test_member_projection.py` — unit tests using fake Redis
- **Success**:
  - All reader functions return correct values from fake Redis fixtures
  - `wait_for_user_complete` handles: already ready, subscribe+recheck race, timeout, generation rotation
  - `is_bot_fresh` returns `False` when `bot:last_seen` is absent
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 183–230) — on-demand populate flow, API side
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 206–245) — keyspace notification protocol and retry loop
- **Dependencies**:
  - Tasks 1.2 and 1.3 must be complete; Phase 2 complete for integration testing

## Phase 4: API Call Site Migration

### Task 4.1: Migrate permissions.py verify_guild_membership

Replace `_get_user_guilds` and `_check_guild_membership` in `services/api/dependencies/permissions.py` with reads from `proj:user_guilds:{gen}:{uid}` via `member_projection.get_user_guilds`. Add an `is_bot_fresh` check that returns a clear HTTP error when the bot is unavailable.

TDD: write `xfail` tests asserting zero OAuth REST calls per route, then implement.

- **Files**:
  - `services/api/dependencies/permissions.py` — replace `_get_user_guilds` / `_check_guild_membership`
  - `tests/unit/api/dependencies/test_permissions.py` — updated unit tests
- **Success**:
  - `verify_guild_membership` makes zero OAuth REST calls
  - Bot-unavailable path returns a clear HTTP error
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 285–295) — call site migration order
- **Dependencies**:
  - Phase 3 must be complete

### Task 4.2: Migrate login_refresh.py Display Name Reads

Replace `get_current_user_guild_member` REST calls in `services/api/services/login_refresh.py` with reads from the projection via `member_projection.get_member`. Replace the `get_user_guilds` REST call with `member_projection.get_user_guilds`.

TDD: write `xfail` tests, then implement.

- **Files**:
  - `services/api/services/login_refresh.py` — replace REST calls with projection reads
  - Corresponding unit test file
- **Success**:
  - No REST calls remain in `login_refresh.py`
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 30–45) — `login_refresh.py` current REST call pattern
- **Dependencies**:
  - Phase 3 must be complete

### Task 4.3: Migrate RoleChecker

Update `services/bot/auth/role_checker.py` `get_user_role_ids` to read from the discord.py client cache (`guild.get_member(int(user_id)).roles`) instead of Redis or REST. With `Intents.members = True`, the client cache is authoritative.

TDD: write `xfail` tests, then implement.

- **Files**:
  - `services/bot/auth/role_checker.py` — replace Redis/REST with client cache read
  - Corresponding unit test file
- **Success**:
  - `get_user_role_ids` reads only from the discord.py client cache
  - No Redis read, no REST call in the role check path
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 295–302) — RoleChecker: client cache is authoritative
- **Dependencies**:
  - Task 1.1 must be complete

### Task 4.4: Migrate DisplayNameResolver

Remove the REST fallback paths in `services/api/services/display_names.py` (`_fetch_and_cache_display_names_avatars` and `DisplayNameResolver._fetch_and_cache_display_names*`). Replace with reads from `proj:member:{gen}:{guild_id}:{uid}` via `member_projection.get_member`.

TDD: write `xfail` tests, then implement.

- **Files**:
  - `services/api/services/display_names.py` — remove REST fallback, add projection read
  - Corresponding unit test file
- **Success**:
  - No `get_guild_members_batch` calls in the display name resolution hot path
  - Unit tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 46–55) — `display_names.py` current REST fallback pattern
- **Dependencies**:
  - Phase 3 must be complete

## Phase 5: Dead Code Removal

### Task 5.1: Remove login_refresh.py and REST Fallback Paths

Delete `services/api/services/login_refresh.py`. Remove remaining REST fallback methods from `display_names.py` and any residual REST helpers from `permissions.py`. Perform a grep audit to confirm zero Discord REST calls from the API server.

- **Files**:
  - `services/api/services/login_refresh.py` — deleted
  - `services/api/services/display_names.py` — remove REST fallback methods
  - `services/api/dependencies/permissions.py` — remove any residual REST call helpers
- **Success**:
  - `grep -r "discord_api\." services/api/` returns zero matches
  - All tests pass after deletion
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 302–315) — dead code list
- **Dependencies**:
  - All of Phase 4 must be complete

### Task 5.2: Remove Obsolete TTL Constants

Remove `USER_ROLES`, `DISPLAY_NAME`, `DISCORD_MEMBER`, and `USER_GUILDS` from `shared/cache/ttl.py`. Remove any corresponding obsolete key functions from `shared/cache/keys.py` that are now unreferenced.

- **Files**:
  - `shared/cache/ttl.py` — remove obsolete TTL constants
  - `shared/cache/keys.py` — remove obsolete key functions
- **Success**:
  - No references to the removed constants anywhere in the codebase
  - All tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 56–65) — existing TTL constants targeted for removal
- **Dependencies**:
  - Task 5.1 must be complete

### Task 5.3: Drop user_display_names Table

Create an Alembic migration to DROP the `user_display_names` table. Delete `shared/models/user_display_name.py` and `shared/services/user_display_names.py`. Verify no remaining callers before applying the migration.

- **Files**:
  - `alembic/versions/<new_migration>.py` — DROP TABLE migration
  - `shared/models/user_display_name.py` — deleted
  - `shared/services/user_display_names.py` — deleted
- **Success**:
  - Migration applies cleanly in CI
  - No references to `UserDisplayNameService` or `user_display_names` table remain
  - All tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 108–117) — `user_display_names` becomes dead code
- **Dependencies**:
  - Task 5.1 must be complete

## Phase 6: Redis ACL Enforcement

### Task 6.1: Create API Read-Only Redis User

Once the API has zero Redis writes, create a dedicated read-only ACL user for the API in the Redis/Valkey configuration. The bot retains the full-access credential. Update the API service environment to use the restricted credential.

ACL rule (from research):

```
ACL SETUSER api-reader on >api-password ~* &* +@read +subscribe +psubscribe -@write nocommands +get +mget +hgetall +lrange +smembers +subscribe +psubscribe
```

- **Files**:
  - Redis/Valkey config or Docker Compose config — add ACL rule
  - API service environment — update Redis credential
- **Success**:
  - API `SET` commands return `NOPERM` error
  - Bot writes succeed as before
  - Integration tests pass with the new credentials
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 315–330) — Redis ACL enforcement
- **Dependencies**:
  - Phase 5 must be complete

## Phase 7: Bot REST Elimination

### Task 7.1: Audit and Eliminate Remaining Bot REST Calls

With `Intents.members = True`, audit all `discord_api.*` calls in the bot. Replace every call that has a discord.py gateway equivalent with client cache reads. Any surviving REST calls must have explicit written justification (e.g. message/channel operations with no gateway equivalent).

- **Files**:
  - All files under `services/bot/` with `discord_api.` calls — modified as needed
- **Success**:
  - Every `discord_api.*` call is either eliminated or has documented justification
  - All unit and integration tests pass
- **Research References**:
  - #file:../research/20260417-01-gateway-intent-redis-projection-research.md (Lines 330–340) — step 13 rationale
- **Dependencies**:
  - Task 1.1 must be complete; Phase 6 must be complete

## Dependencies

- discord.py `Intents.members` privileged intent (Discord Developer Portal toggle required)
- Redis keyspace notifications enabled (`notify-keyspace-events Kg$` or equivalent)
- RabbitMQ topic exchange (already present via `EventPublisher`)
- Python `redis-py` asyncio client (already in use)

## Success Criteria

- `verify_guild_membership` fires zero OAuth REST calls per request after full migration
- `list_games` display name resolution reads only from Redis; no Discord API calls in the hot path
- Bot reconnect does not cause the API to serve mixed-generation data
- First login completes within the on-demand populate timeout under normal conditions
- `bot:last_seen` absence causes a clear degraded response, not a silent error or hang
- All steps pass the full unit + integration test suite before merging
- Zero Discord REST calls from the API server, verified by grep audit
