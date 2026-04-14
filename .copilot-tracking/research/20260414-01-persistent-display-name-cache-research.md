<!-- markdownlint-disable-file -->

# Task Research Notes: Persistent Display Name Cache

## Research Executed

### File Analysis

- `shared/models/user.py`
  - `User` table stores only `discord_id` (snowflake string, max 20 chars); no display name fields
  - Comment explicitly states "Display names are never cached - always fetched at render time"
  - No RLS on `users` table

- `shared/models/participant.py`
  - `GameParticipant.display_name` (line 75): nullable `String(100)` — used only for placeholder rows where `user_id IS NULL`
  - DB constraint: `user_id IS NOT NULL AND display_name IS NULL` OR `user_id IS NULL AND display_name IS NOT NULL`
  - Real participants store only `user_id`; display name resolution is deferred to render time

- `shared/cache/keys.py` / `shared/cache/ttl.py`
  - `CacheKeys.display_name_avatar(user_id, guild_id)` → `display_avatar:{guild_id}:{user_id}`
  - `CacheKeys.discord_member(guild_id, user_id)` → separate key for raw member object
  - `CacheTTL.DISPLAY_NAME = 300` (5 minutes) — workaround for having no persistent storage
  - `CacheTTL.DISCORD_MEMBER = 300` (5 minutes)

- `services/api/services/display_names.py`
  - `DisplayNameResolver`: constructor takes `discord_api` + `cache` only; no DB session
  - `_check_cache_for_users`: checks Redis `display_avatar:` key; on miss, calls Discord API
  - `_fetch_and_cache_display_names_avatars`: calls `get_guild_members_batch`, writes Redis + returns
  - `_resolve_display_name(member)`: priority — `member["nick"] or member["user"]["global_name"] or member["user"]["username"]`
  - `get_display_name_resolver()`: factory function that injects discord_api + redis only
  - No DB session injection path exists today

- `services/bot/handlers/join_game.py`
  - `handle_join_game`: `interaction.user.id` is used; `interaction.user` is `discord.Member` in guild context
  - `discord.Member` exposes: `.nick`, `.global_name`, `.name`, `.display_name` (computed), `.display_avatar.url`
  - `_resolve_bot_role_position`: already reads `interaction.user.roles` — proves `Member` object is fully populated
  - No name data is currently captured or stored at button-press time

- `services/api/auth/oauth2.py`
  - `OAUTH_SCOPES = ["identify", "guilds", "guilds.members.read"]` — `guilds.members.read` already requested
  - Login callback (`auth.py` line 100): calls `get_user_from_token` → fetches `GET /users/@me`
  - Callback also calls `get_user_guilds` → fetches `GET /users/@me/guilds`
  - No member-per-guild fetch happens today

- `shared/discord/client.py`
  - `get_guild_member` (line 782): bot token, `GET /guilds/{guild_id}/members/{user_id}`, rate-limited by bot global budget (~1 req/1.5s per route)
  - `_get_auth_header`: auto-detects Bot vs Bearer token by dot count — `GET /users/@me/guilds/{guild_id}/member` with OAuth token would work via this same method
  - No `get_current_user_guild_member` method exists today

- `alembic/versions/20260412_add_backup_metadata.py`
  - Most recent migration, `down_revision = "fd0d4f43e53a"`
  - Pattern: `op.create_table`, `op.drop_table` in downgrade

- `shared/models/__init__.py`
  - All models imported here for Alembic discovery

### Code Search Results

- `resolve_display_names_and_avatars`
  - Called in `games.py` at lines 470, 747, 835
  - All callers pass `guild_discord_id` (Discord snowflake string) + list of user Discord IDs

- `display_name_avatar` cache key usage
  - Written only in `_fetch_and_cache_display_names_avatars` (display_names.py)
  - Read only in `_check_cache_for_users` (display_names.py)
  - Isolated to `DisplayNameResolver` — clean removal surface

- `display_name` (Redis, not DB)
  - Separate older key `display:{guild_id}:{user_id}` used by `resolve_display_names` (non-avatar path)
  - Both keys are `DisplayNameResolver`-internal

### External Research

