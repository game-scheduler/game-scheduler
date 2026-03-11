---
applyTo: '.copilot-tracking/planning/plans/20260301-01-bot-maintainer-privilege.plan.md'
---

<!-- markdownlint-disable-file -->

# Change Record: Bot Maintainer Privilege Level

## Summary

Adds a dual-flag (`can_be_maintainer` / `is_maintainer`) privilege system for Discord application owners and team members, allowing them to view all bot-present guilds and bypass per-guild permission checks.

---

## Added

- `tests/unit/shared/discord/test_client.py` — Unit tests for `DiscordAPIClient.get_application_info()` covering correct URL, cache key, TTL, and return value.
- `tests/unit/services/api/auth/test_oauth2.py` — Unit tests for `is_app_maintainer()` covering owner match, team member match, non-member rejection, and team-absent fallback to owner check.
- `tests/unit/services/api/auth/test_tokens.py` — Unit tests for `get_guild_token()` (bot token for maintainer, OAuth token for regular/missing flag), and for updated `store_user_tokens()` / `get_user_tokens()` with maintainer flags.
- `services/api/routes/maintainers.py` — New router with `POST /api/v1/maintainers/toggle` (requires `can_be_maintainer`, toggles `is_maintainer` flag: enables after re-validating via `is_app_maintainer()`, disables directly without re-validation) and `POST /api/v1/maintainers/refresh` (requires `is_maintainer`, scans Redis to delete other elevated sessions, flushes `app_info` cache).
- `tests/integration/test_maintainers.py` — Integration tests for toggle (enables maintainer mode, disables maintainer mode, 403 without `can_be_maintainer`, 403 if not in Discord team) and refresh (403 for non-maintainer, deletes other elevated sessions, flushes `app_info` cache).
- `frontend/src/api/maintainers.ts` — New module exporting `toggleMaintainerMode()` and `refreshMaintainers()`, both posting to `/api/v1/maintainers/toggle` and `/api/v1/maintainers/refresh` respectively via `apiClient`.
- `frontend/src/api/maintainers.test.ts` — Vitest tests for `toggleMaintainerMode()` and `refreshMaintainers()`: correct POST URL, resolves on 200, rejects on 4xx.

## Modified

- `shared/cache/ttl.py` — Added `APP_INFO = 3600` constant to `CacheTTL` for 1-hour caching of Discord application info.
- `shared/cache/keys.py` — Added `app_info()` static method to `CacheKeys` returning `"discord:app_info"`.
- `shared/discord/client.py` — Added `get_application_info()` method to `DiscordAPIClient` that fetches `/oauth2/applications/@me` with bot token auth and 1-hour Redis caching. **Outside plan**: Added Redis cache-read check at the start of `get_application_info()` to honour the 1-hour TTL (without this, the method always called Discord). This was necessary to allow integration tests to seed the cache.
- `services/api/auth/oauth2.py` — Added `is_app_maintainer(discord_id)` async function that checks if a user is a Discord application owner or team member using the cached application info.
- `services/api/auth/tokens.py` — Added `get_guild_token(session_data)` sync function returning bot token for maintainers or the plain OAuth token otherwise (no decrypt call since `get_user_tokens()` already returns decrypted tokens); updated `store_user_tokens()` to accept and persist `can_be_maintainer` flag with `is_maintainer: False` default; updated `get_user_tokens()` to return both flags.
- `services/api/routes/auth.py` — Updated OAuth callback to call `is_app_maintainer()` after user identity fetch and pass `can_be_maintainer` to `store_user_tokens()`. Updated `get_user_info()` to split the single `access_token` variable into `access_token` (for identity calls) and `guild_token` (via `get_guild_token()`, for guild list calls); added `can_be_maintainer` and `is_maintainer` to the `UserInfoResponse` return value.
- `shared/schemas/auth.py` — Added `can_be_maintainer: bool` and `is_maintainer: bool` fields (both default `False`) to `UserInfoResponse`.
- `services/api/dependencies/permissions.py` — Applied `get_guild_token(token_data)` in `verify_guild_membership()` and `get_guild_name()` so maintainers use the bot token for guild membership checks. Added `is_maintainer` short-circuits (return `current_user` immediately) to `_require_permission()`, `require_game_host()`, `require_administrator()`, and a `return True` short-circuit to `can_manage_game()`.
- `services/api/services/sse_bridge.py` — Replaced `token_data["access_token"]` with `tokens.get_guild_token(token_data)` for the guild membership check so maintainers receive events for all bot-present guilds.
- `shared/database.py` — Updated `get_db_with_user_guilds()` to fetch `token_data` and use `tokens.get_guild_token(token_data)` instead of `current_user.access_token` for RLS setup; also extended local import to include `tokens`. Added `HTTPException` to fastapi imports.
- `services/api/routes/guilds.py` — Added `tokens` to `services.api.auth` import; updated `list_guilds()` to fetch `token_data` and use `tokens.get_guild_token(token_data)` instead of `current_user.access_token` for the guild query.
- `services/api/app.py` — Added import of `maintainers` router and registered it with `app.include_router(maintainers.router)`.
- `tests/shared/auth_helpers.py` — Added `can_be_maintainer` and `is_maintainer` optional parameters to `create_test_session()` so integration tests can create sessions with maintainer flags.
- `tests/unit/shared/discord/test_client.py` — Added `mock_redis_cache_miss` autouse fixture to patch the Redis cache check added to `get_application_info()`; without this, unit tests would require a live Redis connection.
- `tests/unit/services/api/auth/test_tokens.py` — Updated `_make_session()` to use `"plain_oauth_token"` as `access_token` (reflecting that `get_user_tokens()` returns already-decrypted tokens); removed `decrypt_token` mocks from `get_guild_token` tests; updated assertions accordingly.
- `frontend/src/types/index.ts` — Added `can_be_maintainer?: boolean` and `is_maintainer?: boolean` optional fields to the `CurrentUser` interface.
- `frontend/src/pages/GuildListPage.tsx` — Added maintainer controls: toggle switch ("Maintainer Mode") gated on `user?.can_be_maintainer`, "Refresh Maintainers" button gated on `user?.is_maintainer` (with MUI Dialog confirmation), and conditional page title ("All Servers (Maintainer Mode)" vs "Your Servers"). Added `refreshUser` to `useAuth()` destructure. Updated existing tests from "My Servers" to "Your Servers".
- `frontend/src/pages/__tests__/GuildListPage.test.tsx` — Updated 5 existing assertions from `'My Servers'` to `'Your Servers'` to match the new conditional title.

