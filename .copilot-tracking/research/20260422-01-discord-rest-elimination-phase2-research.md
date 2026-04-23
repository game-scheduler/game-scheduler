<!-- markdownlint-disable-file -->

# Task Research Notes: Discord REST Elimination — Phase 2

## Research Executed

### File Analysis

- `services/api/services/sse_bridge.py` (line 148)
  - `await oauth2.get_user_guilds(guild_token, discord_id)` called inside the per-connection broadcast loop. Only the `g["id"]` set is used for membership check. Fires once per connected client per game event — highest-frequency REST caller in the API.

- `services/api/database/queries.py` (line 149)
  - `await oauth2.get_user_guilds(access_token, user_discord_id)` called inside `require_guild_by_id` when RLS context is not yet set. Only `g["id"]` list used to build `discord_guild_ids` for RLS setup.

- `services/api/routes/guilds.py` — `list_guilds` (lines 90–112)
  - `await oauth2.get_user_guilds(tokens.get_guild_token(token_data), current_user.user.discord_id)` fetches full guild objects `{id, name, icon, owner, permissions}`. Only `g["id"]` and `g.get("name")` fields are used. `GuildBasicInfoResponse` only needs id + guild_name.

- `services/api/routes/auth.py` — `GET /auth/user` (line 249)
  - `guilds = await oauth2.get_user_guilds(guild_token, current_user.user.discord_id)` returned in `UserInfoResponse.guilds`. Frontend `CurrentUser` interface has `guilds?: DiscordGuild[]` marked optional. Confirmed: no frontend code reads `user.guilds` — all guild-list reads go to `GET /api/v1/guilds` separately.

- `services/bot/utils/discord_format.py` (line 57)
  - `await discord_api.get_guild_member(guild_id, user_id)` — `DiscordAPIClient.get_guild_member` has cache-first (5min TTL) then REST fallback. Reads `nick`, `user.global_name`, `user.username`, `avatar`, `user.avatar` from result to build display name + avatar URL.

- `services/bot/handlers/participant_drop.py` (line 95)
  - `user = await bot.fetch_user(int(discord_id))` — direct REST call, no cache attempt. Identical pattern to what `handlers.py` Tasks 3.1/3.2 already fixed.

- `services/api/routes/guilds.py` — `POST /sync` (lines 323–358)
  - `await sync_all_bot_guilds(discord_client, db, config.discord_bot_token)` — calls `discord_client.get_guilds(token=bot_token)` (REST) then creates new guilds. Does NOT call `refresh_guild_channels` for existing guilds. Channel DB reconciliation for existing guilds is already handled by `GET /guilds/{id}/channels?refresh=true` → `guild_service.refresh_guild_channels()` which reads from Redis gateway cache.

- `services/api/services/guild_service.py` — `refresh_guild_channels` (line 83)
  - Already reads from `discord_client.get_guild_channels()` which is Redis-only. Not REST.

- `frontend/src/pages/TemplateManagement.tsx` (line 75)
  - Only frontend caller using `?refresh=true` on channels. Always fires on page load. Gates the only meaningful channel DB reconciliation path — and is maintainer-only in the UI.

- `frontend/src/pages/EditGame.tsx` (line 89)
  - Calls `/api/v1/guilds/{guild_id}/channels` without `?refresh=true`. Acceptable: reads DB as-is; is_active filtering covers deleted channels.

- `shared/cache/projection.py`
  - `get_user_guilds(uid, *, redis)` → returns `list[str] | None` (guild ID strings)
  - `get_member(guild_id, uid, *, redis)` → returns `dict | None` with keys: `roles`, `nick`, `global_name`, `username`, `avatar_url`
  - `get_guild_name(guild_id, *, redis)` → returns `str | None`
  - All three are async, read-only, no network calls — pure Redis reads.

- `shared/schemas/auth.py` — `UserInfoResponse` (line 69)
  - `guilds: list[dict]` field exists. `frontend/src/types/index.ts` `CurrentUser.guilds?: DiscordGuild[]` exists but is never accessed in any frontend component.

### Code Search Results

- `oauth2.get_user_guilds` in `services/**/*.py`
  - 4 call sites: `sse_bridge.py:148`, `queries.py:149`, `guilds.py:91`, `auth.py:249`
