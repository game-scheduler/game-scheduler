<!-- markdownlint-disable-file -->

# Change Record: Discord REST Elimination — Phase 2

## Overview

Tracking file for implementation of plan `20260422-01-discord-rest-elimination-phase2.plan.md`.

## Changes

### Added

- `tests/unit/services/api/services/test_sse_bridge_unit.py` — added `test_broadcast_uses_projection_not_oauth_for_guild_check` verifying the broadcast loop uses `member_projection.get_user_guilds` (written as xfail, then promoted to passing after implementation)

### Modified

- `services/api/services/sse_bridge.py` — replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read; removed `oauth2` import; added `cache_client` and `member_projection` imports
- `services/api/database/queries.py` — replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read in `require_guild_by_id`; renamed `access_token` → `_access_token` (unused, kept for API compatibility); added `cache_client` and `member_projection` imports
- `services/api/routes/guilds.py` — replaced `oauth2.get_user_guilds()` REST call in `list_guilds` with `member_projection.get_user_guilds()` and `member_projection.get_guild_name()` projection reads; removed `oauth2` and `tokens` imports; added `cache_client` and `member_projection` imports
- `tests/unit/services/api/database/test_queries.py` — added `test_require_guild_by_id_uses_projection_not_oauth_for_guild_list`; updated three existing tests to mock projection path instead of `oauth2.get_user_guilds`
- `tests/unit/services/api/routes/test_guilds_routes.py` — added `test_list_guilds_uses_projection_not_oauth`; updated `test_list_guilds_success` and `test_list_guilds_no_configs` to mock projection path instead of `oauth2.get_user_guilds`

- `services/api/routes/auth.py` — removed `oauth2.get_user_guilds()` call and `guild_token` local from `get_user_info`; removed `guilds=guilds` kwarg from `UserInfoResponse` constructor
- `shared/schemas/auth.py` — removed `guilds: list[dict]` field from `UserInfoResponse`
- `frontend/src/types/index.ts` — removed `guilds?: DiscordGuild[]` optional field from `CurrentUser` interface
- `tests/unit/services/api/routes/test_auth_routes.py` — added `test_get_user_info_no_guilds_field` verifying `oauth2.get_user_guilds` is not called and result has no `guilds` attribute
- `services/bot/utils/discord_format.py` — replaced `discord_api.get_guild_member()` call with `member_projection.get_member()` projection read; removed `get_discord_client` and `discord_client` imports; added `cache_client` and `member_projection` imports; updated display name key paths from nested `user` dict to flat projection dict; replaced `_build_avatar_url()` call with direct `member_data.get("avatar_url")`; removed `DiscordAPIError` except clause
- `tests/unit/services/bot/utils/test_discord_format.py` — rewrote all `TestGetMemberDisplayInfo` tests to patch `cache_client.get_redis_client` and `member_projection.get_member` instead of `get_discord_client`; renamed `test_returns_none_on_api_error` → `test_returns_none_on_redis_error` (now tests generic exception); added `test_get_member_display_info_uses_projection_not_discord_api`; removed `DiscordAPIError` import
- `services/bot/handlers/participant_drop.py` — replaced `await bot.fetch_user()` REST call with `bot.get_user()` cache lookup; added `None` guard with `logger.warning` and early return
- `tests/unit/services/bot/handlers/test_participant_drop.py` — new file; added `test_uses_get_user_not_fetch_user` verifying `bot.fetch_user` is not awaited and `bot.get_user` is called
- `services/api/routes/guilds.py` — removed `sync_guilds` handler and `POST /api/v1/guilds/sync` route; removed `os`, `slowapi.Limiter`, `slowapi.util.get_remote_address`, `services.api.config.get_api_config`, `fastapi.Request`, and `services.bot.guild_sync.sync_all_bot_guilds` imports; removed `limiter` and `SYNC_RATE_LIMIT` module-level constants
- `tests/unit/services/api/routes/test_guilds_routes.py` — removed `TestSyncGuilds` class (5 tests); removed `from starlette.requests import Request` import; added `TestSyncEndpointRemoved::test_sync_guilds_handler_not_registered` confirming `sync_guilds` is no longer registered (written as xfail, promoted to passing after implementation)
- `frontend/src/pages/GuildListPage.tsx` — removed `handleSyncGuilds`, `syncing` and `syncMessage` useState entries, `syncUserGuilds` and `GuildSyncResponse` API import, `RefreshIcon` MUI import, Sync button JSX in empty-state and main-view, `syncMessage` Alert JSX in empty-state and main-view
- `frontend/src/api/guilds.ts` — `syncUserGuilds` function and `GuildSyncResponse` interface remain (deletion deferred; API file cleanup out of scope for this task)
- `frontend/src/pages/__tests__/GuildListPage.test.tsx` — removed 4 sync-interaction tests; removed stale `guilds: [...]` from `mockUser`; removed `guilds: []` from `userWithNoGuilds`; added `no Sync Guilds button rendered` test (written as `it.fails`, promoted to `it` after implementation)

- `tests/unit/services/api/test_database_dependencies.py` — added `test_get_db_with_user_guilds_uses_projection_not_oauth` (written as xfail, promoted after implementation); updated three existing tests to patch `shared.cache.client.get_redis_client` and `shared.cache.projection.get_user_guilds` instead of `oauth2.get_user_guilds`; removed `mock_user_guilds` fixture (no longer needed)
- `shared/database.py` — replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read in `get_db_with_user_guilds`; removed `guild_token` extraction and `oauth2` import; added `from shared.cache import client as cache_client` and `from shared.cache import projection as member_projection` imports inside inner function

---

## Phase Progress

- [x] Phase 1: Fix sse_bridge.py guild membership check (Group 2a)
- [x] Phase 2: Fix queries.py RLS setup (Group 2b)
- [x] Phase 3: Fix guilds.py list_guilds route (Group 2c)
- [x] Phase 4: Remove guilds field from auth response (Group 2d)
- [x] Phase 5: Fix discord_format.py member lookup (Group 3)
- [x] Phase 6: Fix participant_drop.py user fetch (Group 4)
- [x] Phase 7: Remove /sync endpoint and frontend Sync button (Group 6)
- [x] Phase 8: Fix shared/database.py missed call site (Finding 1 addendum)
