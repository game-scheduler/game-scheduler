---
applyTo: '.copilot-tracking/changes/20260414-01-persistent-display-name-cache-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Persistent Display Name Cache

## Overview

Add a `user_display_names` DB table and `UserDisplayNameService` to persist Discord display name and avatar data across service restarts, eliminating cold-cache Discord re-fetches for users who have recently logged in or pressed a bot button.

## Objectives

- `list_games` returns in <100ms for users who have logged in or clicked a button in the last 90 days
- Service restart does not force Discord re-fetches — first request after restart reads from DB
- No increase in Discord API call volume under normal operation
- Remove the 5-minute Redis TTL workaround for display names (`display_name_avatar` keys)

## Research Summary

### Project Files

- `shared/models/__init__.py` (line 37) — add `UserDisplayName` import here
- `shared/models/user_display_name.py` — new model file
- `alembic/versions/20260412_add_backup_metadata.py` — down-revision for new migration
- `services/api/services/display_names.py` (lines 199, 226) — `_check_cache_for_users` and `_fetch_and_cache_display_names_avatars` to clean up in Phase 7
- `services/api/routes/games.py` (lines 470, 747, 835) — `resolve_display_names_and_avatars` call sites to replace
- `services/api/routes/auth.py` (line 69) — callback route to add `BackgroundTasks`
- `shared/discord/client.py` (line 812) — add `get_current_user_guild_member` after `get_guild_members_batch`
- `services/bot/handlers/join_game.py` (line 53) — add upsert after participant commit
- `services/bot/handlers/leave_game.py` (line 47) — add upsert after participant removal

### External References

- #file:../research/20260414-01-persistent-display-name-cache-research.md — full research with root cause analysis, service architecture, three write paths, and DDL specification

## Implementation Checklist

### [ ] Phase 1: DB Model and Migration

- [ ] Task 1.1: Create UserDisplayName SQLAlchemy model
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 13-26)

- [ ] Task 1.2: Register model in shared/models/**init**.py
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 27-39)

- [ ] Task 1.3: Write Alembic migration
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 40-53)

### [ ] Phase 2: UserDisplayNameService

- [ ] Task 2.1 (Tests): Write failing tests for UserDisplayNameService
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 58-78)

- [ ] Task 2.2 (Implement): Add UserDisplayNameService
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 79-96)

### [ ] Phase 3: Discord Client Method

- [ ] Task 3.1 (Tests): Write failing test for get_current_user_guild_member
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 101-115)

- [ ] Task 3.2 (Implement): Add get_current_user_guild_member to DiscordAPIClient
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 116-129)

### [ ] Phase 4: Bot Write Path (Path A)

- [ ] Task 4.1 (Tests): Write failing tests for bot handler upsert
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 134-148)

- [ ] Task 4.2 (Implement): Upsert on bot button press
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 149-168)

### [ ] Phase 5: API Read-Through (Path B)

- [ ] Task 5.1 (Tests): Write failing tests for UserDisplayNameService wiring in games routes
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 173-187)

- [ ] Task 5.2 (Implement): Wire UserDisplayNameService into games routes
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 188-202)

### [ ] Phase 6: Login Background Refresh (Path C)

- [ ] Task 6.1 (Tests): Write failing tests for auth callback background task
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 207-225)

- [ ] Task 6.2 (Implement): Add background task to auth callback
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 226-241)

### [ ] Phase 7: Remove Redundant Redis Display Name Layer

- [ ] Task 7.1 (Tests): Write tests confirming display_name_avatar keys are not written
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 246-260)

- [ ] Task 7.2 (Implement): Remove display_name_avatar Redis keys
  - Details: .copilot-tracking/planning/details/20260414-01-persistent-display-name-cache-details.md (Lines 261-277)

## Dependencies

- `SQLAlchemy AsyncSession` — available in API routes and bot handlers
- `DisplayNameResolver` — unchanged; wrapped by `UserDisplayNameService`
- FastAPI `BackgroundTasks` — available in route handlers; no new packages required
- `guilds.members.read` OAuth scope — already requested

## Success Criteria

- `list_games` returns in <100ms for warm users (logged in or button-pressed in last 90 days)
- Service restart does not reset display name resolution
- No increase in Discord API call volume under normal operation
- No `display_avatar:*` Redis keys written after Phase 7
- All new code has passing unit tests; no xfail markers remaining after each phase