- `discord_api.get_guild_member` in `services/bot/**/*.py`
  - 1 production call site: `discord_format.py:57`
- `bot.fetch_user` in `services/bot/**/*.py`
  - 1 remaining call site: `participant_drop.py:95` (handlers.py already fixed in plan 20260421-02)
- `sync_all_bot_guilds` in `services/**/*.py`
  - 1 remaining import: `guilds.py` (bot.py and on_guild_join already fixed in plan 20260421-02)
- `refresh_guild_channels` callers
  - `guilds.py:241` — `GET /{guild_id}/channels?refresh=true` path (gateway-backed, correct)
  - `/sync` endpoint calls `sync_all_bot_guilds` which does NOT call `refresh_guild_channels`
- `user.guilds` in frontend
  - Zero references — `CurrentUser.guilds` is an unused optional field

### Project Conventions

- `permissions.get_guild_name(guild_discord_id, db)` in `guilds.py` already calls `member_projection.get_guild_name()` via Redis — same pattern to adopt in `list_guilds`
- `_build_guild_config_response` (line 62 in `guilds.py`) is the reference implementation for projection-based guild name lookup
- `participant_drop.py` pattern matches what `handlers.py` Tasks 3.1/3.2 already fixed — exact same substitution

## Key Discoveries

### Projection fields satisfy all replacement needs

`member_projection.get_member()` stores: `roles`, `nick`, `global_name`, `username`, `avatar_url`. The `discord_format.py` replacement needs exactly: display_name (nick → global_name → username) and avatar_url. The projection already stores `avatar_url` as a pre-built CDN URL — no reconstruction needed. The current code reconstructs CDN URLs from raw avatar hashes via `_build_avatar_url()`.

### `list_guilds` dependency on REST-returned guild names

The `list_guilds` route uses `discord_guild_data.get("name")` from the full OAuth guild object. `member_projection.get_guild_name(guild_id)` provides the same value (written from gateway on `on_ready` and `on_guild_update`). The `_build_guild_config_response` helper already uses this path via `permissions.get_guild_name`.

### `/sync` endpoint is fully redundant

- New guilds: covered by `on_guild_join` → `sync_single_guild_from_gateway` (done in plan 20260421-02)
- `on_ready`: `sync_guilds_from_gateway` creates any guilds added while bot was offline (done in plan 20260421-02)
- Channel reconciliation for existing guilds: `GET /{guild_id}/channels?refresh=true` → `guild_service.refresh_guild_channels()` (already Redis-backed). Called automatically by `TemplateManagement.tsx` on every page load — the only page where channel selection matters for maintainer actions.
- `sync_all_bot_guilds` function in `guild_sync.py` can be retained (has unit tests); only the API endpoint that calls it is removed.

### Frontend `GuildListPage.tsx` calls `/sync` — needs update

`GuildListPage.tsx` has a Sync button wired to `POST /api/v1/guilds/sync`. Tests in `GuildListPage.test.tsx` cover sync button behavior and the `new_guilds`/`new_channels` success messages. Both the sync button and its tests must be removed when the endpoint is deleted.

### `get_user_guilds` None-return handling

`member_projection.get_user_guilds()` returns `list[str] | None`. Callers must handle `None` (projection not yet populated). In `sse_bridge.py` and `queries.py`, `None` should be treated as empty set / no guilds. In `list_guilds`, `None` yields empty guild list.

## Recommended Approach

For each of the 7 changes, replace the REST/OAuth call with the projection equivalent using `shared/cache/projection.py` functions directly. The `/sync` endpoint is removed entirely with no replacement needed.

### Change details by group

**Group 2a — `sse_bridge.py`**
Replace:

```python
guild_token = tokens.get_guild_token(token_data)
user_guilds = await oauth2.get_user_guilds(guild_token, discord_id)
user_guild_ids = {g["id"] for g in user_guilds}
```

With:

```python
guild_ids = await member_projection.get_user_guilds(discord_id, redis=redis)
user_guild_ids = set(guild_ids) if guild_ids else set()
```

The `guild_token` extraction and `oauth2` import can be removed from this code path. The `redis` dependency injection is already available in the broadcast method's scope (check for existing `redis` parameter or add it).

