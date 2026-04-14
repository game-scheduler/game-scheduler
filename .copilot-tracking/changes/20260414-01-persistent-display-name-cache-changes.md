<!-- markdownlint-disable-file -->

# Changes: Persistent Display Name Cache

## Overview

Add `user_display_names` DB table, `UserDisplayNameService`, and three write paths (bot button, API read-through, login refresh) to persist Discord display names across restarts and eliminate cold-cache latency.

---

## Phase 1: DB Model and Migration

### Added

- `shared/models/user_display_name.py` — `UserDisplayName` SQLAlchemy model with composite PK `(user_discord_id, guild_discord_id)`, nullable `avatar_url`, and `updated_at` with server default
- `alembic/versions/20260414_add_user_display_names.py` — migration creating `user_display_names` table and `idx_user_display_names_updated_at` index; down-revision `20260412_add_backup_metadata`

### Modified

- `shared/models/__init__.py` — added `UserDisplayName` import and `__all__` entry

---

## Phase 2: UserDisplayNameService

### Added

- `tests/unit/services/api/services/test_user_display_names.py` — unit tests for `UserDisplayNameService` covering DB hit, DB miss, mixed hit/miss, `upsert_one`, and `upsert_batch`
- `services/api/services/user_display_names.py` — `UserDisplayNameService` with `resolve`, `upsert_one`, and `upsert_batch` methods

---

## Phase 3: Discord Client Method

### Added

- `tests/unit/shared/discord/test_client.py` (new test) — test for `get_current_user_guild_member` using Bearer token

### Modified

- `shared/discord/client.py` — added `get_current_user_guild_member` method using user OAuth token

---

## Phase 4: Bot Write Path (Path A)

### Modified

- `tests/unit/services/bot/handlers/test_join_game.py` — added upsert assertion test
- `tests/unit/services/bot/handlers/test_leave_game.py` — added upsert assertion test
- `services/bot/handlers/join_game.py` — added `UserDisplayNameService.upsert_one` call after participant commit
- `services/bot/handlers/leave_game.py` — added `UserDisplayNameService.upsert_one` call after participant removal

---

## Phase 5: API Read-Through (Path B)

### Added

- `services/api/services/user_display_names.py` — added `get_user_display_name_service` factory dependency

### Modified

- `tests/unit/services/api/routes/test_games_routes.py` — added wiring tests for `UserDisplayNameService` in `list_games`, `get_game`, participant path
- `services/api/routes/games.py` — replaced direct `DisplayNameResolver` calls with `UserDisplayNameService.resolve`

---

## Phase 6: Login Background Refresh (Path C)

### Added

- `services/api/services/login_refresh.py` — standalone async background task for guild member refresh
- `tests/unit/services/api/routes/test_auth.py` — tests for background task enqueue in auth callback

### Modified

- `services/api/routes/auth.py` — added `BackgroundTasks` parameter and enqueue call

---

## Phase 7: Remove Redundant Redis Display Name Layer

### Modified

- `tests/unit/services/api/services/test_display_names.py` — added tests confirming `display_name_avatar` keys not written
- `services/api/services/display_names.py` — removed `_check_cache_for_users` and `display_name_avatar` key writes
- `shared/cache/keys.py` — removed `display_name_avatar` key if unused elsewhere
- `shared/cache/ttl.py` — removed `DISPLAY_NAME` constant if unused elsewhere
