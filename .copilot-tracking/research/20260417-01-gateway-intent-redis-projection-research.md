<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Gateway Intent Redis Projection Architecture

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - Current `Intents`: `guilds=True, guild_messages=True` only — `members` intent NOT enabled
  - `on_ready` handler exists at line 180; calls `sync_all_bot_guilds` via `setup_hook`
  - No `on_member_update`, `on_member_add`, or `on_member_remove` handlers present

- `services/bot/guild_sync.py`
  - `sync_all_bot_guilds`: uses Discord REST `get_guilds` + `get_guild_channels` — not gateway data
  - Syncs DB guild/channel records; does not write member/role data to Redis

- `services/bot/auth/role_checker.py`
  - `RoleChecker.get_user_role_ids`: checks Redis first, then falls back to `discord_api.get_guild_member` (REST call via bot token)
  - Redis key: `user_roles:{user_id}:{guild_id}` (written by `login_refresh.py`)

- `services/api/services/login_refresh.py`
  - `refresh_display_name_on_login`: called as background task after OAuth callback
  - Calls `get_user_guilds` (OAuth REST), then `client.get_current_user_guild_member` per guild
  - Writes `user_roles:{uid}:{gid}` to Redis with `CacheTTL.USER_ROLES = 300` (5-min TTL)
  - Upserts `user_display_names` DB table via `UserDisplayNameService`

- `services/api/services/display_names.py`
  - `DisplayNameResolver`: on Redis miss, calls `discord_api.get_guild_members_batch` (REST)
  - Writes `display:{guild_id}:{user_id}` to Redis with `CacheTTL.DISPLAY_NAME = 300` (5-min TTL)
  - `_fetch_and_cache_display_names_avatars`: same pattern, `display_avatar:{guild_id}:{user_id}` key

- `services/api/dependencies/permissions.py`
  - `_get_user_guilds` / `_check_guild_membership`: call `oauth2.get_user_guilds` (OAuth REST) on every authorization check
  - `verify_guild_membership`: used as a FastAPI dependency; fires a REST call per route request

- `shared/cache/keys.py` / `shared/cache/ttl.py`
  - Existing keys used by old approach: `user_roles:{uid}:{gid}`, `display:{gid}:{uid}`, `display_avatar:{gid}:{uid}`, `discord_member:{gid}:{uid}`, `user_guilds:{uid}`
  - TTLs: `USER_ROLES=300`, `DISPLAY_NAME=300`, `DISCORD_MEMBER=300`, `USER_GUILDS=300`
  - New projection keys will use a distinct namespace — no collision with existing keys

- `shared/models/user_display_name.py` + `shared/services/user_display_names.py`
  - `user_display_names` DB table: `(user_discord_id, guild_discord_id)` PK, `display_name`, `avatar_url`, `updated_at`
  - `UserDisplayNameService.upsert_batch`: bulk INSERT ... ON CONFLICT DO UPDATE
  - Implemented as output of previous research (20260414-01); will become dead code under the new architecture once migration is complete

- `services/bot/message_refresh_listener.py`
  - Existing pattern for Postgres LISTEN/NOTIFY → bot action
  - Confirms the bot already has infrastructure for responding to external signals asynchronously

- `shared/messaging/events.py` + `shared/messaging/publisher.py`
  - Existing `EventType` enum + `EventPublisher` — topic exchange `game_scheduler`
  - Routing key = event type string; topic exchange allows new routing keys without schema changes
  - New `MEMBER_CACHE_POPULATE` event type slots in cleanly alongside existing events

### Code Search Results

- `on_ready` in `services/bot/bot.py`
  - Line 180: exists; currently only logs and calls `sync_all_bot_guilds`
  - No member iteration or Redis projection write present

- `user_roles` cache key
  - Written only in `login_refresh.py` (API service, TTL-based)
  - Read only in `role_checker.py` (bot service)
  - Both uses will be replaced by the new projection

