<!-- markdownlint-disable-file -->

# Task Details: Persistent Display Name Cache

## Research Reference

**Source Research**: #file:../research/20260414-01-persistent-display-name-cache-research.md

---

## Phase 1: DB Model and Migration

### Task 1.1: Create UserDisplayName SQLAlchemy Model

Create `shared/models/user_display_name.py` with a `UserDisplayName` model. No FK to `users.id` — the bot writes this before a `User` row may exist. No RLS — display names are not sensitive. `updated_at` has a server default of `NOW()` and an index for pruning inactive users.

- **Files**:
  - `shared/models/user_display_name.py` — new model (composite PK, no FK to users)
- **Success**:
  - Model maps to `user_display_names` with composite PK `(user_discord_id, guild_discord_id)`
  - `avatar_url` is nullable; `updated_at` has server default
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 113-126) — table schema DDL
- **Dependencies**:
  - None

### Task 1.2: Register Model in shared/models/**init**.py

Add `from .user_display_name import UserDisplayName` to `shared/models/__init__.py` so Alembic auto-detects the table on the next `autogenerate` run.

- **Files**:
  - `shared/models/__init__.py` — add import after `from .user import User` (line 37)
- **Success**:
  - `UserDisplayName` importable from `shared.models`
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 195-197) — key tasks 1 and 2
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Write Alembic Migration

Create `alembic/versions/20260414_add_user_display_names.py`. Down-revision is `20260412_add_backup_metadata`. `upgrade` creates the table and `idx_user_display_names_updated_at`; `downgrade` drops them in reverse order.

- **Files**:
  - `alembic/versions/20260414_add_user_display_names.py` — new migration file
- **Success**:
  - `alembic upgrade head` creates table and index without errors
  - `alembic downgrade -1` drops table and index cleanly
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 113-126) — DDL specification
- **Dependencies**:
  - Task 1.1 completion

---

## Phase 2: UserDisplayNameService

### Task 2.1 (Tests): Write Failing Tests for UserDisplayNameService

Write unit tests in `tests/unit/services/api/services/test_user_display_names.py` covering:

- DB hit: returns name+avatar without calling `DisplayNameResolver`
- DB miss: falls through to `DisplayNameResolver`, then upserts result to DB
- Mixed hit/miss: only missing IDs reach `DisplayNameResolver`
- `upsert_one` writes correct fields including `updated_at`
- `upsert_batch` handles empty list without error

Mark all tests `@pytest.mark.xfail(strict=True)` — service does not exist yet.

- **Files**:
  - `tests/unit/services/api/services/test_user_display_names.py` — new test file
- **Success**:
  - Tests collected and xfail (not error, not skipped)
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 129-145) — three-layer architecture (DB → Redis/Discord → upsert)
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 205-207) — key task 10
- **Dependencies**:
  - Phase 1 completion

### Task 2.2 (Implement): Add UserDisplayNameService

Create `services/api/services/user_display_names.py`. Constructor takes `AsyncSession` + `DisplayNameResolver`. Implement:

- `resolve(guild_discord_id, user_discord_ids)` — batch DB lookup → Discord fallback → upsert
- `upsert_one(user_discord_id, guild_discord_id, display_name, avatar_url)` — single row INSERT ... ON CONFLICT DO UPDATE
- `upsert_batch(entries)` — bulk variant

- **Files**:
  - `services/api/services/user_display_names.py` — new service
- **Success**:
  - All xfail tests from Task 2.1 pass; remove xfail markers
  - `resolve` returns correct data for DB hit, miss, and mixed
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 129-145) — service architecture
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 199-207) — key tasks 4 and 10
- **Dependencies**:
  - Task 2.1 completion

---

## Phase 3: Discord Client Method

### Task 3.1 (Tests): Write Failing Test for get_current_user_guild_member

Add a unit test to the existing Discord client test file. Verify `get_current_user_guild_member(guild_id, token)` makes `GET /users/@me/guilds/{guild_id}/member` with `Authorization: Bearer {token}` header (not the bot token).
Mark `@pytest.mark.xfail(strict=True)`.