**Outside plan**: Fixed misplaced `# noqa: ANN401` comment in `shared/discord/client.py` `_get_error_message()` (moved from the return type line to the `Any` parameter line where the lint error actually occurs); this was a pre-existing bug discovered while linting Phase 4 changes.

**Outside plan**: The plan spec for `get_guild_token()` called `decrypt_token(session_data["access_token"])`, but `get_user_tokens()` already returns the decrypted token. Calling `decrypt_token` on an already-decrypted Fernet token would raise an error at runtime. The implementation was corrected to return `session_data["access_token"]` directly, and the unit tests updated to reflect that the input is a plain (not encrypted) token.

**Bug fix**: `toggle_maintainer_mode` always set `is_maintainer=True`, making it impossible to disable maintainer mode from the UI. Fixed to check the current `is_maintainer` flag and flip it: disabling skips Discord re-validation and clears the flag directly; enabling still re-validates against Discord. Added integration test `test_toggle_disables_maintainer_mode` to cover the disable path.

**Bug fix**: `list_templates` bypassed `permissions.py` entirely, calling `role_service.check_game_host_permission()` and `role_service.check_bot_manager_permission()` directly (both in `roles.py`, which has no `is_maintainer` knowledge). A maintainer who was not a real guild manager received an empty template list and then a 403. Fixed by:

- Adding `check_bot_manager_permission()` boolean wrapper to `services/api/dependencies/permissions.py` — delegates to `require_bot_manager()` which already contains the `is_maintainer` short-circuit.
- Adding `is_manager: bool = False` parameter to `get_templates_for_user()` in `services/api/services/template_service.py` — when `True`, skips the per-template role-filter loop and returns all templates.
- Updating `list_templates` in `services/api/routes/templates.py` to call `check_bot_manager_permission()` once and pass the result as `is_manager` into both `get_templates_for_user()` and the empty-templates fallback, removing the two direct `roles.py` calls from the route.
- Also removed a pre-existing unused `# ruff: noqa: B008` directive from `services/api/routes/templates.py`.
- Added unit tests: `test_list_templates_maintainer_sees_all` in `tests/services/api/routes/test_templates.py` and `test_get_templates_for_user_is_manager_skips_filtering` in `tests/services/api/services/test_template_service.py`.

## Removed

<!-- List of files removed -->