**Group 2b — `queries.py`**
Replace:

```python
user_guilds = await oauth2.get_user_guilds(access_token, user_discord_id)
discord_guild_ids = [g["id"] for g in user_guilds]
```

With:

```python
discord_guild_ids = await member_projection.get_user_guilds(user_discord_id, redis=redis) or []
```

The `redis` client must be injected — check how `sse_bridge` and other callers get it; likely via `get_redis()` dependency.

**Group 2c — `guilds.py` `list_guilds`**
Replace the `oauth2.get_user_guilds` + name lookup loop with:

1. `guild_ids = await member_projection.get_user_guilds(current_user.user.discord_id, redis=redis) or []`
2. For each `guild_id`: `guild_config = await queries.get_guild_by_discord_id(db, guild_id)`; `guild_name = await member_projection.get_guild_name(guild_id, redis=redis) or "Unknown Guild"`
   This mirrors the pattern already used in `_build_guild_config_response`.

**Group 2d — `auth.py` `/auth/user`**
Remove:

```python
guilds = await oauth2.get_user_guilds(guild_token, current_user.user.discord_id)
```

Return `UserInfoResponse` without `guilds=` kwarg (field has `default_factory=list`, returns `[]`).
Remove `guilds: list[dict]` field from `UserInfoResponse` in `shared/schemas/auth.py`.
Remove `guilds?: DiscordGuild[]` from `CurrentUser` interface in `frontend/src/types/index.ts`.

**Group 3 — `discord_format.py`**
Replace `discord_api.get_guild_member(guild_id, user_id)` call with `member_projection.get_member(guild_id, user_id, redis=redis)`. The projection already stores `avatar_url` as a pre-built URL, so `_build_avatar_url()` call is replaced by direct `member_data.get("avatar_url")`. Display name logic: `member_data.get("nick") or member_data.get("global_name") or member_data.get("username")` — same precedence, different key paths since projection is flat (no nested `user` dict).

**Group 4 — `participant_drop.py`**
Replace:

```python
user = await bot.fetch_user(int(discord_id))
await user.send(DMFormats.removal(game_title))
```

With:

```python
user = bot.get_user(int(discord_id))
if user is None:
    logger.warning("User %s not in cache, cannot send removal DM", discord_id)
    return
await user.send(DMFormats.removal(game_title))
```

**Group 6 — Remove `/sync` endpoint**

- Remove `@router.post("/sync", ...)` route handler and `GuildSyncResponse` return (lines 323–358 in `guilds.py`)
- Remove `sync_all_bot_guilds` import from `guilds.py`
- Remove `GuildSyncResponse` import from guilds route if unused elsewhere
- Remove Sync button from `frontend/src/pages/GuildListPage.tsx` (the button, handler, state vars for syncMessage/syncLoading, and associated imports)
- Remove sync-related tests from `frontend/src/pages/__tests__/GuildListPage.test.tsx`
- `sync_all_bot_guilds` function in `guild_sync.py` may remain (has unit tests and is not harmful)

## Implementation Guidance

- **Objectives**: Eliminate all `oauth2.get_user_guilds()` calls from non-auth paths; eliminate the last `bot.fetch_user()` in `participant_drop.py`; remove the now-redundant `/sync` API endpoint
- **Key Tasks**:
  1. Group 2a: `sse_bridge.py` — projection guild membership check (highest priority, highest frequency)
  2. Group 2b: `queries.py` — projection RLS setup
  3. Group 2c: `guilds.py list_guilds` — projection guild list + names
  4. Group 2d: `auth.py` + `UserInfoResponse` + frontend type — remove guilds field
  5. Group 3: `discord_format.py` — projection member display info
  6. Group 4: `participant_drop.py` — sync user fetch
  7. Group 6: Remove `/sync` endpoint + frontend Sync button
- **Dependencies**:
  - Groups 2a/2b/2c/2d/3/4 are all independent of each other
  - Group 6 is independent but benefits from Groups 2a–2c landing first (confirms `/sync` is last remaining `get_user_guilds` caller to remove after 2d)
  - `redis` client injection may need to be threaded into `queries.py` and `discord_format.py` — verify current injection patterns before implementing