- #fetch:https://discord.com/developers/docs/resources/user#get-current-user-guild-member
  - Endpoint: `GET /users/@me/guilds/{guild.id}/member`
  - Auth: Bearer token (OAuth2), requires `guilds.members.read` scope
  - Response format: identical to `GET /guilds/{guild.id}/members/{user.id}` — same `nick`, `user.global_name`, `user.username`, `avatar`, `user.avatar` fields
  - Rate limit: per-user per-route (separate pool from bot token)
  - No privileged intent required

- #fetch:https://discord.com/developers/docs/topics/gateway#privileged-intents
  - `GUILD_MEMBERS` privileged intent required only for `LIST /guilds/{id}/members` (bulk fetch)
  - Single-member fetch `GET /guilds/{id}/members/{user_id}` does NOT require privileged intent
  - OAuth `GET /users/@me/guilds/{guild_id}/member` also does NOT require privileged intent

### Project Conventions

- Standards referenced: existing migration patterns, `shared/models/` structure, `DisplayNameResolver` injection pattern
- No RLS needed on display name table — display names are not sensitive guild-scoped data

## Key Discoveries

### Root Cause of Linear Scaling

Cold-cache `list_games` latency scales as `max(participants_per_guild) × ~1.5s` because `get_guild_members_batch` dispatches concurrent `asyncio.gather` calls, but Discord's per-route rate limiter for `GET /guilds/{id}/members/{user_id}` serializes them at the network layer. The current Phase 5 optimization reduced the count by deduplicating hosts per guild, but the fundamental constraint is Discord's rate limit on the bot token scope.

### What the Discord Interaction Payload Contains

When a user presses a button in a guild, `interaction.user` is a fully-populated `discord.Member` object. The display name resolution priority `nick → global_name → username` is already present client-side with zero extra API calls. The bot currently discards this data after extracting `user.id` and `user.roles`.

### Redis vs Postgres for This Workload

Redis GET: ~0.1–0.5ms. Postgres indexed PK lookup on a hot small table: ~0.5–2ms. The gap is 1–2ms — noise compared to the 9000ms Discord API serialization this change eliminates. The key difference: Redis is ephemeral. A restart resets the cache and forces a cold Discord re-fetch for every user. Postgres persists across restarts.

The `display_name_avatar` Redis keys exist solely as a workaround for having no persistent storage. Once the DB table exists, they are redundant. The `discord_member` Redis keys (raw member object TTL cache) remain useful as an L1 guard against re-fetching from Discord within a 5-minute window.

### OAuth User Token Advantage

`GET /users/@me/guilds/{guild_id}/member` uses the user's own OAuth rate limit pool, not the bot's. The bot's `GET /guilds/{id}/members/{user_id}` budget is shared across all users. With OAuth, each logged-in user's login callback can refresh their own guild member data in parallel across all their bot-registered guilds with no impact on other users or the bot rate limit budget.

## Recommended Approach

### New Table: `user_display_names`

```sql
user_display_names (
    user_discord_id  VARCHAR(20)   NOT NULL,  -- Discord snowflake
    guild_discord_id VARCHAR(20)   NOT NULL,  -- Discord snowflake
    display_name     VARCHAR(100)  NOT NULL,
    avatar_url       VARCHAR(512),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_discord_id, guild_discord_id)
)
CREATE INDEX idx_user_display_names_updated_at ON user_display_names (updated_at);
```

No FK to `users.id` — the bot writes this at button-press time before a `User` row may exist. No RLS — display names are not sensitive. `updated_at` index supports periodic pruning of rows for users inactive beyond a threshold.

### New Service: `UserDisplayNameService`

A thin wrapper that owns the DB read/write and calls `DisplayNameResolver` only on cache miss. `DisplayNameResolver` stays unchanged — it keeps Redis + Discord API as its two layers. The new service adds DB as a third layer below Redis but above Discord.

```
list_games request
  └── UserDisplayNameService.resolve(guild_id, user_ids)
        ├── [1] DB lookup (SELECT WHERE user_discord_id = ANY(...) AND guild_discord_id = ?)
        │         hit  → return from DB
        │         miss ↓
        ├── [2] DisplayNameResolver (existing Redis → Discord API path)
        │         fetches missing users, writes to Redis (discord_member TTL)
        │         result ↓
        └── [3] Upsert DB (INSERT ... ON CONFLICT DO UPDATE SET ...)
              returns result
```