- `get_guild_members_batch`
  - Called in `display_names.py` lines 116 and 215
  - The root-cause serial REST loop identified in previous performance research

- `get_user_guilds`
  - Called in `login_refresh.py`, `permissions.py` (×2), `database/queries.py`
  - All call sites make OAuth REST round-trips; `permissions.py` calls fire per-route

### External Research

- discord.py `on_ready` timing (verified in previous session)
  - Fires AFTER `_delay_ready()` completes member chunking when `chunk_guilds_at_startup=True` AND `Intents.members=True`
  - At `on_ready`, `guild.members` is fully populated for all guilds
  - Session resume (reconnect without IDENTIFY) does NOT re-fire `on_ready`; missed incremental events are possible during gap — covered by generation rebuild on resumed/reconnect

- Redis atomicity (verified via Redis docs)
  - `SET key value NX EX ttl`: atomic; exactly one concurrent caller wins; returns OK or nil
  - Single-threaded command execution: no MULTI/EXEC needed for single-key lock
  - Lua scripts: fully atomic, block all server activity during execution — available if multi-key atomicity needed

- `GUILD_MEMBERS` privileged intent
  - Enables: full member list in `GUILD_CREATE` on connect, real-time `GUILD_MEMBER_ADD/UPDATE/REMOVE` events
  - discord.py: `Intents.members = True` + optional `chunk_guilds_at_startup=True`
  - Portal toggle required; bot verification required only for 100+ server bots (not applicable here)

### Project Conventions

- Standards referenced: existing `EventPublisher` / `EventConsumer` patterns, `MessageRefreshListener` NOTIFY pattern, Redis key namespacing in `shared/cache/keys.py`
- TDD applicable: Python implementation — tests required before implementation
- Phased cutover: new Redis projection keys are distinct from existing TTL-cache keys; both can coexist during migration

## Key Discoveries

### Why the Previous Approach (DB Table + REST on Login) Is Now Superseded

See [docs/developer/guild-members-privileged-intent.md](../../../docs/developer/guild-members-privileged-intent.md) for the full rationale behind the `GUILD_MEMBERS` privileged intent requirement.

The `user_display_names` DB table and `login_refresh.py` background task were the output of the 20260414-01 research. They solve the cold-cache restart problem but do not eliminate the REST calls — they just pre-warm the DB. The rate-limit problem and per-route `get_user_guilds` calls remain. The gateway projection eliminates both at the source.

### Two Competing Write Paths Do Not Conflict

Existing keys (`user_roles:`, `display:`, `display_avatar:`, `user_guilds:`, `discord_member:`) all use short TTLs and are written by the API service. The new projection uses a new namespace (`proj:member:`, `proj:user_guilds:`, generation-scoped) and is written exclusively by the bot. No collision during the phased cutover.

### Phased Cutover Is Safe

Because the old and new cache namespaces are distinct, every API call site can be migrated independently. The system is always fully functional: before migration a call site uses the old REST path; after migration it reads from the projection. No big-bang cutover needed.

### What the `user_display_names` DB Table Becomes

Once all read sites are migrated to the Redis projection, writes to `user_display_names` become unnecessary. The table and `UserDisplayNameService` become dead code. They will be visible as dead code (no callers) after full migration — removable at that point with a DROP TABLE migration. No linter catches DB table orphaning, so this requires manual verification.

## Recommended Approach

### Architecture Summary

The bot is the sole writer of Discord member/role data into Redis. The API reads only from Redis — no Discord REST calls for member or role data. RabbitMQ carries one-way populate requests from API to bot; there is no RPC.

### Redis Projection Schema

```
proj:gen                               ← current generation pointer (UTC millisecond timestamp string, e.g. "1745000000000")
proj:member:{gen}:{guild_id}:{uid}     ← {roles: [...], nick: str, global_name: str, username: str, avatar_url: str}
proj:user_guilds:{gen}:{uid}           ← [guild_id, ...]  (guilds this user is in that the bot monitors)
proj:user:{gen}:{uid}:complete         ← "ready"  (per-user readiness marker; written last after all data keys)
bot:populate:{gen}:{uid}               ← "1" NX EX 30  (bot-side dedup lock; prevents duplicate populate work)
bot:last_seen                          ← UTC ISO timestamp, updated every N minutes by bot heartbeat
```

