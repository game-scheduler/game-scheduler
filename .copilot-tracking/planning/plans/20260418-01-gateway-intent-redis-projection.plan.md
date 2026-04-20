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

## Dependencies

- `GUILD_MEMBERS` privileged intent toggle in Discord Developer Portal (manual step before deployment)
- `redis-py` async — already present in codebase
- No new RabbitMQ events or consumers required
- No `notify-keyspace-events` Redis configuration required
- Phases 1–2 (bot side) must complete and deploy before any Phase 4 call site migration
- Phase 3 (API reader) can be developed in parallel with Phase 2
- Phase 5 is safe only after all Phase 4 tasks are complete

## Success Criteria

- `verify_guild_membership` fires zero OAuth REST calls per request after Phase 4
- `list_games` display name resolution reads only Redis; no Discord API calls in the hot path
- `api.projection.read.retries` OTel counter is zero under normal (non-reconnect) operation
- `bot:last_seen` absence causes a clear degraded response, not a silent error or hang
- Zero Discord REST calls from the API server — confirmed by grep before closing Phase 5
- All unit tests pass at each phase boundary before merging