- **Files**:
  - Existing Discord client test file — add test method
- **Success**:
  - Test collected and xfail
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 170-181) — method specification
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 77-88) — OAuth endpoint and no-privileged-intent notes
- **Dependencies**:
  - None

### Task 3.2 (Implement): Add get_current_user_guild_member to DiscordAPIClient

Add method to `shared/discord/client.py` after `get_guild_members_batch` (currently line 812). Use `_make_api_request` with a `Bearer {token}` auth header constructed directly. No Redis caching — DB upsert is the persistence layer.

- **Files**:
  - `shared/discord/client.py` — add method after line 812
- **Success**:
  - xfail test from Task 3.1 passes; remove xfail marker
  - Method uses Bearer token, not bot token
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 170-181) — implementation snippet
- **Dependencies**:
  - Task 3.1 completion

---

## Phase 4: Bot Write Path (Path A)

### Task 4.1 (Tests): Write Failing Tests for Bot Handler Upsert

Add tests to the existing join/leave game handler test files verifying that after a successful join or leave, `user_display_names` is upserted with data from `interaction.user`. Priority: `nick → global_name → name`. No extra Discord API calls.
Mark `@pytest.mark.xfail(strict=True)`.

- **Files**:
  - `tests/unit/services/bot/handlers/test_join_game.py` — add upsert assertion test
  - `tests/unit/services/bot/handlers/test_leave_game.py` — add upsert assertion test
- **Success**:
  - Tests collected and xfail
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 147-158) — Path A specification and code snippet
- **Dependencies**:
  - Phase 2 completion

### Task 4.2 (Implement): Upsert on Bot Button Press

In `handle_join_game` (`services/bot/handlers/join_game.py`, function starts line 53) and `handle_leave_game` (starts line 47), after the DB commit writing `GameParticipant`, call `UserDisplayNameService.upsert_one` using `interaction.user` data directly:

```python
display_name = interaction.user.nick or interaction.user.global_name or interaction.user.name
avatar_url = str(interaction.user.display_avatar.url) if interaction.user.display_avatar else None
```

- **Files**:
  - `services/bot/handlers/join_game.py` — add upsert after participant commit
  - `services/bot/handlers/leave_game.py` — add upsert after participant removal
- **Success**:
  - xfail tests from Task 4.1 pass; remove xfail markers
  - Zero additional Discord API calls from bot handlers
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 147-158) — Path A code snippet
- **Dependencies**:
  - Task 4.1 completion; Phase 2 completion

---

## Phase 5: API Read-Through (Path B)

### Task 5.1 (Tests): Write Failing Tests for UserDisplayNameService Wiring in Games Routes

Add tests to `tests/unit/services/api/routes/test_games_routes.py` verifying that `list_games`, `get_game`, and the participant-display path use `UserDisplayNameService.resolve` and that a DB hit does not trigger `DisplayNameResolver`.
Mark `@pytest.mark.xfail(strict=True)`.

- **Files**:
  - `tests/unit/services/api/routes/test_games_routes.py` — add wiring tests
- **Success**:
  - Tests collected and xfail
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 159-161) — Path B description
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 202-203) — key task 7
- **Dependencies**:
  - Phase 2 completion

### Task 5.2 (Implement): Wire UserDisplayNameService into Games Routes

Replace direct `display_name_resolver.resolve_display_names_and_avatars` calls at `games.py` lines 470, 747, and 835 with `user_display_service.resolve`. Add a `get_user_display_name_service` factory dependency that injects `AsyncSession` + `DisplayNameResolver` into `UserDisplayNameService`.

- **Files**:
  - `services/api/routes/games.py` — replace calls at lines 470, 747, 835; update dependency injection
  - `services/api/dependencies/` or `services/api/services/user_display_names.py` — add factory function
- **Success**:
  - xfail tests from Task 5.1 pass; remove xfail markers
  - `list_games` DB-hit path never calls `DisplayNameResolver`
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 129-145) — service architecture
- **Dependencies**:
  - Task 5.1 completion; Phase 2 completion

---

## Phase 6: Login Background Refresh (Path C)