All projection keys under a generation have no TTL — they are maintained by gateway events and explicit bot writes. `bot:last_seen` has a TTL of (heartbeat_interval × 3) so the API can detect bot outage by key absence.

### Generation Bump on Connect / Reconnect

The bot does **not** pre-populate any member data on connect. All data is populated on demand (see On-Demand Populate Flow below).

On `on_ready` and on reconnect after session invalidation (missed gateway events possible):

1. Compute `new_gen = int(datetime.now(UTC).timestamp() * 1000)` (millisecond precision — eliminates same-second collision risk).
2. SCAN+DEL all keys matching `proj:*:{prev_gen}:*` (cleans up previous generation; any deletion order is safe — see Generation Retirement Strategy).
3. `SET proj:gen = new_gen`.
4. Write `bot:last_seen`.

The gen bump alone invalidates all previously cached data. Clients that next request any user will miss on the new gen, trigger `MEMBER_CACHE_POPULATE`, and data is populated on demand.

Incremental gateway events invalidate the current gen user data as they arrive — no gen bump for incremental updates:

- `on_member_update`: delete `proj:member:{gen}:{guild_id}:{uid}`, `proj:user_guilds:{gen}:{uid}`, and `proj:user:{gen}:{uid}:complete`. The user is demand-faulted back in on next API access with fresh data.
- `on_member_remove`: same deletion — remove all three keys.
- `on_member_add`: no-op — new members are demand-faulted in when the API first needs them.

Both `on_member_update` and `on_member_remove` use delete-all rather than update-in-place to preserve the complete marker contract: **the marker may only be set after all data keys are written in a single coherent sequence**. Updating a member key while leaving the marker set would allow the API to read partially-updated data without knowing the write is in progress. Deleting all keys (including the marker) forces a clean demand-fault cycle that re-establishes the invariant.

API always reads `proj:gen` first, then constructs all projection keys from it.

### Generation Retirement Strategy

Old generation keys may be deleted at any point **after `proj:gen` is flipped** — immediately after the flip, lazily, or via a background task. The current implementation deletes them immediately after flipping the generation (step 2 of the Generation Bump sequence above), but this is an implementation choice, not an architectural requirement.

**Why deletion order doesn't matter**: `proj:gen` has already flipped to the new gen before any client can observe missing old-gen keys. If a client reads a nil for a key under the old gen, it re-reads `proj:gen`, gets the new gen, and proceeds. It never re-constructs old-gen keys. Deletion order is irrelevant — the generation pointer is the invariant that makes the client recovery safe.

**Why no TTL-based retirement**: there is no safe upper bound on how long an in-flight API request may hold a gen value. The client-side retry loop (below) makes this a non-issue.

**Option not taken — delayed deletion**: a short sleep (e.g. 5–10s) after flipping `proj:gen` before running SCAN+DEL would cover virtually all in-flight requests (Redis reads complete in milliseconds) and reduce retry frequency for an already-rare event. Decided not worth the added complexity: bot reconnects are rare, the retry loop is the correct safety net regardless, and an `asyncio.sleep` in the reconnect handler adds noise for negligible practical gain.

### Per-User Completion Marker Contract

The single invariant: **`proj:user:{gen}:{uid}:complete = "ready"` is written last, after all `proj:member` and `proj:user_guilds` keys for that user are fully written**.

The marker is written only by the on-demand populate path (bot after handling `MEMBER_CACHE_POPULATE`). Incremental gateway events (`on_member_update`, `on_member_remove`) delete all keys including the marker — they never write `ready`.

The API waits on this key using Redis keyspace notifications (not polling — see below).

