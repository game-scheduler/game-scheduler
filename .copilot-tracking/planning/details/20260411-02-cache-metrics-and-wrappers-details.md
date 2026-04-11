<!-- markdownlint-disable-file -->

# Task Details: Cache Metrics and Read-Through Wrapper Consolidation

## Research Reference

**Source Research**: #file:../research/20260411-02-cache-metrics-and-wrappers-research.md

---

## Phase 1: Create `shared/cache/operations.py`

### Task 1.1: Write failing unit tests for `CacheOperation` and `cache_get`

Write `xfail` unit tests verifying `CacheOperation` is a `StrEnum` with the expected members and that `cache_get` records hit/miss counters and latency.

- **Files**:
  - `tests/unit/shared/cache/test_operations.py` — new file
- **Test cases to write (xfail)**:
  - `CacheOperation` is a `StrEnum`
  - `CacheOperation.FETCH_GUILD == "fetch_guild"` and all 15 members exist
  - `cache_get` returns value on hit and records `cache.hits` counter
  - `cache_get` returns `None` on miss and records `cache.misses` counter
  - `cache_get` records `cache.duration` histogram for both hit and miss
  - `cache_get` passes `operation` as label on all metric calls
- **Success**:
  - All tests show `xfail` before implementation
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 92-115) — `CacheOperation` StrEnum values
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 162-182) — `cache_get` signature and metric calls
- **Dependencies**:
  - None

### Task 1.2: Implement `shared/cache/operations.py`

Create `shared/cache/operations.py` with `CacheOperation` StrEnum, module-level OTel meters, and `cache_get` coroutine.

- **Files**:
  - `shared/cache/operations.py` — new file
- **Implementation details**:
  - `CacheOperation(StrEnum)` with all 15 values from research
  - Module-level meters via `metrics.get_meter(__name__)`
  - `_hit_counter = meter.create_counter("cache.hits", description="Cache hits", unit="1")`
  - `_miss_counter = meter.create_counter("cache.misses", description="Cache misses", unit="1")`
  - `_duration_histogram = meter.create_histogram("cache.duration", unit="s")`
  - `async def cache_get(key: str, operation: CacheOperation) -> Any | None:`
    - calls `redis.get_json(key)`, records hit/miss counter and duration histogram, returns result
  - Import: `from shared.cache.client import get_redis_client`
- **Success**:
  - `xfail` tests from Task 1.1 pass; remove `xfail` markers
  - `RedisClient` has no metrics imports
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 92-115) — `CacheOperation` StrEnum
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 162-182) — `cache_get` full implementation
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 49-56) — OTel meter convention (`metrics.get_meter(__name__)`)
- **Dependencies**:
  - Task 1.1 tests must exist first

---

## Phase 2: Add `_get_or_fetch` to `DiscordAPIClient`

### Task 2.1: Write failing unit tests for `_get_or_fetch`

Write `xfail` unit tests verifying `_get_or_fetch` records `discord.cache.hits` / `discord.cache.misses` counters and `discord.cache.duration` histogram correctly.

- **Files**:
  - `tests/unit/shared/discord/test_discord_api_client.py` — existing file; add to `TestDiscordAPIClientHelpers` class or create new class
- **Test cases to write (xfail)**:
  - Returns cached value on hit; records `discord.cache.hits` with `operation` label
  - Calls `fetch_fn` on miss; records `discord.cache.misses` with `operation` label
  - Writes result to Redis after miss
  - Records `discord.cache.duration` for both hit and miss paths
- **Success**:
  - All tests show `xfail` before implementation
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 119-160) — `_get_or_fetch` signature and metric calls
- **Dependencies**:
  - Phase 1 complete (`CacheOperation` must exist for the `operation` parameter)

### Task 2.2: Add OTel meters and `_get_or_fetch` to `shared/discord/client.py`

Add three module-level OTel metrics and the `_get_or_fetch` instance method to `DiscordAPIClient`.

- **Files**:
  - `shared/discord/client.py` — add module-level meters and `_get_or_fetch` method
