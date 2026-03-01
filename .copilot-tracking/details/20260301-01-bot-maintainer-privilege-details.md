<!-- markdownlint-disable-file -->

# Task Details: Bot Maintainer Privilege Level

## Research Reference

**Source Research**: #file:../research/20260301-01-bot-maintainer-privilege-research.md

---

## Phase 1: Shared Infrastructure

### Task 1.1: Add `APP_INFO` TTL constant

Add `APP_INFO = 3600` to `shared/cache/ttl.py` as a class constant alongside existing constants.

- **Files**:
  - `shared/cache/ttl.py` — add `APP_INFO = 3600` (1 hour) to `CacheTTL` class
- **Success**:
  - `CacheTTL.APP_INFO` is importable and equals `3600`
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 50-52) — TTL pattern
- **Dependencies**: None

### Task 1.2: Add `app_info()` cache key

Add static method `app_info()` to `shared/cache/keys.py` returning `"discord:app_info"`.

- **Files**:
  - `shared/cache/keys.py` — add `@staticmethod def app_info() -> str: return "discord:app_info"` to `CacheKeys` class
- **Success**:
  - `CacheKeys.app_info()` returns `"discord:app_info"`
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 50-52) — keys pattern
- **Dependencies**: None

### Task 1.3: Add `get_application_info()` stub to `DiscordAPIClient`

- **Files**:
  - `shared/discord/client.py` — add async method raising `NotImplementedError`
- **Success**:
  - Method exists and raises `NotImplementedError` when called
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 148-160) — caching pattern
- **Dependencies**: Tasks 1.1, 1.2

### Task 1.4: Write tests for `get_application_info()` (RED)

Write unit tests with `@pytest.mark.xfail(strict=True)` asserting the real caching behavior (correct URL, cache key, TTL, returns dict).

- **Files**:
  - `tests/unit/shared/discord/test_client.py` — new test class or new test functions
- **Success**:
  - Tests fail as expected (xfail)
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 148-160) — method spec
- **Dependencies**: Task 1.3

### Task 1.5: Implement `get_application_info()` and remove xfail markers (GREEN)

Implement using `_make_api_request` with bot token auth, `CacheKeys.app_info()`, and `CacheTTL.APP_INFO`.

- **Files**:
  - `shared/discord/client.py` — replace `NotImplementedError` stub with real implementation
  - `tests/unit/shared/discord/test_client.py` — remove `xfail` markers only; do not alter assertions
- **Success**:
  - All tests pass without xfail markers
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 148-160) — full implementation spec
- **Dependencies**: Task 1.4

---

## Phase 2: Auth Helper Functions

### Task 2.1: Add `is_app_maintainer()` stub to `services/api/auth/oauth2.py`

Async function `is_app_maintainer(discord_id: str) -> bool` raising `NotImplementedError`.

- **Files**:
  - `services/api/auth/oauth2.py` — new async function stub
- **Success**:
  - Function exists and raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 139-151) — implementation spec
- **Dependencies**: Task 1.5

### Task 2.2: Write tests for `is_app_maintainer()` (RED)

Tests with `@pytest.mark.xfail(strict=True)`: owner match returns `True`, team member match returns `True`, non-member returns `False`, team absent falls back to owner check.

- **Files**:
  - `tests/unit/services/api/auth/test_oauth2.py` — new test class or new test functions
- **Success**:
  - Tests fail as expected (xfail)
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 139-151) — IS_APP_MAINTAINER logic
- **Dependencies**: Task 2.1

### Task 2.3: Implement `is_app_maintainer()` and remove xfail markers (GREEN)

Calls `discord.get_application_info()`, checks `owner.id` then `team.members[].user.id`.

- **Files**:
  - `services/api/auth/oauth2.py` — replace stub with real implementation
  - `tests/unit/services/api/auth/test_oauth2.py` — remove `xfail` markers only
- **Success**:
  - All tests pass
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 139-151)
- **Dependencies**: Task 2.2

### Task 2.4: Add `get_guild_token()` stub to `services/api/auth/tokens.py`

Synchronous function `get_guild_token(session_data: dict) -> str` raising `NotImplementedError`.

- **Files**:
  - `services/api/auth/tokens.py` — new function stub
