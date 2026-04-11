<!-- markdownlint-disable-file -->

# Task Details: Gateway-Driven Cache Enhancement

## Research Reference

**Source Research**: #file:../research/20260410-01-gateway-cache-enhancement-research.md

---

## Phase 1: on_ready Redis Cache Rebuild

### Task 1.1: Write failing unit tests for on_ready cache rebuild

Create stub + `xfail` unit tests verifying the `on_ready` handler writes channel, guild,
channel-list, and role-list data into Redis from `self.guilds`.

- **Files**:
  - `tests/unit/bot/test_bot_ready.py` — new test file
- **Test cases to write (xfail)**:
  - `on_ready` writes `discord:channel:{id}` for every channel in every guild
  - `on_ready` writes `discord:guild:{id}` with `{"id": ..., "name": ...}` for every guild
  - `on_ready` writes `discord:guild_channels:{id}` list for every guild
  - `on_ready` writes `discord:guild_roles:{id}` list for every guild
  - Role dict shape: `{"id": str(role.id), "name": ..., "color": role.color.value, "position": ..., "managed": ...}`
- **Success**:
  - All tests show `xfail` before implementation
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 64-97) — on_ready rebuild design and role dict shape
- **Dependencies**:
  - None

### Task 1.2: Implement on_ready Redis rebuild in bot.py

In `bot.py`'s `on_ready` event handler, loop over `self.guilds` and write all channel
and role data to Redis without any REST calls.

- **Files**:
  - `services/bot/bot.py` — update `on_ready` handler
- **Implementation details**:
  - Loop `for guild in self.guilds:`
  - Write `discord:guild:{guild.id}`: `{"id": str(guild.id), "name": guild.name}`
  - Write `discord:guild_channels:{guild.id}`: list of `{"id": str(c.id), "name": c.name, "type": c.type.value}` per channel
  - Write each `discord:channel:{channel.id}`: `{"name": channel.name}` per channel
  - Write `discord:guild_roles:{guild.id}`: list of role dicts per guild
  - Role dict shape: `{"id": str(r.id), "name": r.name, "color": r.color.value, "position": r.position, "managed": r.managed}`
  - Use `shared/cache/keys.py` constants for key names
  - Use `shared/cache/ttl.py` TTL constants (later set to `None` in Phase 5)
- **Success**:
  - xfail tests from Task 1.1 pass; remove `xfail` markers
  - No REST calls to Discord during `on_ready` cache population
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 64-97) — cache key shapes and field mapping
- **Dependencies**:
  - Task 1.1 tests must exist first

---

## Phase 2: role_checker.py — Use In-Memory Cache

### Task 2.1: Write failing unit tests for get_guild() usage

Write unit tests (marked `xfail`) verifying each of the five methods in `role_checker.py`
does not call `self.bot.fetch_guild()` (REST).

- **Files**:
  - `tests/unit/services/bot/auth/test_role_checker.py` — existing test file
- **Test cases to write (xfail)**:
  - `get_user_role_ids` does not call `fetch_guild`
  - `get_guild_roles` does not call `fetch_guild`
  - `check_manage_guild_permission` does not call `fetch_guild`
  - `check_manage_channels_permission` does not call `fetch_guild`
  - `check_administrator_permission` does not call `fetch_guild`
  - `check_game_host_permission` does not call `fetch_guild`
- **Success**:
  - All tests show `xfail` before the change
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 16-20) — fetch_guild call locations in role_checker
- **Dependencies**:
  - Phase 1 complete (in-memory cache populated on startup)

### Task 2.2: Replace fetch_guild() with get_guild() in role_checker.py

In all five methods (`get_user_role_ids`, `get_guild_roles`, `check_manage_guild_permission`,
`check_manage_channels_permission`, `check_administrator_permission`, `check_game_host_permission`),
replace `await self.bot.fetch_guild(guild_id)` with `self.bot.get_guild(guild_id)`.

- **Files**:
  - `services/bot/auth/role_checker.py` — lines 78, 114, 151, 177, 203
- **Implementation details**:
  - `get_guild()` is synchronous; remove any `await` before the call
  - If `guild` is `None`, the bot has left the guild — same condition as `NotFound` from `fetch_guild`; existing error handling is appropriate
- **Success**:
  - xfail tests from Task 2.1 now pass; remove markers
  - No REST calls to `fetch_guild` during role checks
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 16-20, 115-119) — call locations and in-memory cache rationale
- **Dependencies**:
  - Task 2.1 tests

---

## Phase 3: Remove Redundant fetch_channel in handlers.py

### Task 3.1: Write failing unit tests for \_validate_discord_channel

Write unit tests (marked `xfail`) verifying `_validate_discord_channel` in `handlers.py`
does not call `discord_api.fetch_channel()` and uses `self.bot.get_channel()` directly.