- **Implementation details**:
  - Add after existing imports: `import time` and `from opentelemetry import metrics`
  - Add `from shared.cache.operations import CacheOperation`
  - Module-level meters:
    ```python
    _cache_meter = metrics.get_meter(__name__)
    _cache_hit_counter = _cache_meter.create_counter("discord.cache.hits", ...)
    _cache_miss_counter = _cache_meter.create_counter("discord.cache.misses", ...)
    _cache_duration_histogram = _cache_meter.create_histogram("discord.cache.duration", ...)
    ```
  - `_get_or_fetch(self, cache_key, cache_ttl, fetch_fn, operation)` method per research spec
- **Success**:
  - `xfail` tests from Task 2.1 pass; remove `xfail` markers
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 119-160) — full `_get_or_fetch` implementation
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 49-56) — OTel meter convention
- **Dependencies**:
  - Task 2.1 tests must exist first
  - Phase 1 complete

---

## Phase 3: Replace Copy-Pasted Read-Through Sites

### Task 3.1: Write failing unit tests asserting `_get_or_fetch` is used at all 7 sites

Write `xfail` unit tests verifying that each of the 7 non-locking read-through methods in `DiscordAPIClient` delegates to `_get_or_fetch` instead of directly calling `redis.get`.

- **Files**:
  - `tests/unit/shared/discord/test_discord_api_client.py` — existing file; extend existing test classes
- **Test cases to write (xfail)** — one per method:
  - `fetch_guild` does not call `redis.get` directly
  - `fetch_channel` does not call `redis.get` directly
  - `fetch_guild_roles` does not call `redis.get` directly
  - `fetch_guild_channels` does not call `redis.get` directly
  - `fetch_user` does not call `redis.get` directly
  - `get_application_info` does not call `redis.get` directly
  - `get_user_guilds` does not call `redis.get` directly
- **Success**:
  - All tests show `xfail` before refactor
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 7-38) — list of read sites and their line numbers
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Replace 7 copy-pasted read-through blocks in `discord/client.py` with `_get_or_fetch`

For each of the 7 non-locking read-through methods, replace the `redis.get` / `if cached: return json.loads` / fetch / `redis.set` block with a single `_get_or_fetch` call.

- **Files**:
  - `shared/discord/client.py` — 7 method bodies modified
- **Pattern to replace** (in each method):
  ```python
  cached = await redis.get(cache_key)
  if cached:
      return json.loads(cached)
  result = await self._make_api_request(...)
  await redis.set(cache_key, json.dumps(result), ttl=...)
  return result
  ```
  Replaced with:
  ```python
  return await self._get_or_fetch(
      cache_key, cache_ttl, lambda: self._make_api_request(...), CacheOperation.XXX
  )
  ```
- **Methods**: `fetch_guild`, `fetch_channel`, `fetch_guild_roles`, `fetch_guild_channels`, `fetch_user`, `get_application_info`, `get_user_guilds`
- **Success**:
  - `xfail` tests from Task 3.1 pass; remove `xfail` markers
  - No bare `redis.get` + `json.loads` block remains in these 7 methods
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 59-75) — Pattern 1 description
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 119-160) — `_get_or_fetch` spec
- **Dependencies**:
  - Task 3.1 tests must exist first

### Task 3.3: Fix `get_guilds` inner slow-path to use `_get_or_fetch`; leave pre-lock read raw

In `get_guilds`, keep the pre-lock fast-path `redis.get` as a raw call (no metrics). Replace only the inner slow-path (after lock acquisition) with `_get_or_fetch`.

- **Files**:
  - `shared/discord/client.py` — `get_guilds` method
- **Implementation details**:
  - Pre-lock: `cached = await redis.get(key)` — unchanged, no metrics, no `_get_or_fetch`
  - Inner slow-path after lock: replace the second `redis.get` / fetch / `redis.set` block with `_get_or_fetch`
  - Use `CacheOperation.GET_USER_GUILDS` (or a dedicated `GET_GUILDS` value if needed)
- **Success**:
  - `get_guilds` pre-lock path makes no metric calls
  - `get_guilds` slow-path increments counters exactly once per logical miss
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 76-87) — double-counting trap explanation
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 7-38) — `get_guilds` double-checked locking site
- **Dependencies**:
  - Task 3.2 complete

---

## Phase 4: Replace Existence-Lookup Reads with `cache_get`

