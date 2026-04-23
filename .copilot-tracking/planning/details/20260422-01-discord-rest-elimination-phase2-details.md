<!-- markdownlint-disable-file -->

# Task Details: Discord REST Elimination — Phase 2

## Research Reference

**Source Research**: #file:../research/20260422-01-discord-rest-elimination-phase2-research.md

---

## Phase 1: Fix sse_bridge.py guild membership check (Group 2a)

### Task 1.1: Write failing test for projection-based guild lookup in sse_bridge.py

Write a test that verifies the broadcast loop uses `member_projection.get_user_guilds()` instead of `oauth2.get_user_guilds()`. Mark `xfail(strict=True)` — will fail until implementation in Task 1.2.

- **Files**:
  - `tests/unit/test_sse_bridge.py` — add test for projection guild membership
- **Success**:
  - Test exists and is marked `xfail(strict=True)`
  - Test fails (XFAIL) with current implementation
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 1-12) — sse_bridge.py call site analysis
- **Dependencies**:
  - None

### Task 1.2: Replace oauth2.get_user_guilds() with projection in sse_bridge.py

In `services/api/services/sse_bridge.py` around line 148, replace:

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

Remove `guild_token` extraction and `oauth2` import from this path. Confirm `redis` is available in the broadcast method scope.

- **Files**:
  - `services/api/services/sse_bridge.py` — replace REST call with projection read
- **Success**:
  - Task 1.1 xfail test now passes; remove xfail marker
  - No `oauth2.get_user_guilds` call in sse_bridge.py
  - `redis` parameter confirmed available in broadcast method
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 101-118) — Group 2a replacement code
- **Dependencies**:
  - Task 1.1 complete

---

## Phase 2: Fix queries.py RLS setup (Group 2b)

### Task 2.1: Write failing test for projection-based RLS guild list in queries.py

Write a test that verifies `require_guild_by_id` uses `member_projection.get_user_guilds()` for RLS setup instead of `oauth2.get_user_guilds()`. Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_queries.py` — add test for projection-based RLS guild list
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 6-12) — queries.py call site analysis
- **Dependencies**:
  - None

### Task 2.2: Replace oauth2.get_user_guilds() with projection in queries.py

In `services/api/database/queries.py` around line 149, replace:

```python
user_guilds = await oauth2.get_user_guilds(access_token, user_discord_id)
discord_guild_ids = [g["id"] for g in user_guilds]
```

With:

```python
discord_guild_ids = await member_projection.get_user_guilds(user_discord_id, redis=redis) or []
```

Verify how `redis` is injected in this function — check other DB query functions for the existing injection pattern before implementing.

- **Files**:
  - `services/api/database/queries.py` — replace REST call; inject redis client
- **Success**:
  - Task 2.1 xfail test now passes; remove xfail marker
  - No `oauth2.get_user_guilds` call in queries.py
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 119-135) — Group 2b replacement code
- **Dependencies**:
  - Task 2.1 complete

---

## Phase 3: Fix guilds.py list_guilds route (Group 2c)

### Task 3.1: Write failing test for projection-based guild list in list_guilds

Write a test that verifies `list_guilds` returns guild data using projection reads only — no `oauth2.get_user_guilds()` call. Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_guilds_routes.py` — add test for projection-based list_guilds
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 14-22) — guilds.py list_guilds call site analysis
- **Dependencies**:
  - None

### Task 3.2: Replace oauth2.get_user_guilds() with projection in list_guilds

In `services/api/routes/guilds.py` `list_guilds` (lines 90–112), replace the guild-fetch loop with:

1. `guild_ids = await member_projection.get_user_guilds(current_user.user.discord_id, redis=redis) or []`
2. For each `guild_id`: `guild_config = await queries.get_guild_by_discord_id(db, guild_id)` and `guild_name = await member_projection.get_guild_name(guild_id, redis=redis) or "Unknown Guild"`

Mirror the pattern already used in `_build_guild_config_response` (line 62 in `guilds.py`).

- **Files**:
  - `services/api/routes/guilds.py` — replace REST call with projection reads in list_guilds
