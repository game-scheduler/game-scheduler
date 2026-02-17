---
applyTo: '.copilot-tracking/changes/20260214-01-discord-webhook-events-automatic-sync-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Webhook Events for Automatic Guild Sync

## Overview

Implement Discord webhook endpoint with Ed25519 signature validation to automatically sync guilds when bot joins servers, eliminating manual sync requirement.

## Objectives

- Automatic guild creation when bot joins Discord server via APPLICATION_AUTHORIZED webhook
- Secure Ed25519 signature validation for all webhook requests
- RabbitMQ-based decoupled architecture for guild sync operations
- Bot-driven sync logic using bot token (no user authentication required)
- Lazy channel loading when users edit templates

## Research Summary

### Project Files

- services/api/routes/guilds.py - Existing manual sync endpoint
- services/api/services/guild_service.py - Current user-driven sync logic
- shared/discord/client.py - Discord API client with guild/channel fetching
- services/api/config.py - API configuration (needs DISCORD_PUBLIC_KEY)

### External References

- #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md - Complete implementation research
- #fetch:https://docs.discord.com/developers/events/webhook-events - Discord webhook event specifications
- #fetch:https://pynacl.readthedocs.io/en/latest/signing/ - PyNaCl Ed25519 signature validation

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Transaction management

## Implementation Checklist

### [x] Phase 1: Environment and Dependencies Setup

- [x] Task 1.1: Add DISCORD_PUBLIC_KEY environment variable to all env files
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 15-27)

- [x] Task 1.2: Add PyNaCl dependency to pyproject.toml
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 29-39)

- [x] Task 1.3: Update APIConfig to include discord_public_key
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 41-51)

### [x] Phase 2: Webhook Signature Validation (TDD)

- [x] Task 2.1: Create validate_discord_webhook dependency stub
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 53-63)

- [x] Task 2.2: Write failing tests for signature validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 65-80)

- [x] Task 2.3: Implement Ed25519 signature validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 82-94)

- [x] Task 2.4: Update tests to verify actual signature validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 96-107)

- [x] Task 2.5: Refactor validation with comprehensive edge case tests
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 109-120)

### [x] Phase 3: Webhook Endpoint Implementation (TDD)

- [x] Task 3.1: Create webhook endpoint stub returning 501
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 122-132)

- [x] Task 3.2: Write failing integration tests for webhook endpoint
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 134-150)

- [x] Task 3.3: Implement PING handling (type 0 → 204)
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 152-162)

- [x] Task 3.4: Implement APPLICATION_AUTHORIZED webhook handling with stub sync
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 164-178)

- [x] Task 3.5: Update integration tests and add comprehensive edge cases
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 180-192)

### [x] Phase 4: Bot Guild Sync Service (TDD)

- [x] Task 4.1: Create sync_all_bot_guilds stub in guild_service
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 211-223)

- [x] Task 4.2: Write tests with real assertions marked as expected failures
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 224-242)

- [x] Task 4.3: Implement bot guild sync and remove xfail markers
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 243-266)

- [x] Task 4.4: Refactor and add comprehensive edge case tests
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 267-285)

### [ ] Phase 5: Move Sync Logic to Bot Service (Architecture Refactoring)

- [x] Task 5.1: Move sync_all_bot_guilds() from API to bot service
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 288-306)

- [x] Task 5.2: Move and update unit tests to bot service
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 308-322)

- [x] Task 5.3: Verify all tests pass after relocation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 324-338)

- [x] Task 5.4: Add guild sync to bot service startup
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 340-354)

- [ ] Task 5.5: Add E2E ordered test for bot startup sync verification using pytest-order
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 356-387)

- [ ] Task 5.6: Verify all tests pass with startup sync
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 375-391)

- [ ] Task 5.7: Add GUILD_SYNC_REQUESTED event type
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 393-404)

- [ ] Task 5.8: Add bot event handler for webhook-triggered guild sync
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 406-420)

### [ ] Phase 6: RabbitMQ Integration for Webhook

- [ ] Task 6.1: Update webhook endpoint to publish GUILD_SYNC_REQUESTED event
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 424-439)

- [ ] Task 6.2: Add integration tests for RabbitMQ message publishing
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 441-454)

### [ ] Phase 7: Lazy Channel Loading (TDD)

- [ ] Task 7.1: Create refresh_guild_channels function stub
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 458-469)

- [ ] Task 7.2: Write tests with real assertions marked as expected failures
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 471-487)

- [ ] Task 7.3: Implement channel refresh and remove xfail markers
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 489-510)

- [ ] Task 7.4: Refactor and add comprehensive edge case tests
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 512-530)

### [ ] Phase 8: Manual Discord Portal Configuration

- [ ] Task 8.1: Document webhook configuration steps in deployment docs
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 543-557)

- [ ] Task 8.2: Create testing checklist for webhook validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 559-573)

## Dependencies

- PyNaCl >= 1.5.0 for Ed25519 signature verification
- Existing DiscordAPIClient for guild/channel fetching
- RabbitMQ for message queue integration
- Existing database models (GuildConfiguration, ChannelConfiguration, GameTemplate)
- Access to Discord Developer Portal for webhook configuration

## Success Criteria

- Webhook endpoint successfully validates Ed25519 signatures (401 for invalid)
- PING requests receive 204 response
- APPLICATION_AUTHORIZED events publish RabbitMQ event to trigger bot sync
- Bot service syncs guilds automatically on its own startup
- Bot service processes webhook-triggered sync events from RabbitMQ
- Existing guilds are not duplicated
- Bot sync works without user authentication
- Channel refresh updates database when users edit templates
- Comprehensive unit and integration test coverage (>90%)
- Manual sync button continues to work for backward compatibility
- Documentation complete for webhook configuration in Discord Portal
