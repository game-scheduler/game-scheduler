---
applyTo: ".copilot-tracking/changes/20251220-discord-client-consolidation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord API Client Consolidation

## Overview

Move DiscordAPIClient from API service to shared layer and integrate it into bot service to eliminate duplicate Discord API calls and share Redis caching across both services.

## Objectives

- Reduce Discord API rate limit consumption by sharing cache across API and bot services
- Eliminate 18+ uncached Discord REST API calls in bot service
- Consolidate cache key patterns for consistency
- Maintain existing functionality while improving performance
- Preserve discord.py WebSocket operations in bot service

## Research Summary

### Project Files

- [services/api/auth/discord_client.py](services/api/auth/discord_client.py) - 740-line DiscordAPIClient with comprehensive Redis caching
- [services/bot/utils/discord_format.py](services/bot/utils/discord_format.py) - get_member_display_info() with no caching
- [services/bot/auth/role_checker.py](services/bot/auth/role_checker.py) - 8 uncached guild fetch calls for permission checks
- [services/bot/events/handlers.py](services/bot/events/handlers.py) - 4 uncached channel/user fetch calls
- [services/api/services/display_names.py](services/api/services/display_names.py) - DisplayNameResolver using DiscordAPIClient

### External References

- #file:../research/20251220-discord-client-consolidation-research.md - Comprehensive analysis of current architecture, duplicate API calls, and consolidation strategy

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Code quality standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Create Shared Discord Module

- [x] Task 1.1: Create shared/discord directory structure and move DiscordAPIClient
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 9-26)

- [x] Task 1.2: Update DiscordAPIClient to accept credentials as constructor parameters
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 28-45)

- [x] Task 1.3: Update DiscordAPIClient imports to use shared.cache
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 47-60)

### [x] Phase 2: Update API Service Imports

- [x] Task 2.1: Find all files importing services.api.auth.discord_client
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 62-76)

- [x] Task 2.2: Update imports to shared.discord.client across all 19 API files
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 78-94)

- [x] Task 2.3: Update get_discord_client() singleton in API service
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 96-112)

- [x] Task 2.4: Verify API unit tests pass
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 114-124)

### [x] Phase 3: Integrate DiscordAPIClient in Bot Service

- [x] Task 3.1: Create bot service singleton for DiscordAPIClient
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 126-145)

- [x] Task 3.2: Update get_member_display_info() to use cached client
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 147-169)

- [x] Task 3.3: Replace uncached fetch calls in role_checker.py
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 171-193)

- [x] Task 3.4: Replace uncached fetch calls in handlers.py
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 195-215)

- [x] Task 3.5: Verify bot unit tests pass
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 217-227)

### [x] Phase 4: Consolidate Cache Keys
- [x] Task 4.1: Audit and document all cache key patterns
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 229-246)

- [x] Task 4.2: Update DiscordAPIClient to use CacheKeys constants
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 248-265)

- [x] Task 4.3: Update DisplayNameResolver cache keys for consistency
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 267-282)

### [x] Phase 5: Testing and Validation

- [x] Task 5.1: Run full test suite
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 284-296)

- [x] Task 5.2: Verify integration tests pass
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 298-309)

- [x] Task 5.3: Manual testing of avatar display and member info
  - Details: [.copilot-tracking/details/20251220-discord-client-consolidation-details.md](.copilot-tracking/details/20251220-discord-client-consolidation-details.md) (Lines 311-326)

## Dependencies

- aiohttp (already in API dependencies)
- discord.py (already in bot dependencies)
- shared.cache.client.RedisClient (already in both services)
- shared.cache.keys.CacheKeys (already in both services)
- shared.cache.ttl.CacheTTL (already in both services)

## Success Criteria

- All 19 API files successfully import from shared.discord.client
- Bot service uses DiscordAPIClient for get_member_display_info() with caching
- 18+ uncached Discord API calls in bot replaced with cached versions
- Cache hit rate > 80% for member info in bot service
- All unit tests pass (API and bot)
- All integration tests pass
- Avatar display works correctly in frontend and Discord embeds
- No increase in Discord API rate limit errors
- Cache key patterns are consistent across services
