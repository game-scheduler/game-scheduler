<!-- markdownlint-disable-file -->

# Task Research Notes: Cache Metrics and Read-Through Wrapper Consolidation

## Research Executed

### File Analysis

- `shared/cache/client.py`
  - `RedisClient` class: `get`, `set`, `get_json`, `set_json`, `delete`, `exists`, `expire`, `ttl`, `claim_global_slot`, `claim_global_and_channel_slot` — clean low-level I/O wrapper; zero metrics knowledge today
  - Global singleton via `get_redis_client()`

- `shared/discord/client.py`
  - 9 explicit cache read sites (lines 310, 387, 400, 562, 620, 675, 709, 757, 791)
  - 7 follow identical pattern: `cached = await redis.get(key)` then `if cached: return json.loads(cached)` then fetch then `await redis.set(key, json.dumps(result), ttl=...)`
  - `get_guilds` (lines 387-407): double-checked locking variant — pre-lock fast-path read, same pattern inside the lock
  - `_make_api_request`: writes to cache on success but does NOT check on entry — callers do the read before calling it

- `services/api/auth/tokens.py`
  - 2 existence lookup reads (`get_user_tokens`, `refresh_user_tokens`) — miss means session expired, no fallback fetch
  - 2 writes, 1 delete

- `services/api/auth/oauth2.py`
  - 1 existence lookup read (`validate_and_consume_oauth_state`) — miss means invalid/expired state token
  - 1 write, 1 delete

- `services/api/auth/roles.py`
  - 1 read-through via `get_json`: `get_user_role_ids` — miss fetches from `discord_api.get_guild_member`

- `services/api/services/display_names.py`
  - 2 looped existence reads per batch (`_check_cache_for_display_names`, `_check_cache_for_users`)

- `services/bot/auth/cache.py`
  - 2 existence reads (`get_user_roles`, `get_guild_roles`) — miss returns None, caller decides whether to fetch

- `services/bot/bot.py`
  - 10 pure writes/deletes for gateway event handlers — no reads

### Code Search Results

- `meter.create_counter|meter.create_histogram|get_meter`
  - `services/bot/bot.py`: 5 sweep metrics (started, interrupted, messages_checked, deletions_detected, duration)
  - `services/retry/retry_daemon.py`: 4 retry metrics (processed, failed, dlq_depth, processing_duration)
  - Zero cache metrics anywhere in the codebase

- `cache_hit|cache_miss` in production code
  - Zero OTel metric calls; only `logger.debug("Cache hit for ...")` log statements

### Project Conventions

- OTel meter obtained via `metrics.get_meter(__name__)` at module level
- Counters: `meter.create_counter(name="service.domain.event", description=..., unit="1")`
- Histograms: `meter.create_histogram(name="service.domain.metric", description=..., unit="s")`
- `StrEnum` already used in `shared/models/` — established convention in this codebase
- `shared/telemetry.py` initialises `MeterProvider` with OTLP export every 60s; no special setup needed in callers

## Key Discoveries

### Three Distinct Cache Access Patterns

**Pattern 1 — Read-through**

- Check Redis -> on hit return immediately -> on miss fetch from upstream -> write to Redis -> return
- 9 sites in `discord/client.py`, 1 in `roles.py`, 2 loops in `display_names.py`
- The 7 non-locking sites in `discord/client.py` are copy-pasted byte-for-byte

**Pattern 2 — Double-checked locking (`get_guilds` only)**

- Pre-lock fast-path read (intentional — avoids lock acquisition cost on hit)
- Acquire per-user lock -> check cache again -> fetch -> write
- The inner section after lock acquisition is exactly Pattern 1

**Pattern 3 — Existence lookup**

- Check Redis -> on hit return value -> on miss return None or raise
- No upstream fetch; miss is a terminal condition (expired session, invalid state)
- Sites: `tokens.py` (x2), `oauth2.py` (x1), `bot/auth/cache.py` (x2)

### Why `RedisClient.get()` Instrumentation Causes Double-Counting

If `RedisClient.get()` is instrumented and `_get_or_fetch` also records metrics, every read-through lookup produces two increments per logical cache read. Metrics must live at exactly one layer.

### Why Domain-Layer Instrumentation Is Correct

`RedisClient` is a transport. It has no knowledge of what a key represents or what a miss means. Operation names (`"fetch_guild"`, `"session_lookup"`) only exist at the domain layer. Instrumenting `RedisClient` requires either no labels or key-string parsing — both are wrong.

### Double-Counting Trap for `get_guilds` Pre-Lock Read

The pre-lock fast-path `redis.get` in `get_guilds` must remain a raw call and must NOT be instrumented — if it hits, `_get_or_fetch` is never called, so there is no double-count. If it misses, `_get_or_fetch` will do its own read inside the lock and record that. The pre-lock read is an optimistic short-circuit, not a counted cache operation.

## Recommended Approach

Two domain-layer wrappers plus one `StrEnum`. `RedisClient` unchanged.

### `CacheOperation` StrEnum in `shared/cache/operations.py` (new file)

```python
from enum import StrEnum

class CacheOperation(StrEnum):
    # Discord API read-through caches
    FETCH_GUILD            = "fetch_guild"
    FETCH_CHANNEL          = "fetch_channel"
    FETCH_GUILD_ROLES      = "fetch_guild_roles"
    FETCH_GUILD_CHANNELS   = "fetch_guild_channels"
    FETCH_USER             = "fetch_user"
    GET_GUILD_MEMBER       = "get_guild_member"
    GET_APPLICATION_INFO   = "get_application_info"
    GET_USER_GUILDS        = "get_user_guilds"
    # API service read-through caches
    USER_ROLES_API         = "user_roles_api"
    DISPLAY_NAME           = "display_name"
    DISPLAY_NAME_AVATAR    = "display_name_avatar"
    # Existence lookups
    SESSION_LOOKUP         = "session_lookup"
    SESSION_REFRESH        = "session_refresh"
    OAUTH_STATE            = "oauth_state"
    USER_ROLES_BOT         = "user_roles_bot"
    GUILD_ROLES_BOT        = "guild_roles_bot"
```