- **Files**:
  - `tests/unit/bot/events/test_handlers_lifecycle_events.py` — existing test file
- **Test cases to write (xfail)**:
  - `_validate_discord_channel` does not call `discord_api.fetch_channel`
  - Returns `None` (or equivalent failure) when `get_channel()` returns `None`
  - Returns the channel object when `get_channel()` returns a valid channel
- **Success**:
  - Tests show `xfail` before implementation
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 24-30) — redundant fetch_channel analysis
- **Dependencies**:
  - Phase 1 complete

### Task 3.2: Remove redundant fetch_channel call in handlers.py

Replace the body of `_validate_discord_channel` (line 189 in `handlers.py`) to use
`self.bot.get_channel()` directly, removing the `discord_api.fetch_channel()` pre-check.

- **Files**:
  - `services/bot/events/handlers.py` — `_validate_discord_channel` at line 189
- **Implementation details**:
  - Use `self.bot.get_channel(channel_id)` as the sole lookup
  - `None` return from `get_channel()` already signals inaccessibility
  - Follow the pattern already used in `_get_bot_channel` in the same file
- **Success**:
  - xfail tests from Task 3.1 pass; remove markers
  - `handlers.py` no longer calls `discord_api.fetch_channel` in `_validate_discord_channel`
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 24-30) — handlers.py analysis
- **Dependencies**:
  - Task 3.1 tests

---

## Phase 4: Gateway Event Handlers

### Task 4.1: Write failing unit tests for gateway event handlers

Write unit tests (marked `xfail`) for all six new event handlers verifying they correctly
write/invalidate Redis keys on Discord gateway events.

- **Files**:
  - `tests/unit/bot/test_bot_events.py` — new test file
- **Test cases to write (xfail)**:
  - `on_guild_channel_create`: writes `discord:channel:{id}` and invalidates `discord:guild_channels:{guild_id}`
  - `on_guild_channel_update`: updates `discord:channel:{id}` and invalidates `discord:guild_channels:{guild_id}`
  - `on_guild_channel_delete`: deletes `discord:channel:{id}` and invalidates `discord:guild_channels:{guild_id}`
  - `on_guild_role_create`: invalidates `discord:guild_roles:{guild_id}`
  - `on_guild_role_update`: invalidates `discord:guild_roles:{guild_id}`
  - `on_guild_role_delete`: invalidates `discord:guild_roles:{guild_id}`
- **Success**:
  - All tests show `xfail` before implementation
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 89-110) — gateway event invalidation design
- **Dependencies**:
  - Phase 1 complete

### Task 4.2: Implement channel event handlers in bot.py

Add `on_guild_channel_create`, `on_guild_channel_update`, `on_guild_channel_delete`
event handlers to `bot.py`.

- **Files**:
  - `services/bot/bot.py` — add three new channel event handler methods
- **Implementation details**:
  - `on_guild_channel_create(channel)`: write `discord:channel:{channel.id}` → `{"name": channel.name}`; delete `discord:guild_channels:{channel.guild.id}`
  - `on_guild_channel_update(before, after)`: write `discord:channel:{after.id}` → `{"name": after.name}`; delete `discord:guild_channels:{after.guild.id}`
  - `on_guild_channel_delete(channel)`: delete `discord:channel:{channel.id}`; delete `discord:guild_channels:{channel.guild.id}`
  - Use `shared/cache/keys.py` constants for key names
- **Success**:
  - xfail channel tests from Task 4.1 pass; remove markers
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 89-105) — channel event design
- **Dependencies**:
  - Task 4.1 tests

### Task 4.3: Implement role event handlers in bot.py

Add `on_guild_role_create`, `on_guild_role_update`, `on_guild_role_delete` event handlers
to `bot.py`. Prefer cache key invalidation over read-modify-write to keep handler logic simple.

- **Files**:
  - `services/bot/bot.py` — add three new role event handler methods
- **Implementation details**:
  - `on_guild_role_create(role)` / `on_guild_role_update(before, after)`: invalidate `discord:guild_roles:{role.guild.id}` (let next `fetch_guild_roles` call rebuild from Discord)
  - `on_guild_role_delete(role)`: invalidate `discord:guild_roles:{role.guild.id}`
  - Use `shared/cache/keys.py` constants for key names
- **Success**:
  - xfail role tests from Task 4.1 pass; remove markers
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 100-110) — role event design
- **Dependencies**:
  - Task 4.1 tests

---

## Phase 5: Fix \_make_api_request Guard + Remove TTLs

### Task 5.1: Write failing unit test for \_make_api_request with cache_ttl=None