- **Success**:
  - Task 3.1 xfail test now passes; remove xfail marker
  - No `oauth2.get_user_guilds` in list_guilds
  - Guild names sourced from `member_projection.get_guild_name()`
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 136-162) — Group 2c replacement strategy
- **Dependencies**:
  - Task 3.1 complete

---

## Phase 4: Remove guilds field from auth response (Group 2d)

### Task 4.1: Write failing test confirming guilds field absent from /auth/user response

Write a test that verifies the `/auth/user` response does NOT include a `guilds` field and that `oauth2.get_user_guilds()` is not called in the handler. Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_auth_routes.py` — add test confirming guilds absent from UserInfoResponse
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 24-34) — auth.py call site and frontend field analysis
- **Dependencies**:
  - None

### Task 4.2: Remove guilds from auth.py, UserInfoResponse schema, and frontend CurrentUser

Three coordinated changes:

1. `services/api/routes/auth.py` (line 249): Remove `guilds = await oauth2.get_user_guilds(...)` and the `guilds=guilds` kwarg from the `UserInfoResponse(...)` call.
2. `shared/schemas/auth.py` (line 69): Remove `guilds: list[dict]` field from `UserInfoResponse`.
3. `frontend/src/types/index.ts`: Remove `guilds?: DiscordGuild[]` from `CurrentUser` interface.

The `guilds` field is confirmed unused in all frontend components — `GET /api/v1/guilds` is the authoritative guild data source.

- **Files**:
  - `services/api/routes/auth.py` — remove get_user_guilds call and guilds kwarg
  - `shared/schemas/auth.py` — remove guilds field from UserInfoResponse
  - `frontend/src/types/index.ts` — remove guilds optional field from CurrentUser
- **Success**:
  - Task 4.1 xfail test now passes; remove xfail marker
  - No `oauth2.get_user_guilds` in auth.py
  - `UserInfoResponse` has no `guilds` field
  - `CurrentUser` interface has no `guilds` field
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 163-182) — Group 2d removal strategy
- **Dependencies**:
  - Task 4.1 complete

---

## Phase 5: Fix discord_format.py member lookup (Group 3)

### Task 5.1: Write failing test for projection-based member display info

Write a test that verifies `get_member_display_info` (or equivalent) reads from `member_projection.get_member()` instead of `discord_api.get_guild_member()`. Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_discord_format.py` — add test for projection-based member display info
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 36-49) — discord_format.py call site analysis
- **Dependencies**:
  - None

### Task 5.2: Replace discord_api.get_guild_member() with projection in discord_format.py

In `services/bot/utils/discord_format.py` (line 57), replace `discord_api.get_guild_member(guild_id, user_id)` with `member_projection.get_member(guild_id, user_id, redis=redis)`.

The projection stores `avatar_url` as a pre-built CDN URL — replace any `_build_avatar_url()` call with direct `member_data.get("avatar_url")`. Display name logic uses the flat projection dict: `member_data.get("nick") or member_data.get("global_name") or member_data.get("username")` (no nested `user` key unlike the REST response).

- **Files**:
  - `services/bot/utils/discord_format.py` — replace REST call; update avatar_url and display name key paths
- **Success**:
  - Task 5.1 xfail test now passes; remove xfail marker
  - No `discord_api.get_guild_member` call in discord_format.py
  - `_build_avatar_url()` no longer called for member lookups
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 183-210) — Group 3 replacement strategy and projection key mapping
- **Dependencies**:
  - Task 5.1 complete

---

## Phase 6: Fix participant_drop.py user fetch (Group 4)

### Task 6.1: Write failing test for sync user fetch in participant_drop.py

