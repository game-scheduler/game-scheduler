---
applyTo: '.copilot-tracking/changes/20260418-01-gateway-intent-redis-projection-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Gateway Intent Redis Projection

## Overview

Eliminate all Discord REST API calls from the per-request API path by pre-populating a Redis projection from gateway member events in the Discord bot, then migrating each API call site to read from that projection.

## Objectives

- Enable `GUILD_MEMBERS` privileged intent so the bot receives real-time member data via the Discord gateway
- Write a full Redis projection on `on_ready` and every gateway member event, using a generation-pointer scheme for atomic visibility
- Create an API-side reader that handles gen-rotation with a bounded retry loop (max 6 Redis GETs)
- Migrate the four highest-frequency REST call sites to projection reads, in order of call frequency
- Delete all dead code and drop the `user_display_names` DB table once migration is complete

## Research Summary

### Project Files

- `services/bot/bot.py` — `Intents` definition, existing OTel meter pattern (lines 62–88), `on_ready` handler
- `services/bot/guild_sync.py` — existing REST-based guild sync; not replaced by this task
- `services/bot/auth/role_checker.py` — Redis-first role check with REST fallback; REST fallback replaced in Phase 4
- `services/api/services/login_refresh.py` — background task that makes per-guild REST calls; replaced in Phase 4
- `services/api/services/display_names.py` — `DisplayNameResolver` with REST fallback; REST fallback replaced in Phase 4
- `services/api/dependencies/permissions.py` — `verify_guild_membership`: OAuth REST call on every protected route; replaced in Phase 4
- `shared/cache/keys.py` — existing key constants; projection keys added in Phase 1
- `shared/cache/ttl.py` — existing TTL constants; removed in Phase 5

### External References

- #file:../research/20260418-01-gateway-intent-redis-projection-research.md — all key discoveries, recommended approach, implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow (stub + xfail for new production code)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style

## Implementation Checklist

### [x] Phase 1: Foundation — Enable Intent and Add Key Constants

- [x] Task 1.1: Enable `GUILD_MEMBERS` privileged intent in `services/bot/bot.py`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 13–28)

- [x] Task 1.2: Add `proj_gen`, `proj_member`, `proj_user_guilds`, `bot_last_seen` key functions to `shared/cache/keys.py`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 29–52)

### [x] Phase 2: Bot-side Writer

- [x] Task 2.1: Create `services/bot/guild_projection.py` with OTel instruments and `repopulate_all` writer
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 55–106)

- [x] Task 2.2: Wire `on_ready`, `on_member_add`, `on_member_update`, `on_member_remove`, and heartbeat task in `services/bot/bot.py`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 107–142)

### [x] Phase 3: API-side Reader

- [x] Task 3.1: Create `services/api/services/member_projection.py` with gen-rotation retry and all reader functions
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 145–198)

### [x] Phase 4: Call Site Migration

- [x] Task 4.1: Migrate `permissions.py` `verify_guild_membership` → `get_user_guilds()` (highest frequency)
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 204–222)
  - **Completed**: Also migrated `get_guild_name()` from OAuth to projection read

- [x] Task 4.2: Migrate `login_refresh.py` display name reads → `get_member()`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 223–237)

- [x] Task 4.3: Migrate `RoleChecker.get_user_role_ids` REST fallback → `get_user_roles()`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 238–251)

- [x] Task 4.4: Migrate `DisplayNameResolver` REST fallback → `get_member()`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 252–268)

### [x] Phase 5: Cleanup

- [x] Task 5.1: Remove all dead code: `login_refresh.py` REST paths, `_get_user_guilds`, old TTL constants; verify zero Discord REST calls from API
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 271–296)

- [x] Task 5.2: Drop `user_display_names` DB table via Alembic migration; delete `UserDisplayNameService`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 297–315)

### [x] Phase 6: Drop REST Fallbacks in DiscordAPIClient (Work Type A)

- [x] Task 6.1: Remove `GET /guilds/{id}/channels` REST fallback; update `channel_resolver.py` and `games.py` to return 503 on cache miss
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 339–357)

