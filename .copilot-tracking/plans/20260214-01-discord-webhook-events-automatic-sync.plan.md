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

### [ ] Phase 1: Environment and Dependencies Setup

- [ ] Task 1.1: Add DISCORD_PUBLIC_KEY environment variable to all env files
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 15-27)

- [ ] Task 1.2: Add PyNaCl dependency to pyproject.toml
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 29-39)

- [ ] Task 1.3: Update APIConfig to include discord_public_key
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 41-51)

### [ ] Phase 2: Webhook Signature Validation (TDD)

- [ ] Task 2.1: Create validate_discord_webhook dependency stub
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 53-63)

- [ ] Task 2.2: Write failing tests for signature validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 65-80)

- [ ] Task 2.3: Implement Ed25519 signature validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 82-94)

- [ ] Task 2.4: Update tests to verify actual signature validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 96-107)

- [ ] Task 2.5: Refactor validation with comprehensive edge case tests
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 109-120)

### [ ] Phase 3: Webhook Endpoint Implementation (TDD)

- [ ] Task 3.1: Create webhook endpoint stub returning 501
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 122-132)

- [ ] Task 3.2: Write failing integration tests for webhook endpoint
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 134-150)

- [ ] Task 3.3: Implement PING handling (type 0 → 204)
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 152-162)

- [ ] Task 3.4: Implement APPLICATION_AUTHORIZED webhook handling with stub sync
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 164-178)

- [ ] Task 3.5: Update integration tests and add comprehensive edge cases
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 180-192)

### [ ] Phase 4: Bot Guild Sync Service (TDD)

- [ ] Task 4.1: Create sync_all_bot_guilds stub in guild_service
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 194-204)

- [ ] Task 4.2: Write failing tests for bot guild sync
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 206-223)

- [ ] Task 4.3: Implement guild creation logic (new guilds only)
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 225-238)

- [ ] Task 4.4: Implement channel creation for new guilds
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 240-251)

- [ ] Task 4.5: Implement default template creation and inactive guild marking
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 253-265)

- [ ] Task 4.6: Update tests and add comprehensive edge cases
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 267-278)

### [ ] Phase 5: RabbitMQ Integration for Webhook

- [ ] Task 5.1: Update webhook endpoint to publish sync_guild message
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 280-291)

- [ ] Task 5.2: Add integration tests for RabbitMQ message publishing
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 293-303)

### [ ] Phase 6: Lazy Channel Loading (TDD)

- [ ] Task 6.1: Create refresh_guild_channels function stub
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 305-315)

- [ ] Task 6.2: Write failing tests for channel refresh
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 317-331)

- [ ] Task 6.3: Implement channel fetching and database sync
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 333-344)

- [ ] Task 6.4: Add refresh query parameter to GET /guilds/{guild_id}/channels
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 346-357)

- [ ] Task 6.5: Update tests and add comprehensive edge cases
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 359-370)

### [ ] Phase 7: Manual Discord Portal Configuration

- [ ] Task 7.1: Document webhook configuration steps in deployment docs
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 372-382)

- [ ] Task 7.2: Create testing checklist for webhook validation
  - Details: .copilot-tracking/details/20260214-01-discord-webhook-events-automatic-sync-details.md (Lines 384-394)

## Dependencies

- PyNaCl >= 1.5.0 for Ed25519 signature verification
- Existing DiscordAPIClient for guild/channel fetching
- RabbitMQ for message queue integration
- Existing database models (GuildConfiguration, ChannelConfiguration, GameTemplate)
- Access to Discord Developer Portal for webhook configuration

## Success Criteria

- Webhook endpoint successfully validates Ed25519 signatures (401 for invalid)
- PING requests receive 204 response
- APPLICATION_AUTHORIZED events create new guilds with channels and default template
- Existing guilds are not duplicated
- Bot sync works without user authentication
- Channel refresh updates database when users edit templates
- Comprehensive unit and integration test coverage (>90%)
- Manual sync button continues to work for backward compatibility
- Documentation complete for webhook configuration in Discord Portal