- **Success Criteria**:
  - Zero calls to `oauth2.get_user_guilds` remain in the codebase outside of `services/api/auth/oauth2.py` itself
  - Zero calls to `bot.fetch_user` remain in `services/bot/`

---

## Addendum: Post-Implementation Verification (2026-04-23)

### Verification Results

All 7 phases confirmed complete by code inspection. Every targeted call site was replaced as planned. The following findings emerged from a full audit of the live codebase after Phase 7 merged.

### Finding 1: `shared/database.py` — Missed call site (oversight)

`get_db_with_user_guilds()` in `shared/database.py` (line 157) still calls `oauth2.get_user_guilds()`:

```python
user_guilds = await oauth2.get_user_guilds(guild_token, current_user.user.discord_id)
discord_guild_ids = [g["id"] for g in user_guilds]
```

This function is a FastAPI dependency used by every route that needs RLS context (`games`, `guilds`, `templates`, `export`). It was not in the original research because the original call-site audit searched `services/**/*.py` and this file is in `shared/`. It is the highest-frequency remaining REST caller.

**Fix**: Same pattern as all other eliminated sites:

```python
redis = await cache_client.get_redis_client()
discord_guild_ids = await member_projection.get_user_guilds(
    current_user.user.discord_id, redis=redis
) or []
```

Remove `guild_token = tokens.get_guild_token(token_data)` (no longer needed). Update inner imports: remove `oauth2` from `from services.api.auth import oauth2, tokens`; add `from shared.cache import client as cache_client` and `from shared.cache import projection as member_projection`.

The `token_data` fetch and 401 guard stay unchanged.

### Finding 2: `get_guild_channels()` and `fetch_guild_roles()` — Not REST calls

`discord_client.get_guild_channels()` and `discord_client.fetch_guild_roles()` in API routes (`guilds.py`, `guild_service.py`, `channel_resolver.py`) look like REST calls by name but are not. Both delegate to `DiscordAPIClient._read_cache_only()`, which raises `DiscordAPIError(503)` on cache miss rather than falling back to REST. The bot keeps these keys current via gateway events (`on_guild_channel_create/update/delete`, `on_guild_role_create/update/delete`, `on_ready`). These calls are pure Redis reads and do not need to be eliminated.

### Finding 3: `guild_sync.py` — Three dead functions with REST calls

`sync_all_bot_guilds()`, `_create_guild_with_channels_and_template()`, and `_refresh_guild_channels()` in `services/bot/guild_sync.py` are unreachable dead code:

- `sync_all_bot_guilds()` was the backend of the `/sync` endpoint removed in Phase 7. No other caller exists.
- `_create_guild_with_channels_and_template()` is only called by `sync_all_bot_guilds()`.
- `_refresh_guild_channels()` has no callers anywhere in the codebase.

The live code paths (`on_ready` → `sync_guilds_from_gateway`, `on_guild_join` → `sync_single_guild_from_gateway`) use the gateway-based replacements `_create_guild_with_gateway_channels()` and never touch these three functions. The `DiscordAPIClient` import in `guild_sync.py` is only needed by these dead functions and should be removed with them.

**Tests to delete** in `tests/unit/services/bot/test_guild_sync.py`:

- All `test_sync_all_bot_guilds_*` functions (~11 tests)
- `TestCreateGuildWithChannelsAndTemplate` class (~3 tests)
- All `test_refresh_guild_channels_*` functions (~4 tests)

### Corrected Success Criteria

The original success criteria are met. Two additional criteria apply:

- `grep -r "oauth2.get_user_guilds" shared/` returns no results outside `services/api/auth/oauth2.py`
- `sync_all_bot_guilds`, `_create_guild_with_channels_and_template`, and `_refresh_guild_channels` are deleted from `guild_sync.py` along with the `DiscordAPIClient` import
  - `POST /api/v1/guilds/sync` endpoint returns 404 (removed)
  - `UserInfoResponse.guilds` field removed from schema and frontend type
  - `discord_format.get_member_display_info` makes no REST or `DiscordAPIClient` calls
  - All unit test suites pass with no skips
  - TDD applies to all Python changes: update tests first (RED), then fix production code (GREEN)