Write a unit test (marked `xfail`) verifying `_make_api_request` writes to Redis when
`cache_key` is set and `cache_ttl=None`. Currently the `if cache_key and cache_ttl:`
guard silently skips the write when TTL is `None`.

- **Files**:
  - `tests/unit/shared/discord/test_discord_api_client.py` — existing test file
- **Test cases**:
  - `xfail`: `_make_api_request` with `cache_key="key"` and `cache_ttl=None` writes result to Redis
  - `pass`: `_make_api_request` with `cache_key="key"` and `cache_ttl=300` writes to Redis (regression guard)
- **Success**:
  - First test shows `xfail`; second still passes before code change
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 106-115) — guard bug analysis
- **Dependencies**:
  - None

### Task 5.2: Fix \_make_api_request guard in shared/discord/client.py

Change line 240 of `shared/discord/client.py` from `if cache_key and cache_ttl:` to
`if cache_key:`. The `redis.set()` wrapper in `shared/cache/client.py` already handles
`ttl=None` via plain `SET` without `SETEX`.

- **Files**:
  - `shared/discord/client.py` — line 240
- **Success**:
  - xfail test from Task 5.1 now passes; remove marker
  - Regression test (TTL=300 path) still passes
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 106-115)
- **Dependencies**:
  - Task 5.1 test; Phase 4 complete

### Task 5.3: Set TTLs to None for gateway-maintained cache keys

In `shared/cache/ttl.py`, set `DISCORD_CHANNEL`, `DISCORD_GUILD`, `DISCORD_GUILD_CHANNELS`,
and `DISCORD_GUILD_ROLES` to `None` (no expiry). `DISCORD_MEMBER` retains its TTL since
member events require the privileged `GUILD_MEMBERS` intent.

- **Files**:
  - `shared/cache/ttl.py` — update four constants to `None`
- **Success**:
  - Channel/guild/role keys written to Redis with no expiry (no `SETEX`/`PSETEX`)
  - `DISCORD_MEMBER` (added in Phase 6) still expires on its TTL
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 106-115) — TTL removal rationale
- **Dependencies**:
  - Task 5.2 complete; Phase 4 complete

---

## Phase 6: get_guild_member Redis Caching

### Task 6.1: Write failing unit tests for get_guild_member caching

Write unit tests (marked `xfail`) verifying `get_guild_member` in `shared/discord/client.py`
caches its result using the `discord:member:{guild_id}:{user_id}` key.

- **Files**:
  - `tests/unit/shared/discord/test_discord_api_client.py` — existing test file
- **Test cases (xfail)**:
  - First call fetches from Discord API and stores result in Redis
  - Second call returns cached result without a Discord REST call
  - Cache key format: `discord:member:{guild_id}:{user_id}`
  - Cache TTL equals `DISCORD_MEMBER` from `ttl.py`
- **Success**:
  - Tests show `xfail` before implementation
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 36-40, 121-135) — get_guild_member caching design
- **Dependencies**:
  - None

### Task 6.2: Add discord_member cache key and TTL constant

Add `discord_member` to `shared/cache/keys.py` and `DISCORD_MEMBER = 300` to
`shared/cache/ttl.py`.

- **Files**:
  - `shared/cache/keys.py` — add `discord_member` key function
  - `shared/cache/ttl.py` — add `DISCORD_MEMBER = 300`
- **Success**:
  - Key constant and TTL importable by `shared/discord/client.py`
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 36-40) — no discord_member key exists yet
- **Dependencies**:
  - Task 6.1 tests

### Task 6.3: Add caching to get_guild_member in shared/discord/client.py

Wire `cache_key` and `cache_ttl` into the `_make_api_request` call inside `get_guild_member`.

- **Files**:
  - `shared/discord/client.py` — `get_guild_member` method
- **Implementation details**:
  - `cache_key = CacheKeys.discord_member(guild_id, user_id)` (or equivalent naming convention)
  - `cache_ttl = CacheTTL.DISCORD_MEMBER`
  - Follow the same pattern as `fetch_channel` and `fetch_guild` in the same file
- **Success**:
  - xfail tests from Task 6.1 now pass; remove markers
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 121-135)
- **Dependencies**:
  - Task 6.2 complete; Task 5.2 complete (guard fix required for None-TTL path)

### Task 6.4: Wire role_checker.get_user_role_ids to use get_guild_member

Replace the `fetch_guild()` + `fetch_member()` pattern in `get_user_role_ids` with a
single `DiscordAPIClient.get_guild_member()` call, collapsing two uncached REST calls
into one cached call.

- **Files**:
  - `services/bot/auth/role_checker.py` — `get_user_role_ids` method
