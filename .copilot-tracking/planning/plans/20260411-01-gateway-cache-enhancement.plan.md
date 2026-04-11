---
applyTo: '.copilot-tracking/changes/20260411-01-gateway-cache-enhancement-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Gateway-Driven Cache Enhancement

## Overview

Replace REST-based Discord cache population with gateway-driven Redis writes and in-memory lookups across the bot service and shared Discord client.

## Objectives

- `on_ready` rebuilds Redis from the in-memory gateway cache without any REST calls
- Gateway events (`CHANNEL_*`, `GUILD_ROLE_*`) keep Redis current in real time
- `role_checker.py` uses `get_guild()` (in-memory) instead of `fetch_guild()` (REST)
- `get_guild_member` results are cached in Redis
- Gateway-maintained cache keys have no TTL; only member data retains a TTL
- Redundant `fetch_channel` pre-check in `handlers.py` is removed

## Research Summary

### Project Files

- `services/bot/bot.py` — target for `on_ready` rebuild and gateway event handlers
- `services/bot/auth/role_checker.py` — five methods calling `fetch_guild()` (REST)
- `services/bot/events/handlers.py` — redundant `fetch_channel` in `_validate_discord_channel` (line 189)
- `shared/discord/client.py` — `_make_api_request` guard bug (line 240); `get_guild_member` lacks caching
- `shared/cache/ttl.py` — TTL constants to be set to `None` for gateway-maintained keys
- `shared/cache/keys.py` — needs `discord_member` key added

### External References

- #file:../research/20260410-01-gateway-cache-enhancement-research.md — full research findings

### Standards References

- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/python.instructions.md — Python conventions

## Implementation Checklist

### [x] Phase 1: on_ready Redis Cache Rebuild

- [x] Task 1.1: Write failing unit tests for on_ready cache rebuild
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 13-32)

- [x] Task 1.2: Implement on_ready Redis rebuild in bot.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 33-57)

### [x] Phase 2: role_checker.py — Use In-Memory Cache

- [x] Task 2.1: Write failing unit tests for get_guild() usage
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 61-81)

- [x] Task 2.2: Replace fetch_guild() with get_guild() in role_checker.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 82-101)

### [x] Phase 3: Remove Redundant fetch_channel in handlers.py

- [x] Task 3.1: Write failing unit tests for \_validate_discord_channel
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 105-122)

- [x] Task 3.2: Remove redundant fetch_channel call in handlers.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 123-142)

### [x] Phase 4: Gateway Event Handlers

- [x] Task 4.1: Write failing unit tests for gateway event handlers
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 146-166)

- [x] Task 4.2: Implement channel event handlers in bot.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 167-185)

- [x] Task 4.3: Implement role event handlers in bot.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 186-204)

### [x] Phase 5: Fix \_make_api_request Guard + Remove TTLs

- [x] Task 5.1: Write failing unit test for \_make_api_request with cache_ttl=None
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 208-225)

- [x] Task 5.2: Fix \_make_api_request guard in shared/discord/client.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 226-241)

- [x] Task 5.3: Set TTLs to None for gateway-maintained cache keys
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 242-258)

### [x] Phase 6: get_guild_member Redis Caching

- [x] Task 6.1: Write failing unit tests for get_guild_member caching
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 262-280)

- [x] Task 6.2: Add discord_member cache key and TTL constant
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 281-295)

- [x] Task 6.3: Add caching to get_guild_member in shared/discord/client.py
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 296-312)

- [x] Task 6.4: Wire role_checker.get_user_role_ids to use get_guild_member
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 313-340)

### [ ] Phase 7: E2E Gateway Cache Population Tests

- [ ] Task 7.1: Write e2e tests for startup cache population
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 339-364)

- [ ] Task 7.2: Write e2e test for known role ID in guild roles cache
  - Details: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md (Lines 365-385)

## Dependencies

- discord.py (already a project dependency)
- Redis (already a project dependency)
- `shared/cache/keys.py` and `shared/cache/ttl.py` (already exist)
- `shared/discord/client.py` `DiscordAPIClient` (already exists)

## Success Criteria

- `on_ready` writes all channel/guild/role Redis keys from in-memory gateway cache without REST calls
- Gateway event handlers keep channel and role Redis keys current in real time
- `role_checker.py` uses `get_guild()` (in-memory) not `fetch_guild()` (REST)
- `get_guild_member` results are cached in Redis using `discord:member:{guild_id}:{user_id}`
- `discord:channel`, `discord:guild`, `discord:guild_channels`, `discord:guild_roles` keys have no TTL
- `discord:member` keys expire on `DISCORD_MEMBER` TTL
- `_validate_discord_channel` in `handlers.py` uses `get_channel()` only
- All unit tests pass
- E2e tests in `test_gateway_cache_e2e.py` verify all four key families populated at startup
- E2e test confirms known role ID (`DISCORD_TEST_ROLE_A_ID`) appears in guild roles cache