- **Success**:
  - Function exists and raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 132-137) — get_guild_token spec
- **Dependencies**: None

### Task 2.5: Write tests for `get_guild_token()` (RED)

Tests with `@pytest.mark.xfail(strict=True)`: returns bot token when `is_maintainer=True`, returns decrypted OAuth token when `is_maintainer=False` or missing.

- **Files**:
  - `tests/unit/services/api/auth/test_tokens.py` — new test functions
- **Success**:
  - Tests fail as expected (xfail)
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 132-137)
- **Dependencies**: Task 2.4

### Task 2.6: Implement `get_guild_token()` and remove xfail markers (GREEN)

- **Files**:
  - `services/api/auth/tokens.py` — replace stub with real implementation
  - `tests/unit/services/api/auth/test_tokens.py` — remove `xfail` markers only
- **Success**:
  - All tests pass
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 132-137)
- **Dependencies**: Task 2.5

### Task 2.7: Update `store_user_tokens()` and `get_user_tokens()` in `services/api/auth/tokens.py`

Add `can_be_maintainer: bool = False` parameter to `store_user_tokens()`. Store it alongside `is_maintainer: False` (always starts false). Update `get_user_tokens()` to return both fields.

- **Files**:
  - `services/api/auth/tokens.py` — update two functions
  - `tests/unit/services/api/auth/test_tokens.py` — add tests covering new fields; follow TDD cycle (stub → xfail tests → implement → remove xfail)
- **Success**:
  - `store_user_tokens` accepts `can_be_maintainer`; stored session contains both flags
  - `get_user_tokens` returns `can_be_maintainer` and `is_maintainer`
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 119-131) — session shape
- **Dependencies**: Task 2.6

### Task 2.8: Update OAuth callback to pass `can_be_maintainer`

In `services/api/routes/auth.py` callback handler: call `await is_app_maintainer(user_info["id"])` after successfully fetching the user identity (before `store_user_tokens`). Pass the result as `can_be_maintainer` to `store_user_tokens`.

- **Files**:
  - `services/api/routes/auth.py` — update callback handler only; no change to lines 100 or 122 access_token usages
- **Success**:
  - Login sets `can_be_maintainer` correctly in Redis session
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 8-12) — auth.py notes; Lines 107-117 — call site classification
- **Dependencies**: Tasks 2.3, 2.7

---

## Phase 3: Route and Permission Updates

### Task 3.1: Update `get_user_info()` in `services/api/routes/auth.py`

Split the single `access_token` local variable into two: keep original for `get_user_from_token()`, use `get_guild_token(token_data)` for `get_user_guilds()`. Add `can_be_maintainer` and `is_maintainer` to `UserInfoResponse` schema and populate them from `token_data`.

- **Files**:
  - `services/api/routes/auth.py` — lines around 233 (`get_user_info`)
  - `services/api/schemas/auth.py` (or wherever `UserInfoResponse` is defined) — add two fields
- **Success**:
  - `GET /api/v1/auth/user` returns `can_be_maintainer` and `is_maintainer` fields
  - Maintainer calling this endpoint uses bot token for guild list, real token for identity
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 14-18) — get_user_info split; Lines 107-117 — call site table
- **Dependencies**: Tasks 2.7

### Task 3.2: Update `services/api/dependencies/permissions.py`

Four targeted changes — do NOT alter surrounding logic:

1. Line 104 (`verify_guild_membership`): replace `access_token` with `get_guild_token(token_data)`
2. Line 311 (`_require_permission`): add `if token_data.get("is_maintainer"): return current_user` before existing logic
3. Line 447 (`get_guild_name`): replace `access_token` with `get_guild_token(token_data)`
4. Lines 533, 593, 683 (`require_game_host`, `can_manage_game`, `require_administrator`): add `is_maintainer` short-circuit in each

- **Files**:
  - `services/api/dependencies/permissions.py` — six surgical edits across the file
- **Success**:
  - Maintainer bypasses all four permission gates
  - Normal users hit all existing permission logic unchanged
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 22-32) — permissions.py notes; Lines 107-117 — call site table; Lines 163-175 — short-circuit pattern
- **Dependencies**: Tasks 2.6, 2.7