Write a test that verifies the drop handler uses `bot.get_user()` (sync cache lookup) rather than `bot.fetch_user()` (REST call). Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_participant_drop.py` — add test confirming get_user not fetch_user
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 51-58) — participant_drop.py call site
- **Dependencies**:
  - None

### Task 6.2: Replace bot.fetch_user() with bot.get_user() in participant_drop.py

In `services/bot/handlers/participant_drop.py` (line 95), replace:

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

This mirrors the pattern already applied in `handlers.py` Tasks 3.1/3.2 (plan 20260421-02).

- **Files**:
  - `services/bot/handlers/participant_drop.py` — replace fetch_user with get_user + None guard
- **Success**:
  - Task 6.1 xfail test now passes; remove xfail marker
  - No `bot.fetch_user` calls in services/bot/
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 211-228) — Group 4 replacement code
- **Dependencies**:
  - Task 6.1 complete

---

## Phase 7: Remove /sync endpoint and frontend Sync button (Group 6)

### Task 7.1: Write failing test confirming /sync returns 404

Write a test that verifies `POST /api/v1/guilds/sync` returns 404 or 405. Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_guilds_routes.py` — add test for /sync returning 404
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 60-80) — /sync redundancy analysis
- **Dependencies**:
  - None

### Task 7.2: Remove /sync route handler from guilds.py

In `services/api/routes/guilds.py` (lines 323–358), remove:

- The `@router.post("/sync", ...)` route handler and its body
- The `sync_all_bot_guilds` import from guilds.py
- The `GuildSyncResponse` import if no longer used elsewhere in the file

The `sync_all_bot_guilds` function in `guild_sync.py` may remain — it has unit tests and is not harmful to keep.

- **Files**:
  - `services/api/routes/guilds.py` — remove /sync route, sync_all_bot_guilds import, GuildSyncResponse import
- **Success**:
  - Task 7.1 xfail test now passes; remove xfail marker
  - `POST /api/v1/guilds/sync` no longer registered in router
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 229-260) — /sync endpoint removal rationale
- **Dependencies**:
  - Task 7.1 complete

### Task 7.3: Remove Sync button and tests from frontend

In `frontend/src/pages/GuildListPage.tsx`, remove:

- The Sync button component and its click handler
- `syncMessage` and `syncLoading` state variables and their setters
- Any imports used only by the sync button

In `frontend/src/pages/__tests__/GuildListPage.test.tsx`, remove sync-related tests (sync button behavior, `new_guilds`/`new_channels` success messages) and add a test confirming no Sync button is rendered. TypeScript changes follow TDD: write the failing "no sync button" test first, then remove the button code.

- **Files**:
  - `frontend/src/pages/GuildListPage.tsx` — remove Sync button, handler, state vars, imports
  - `frontend/src/pages/__tests__/GuildListPage.test.tsx` — remove sync tests; add "no sync button" test
- **Success**:
  - No Sync button rendered in GuildListPage
  - New "no sync button" test passes
  - Frontend TypeScript compiles with no errors
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 75-88) — frontend sync button and test analysis
- **Dependencies**:
  - Task 7.2 complete

---

## Phase 8: Fix shared/database.py missed call site (Finding 1 addendum)

### Task 8.1: Write failing test for projection-based guild membership in get_db_with_user_guilds

Write a test that verifies `get_db_with_user_guilds()` uses `member_projection.get_user_guilds()` instead of `oauth2.get_user_guilds()`. Mark `xfail(strict=True)`.

- **Files**:
  - `tests/unit/test_database.py` — add test for projection-based guild membership in get_db_with_user_guilds
- **Success**:
  - Test is marked `xfail(strict=True)` and shows as XFAIL
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 218-255) — Finding 1: shared/database.py missed call site
- **Dependencies**:
  - None

### Task 8.2: Replace oauth2.get_user_guilds() with projection in shared/database.py

In `shared/database.py` (line 157), inside `get_db_with_user_guilds()`, replace:

```python
user_guilds = await oauth2.get_user_guilds(guild_token, current_user.user.discord_id)
discord_guild_ids = [g["id"] for g in user_guilds]
```

With:

```python
redis = await cache_client.get_redis_client()
discord_guild_ids = await member_projection.get_user_guilds(
    current_user.user.discord_id, redis=redis
) or []
```