### Task 4.1: Write failing unit tests for `cache_get` usage at each existence-lookup site

Write `xfail` unit tests verifying each existence-lookup call site does not call `redis.get` / `redis.get_json` directly. One test per site, six sites total.

- **Files**:
  - `tests/unit/services/api/auth/test_tokens.py` — existing; add 2 tests
  - `tests/unit/services/api/auth/test_oauth2.py` — existing; add 1 test
  - `tests/unit/services/api/auth/test_roles.py` — existing; add 1 test
  - `tests/unit/services/api/services/test_display_names.py` — existing; add 2 tests
  - `tests/unit/services/bot/auth/test_cache.py` — existing; add 2 tests
- **Test cases (xfail)**:
  - `get_user_tokens` does not call `redis.get` directly
  - `refresh_user_tokens` does not call `redis.get` directly
  - `validate_and_consume_oauth_state` does not call `redis.get` directly
  - `get_user_role_ids` does not call `redis.get_json` directly
  - `_check_cache_for_display_names` does not call `redis.get_json` directly
  - `_check_cache_for_users` does not call `redis.get_json` directly
  - `get_user_roles` does not call `redis.get` directly
  - `get_guild_roles` does not call `redis.get` directly
- **Success**:
  - All tests show `xfail` before refactor
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 7-38) — existence-lookup sites list
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 59-75) — Pattern 3 description
- **Dependencies**:
  - Phase 1 complete (`cache_get` must exist)

### Task 4.2: Replace existence-lookup reads in all five files with `cache_get`

Import and call `cache_get` with the appropriate `CacheOperation` value at each of the eight existence-lookup sites.

- **Files**:
  - `services/api/auth/tokens.py` — 2 sites
  - `services/api/auth/oauth2.py` — 1 site
  - `services/api/auth/roles.py` — 1 site
  - `services/api/services/display_names.py` — 2 sites
  - `services/bot/auth/cache.py` — 2 sites
- **Pattern to replace**:
  ```python
  cached = await redis.get(key)   # or redis.get_json(key)
  if cached:
      return json.loads(cached)   # where applicable
  ```
  Replaced with:
  ```python
  cached = await cache_get(key, CacheOperation.SESSION_LOOKUP)  # use correct operation value
  if cached:
      return cached
  ```
- **Operation mapping**:
  - `tokens.py` `get_user_tokens` → `CacheOperation.SESSION_LOOKUP`
  - `tokens.py` `refresh_user_tokens` → `CacheOperation.SESSION_REFRESH`
  - `oauth2.py` `validate_and_consume_oauth_state` → `CacheOperation.OAUTH_STATE`
  - `roles.py` `get_user_role_ids` → `CacheOperation.USER_ROLES_API`
  - `display_names.py` `_check_cache_for_display_names` → `CacheOperation.DISPLAY_NAME`
  - `display_names.py` `_check_cache_for_users` → `CacheOperation.DISPLAY_NAME_AVATAR`
  - `bot/auth/cache.py` `get_user_roles` → `CacheOperation.USER_ROLES_BOT`
  - `bot/auth/cache.py` `get_guild_roles` → `CacheOperation.GUILD_ROLES_BOT`
- **Success**:
  - `xfail` tests from Task 4.1 pass; remove `xfail` markers
  - No bare `redis.get` / `redis.get_json` remains at existence-lookup sites
- **Research References**:
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 92-115) — `CacheOperation` values
  - #file:../research/20260411-02-cache-metrics-and-wrappers-research.md (Lines 162-182) — `cache_get` signature
- **Dependencies**:
  - Task 4.1 tests must exist first

---

## Dependencies

- `opentelemetry-api` already installed
- `time` stdlib
- `shared/cache/client.py` `get_redis_client` already exists

## Success Criteria

- No bare `redis.get` + `json.loads` pattern remains in `shared/discord/client.py`
- All existence-lookup call sites use `cache_get`
- `RedisClient` has zero metrics imports
- `CacheOperation` covers all 15 operation names
- Six OTel metrics produced: `discord.cache.hits`, `discord.cache.misses`, `discord.cache.duration`, `cache.hits`, `cache.misses`, `cache.duration`
- All existing and new unit tests pass