### Task 3.3: Update `services/api/services/sse_bridge.py`

At line 147, replace `access_token` with `get_guild_token(token_data)` for the guild membership check that gates SSE event delivery.

- **Files**:
  - `services/api/services/sse_bridge.py` — one surgical change at line 147
- **Success**:
  - Maintainer receives events for all bot-present guilds
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 34-36) — sse_bridge note; Lines 107-117 — call site table
- **Dependencies**: Task 2.6

### Task 3.4: Update `shared/database.py` `get_db_with_user_guilds()`

Replace `current_user.access_token` with `get_guild_token()` derived from the session for RLS setup.

- **Files**:
  - `shared/database.py` — one surgical change in `get_db_with_user_guilds()`
- **Success**:
  - Maintainer's RLS token is the bot token (provides access to all guilds)
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 38-40) — database note; Lines 107-117 — call site table
- **Dependencies**: Task 2.6

### Task 3.5: Update `services/api/routes/guilds.py` `list_guilds()`

Replace `current_user.access_token` with `get_guild_token()` derived from the session for the guild list query.

- **Files**:
  - `services/api/routes/guilds.py` — one surgical change in `list_guilds()`
- **Success**:
  - Maintainer sees all bot-present guilds in the guild list
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 42-44) — guilds.py note; Lines 107-117 — call site table
- **Dependencies**: Task 2.6

---

## Phase 4: New Maintainer API Endpoints

### Task 4.1: Create toggle endpoint stub

Add `POST /api/v1/maintainers/toggle` route returning `501 Not Implemented`.

- **Files**:
  - `services/api/routes/maintainers.py` — new file with router and stub endpoint
  - `services/api/main.py` (or router aggregator) — register the new router
- **Success**:
  - `POST /api/v1/maintainers/toggle` returns 501
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 176-186) — toggle behavior
- **Dependencies**: Task 2.7

### Task 4.2: Write integration tests for toggle endpoint (RED)

Tests with `@pytest.mark.xfail(strict=True)`: returns 200 and sets `is_maintainer=True` for valid `can_be_maintainer` user; returns 403 for user where `can_be_maintainer=False`; returns 403 if Discord confirms user no longer on app team.

- **Files**:
  - `tests/integration/test_maintainers.py` — new test file
- **Success**:
  - Tests fail as expected (xfail) against the 501 stub
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 176-186) — toggle behavior spec
- **Dependencies**: Task 4.1

### Task 4.3: Implement toggle endpoint and remove xfail markers (GREEN)

Endpoint: requires `can_be_maintainer=True` in session; calls `is_app_maintainer()` live (hits cache); sets `is_maintainer=True` in Redis session on success; returns 403 on failure.

- **Files**:
  - `services/api/routes/maintainers.py` — replace stub with real implementation
  - `tests/integration/test_maintainers.py` — remove `xfail` markers only
- **Success**:
  - All toggle tests pass
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 176-186)
- **Dependencies**: Task 4.2

### Task 4.4: Create refresh endpoint stub

Add `POST /api/v1/maintainers/refresh` route returning `501 Not Implemented`.

- **Files**:
  - `services/api/routes/maintainers.py` — add second stub endpoint
- **Success**:
  - `POST /api/v1/maintainers/refresh` returns 501
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 188-202) — refresh behavior
- **Dependencies**: Task 4.1

### Task 4.5: Write integration tests for refresh endpoint (RED)

Tests with `@pytest.mark.xfail(strict=True)`: non-maintainer gets 403; maintainer call deletes other `is_maintainer=True` sessions, preserves caller session, flushes `app_info` cache key; returns 200.

- **Files**:
  - `tests/integration/test_maintainers.py` — add refresh test functions
- **Success**:
  - Tests fail as expected (xfail) against the 501 stub
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 188-202) — refresh spec
- **Dependencies**: Task 4.4

### Task 4.6: Implement refresh endpoint and remove xfail markers (GREEN)

Endpoint: requires `is_maintainer=True`; scans `session:*` keys; deletes all where `is_maintainer=True` except caller; deletes `CacheKeys.app_info()` from Redis.