### On-Demand Populate Flow (First Login / Cache Miss)

When the API needs projection data for a user not yet in the current generation:

**API side** (unconditional — no branching, no dedup logic):

1. GET `proj:user:{gen}:{uid}:complete` — if `ready`, proceed immediately (common case; no subscription created).
2. Subscribe to keyspace notifications for `proj:user:{gen}:{uid}:complete`.
3. GET again — if `ready` now, unsubscribe and proceed (closed the TOCTOU window: bot wrote `ready` between step 1 and step 2).
4. Publish `MEMBER_CACHE_POPULATE` event to RabbitMQ with `{user_discord_id, guild_ids, gen}`.
5. Wait for keyspace notification that the complete key was set (with timeout).
6. On timeout: bot is down or slow — return degraded response (placeholder names / deny permission with friendly message).

**Bot side** (dedup lives here):

1. On receiving `MEMBER_CACHE_POPULATE`, check `proj:user:{gen}:{uid}:complete` — if `ready`, return immediately (data already present; API callers will see it on their next read).
2. Attempt `SET bot:populate:{gen}:{uid} 1 NX EX 30`.
3. If NX wins: write `proj:member` + `proj:user_guilds` keys, write `proj:user:{gen}:{uid}:complete = ready`, then **delete `bot:populate:{gen}:{uid}`**.
4. If NX loses: a concurrent handler is already doing the work — return immediately. The waiting API callers will be unblocked when the winner writes the complete marker.

The lock must be deleted immediately after writing `ready` (not left to expire). If left alive and `on_member_update` subsequently invalidates the complete marker, a fresh API request would publish a new `MEMBER_CACHE_POPULATE` — but the stale lock would cause the bot to discard it, leaving the API waiting for a `ready` that never arrives until the lock's TTL expires (up to 30s false timeout).

### Client Retry Loop (Generation Rotation During Wait)

If a client finds `complete = ready` but then reads nil for a member key (gen rotated between those two reads):

1. Re-read `proj:gen`.
2. Check `proj:user:{new_gen}:{uid}:complete`.
3. If not present: publish populate request for the new gen, subscribe and wait.
4. If `ready`: read data — proceed.

Bound to 3 attempts max. After exhausting retries, treat as bot-unavailable and return degraded response.

### Waiting for the Complete Marker (Redis Keyspace Notifications)

Rather than polling, the API blocks on a Redis pub/sub subscription. Redis publishes to `__keyevent@{db}__:set` whenever any key is written.

Required Redis configuration: `notify-keyspace-events` must include `K` (keyspace) and `g` (generic SET events) — e.g. `Kg$` or `KEA`.

Protocol (GET first for the common hit case; subscribe + re-check closes the TOCTOU window on miss):

```python
# 1. Fast path: check before touching the connection pool for pub/sub
if await redis.get(marker_key) == "ready":
    return  # already done — no subscription needed

# 2. Miss: subscribe before the second check to avoid missing the write
pubsub = redis.pubsub()
await pubsub.subscribe("__keyevent@0__:set")

# 3. Re-check: bot may have written ready between step 1 and step 2
if await redis.get(marker_key) == "ready":
    await pubsub.aclose()
    return  # raced in; no need to wait

# 4. Publish populate request, then block on notification (with timeout)
await publisher.publish(MEMBER_CACHE_POPULATE, {...})
async for message in pubsub.listen():
    if message["data"] == marker_key:
        break  # bot wrote the complete marker
```

Implementation notes:

- **Per-request, pool-backed**: each cache-miss calls `redis_singleton._client.pubsub()`, which borrows one connection from the existing `ConnectionPool` (max 100 connections, shared with regular commands). No new TCP connection is created per miss. The connection is returned to the pool after `await pubsub.aclose()`. The wait holds one pool slot for up to the timeout duration — acceptable at this scale.

- **Dedicated connection required**: a connection in pub/sub mode cannot issue normal GET/SET commands. `pubsub()` handles this by borrowing a separate connection from the pool rather than reusing the command connection.