The `display_name_avatar` Redis keys (5-min TTL) are removed. `discord_member` Redis keys stay.

### Three Write Paths

**Path A — Bot button press (zero extra API calls):**
In `handle_join_game` / `handle_leave_game`, after the DB commit that writes `GameParticipant`, upsert `user_display_names` using data directly from `interaction.user` (a `discord.Member`):

```python
display_name = interaction.user.nick or interaction.user.global_name or interaction.user.name
avatar_url = str(interaction.user.display_avatar.url) if interaction.user.display_avatar else None
# upsert user_display_names
```

**Path B — API read-through (write-through on Discord API fetch):**
`UserDisplayNameService.resolve()` upserts to DB whenever it falls through to Discord (step 3 above). Subsequent requests within and beyond the Redis TTL window find DB.

**Path C — Login background refresh (OAuth, user's own rate limit):**
After the auth callback fetches `get_user_guilds`, fire a background task that:

1. Queries DB for which of the user's 44 guilds have a `guild_configurations` row
2. For each matching guild, calls `GET /users/@me/guilds/{guild_id}/member` with the user's OAuth token via a new `DiscordAPIClient.get_current_user_guild_member(guild_id, token)` method
3. Upserts `user_display_names` for that user across all their registered guilds

This means every login refreshes the logged-in user's display data for all their guilds simultaneously, at their own rate limit cost.

### New Discord Client Method

```python
async def get_current_user_guild_member(self, guild_id: str, token: str) -> dict[str, Any]:
    return await self._make_api_request(
        method="GET",
        url=f"{self._api_base_url}/users/@me/guilds/{guild_id}/member",
        operation_name="get_current_user_guild_member",
        headers={"Authorization": f"Bearer {token}"},
    )
```

No Redis caching at the client level for this method — the DB upsert is the persistence layer.

### Pruning

A scheduled task (or Postgres cron via `pg_cron`, or a manual admin endpoint) deletes rows where `updated_at < NOW() - INTERVAL '90 days'`. This bounds table growth to active users only.

## Implementation Guidance

- **Objectives**:
  - Eliminate cold-cache `list_games` latency for users who have logged in or pressed a button recently
  - Survive service restarts without requiring Discord re-fetches
  - Remove the 5-minute Redis TTL workaround for display names

- **Key Tasks**:
  1. Add `UserDisplayName` SQLAlchemy model in `shared/models/user_display_name.py`
  2. Register in `shared/models/__init__.py`
  3. Write Alembic migration (revision after `20260412_add_backup_metadata`)
  4. Add `UserDisplayNameService` in `services/api/services/user_display_names.py` with batch `resolve`, `upsert_one`, `upsert_batch` methods
  5. Add `DiscordAPIClient.get_current_user_guild_member` in `shared/discord/client.py`
  6. Update `handle_join_game` and `handle_leave_game` to upsert on button press (Path A)
  7. Wire `UserDisplayNameService` into `list_games`, `get_game`, and the single-game participant path as a drop-in replacement for direct `DisplayNameResolver` calls (Path B)
  8. Add background task to auth callback for login refresh (Path C)
  9. Remove `display_name_avatar` Redis key writing from `_fetch_and_cache_display_names_avatars`; remove `_check_cache_for_users` Redis layer (or leave as optional L1, to be decided)
  10. Unit tests for `UserDisplayNameService` (DB hit, DB miss → Discord, upsert logic)

- **Dependencies**:
  - `UserDisplayNameService` depends on: SQLAlchemy `AsyncSession`, existing `DisplayNameResolver`
  - Auth callback background task depends on: `get_current_user_guild_member`, guild config DB query
  - Bot handler upsert depends on: direct DB session (already available in `handle_join_game`)

- **Success Criteria**:
  - `list_games` returns in <100ms for any user who has logged in or clicked a button in the last 90 days
  - Service restart does not reset display name resolution — first request after restart reads from DB
  - No increase in Discord API call volume under normal operation
  - Table rows are bounded by `updated_at` pruning