- **Files**:
  - `services/api/routes/maintainers.py` — replace stub with real implementation
  - `tests/integration/test_maintainers.py` — remove `xfail` markers only
- **Success**:
  - All refresh tests pass
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 188-202)
- **Dependencies**: Task 4.5

---

## Phase 5: Frontend

### Task 5.1: Update `CurrentUser` interface in `frontend/src/types/index.ts`

Add `can_be_maintainer?: boolean` and `is_maintainer?: boolean` to the `CurrentUser` interface at line 132.

- **Files**:
  - `frontend/src/types/index.ts` — two new optional fields on `CurrentUser`
- **Success**:
  - TypeScript compiles without errors; fields accessible in components
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 58-62) — types.ts note
- **Dependencies**: None (can proceed in parallel with backend, verify end-to-end after Task 3.1)

### Task 5.2: Create `frontend/src/api/maintainers.ts` stub module

New module exporting `toggleMaintainerMode()` and `refreshMaintainers()`, both throwing `Error("Not implemented")`.

- **Files**:
  - `frontend/src/api/maintainers.ts` — new file with two stub exports
- **Success**:
  - Module importable; functions throw on call
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 64-70) — api/client.ts pattern
- **Dependencies**: Task 5.1

### Task 5.3: Write Vitest tests for `maintainers.ts` API module (RED)

Tests with `test.failing`: `toggleMaintainerMode()` calls `POST /api/v1/maintainers/toggle`; `refreshMaintainers()` calls `POST /api/v1/maintainers/refresh`; both return resolved promise on 200; both reject on 4xx.

- **Files**:
  - `frontend/src/api/maintainers.test.ts` — new test file using Vitest and axios mock
- **Success**:
  - Tests fail as expected
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 64-70)
- **Dependencies**: Task 5.2

### Task 5.4: Implement `maintainers.ts` and remove `test.failing` markers (GREEN)

Implement both functions using `apiClient` from `frontend/src/api/client.ts`.

- **Files**:
  - `frontend/src/api/maintainers.ts` — replace stubs with real axios calls
  - `frontend/src/api/maintainers.test.ts` — remove `test.failing` wrappers only
- **Success**:
  - All tests pass
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 64-70)
- **Dependencies**: Task 5.3

### Task 5.5: Update `frontend/src/pages/GuildListPage.tsx`

In the top `Box` alongside the existing "Sync Servers and Channels" button, add:

- A toggle switch "Maintainer Mode" gated on `user?.can_be_maintainer`; calls `toggleMaintainerMode()` then `refreshUser()` on toggle
- A "Refresh Maintainers" button gated on `user?.is_maintainer`; clicking opens MUI `Dialog` with confirmation text "This will refresh the maintainer list and log out all other elevated maintainers. Continue?"; on confirm calls `refreshMaintainers()` then `refreshUser()`
- Page title conditionally renders "All Servers (Maintainer Mode)" when `user?.is_maintainer`, otherwise "Your Servers"

- **Files**:
  - `frontend/src/pages/GuildListPage.tsx` — surgical additions to existing `Box` and title; follow existing async handler pattern
- **Success**:
  - Maintainer controls are visible only for users with `can_be_maintainer=true`
  - Toggle and refresh work end-to-end; `refreshUser()` updates auth context after each action
  - Page title changes when maintainer mode is active
- **Research References**:
  - #file:../research/20260301-01-bot-maintainer-privilege-research.md (Lines 72-86) — GuildListPage note; Lines 204-216 — frontend architecture
- **Dependencies**: Task 5.4

---

## Dependencies

- Python: `pytest`, `pytest-asyncio`, `httpx` (integration tests)
- TypeScript: `vitest`, `axios-mock-adapter` or `msw`
- Redis available for integration tests

## Success Criteria

- Discord application owner can log in, enable maintainer mode, see all bot-present guilds, bypass per-guild permission checks
- Normal user code paths are completely unchanged
- "Refresh Maintainers" deletes all `is_maintainer: true` sessions (except caller) and flushes app info cache
- Toggle re-validates live against Discord; rejects if removed from app team (honor cache expiry)
- Maintainer UI controls appear only for `can_be_maintainer: true` users
- All existing tests pass; all new tests added via TDD cycle pass