### Wrapper 1 — `_get_or_fetch` method on `DiscordAPIClient`

Replaces the 7 copy-pasted read-through sites (all except `get_guilds` pre-lock fast-path).

```python
async def _get_or_fetch(
    self,
    cache_key: str,
    cache_ttl: int | None,
    fetch_fn: Callable[[], Awaitable[dict[str, Any]]],
    operation: CacheOperation,
) -> dict[str, Any]:
    redis = await cache_client.get_redis_client()
    t0 = time.monotonic()
    cached = await redis.get(cache_key)
    if cached:
        _cache_hit_counter.add(1, {"operation": operation})
        _cache_duration_histogram.record(time.monotonic() - t0, {"operation": operation, "result": "hit"})
        return json.loads(cached)
    _cache_miss_counter.add(1, {"operation": operation})
    result = await fetch_fn()
    await redis.set(cache_key, json.dumps(result), ttl=cache_ttl)
    _cache_duration_histogram.record(time.monotonic() - t0, {"operation": operation, "result": "miss"})
    return result
```

Module-level meters in `shared/discord/client.py`:

```python
_cache_meter = metrics.get_meter(__name__)
_cache_hit_counter = _cache_meter.create_counter(
    "discord.cache.hits", description="Discord API cache hits", unit="1"
)
_cache_miss_counter = _cache_meter.create_counter(
    "discord.cache.misses", description="Discord API cache misses", unit="1"
)
_cache_duration_histogram = _cache_meter.create_histogram(
    "discord.cache.duration", description="Time from cache read to result (hit or fetch)", unit="s"
)
```

`get_guilds` handling: pre-lock fast-path read stays as raw `redis.get` (no metrics, intentional). Inner slow-path after lock acquisition calls `_get_or_fetch`.

### Wrapper 2 — `cache_get` function in `shared/cache/operations.py`

Replaces bare `redis.get` / `redis.get_json` existence lookup reads in `tokens.py`, `oauth2.py`, `roles.py`, `display_names.py`, `bot/auth/cache.py`.

```python
_meter = metrics.get_meter(__name__)
_hit_counter = _meter.create_counter("cache.hits", description="Cache hits", unit="1")
_miss_counter = _meter.create_counter("cache.misses", description="Cache misses", unit="1")
_duration_histogram = _meter.create_histogram("cache.duration", unit="s")

async def cache_get(key: str, operation: CacheOperation) -> Any | None:
    redis = await get_redis_client()
    t0 = time.monotonic()
    result = await redis.get_json(key)
    hit = result is not None
    (  _hit_counter if hit else _miss_counter).add(1, {"operation": operation})
    _duration_histogram.record(
        time.monotonic() - t0, {"operation": operation, "result": "hit" if hit else "miss"}
    )
    return result
```

### Metric names produced

| Metric                   | Type          | Labels                           |
| ------------------------ | ------------- | -------------------------------- |
| `discord.cache.hits`     | Counter       | `operation`                      |
| `discord.cache.misses`   | Counter       | `operation`                      |
| `discord.cache.duration` | Histogram (s) | `operation`, `result` (hit/miss) |
| `cache.hits`             | Counter       | `operation`                      |
| `cache.misses`           | Counter       | `operation`                      |
| `cache.duration`         | Histogram (s) | `operation`, `result`            |

### What is NOT instrumented (intentional)

- `redis.set` / `redis.set_json` — writes; no hit/miss concept
- `redis.delete` — cache invalidations from gateway events; not reads
- `get_guilds` pre-lock fast-path `redis.get` — optimistic short-circuit, not a domain operation
- `RedisClient` Lua rate-limit scripts — not cache operations

## Implementation Guidance

- **Objectives**: eliminate copy-pasted read-through pattern in `discord/client.py`; add per-operation hit/miss counters and latency histograms for every cache read
- **Key Tasks**:
  1. Create `shared/cache/operations.py` with `CacheOperation` StrEnum, `cache_get`, and its module-level OTel meters
  2. Add module-level OTel meters to `shared/discord/client.py`; add `_get_or_fetch` to `DiscordAPIClient`
  3. Replace 7 copy-pasted read-through sites in `discord/client.py` with `_get_or_fetch`
  4. Leave `get_guilds` pre-lock fast-path as raw `redis.get`; use `_get_or_fetch` for the inner slow-path
  5. Replace existence lookup reads in `tokens.py`, `oauth2.py`, `roles.py`, `display_names.py`, `bot/auth/cache.py` with `cache_get`
  6. Update affected unit tests: cache_hit/cache_miss tests in `test_discord_api_client.py` currently patch `redis.get` directly; after the change they patch `_get_or_fetch` or assert on counter mocks
- **Dependencies**: `opentelemetry-api` already installed; `time` stdlib; no new packages needed
- **Success Criteria**:
  - No bare `redis.get` + `json.loads` pattern remains in `discord/client.py`
  - All existence lookup sites use `cache_get`
  - `RedisClient` has zero metrics imports
  - `discord.cache.hits{operation="fetch_guild"}` and `cache.misses{operation="session_lookup"}` visible in Grafana Mimir after deployment
  - All existing unit tests pass