### Task 6.1 (Tests): Write Failing Tests for Auth Callback Background Task

Add tests (create `tests/unit/services/api/routes/test_auth.py` if absent) verifying the successful callback enqueues a background task that:

1. Queries `guild_configurations` for the user's registered guilds
2. Calls `get_current_user_guild_member` with the user's OAuth token per matching guild
3. Upserts `user_display_names` for each result

Mark `@pytest.mark.xfail(strict=True)`.

- **Files**:
  - `tests/unit/services/api/routes/test_auth.py` — new or existing test file
- **Success**:
  - Tests collected and xfail
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 162-170) — Path C steps
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 109-112) — OAuth rate limit advantage
- **Dependencies**:
  - Phase 3 completion; Phase 2 completion

### Task 6.2 (Implement): Add Background Task to Auth Callback

In `services/api/routes/auth.py`, add `BackgroundTasks` dependency to the `callback` route (currently line 69). Enqueue the guild member refresh after `store_user_tokens`. Implement the background task as a standalone async function for testability.

- **Files**:
  - `services/api/routes/auth.py` — add `BackgroundTasks` parameter and enqueue call
  - `services/api/services/login_refresh.py` (or similar) — standalone background task function
- **Success**:
  - xfail tests from Task 6.1 pass; remove xfail markers
  - Background task does not block the callback response
  - Uses user's OAuth token; leaves bot token budget untouched
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 162-170) — Path C implementation steps
- **Dependencies**:
  - Task 6.1 completion; Phase 3 completion

---

## Phase 7: Remove Redundant Redis Display Name Layer

### Task 7.1 (Tests): Write Tests Confirming display_name_avatar Keys Are Not Written

Add tests to `tests/unit/services/api/services/test_display_names.py` verifying `_fetch_and_cache_display_names_avatars` no longer writes `display_avatar:*` Redis keys, and `_check_cache_for_users` is removed or bypassed.
Mark `@pytest.mark.xfail(strict=True)`.

- **Files**:
  - `tests/unit/services/api/services/test_display_names.py` — add/update tests
- **Success**:
  - Tests collected and xfail
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 107-112) — Redis vs Postgres analysis: `display_name_avatar` keys are redundant once DB exists
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 204-206) — key task 9
- **Dependencies**:
  - Phase 5 completion (DB path must be primary before removing Redis layer)

### Task 7.2 (Implement): Remove display_name_avatar Redis Keys

Remove `display_name_avatar` Redis key writing from `_fetch_and_cache_display_names_avatars`. Remove `_check_cache_for_users`. Remove `CacheKeys.display_name_avatar` and `CacheTTL.DISPLAY_NAME` if they become unused elsewhere. Keep `discord_member` Redis keys (raw member TTL cache) intact.

- **Files**:
  - `services/api/services/display_names.py` — remove `_check_cache_for_users` and avatar key write
  - `shared/cache/keys.py` — remove `display_name_avatar` if unused
  - `shared/cache/ttl.py` — remove `DISPLAY_NAME` constant if unused
- **Success**:
  - xfail tests from Task 7.1 pass; remove xfail markers
  - No `display_avatar:*` Redis keys written during `list_games` or `get_game`
  - `discord_member:*` Redis keys still written
- **Research References**:
  - #file:../research/20260414-01-persistent-display-name-cache-research.md (Lines 107-112) — rationale for removal
- **Dependencies**:
  - Task 7.1 completion; Phase 5 completion

---

## Dependencies

- `SQLAlchemy AsyncSession` — available in both API routes and bot handlers
- `DisplayNameResolver` — unchanged; `UserDisplayNameService` wraps it
- FastAPI `BackgroundTasks` — available in route handlers; no new packages required
- `guilds.members.read` OAuth scope — already requested (research line 65)

## Success Criteria

- `list_games` returns in <100ms for users who have logged in or clicked a button in the last 90 days
- Service restart does not require Discord re-fetches — first request reads from DB
- No increase in Discord API call volume under normal operation
- No `display_avatar:*` Redis keys written after Phase 7
- Table growth bounded by `updated_at` (pruning task is out of scope for this plan)
