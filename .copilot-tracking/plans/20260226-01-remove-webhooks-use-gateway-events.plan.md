---
applyTo: '.copilot-tracking/changes/20260226-01-remove-webhooks-use-gateway-events-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove Discord Webhooks and Use Gateway Events

## Overview

Simplify architecture by removing unnecessary HTTP webhook infrastructure and using Discord gateway events directly for automatic guild synchronization.

## Objectives

- Remove webhook HTTP endpoint and Ed25519 signature validation infrastructure
- Remove RabbitMQ GUILD_SYNC_REQUESTED event and handler
- Enable automatic guild sync using Discord gateway events (on_guild_join)
- Unify guild sync to single function (sync_all_bot_guilds)
- Add rate limiting to GUI sync endpoint to prevent abuse
- Simplify architecture by eliminating cross-service communication for guild events

## Research Summary

### Project Files

- [services/api/routes/webhooks.py](../../services/api/routes/webhooks.py) - HTTP webhook endpoint with Ed25519 validation
- [services/api/dependencies/discord_webhook.py](../../services/api/dependencies/discord_webhook.py) - Signature validation logic
- [services/bot/bot.py](../../services/bot/bot.py) - Bot with on_guild_join/remove events (lines 193-222)
- [services/bot/events/handlers.py](../../services/bot/events/handlers.py) - RabbitMQ event handlers including GUILD_SYNC_REQUESTED (lines 1080-1118)
- [services/api/routes/guilds.py](../../services/api/routes/guilds.py) - GUI sync endpoint (lines 301-329)
- [shared/messaging/events.py](../../shared/messaging/events.py) - Event type definitions

### External References

- #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md - Comprehensive research on webhook removal and gateway events
- Discord Gateway Events: on_guild_join and on_guild_remove are non-privileged events received automatically

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - FastAPI patterns
- #file:../../.github/instructions/api-authorization.instructions.md - API authorization patterns

## Implementation Checklist

### [x] Phase 1: Remove Webhook Infrastructure

- [x] Task 1.1: Delete webhook files
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 16-32)

- [x] Task 1.2: Remove webhook router registration from API app
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 34-50)

- [x] Task 1.3: Remove DISCORD_PUBLIC_KEY configuration
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 52-71)

- [x] Task 1.4: Remove PyNaCl dependency
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 73-92)

### [x] Phase 2: Remove RabbitMQ Guild Sync Event

- [x] Task 2.1: Remove GUILD_SYNC_REQUESTED event definition
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 96-113)

- [x] Task 2.2: Remove guild sync event handler from bot
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 115-133)

- [x] Task 2.3: Remove event handler tests
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 135-152)

### [x] Phase 3: Update Bot on_guild_join Event (TDD)

- [x] Task 3.1: Create stub for enhanced on_guild_join (RED phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 156-174)

- [x] Task 3.2: Write tests for on_guild_join sync behavior (RED phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 176-195)

- [x] Task 3.3: Implement on_guild_join to call sync_all_bot_guilds (GREEN phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 197-216)

- [x] Task 3.4: Refactor and add edge case tests (REFACTOR phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 218-236)

### [ ] Phase 4: Simplify GUI Sync Endpoint with Rate Limiting (TDD)

- [ ] Task 4.1: Create stub for updated sync endpoint (RED phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 240-259)

- [ ] Task 4.2: Write tests for sync endpoint with rate limiting (RED phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 261-281)

- [ ] Task 4.3: Implement sync endpoint with sync_all_bot_guilds and rate limiting (GREEN phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 283-303)

- [ ] Task 4.4: Refactor and add edge case tests (REFACTOR phase)
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 305-323)

### [ ] Phase 5: Remove Obsolete Functions

- [ ] Task 5.1: Analyze and remove sync_user_guilds and helpers
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 327-348)

- [ ] Task 5.2: Update remaining tests to use sync_all_bot_guilds
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 350-367)

### [ ] Phase 6: Verification and Cleanup

- [ ] Task 6.1: Run full test suite and verify all tests pass
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 371-387)

- [ ] Task 6.2: Verify no remaining references to webhook infrastructure
  - Details: .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md (Lines 389-406)

## Dependencies

- slowapi library (already configured for rate limiting)
- Discord.py library for gateway events
- RabbitMQ messaging infrastructure
- PostgreSQL database for guild storage
- Existing sync_all_bot_guilds function

## Success Criteria

- All webhook files and tests removed
- No DISCORD_PUBLIC_KEY configuration required
- PyNaCl dependency removed from pyproject.toml
- GUILD_SYNC_REQUESTED event and handler removed
- Bot automatically syncs guilds when on_guild_join event fires
- GUI sync endpoint uses sync_all_bot_guilds with rate limiting (1/minute)
- Rate limiting returns 429 Too Many Requests on abuse
- All tests pass with updated behavior
- Architecture simplified with fewer moving parts
- No cross-service communication needed for guild events
