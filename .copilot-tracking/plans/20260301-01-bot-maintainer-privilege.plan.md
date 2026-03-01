---
applyTo: '.copilot-tracking/changes/20260301-01-bot-maintainer-privilege-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Bot Maintainer Privilege Level

## Overview

Add a dual-flag (`can_be_maintainer` / `is_maintainer`) privilege system allowing Discord application owners and team members to view all bot-present guilds and bypass per-guild permission checks.

## Objectives

- Allow Discord application owners/team members to enable "Maintainer Mode" via a toggle endpoint
- Replace guild/RLS token calls with `get_guild_token()` so maintainers use the bot token transparently
- Short-circuit the four permission gates in `permissions.py` for `is_maintainer` sessions
- Provide a "Refresh Maintainers" endpoint that revokes all other elevated sessions and flushes the app info cache
- Expose maintainer controls in the frontend gated strictly on `can_be_maintainer` / `is_maintainer` flags
- Leave all normal-user code paths completely unchanged

## Research Summary

### Project Files

- `shared/cache/ttl.py` — add `APP_INFO` TTL constant
- `shared/cache/keys.py` — add `app_info()` cache key method
- `shared/discord/client.py` — add `get_application_info()` method
- `services/api/auth/oauth2.py` — add `is_app_maintainer()` helper
- `services/api/auth/tokens.py` — add `get_guild_token()`, extend `store_user_tokens()` / `get_user_tokens()`
- `services/api/routes/auth.py` — update OAuth callback and `get_user_info()`
- `services/api/dependencies/permissions.py` — apply `get_guild_token()` and `is_maintainer` short-circuits
- `services/api/services/sse_bridge.py` — apply `get_guild_token()` for SSE event routing
- `shared/database.py` — apply `get_guild_token()` for RLS setup
- `services/api/routes/guilds.py` — apply `get_guild_token()` for guild list
- `services/api/routes/maintainers.py` — new router with toggle and refresh endpoints
- `frontend/src/types/index.ts` — add `can_be_maintainer` / `is_maintainer` to `CurrentUser`
- `frontend/src/api/maintainers.ts` — new API module
- `frontend/src/pages/GuildListPage.tsx` — maintainer UI controls

### External References

- #file:../research/20260301-01-bot-maintainer-privilege-research.md — full research findings, code specs, and call-site classification

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md — FastAPI patterns
- #file:../../.github/instructions/api-authorization.instructions.md — authorization patterns
- #file:../../.github/instructions/reactjs.instructions.md — React/TypeScript conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style
- #file:../../.github/instructions/task-implementation.instructions.md — tracking conventions

## Implementation Checklist

### [ ] Phase 1: Shared Infrastructure

- [ ] Task 1.1: Add `APP_INFO = 3600` to `CacheTTL` in `shared/cache/ttl.py`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 13-24)

- [ ] Task 1.2: Add `app_info()` static method to `CacheKeys` in `shared/cache/keys.py`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 25-36)

- [ ] Task 1.3: Add `get_application_info()` stub to `DiscordAPIClient` in `shared/discord/client.py`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 37-46)

- [ ] Task 1.4: Write xfail tests for `get_application_info()` (RED)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 47-58)

- [ ] Task 1.5: Implement `get_application_info()` and remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 59-72)

### [ ] Phase 2: Auth Helper Functions

- [ ] Task 2.1: Add `is_app_maintainer()` stub to `services/api/auth/oauth2.py`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 76-87)

- [ ] Task 2.2: Write xfail tests for `is_app_maintainer()` (RED)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 88-99)

- [ ] Task 2.3: Implement `is_app_maintainer()` and remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 100-111)

- [ ] Task 2.4: Add `get_guild_token()` stub to `services/api/auth/tokens.py`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 113-124)

- [ ] Task 2.5: Write xfail tests for `get_guild_token()` (RED)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 125-136)

- [ ] Task 2.6: Implement `get_guild_token()` and remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 137-147)

- [ ] Task 2.7: Update `store_user_tokens()` / `get_user_tokens()` with TDD cycle
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 148-161)

- [ ] Task 2.8: Update OAuth callback to pass `can_be_maintainer` to `store_user_tokens()`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 162-175)

### [ ] Phase 3: Route and Permission Updates

- [ ] Task 3.1: Update `get_user_info()` — split token variable and extend `UserInfoResponse`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 178-191)

- [ ] Task 3.2: Update `services/api/dependencies/permissions.py` — `get_guild_token()` and `is_maintainer` short-circuits
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 192-208)

- [ ] Task 3.3: Update `services/api/services/sse_bridge.py` at line 147
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 209-220)

- [ ] Task 3.4: Update `shared/database.py` `get_db_with_user_guilds()`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 221-232)

- [ ] Task 3.5: Update `services/api/routes/guilds.py` `list_guilds()`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 233-245)

### [ ] Phase 4: New Maintainer API Endpoints

- [ ] Task 4.1: Create `POST /api/v1/maintainers/toggle` stub (501)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 249-261)

- [ ] Task 4.2: Write xfail integration tests for toggle endpoint (RED)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 262-273)

- [ ] Task 4.3: Implement toggle endpoint and remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 274-286)

- [ ] Task 4.4: Create `POST /api/v1/maintainers/refresh` stub (501)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 287-298)

- [ ] Task 4.5: Write xfail integration tests for refresh endpoint (RED)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 299-310)

- [ ] Task 4.6: Implement refresh endpoint and remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 311-324)

### [ ] Phase 5: Frontend

- [ ] Task 5.1: Add `can_be_maintainer` / `is_maintainer` to `CurrentUser` interface
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 328-339)

- [ ] Task 5.2: Create `frontend/src/api/maintainers.ts` stub module
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 340-351)

- [ ] Task 5.3: Write Vitest `test.failing` tests for `maintainers.ts` (RED)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 352-363)

- [ ] Task 5.4: Implement `maintainers.ts` and remove `test.failing` markers (GREEN)
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 364-376)

- [ ] Task 5.5: Add maintainer controls to `GuildListPage.tsx`
  - Details: .copilot-tracking/details/20260301-01-bot-maintainer-privilege-details.md (Lines 377-395)

## Dependencies

- Python 3.12+, pytest, pytest-asyncio, httpx
- Redis (for integration tests)
- TypeScript 5.x, Vitest, axios
- `discord_bot_token` available as `api_config.discord_bot_token`

## Success Criteria

- Discord application owner can log in, enable maintainer mode, see all bot-present guilds, bypass all per-guild permission checks
- Normal user code paths are completely unchanged
- "Refresh Maintainers" revokes all other elevated sessions and flushes the app info cache
- Toggle re-validates live against Discord; 403 if user was removed from app team
- Maintainer UI controls visible only for `can_be_maintainer=true` users
- All existing tests pass; all new TDD tests pass