- **Implementation details**:
  - Inject or access `DiscordAPIClient` within `RoleChecker` (currently unused)
  - Replace `guild.fetch_member(user_id)` with `await discord_api_client.get_guild_member(guild_id, user_id)`
  - Extract `roles` from the returned member dict (verify field name against Discord API response shape)
- **Success**:
  - `get_user_role_ids` issues at most one Discord API call per cache miss
  - Existing tests in `test_role_checker.py` still pass
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 16-22) — get_user_role_ids REST call analysis
- **Dependencies**:
  - Task 6.3 complete; Phase 2 complete

---

---

## Phase 7: E2E Gateway Cache Population Tests

### Task 7.1: Write e2e tests for startup cache population

Create `tests/e2e/test_gateway_cache_e2e.py` with four tests that read Redis directly
and assert all four key families written by `_rebuild_redis_from_gateway` are populated
correctly after bot startup.

- **Files**:
  - `tests/e2e/test_gateway_cache_e2e.py` — new file
- **Test cases**:
  - `test_startup_cache_guild_key_written`: reads `discord:guild:{guild_a_id}`; asserts it is a dict containing `id` and `name` fields
  - `test_startup_cache_guild_channels_key_written`: reads `discord:guild_channels:{guild_a_id}`; asserts it is a non-empty list; each item contains `id`, `name`, `type`
  - `test_startup_cache_channel_key_written`: reads `discord:channel:{channel_a_id}`; asserts it is a dict containing a `name` field
  - `test_startup_cache_guild_roles_key_written`: reads `discord:guild_roles:{guild_a_id}`; asserts it is a non-empty list; each item contains `id`, `name`, `color`, `position`, `managed`
- **Setup**:
  - File-level: `pytestmark = [pytest.mark.e2e, pytest.mark.order(1)]`
  - Use `discord_ids` fixture for `guild_a_id` and `channel_a_id`
  - Use `await cache_client.get_redis_client()` then `CacheKeys.*` to read keys — matches the pattern in `test_guild_sync_e2e.py`
  - No polling or waiting — `depends_on: bot: condition: service_healthy` guarantees `_rebuild_redis_from_gateway` completed before any e2e test runs
- **Success**:
  - All four tests pass against the live Redis instance in the e2e container
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 191-218) — e2e addendum Category 1 key assertions table
- **Dependencies**:
  - Phases 1–6 complete (bot must be writing the keys being asserted)
  - `discord_ids` fixture and `cache_client` already wired in `test_guild_sync_e2e.py` — reuse without changes

### Task 7.2: Write e2e test for known role ID in guild roles cache

Add one test to the same file asserting that `DISCORD_TEST_ROLE_A_ID` appears in the
`discord:guild_roles:{guild_a_id}` list written by `_rebuild_redis_from_gateway`. The
test must skip gracefully (not fail) when the env var is absent.

- **Files**:
  - `tests/e2e/test_gateway_cache_e2e.py` — same file as Task 7.1
- **Test case**:
  - `test_startup_cache_known_role_id_in_guild_roles`:
    - Read `DISCORD_TEST_ROLE_A_ID` from env; call `pytest.skip` if absent
    - Read `discord:guild_roles:{guild_a_id}` from Redis
    - Assert that the role ID appears in the list of `id` values from the cached role dicts
- **Success**:
  - Test passes when `DISCORD_TEST_ROLE_A_ID` is configured in the test environment
  - Test skips (not fails or errors) when the env var is absent
- **Research References**:
  - #file:../research/20260410-01-gateway-cache-enhancement-research.md (Lines 218-229) — e2e addendum Category 2 and skip pattern guidance
- **Dependencies**:
  - Task 7.1 complete (guild roles key must be confirmed populated before asserting its contents)
  - `DISCORD_TEST_ROLE_A_ID` already present in `compose.e2e.yaml` — same env var used by `test_role_based_signup.py`

---

## Dependencies

- discord.py (already a project dependency)
- Redis (already a project dependency)
- `shared/cache/keys.py` and `shared/cache/ttl.py` (already exist)
- `shared/discord/client.py` `DiscordAPIClient` (already exists)

## Success Criteria

- `on_ready` writes all channel/guild/role Redis keys from in-memory gateway cache without REST calls
- Gateway event handlers keep channel and role Redis keys current in real time
- `role_checker.py` uses `get_guild()` (in-memory) not `fetch_guild()` (REST)
- `get_guild_member` results are cached in Redis using `discord:member:{guild_id}:{user_id}`
- `discord:channel`, `discord:guild`, `discord:guild_channels`, `discord:guild_roles` keys have no TTL
- `discord:member` keys expire on `DISCORD_MEMBER` TTL
- `_validate_discord_channel` in `handlers.py` uses `get_channel()` only
- E2e tests in `test_gateway_cache_e2e.py` pass against the live Redis/bot instance
- All unit tests pass