- **Shared dispatcher (not taken)**: a single background task could hold one permanent pub/sub connection and dispatch events to per-request `asyncio.Event` objects, consuming only one pool slot regardless of concurrent waiter count. More complex to implement; not warranted for a game scheduler.

- `notify-keyspace-events` is off by default; must be set in `redis.conf` or via `CONFIG SET notify-keyspace-events Kg$`.

### Bot Freshness Signal

Bot writes `bot:last_seen = <utc_iso>` with TTL = heartbeat_interval × 3 every N minutes.

API checks this key before trusting projection data. If absent or stale beyond threshold, API returns a friendly "bot is unavailable" degraded response rather than silently serving stale or empty data.

### What This Replaces (Phased — Each Step Is Independently Shippable)

| Old Component                                                                          | New Replacement                                 | Notes                                              |
| -------------------------------------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------- |
| `login_refresh.py` + `get_current_user_guild_member` REST calls                        | Bot `on_ready` + `on_member_update` writes      | Entire file deleted eventually                     |
| `DisplayNameResolver._fetch_and_cache_display_names*` (REST fallback)                  | Redis projection read                           | REST fallback path removed per call site           |
| `permissions.py` `_get_user_guilds` / `_check_guild_membership` (OAuth REST per-route) | `proj:user_guilds:{gen}:{uid}` Redis read       | Highest-frequency elimination                      |
| `RoleChecker.get_guild_member` REST call                                               | `proj:member:{gen}:{guild_id}:{uid}` Redis read |                                                    |
| `CacheTTL.DISPLAY_NAME / USER_ROLES / DISCORD_MEMBER` (5-min TTLs)                     | No TTL on projection keys                       | Keys removed from `ttl.py` per namespace           |
| `user_display_names` DB table + `UserDisplayNameService`                               | Redis projection                                | Becomes dead code; drop table after full migration |
| `services/api/dependencies/discord.py` `DiscordAPIClient` singleton in API             | Unused in API                                   | May be deleted once bot is sole REST caller        |

Note: the `user_display_names` DB table was implemented from the 20260414-01 research. It is functional and can remain in place throughout the migration — it simply stops receiving writes once `login_refresh.py` is removed.

## Implementation Guidance

- **Objectives**:
  - Eliminate all Discord REST calls from the per-request API path
  - Eliminate the 5-minute stale window on role and display name data
  - Survive bot reconnects without serving mixed/partial state to the API
  - Provide a first-login UX that degrades gracefully when the bot is unavailable
  - Always-functional phased cutover: no big-bang migration, no flag days