Remove `guild_token = tokens.get_guild_token(token_data)` (no longer needed). Update imports: remove `oauth2` from the `from services.api.auth import ...` line; add `from shared.cache import client as cache_client` and `from shared.cache import projection as member_projection`.

- **Files**:
  - `shared/database.py` — replace REST call; remove guild_token extraction; update imports
- **Success**:
  - Task 8.1 xfail test now passes; remove xfail marker
  - No `oauth2.get_user_guilds` call in `shared/database.py`
  - `guild_token` extraction removed
  - `token_data` fetch and 401 guard unchanged
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 218-255) — Finding 1: replacement pattern and import updates
- **Dependencies**:
  - Task 8.1 complete

---

## Phase 9: Remove dead REST functions from guild_sync.py (Finding 3 addendum)

### Task 9.1: Delete dead test functions from test_guild_sync.py

In `tests/unit/services/bot/test_guild_sync.py`, delete:

- All `test_sync_all_bot_guilds_*` functions (~11 tests)
- The entire `TestCreateGuildWithChannelsAndTemplate` class (~3 tests)
- All `test_refresh_guild_channels_*` functions (~4 tests)

Note: Phase 7 Task 7.2 left `sync_all_bot_guilds` in `guild_sync.py` intentionally. The addendum audit revealed these functions are unreachable dead code — delete the tests first before removing production code.

- **Files**:
  - `tests/unit/services/bot/test_guild_sync.py` — delete dead test functions and class
- **Success**:
  - Deleted tests no longer appear in test output
  - Remaining `test_guild_sync.py` tests (for gateway-backed functions) still pass
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 256-300) — Finding 3: dead functions analysis and test list
- **Dependencies**:
  - None

### Task 9.2: Delete dead functions and DiscordAPIClient import from guild_sync.py

In `services/bot/guild_sync.py`, delete:

- `sync_all_bot_guilds()` function (was the backend of the removed `/sync` endpoint; no callers remain)
- `_create_guild_with_channels_and_template()` function (only called by `sync_all_bot_guilds`)
- `_refresh_guild_channels()` function (no callers anywhere in the codebase)
- The `DiscordAPIClient` import (only used by the three deleted functions)

The live code paths (`on_ready` → `sync_guilds_from_gateway`, `on_guild_join` → `sync_single_guild_from_gateway`) use `_create_guild_with_gateway_channels()` and are unaffected.

- **Files**:
  - `services/bot/guild_sync.py` — delete three dead functions and DiscordAPIClient import
- **Success**:
  - Task 9.1 tests deleted
  - `sync_all_bot_guilds`, `_create_guild_with_channels_and_template`, `_refresh_guild_channels` absent from `guild_sync.py`
  - `DiscordAPIClient` no longer imported in `guild_sync.py`
  - `grep -r "sync_all_bot_guilds" services/` returns no results
  - Remaining `guild_sync.py` tests pass
- **Research References**:
  - #file:../research/20260422-01-discord-rest-elimination-phase2-research.md (Lines 256-300) — Finding 3: dead function identification and DiscordAPIClient import removal
- **Dependencies**:
  - Task 9.1 complete

---

## Dependencies

- `shared/cache/projection.py` provides `get_user_guilds`, `get_member`, `get_guild_name`
- Redis client injection pattern — verify existing injection in `queries.py` and `discord_format.py`
- Plan 20260421-02 must be complete (on_ready/on_guild_join gateway sync already implemented)

## Success Criteria

- `grep -r "oauth2.get_user_guilds" services/` returns no results outside `services/api/auth/oauth2.py`
- `grep -r "oauth2.get_user_guilds" shared/` returns no results
- `grep -r "bot.fetch_user" services/bot/` returns no results
- `POST /api/v1/guilds/sync` returns 404
- `UserInfoResponse` has no `guilds` field
- `discord_format` member lookup makes no `DiscordAPIClient` calls
- `sync_all_bot_guilds`, `_create_guild_with_channels_and_template`, and `_refresh_guild_channels` deleted from `guild_sync.py`; `DiscordAPIClient` import removed
- Full unit test suite passes with zero skips
