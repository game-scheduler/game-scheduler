---
applyTo: '.copilot-tracking/changes/20260417-01-gateway-intent-redis-projection-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Gateway Intent Redis Projection Architecture

## Overview

Replace all Discord REST calls in the per-request API path with a Redis projection populated exclusively by the Discord bot via the gateway, eliminating rate-limit exposure and stale cache windows.

## Objectives

- Eliminate all Discord REST calls from the API per-request path
- Eliminate the 5-minute stale window on role and display name data
- Survive bot reconnects without serving mixed/partial state to the API
- Provide a first-login UX that degrades gracefully when the bot is unavailable
- Achieve a phased, always-functional cutover with no flag days

## Research Summary

### Project Files

- `services/bot/bot.py` — current `Intents` setup (line 180: `on_ready`); location for intent enable and gateway handlers
- `services/bot/guild_sync.py` — existing bot guild sync (REST-based); no member/role writes to Redis
- `services/bot/auth/role_checker.py` — current Redis/REST role check; target for Phase 4 migration
- `services/api/services/login_refresh.py` — background task with REST calls on login; target for removal in Phase 5
- `services/api/services/display_names.py` — `DisplayNameResolver` with REST fallback; target for Phase 4 migration
- `services/api/dependencies/permissions.py` — OAuth REST call per route (`_get_user_guilds`); highest-priority migration target
- `shared/cache/keys.py` — existing key functions; location for new projection key functions
- `shared/cache/ttl.py` — existing TTL constants; old constants removed in Phase 5
- `shared/messaging/events.py` — `EventType` enum; location for `MEMBER_CACHE_POPULATE`

### External References

- #file:../research/20260417-01-gateway-intent-redis-projection-research.md — complete architecture research with Redis schema, generation rotation strategy, on-demand populate flow, and keyspace notification protocol

### Standards References

- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology for all Python production code
- #file:../../.github/instructions/python.instructions.md — Python coding conventions

## Implementation Checklist

### [ ] Phase 1: Foundation (Steps 1–3)

- [ ] Task 1.1: Enable GUILD_MEMBERS privileged intent in `services/bot/bot.py`
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 11–23)

- [ ] Task 1.2: Add Redis projection key constants to `shared/cache/keys.py`
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 25–47)

- [ ] Task 1.3: Add `MEMBER_CACHE_POPULATE` event type and `MemberCachePopulateEvent` payload model
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 49–65)

### [ ] Phase 2: Bot Projection Writer

- [ ] Task 2.1: Implement `services/bot/guild_projection.py` writer module
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 69–92)

- [ ] Task 2.2: Wire `on_ready` and reconnect with generation bump in `services/bot/bot.py`
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 94–120)

- [ ] Task 2.3: Add `on_member_update` and `on_member_remove` handlers to `services/bot/bot.py`
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 122–137)

- [ ] Task 2.4: Add bot heartbeat task writing `bot:last_seen`
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 139–154)

- [ ] Task 2.5: Add `MEMBER_CACHE_POPULATE` RabbitMQ consumer in bot
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 156–179)

### [ ] Phase 3: API Projection Reader

- [ ] Task 3.1: Implement `services/api/services/member_projection.py` reader module
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 183–208)

### [ ] Phase 4: API Call Site Migration

- [ ] Task 4.1: Migrate `permissions.py` `verify_guild_membership` to projection read
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 212–228)

- [ ] Task 4.2: Migrate `login_refresh.py` display name reads to projection
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 230–245)

- [ ] Task 4.3: Migrate `RoleChecker` to discord.py client cache
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 247–263)

- [ ] Task 4.4: Migrate `DisplayNameResolver` REST fallback to projection read
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 265–280)

### [ ] Phase 5: Dead Code Removal

- [ ] Task 5.1: Delete `login_refresh.py` and remove all REST fallback paths; grep-verify zero API REST calls
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 284–298)

- [ ] Task 5.2: Remove obsolete TTL constants and unused key functions
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 300–313)

- [ ] Task 5.3: Drop `user_display_names` table via Alembic migration
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 315–330)

### [ ] Phase 6: Redis ACL Enforcement

- [ ] Task 6.1: Create API read-only Redis ACL user; update API service credential
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 334–354)

### [ ] Phase 7: Bot REST Elimination

- [ ] Task 7.1: Audit and eliminate remaining bot REST calls replaceable by discord.py client cache
  - Details: .copilot-tracking/planning/details/20260417-01-gateway-intent-redis-projection-details.md (Lines 358–370)

## Dependencies

- discord.py `Intents.members` privileged intent (Discord Developer Portal toggle required)
- Redis keyspace notifications enabled (`notify-keyspace-events Kg$`)
- RabbitMQ topic exchange (already present via `EventPublisher`)
- Python `redis-py` asyncio client (already in use)

## Success Criteria

- `verify_guild_membership` fires zero OAuth REST calls per request after full migration
- `list_games` display name resolution reads only from Redis; no Discord API calls in the hot path
- Bot reconnect does not cause the API to serve mixed-generation data
- First login completes within the on-demand populate timeout under normal conditions
- `bot:last_seen` absence causes a clear degraded response, not a silent error or hang
- All steps pass the full unit + integration test suite before merging
- Zero Discord REST calls from the API server, verified by grep audit