- **Key Tasks** (in dependency order):
  1. **Enable `GUILD_MEMBERS` intent** in `services/bot/bot.py` (`Intents.members = True`, `chunk_guilds_at_startup=True`) and toggle in Discord Developer Portal. System still works; no new behavior yet.

  2. **Add new Redis key constants** to `shared/cache/keys.py`: `proj_gen()`, `proj_member(gen, guild_id, uid)`, `proj_user_guilds(gen, uid)`, `proj_user_complete(gen, uid)`, `bot_last_seen()`.

  3. **Add `MEMBER_CACHE_POPULATE` to `EventType`** in `shared/messaging/events.py`. Add `MemberCachePopulateEvent` payload model.

  4. **Implement bot projection writer** (`services/bot/guild_projection.py`): `write_member(gen, guild, member)`, `write_user_complete(gen, uid)`, `new_generation()`.

  5. **Wire `on_ready` and reconnect**: bump `proj:gen`, SCAN+DEL previous gen keys, write `bot:last_seen`. No member pre-population.

  6. **Add `on_member_update` and `on_member_remove` handlers**: both delete `proj:member`, `proj:user_guilds`, and `proj:user:complete` keys for the affected user — delete-all preserves the marker contract. `on_member_add` is a no-op (demand-fault).

  7. **Add bot heartbeat task**: writes `bot:last_seen` every N minutes with TTL.

  8. **Add `MEMBER_CACHE_POPULATE` consumer** in bot event handlers: first check `proj:user:{gen}:{uid}:complete` — if `ready`, return immediately. Otherwise attempt `SET bot:populate:{gen}:{uid} 1 NX EX 30` — if NX wins, write `proj:member` + `proj:user_guilds` keys for the specified user + guilds, write `proj:user:{gen}:{uid}:complete = ready`, then delete `bot:populate:{gen}:{uid}`; if NX loses, return immediately (another handler is already doing the work).

  9. **Add API projection reader** (`services/api/services/member_projection.py`): `get_user_guilds(uid)`, `get_member(guild_id, uid)`, `get_user_roles(guild_id, uid)`, `is_bot_fresh()`, `wait_for_user_complete(uid, timeout)` (subscribes to keyspace notification for on-demand hydration).

  10. **Migrate call sites one at a time** — starting with the highest-frequency: `permissions.py` `verify_guild_membership`, then `login_refresh.py` display name reads, then `RoleChecker`, then `DisplayNameResolver`. System functional at every step.

      Note on `RoleChecker`: once `Intents.members=True` with `chunk_guilds_at_startup=True`, the bot's discord.py in-memory client cache (`guild.get_member(int(user_id)).roles`) is authoritative. `RoleChecker.get_user_role_ids` should read from the client cache directly — not from Redis and not via REST. The bot writing its own projection back from Redis would be a round-trip through a system it owns. Redis projection exists only for the API's benefit.

  11. **Remove dead code** after all call sites migrated: `login_refresh.py`, REST fallback paths in `DisplayNameResolver`, `_get_user_guilds` in `permissions.py`, TTL constants, and eventually the `user_display_names` DB table (with DROP TABLE migration). The goal is **zero Discord REST calls from the API server** — verify this is achieved before closing out this step.

  12. **Enforce Redis ACL read-only for the API** — Redis 6.0+ (and Valkey) support ACL users with restricted command sets. Once step 11 is complete and the API has zero Redis writes, create a dedicated API user with only read commands (`GET`, `MGET`, `HGETALL`, `LRANGE`, `SUBSCRIBE`, `PSUBSCRIBE`, etc.) and deny write commands. The bot retains the full-access credential. This cannot happen earlier: the old system writes `user_roles:*`, `display:*`, `display_avatar:*`, and `discord_member:*` from the API side throughout the migration.

  Example ACL rule (added to Valkey config or via `ACL SETUSER`):

  ```
  ACL SETUSER api-reader on >api-password ~* &* +@read +subscribe +psubscribe -@write nocommands +get +mget +hgetall +lrange +smembers +subscribe +psubscribe
  ```

  13. **Eliminate remaining bot REST calls** — after step 12, audit all remaining `discord_api.*` calls in the bot. The goal is to remove every REST call that can be replaced by the discord.py client cache. With `Intents.members` enabled, member data, role data, and guild membership are all available in-process. Each surviving REST call must be explicitly justified as having no gateway equivalent (e.g. certain message or channel operations). The target is as close to zero bot REST calls as the Discord gateway allows.
  - Steps 1–3 are independent and can ship together.
  - Step 4–8 (bot side) must complete before any API call site migration.
  - Step 9 can be developed in parallel with steps 4–8, tested against a bot that has completed step 5.
  - Step 10 is N independent PRs, each shippable independently.
  - Step 11 is safe only when step 10 is 100% complete.

- **Success Criteria**:
  - `verify_guild_membership` fires zero OAuth REST calls per request after migration.
  - `list_games` display name resolution reads only Redis; no Discord API calls in the hot path.
  - Bot reconnect does not cause API to serve mixed-generation data.
  - First-login completes within the on-demand populate timeout under normal conditions.
  - `bot:last_seen` absence causes a clear degraded response, not a silent error or hang.
  - All steps pass the full unit + integration test suite before merging.
