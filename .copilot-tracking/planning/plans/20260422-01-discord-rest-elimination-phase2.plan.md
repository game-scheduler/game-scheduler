---
applyTo: '.copilot-tracking/changes/20260422-01-discord-rest-elimination-phase2-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord REST Elimination — Phase 2

## Overview

Replace all remaining `oauth2.get_user_guilds()` REST calls (4 sites), the last `bot.fetch_user()` call, and the `discord_api.get_guild_member()` call with Redis projection reads, then remove the now-redundant `/sync` API endpoint and frontend Sync button.

## Objectives

- Eliminate all `oauth2.get_user_guilds()` calls from non-auth code paths (sse_bridge, queries, guilds, auth)
- Replace `discord_api.get_guild_member()` in `discord_format.py` with projection read
- Eliminate the last `bot.fetch_user()` call in `participant_drop.py`
- Remove the redundant `POST /api/v1/guilds/sync` endpoint and frontend Sync button

## Research Summary

### Project Files

- `services/api/services/sse_bridge.py` (line 148) — per-connection broadcast loop guild membership check; highest-frequency REST caller
- `services/api/database/queries.py` (line 149) — RLS context setup uses guild membership list
- `services/api/routes/guilds.py` (lines 90–112, 323–358) — `list_guilds` OAuth guild fetch and `/sync` endpoint
- `services/api/routes/auth.py` (line 249) — `/auth/user` response includes unused `guilds` field
- `services/bot/utils/discord_format.py` (line 57) — member display name/avatar lookup via DiscordAPIClient
- `services/bot/handlers/participant_drop.py` (line 95) — last `bot.fetch_user()` REST call in bot
- `shared/cache/projection.py` — `get_user_guilds`, `get_member`, `get_guild_name` Redis projection reads
- `shared/schemas/auth.py` (line 69) — `UserInfoResponse.guilds` field to be removed
- `frontend/src/types/index.ts` — `CurrentUser.guilds?: DiscordGuild[]` unused optional field
- `frontend/src/pages/GuildListPage.tsx` — Sync button wired to removed endpoint

### External References

- #file:../research/20260422-01-discord-rest-elimination-phase2-research.md — full call-site analysis, projection field mapping, and replacement code for all 7 changes

## Implementation Checklist

### [x] Phase 1: Fix sse_bridge.py guild membership check (Group 2a)

- [x] Task 1.1: Write failing test for projection-based guild lookup in sse_bridge.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 13-26)

- [x] Task 1.2: Replace `oauth2.get_user_guilds()` with `member_projection.get_user_guilds()` in sse_bridge.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 27-58)

### [x] Phase 2: Fix queries.py RLS setup (Group 2b)

- [x] Task 2.1: Write failing test for projection-based RLS guild list in queries.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 61-73)

- [x] Task 2.2: Replace `oauth2.get_user_guilds()` with `member_projection.get_user_guilds()` in queries.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 74-102)

### [x] Phase 3: Fix guilds.py list_guilds route (Group 2c)

- [x] Task 3.1: Write failing test for projection-based guild list in list_guilds
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 105-113)

- [x] Task 3.2: Replace oauth2.get_user_guilds() with projection in list_guilds
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 118-140)

### [x] Phase 4: Remove guilds field from auth response (Group 2d)

- [x] Task 4.1: Write failing test confirming guilds field absent from /auth/user response
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 142-154)

- [x] Task 4.2: Remove guilds from auth.py, UserInfoResponse schema, and frontend CurrentUser
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 155-181)

### [x] Phase 5: Fix discord_format.py member lookup (Group 3)

- [x] Task 5.1: Write failing test for projection-based member display info
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 183-195)

- [x] Task 5.2: Replace `discord_api.get_guild_member()` with `member_projection.get_member()` in discord_format.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 196-215)

### [x] Phase 6: Fix participant_drop.py user fetch (Group 4)

- [x] Task 6.1: Write failing test for sync user fetch in participant_drop.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 217-229)

- [x] Task 6.2: Replace `bot.fetch_user()` with `bot.get_user()` in participant_drop.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 230-263)

### [x] Phase 7: Remove /sync endpoint and frontend Sync button (Group 6)

- [x] Task 7.1: Write failing test confirming /sync returns 404
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 265-277)

- [x] Task 7.2: Remove /sync route handler from guilds.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 278-296)

- [x] Task 7.3: Remove Sync button and tests from frontend
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 298-331)

### [ ] Phase 8: Fix shared/database.py missed call site (Finding 1 addendum)

- [ ] Task 8.1: Write failing test for projection-based guild membership in get_db_with_user_guilds
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 324-336)

- [ ] Task 8.2: Replace oauth2.get_user_guilds() with projection in shared/database.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 337-370)

### [ ] Phase 9: Remove dead REST functions from guild_sync.py (Finding 3 addendum)

- [ ] Task 9.1: Delete dead test functions from test_guild_sync.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 373-392)

- [ ] Task 9.2: Delete dead functions and DiscordAPIClient import from guild_sync.py
  - Details: .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md (Lines 393-418)

## Dependencies

- `shared/cache/projection.py` — `get_user_guilds`, `get_member`, `get_guild_name` already implemented
- Redis client injection available in API paths; must be threaded into `queries.py` and bot's `discord_format.py`
- Plan 20260421-02 must be complete — gateway-backed on_ready/on_guild_join sync is the replacement for `/sync`

## Success Criteria

- `grep -r "oauth2.get_user_guilds" services/` returns no results outside `services/api/auth/oauth2.py`
- `grep -r "oauth2.get_user_guilds" shared/` returns no results
- `grep -r "bot.fetch_user" services/bot/` returns no results
- `POST /api/v1/guilds/sync` returns 404
- `UserInfoResponse` has no `guilds` field; `CurrentUser` interface has no `guilds` field
- `discord_format` member lookup makes no `DiscordAPIClient` calls
- `sync_all_bot_guilds`, `_create_guild_with_channels_and_template`, and `_refresh_guild_channels` deleted from `guild_sync.py`; `DiscordAPIClient` import removed
- All unit test suites pass with zero skips