- [x] Task 6.2: Remove `GET /channels/{id}` REST fallback; update `games.py`, `templates.py`, `calendar_export.py` to return 503 on cache miss
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 358–377)

- [x] Task 6.3: Remove `GET /guilds/{id}` REST fallback; update `games.py` and `calendar_export.py` to return 503 on cache miss
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 378–395)

- [x] Task 6.4: Remove `GET /guilds/{id}/roles` REST fallback; update call sites to handle cache miss without REST
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 396–411)

- [x] Task 6.5: Replace `GET /users/{user_id}` in `calendar_export.py` with `member_projection.get_member()` read
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 412–428)

### [ ] Phase 7: Add Permissions Bitfield and Replace has_permissions() (Work Type B)

- [ ] Task 7.1: Add `"permissions": r.permissions.value` to `_role_list()` in `bot.py` so the `discord_guild_roles` cache carries permission data
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 433–448)

- [ ] Task 7.2: Replace `RoleVerificationService.has_permissions()` OAuth REST call with local bitfield computation from `discord_guild_roles` cache and `member_projection.get_user_roles()`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 449–473)

### [ ] Phase 8: Username Sorted Set Index for Member Search (Work Type C)

- [ ] Task 8.1: Add `proj_usernames(gen, guild_id)` key constant to `shared/cache/keys.py`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 478–492)

- [ ] Task 8.2: Update `write_member()` in `guild_projection.py` to `ZADD` lowercased name entries (`{name}\x00{uid}`) to the `proj:usernames` sorted set; deduplicate when `global_name == username`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 493–509)

- [ ] Task 8.3: Add `search_members_by_prefix()` to `member_projection.py`; replace `_search_guild_members()` in `participant_resolver.py` with `ZRANGEBYLEX` read on `proj:usernames`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 510–530)

### [ ] Phase 9: Final Verification and Test Updates

- [ ] Task 9.1: Run grep verification; confirm all revised checklist items (A1–A5, B, C) are satisfied; zero `discord.com/api` hits in `services/api/` outside `shared/discord/client.py`
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 533–546)

- [ ] Task 9.2: Update integration and e2e tests to seed Redis projection data in place of Discord REST mocks for all migrated endpoints
  - Details: .copilot-tracking/planning/details/20260418-01-gateway-intent-redis-projection-details.md (Lines 547–565)

## Dependencies

- `GUILD_MEMBERS` privileged intent toggle in Discord Developer Portal (manual step before deployment)
- `redis-py` async — already present in codebase
- No new RabbitMQ events or consumers required
- No `notify-keyspace-events` Redis configuration required
- Phases 1–2 (bot side) must complete and deploy before any Phase 4 call site migration
- Phase 3 (API reader) can be developed in parallel with Phase 2
- Phase 5 is safe only after all Phase 4 tasks are complete
- Phase 6 is safe only after Phase 5 is complete
- Phase 7 requires Phase 3 (member_projection.py) and Phase 6 complete
- Phase 8 requires Phase 3 (member_projection.py) and Phase 2 (`write_member()` in guild_projection.py) complete
- Phase 9 is the final verification step; requires Phases 6, 7, and 8 complete

## Success Criteria

- `verify_guild_membership` fires zero OAuth REST calls per request after Phase 4
- `list_games` display name resolution reads only Redis; no Discord API calls in the hot path
- `api.projection.read.retries` OTel counter is zero under normal (non-reconnect) operation
- `bot:last_seen` absence causes a clear degraded response, not a silent error or hang
- All Phase 6 REST fallbacks removed; cache miss returns 503 or graceful degradation — never triggers Discord REST
- `has_permissions()` computes permission flags from local Redis data; zero OAuth REST calls per check
- Member search uses `ZRANGEBYLEX` on `proj:usernames` sorted set; zero REST calls
- Zero Discord REST calls from the API server — confirmed by grep before closing Phase 9
- All unit tests pass at each phase boundary before merging
