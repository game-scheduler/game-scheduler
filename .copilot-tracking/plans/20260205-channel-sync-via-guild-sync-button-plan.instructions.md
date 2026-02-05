---
applyTo: ".copilot-tracking/changes/20260205-channel-sync-via-guild-sync-button-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Channel Sync via Guild Sync Button

## Overview

Extend existing guild sync operation to refresh channel lists for existing guilds, marking new channels as active and deleted channels as inactive.

## Objectives

- Sync channels from Discord for both new and existing guilds when user clicks sync button
- Add new Discord channels to database with `is_active=True`
- Mark channels deleted from Discord as `is_active=False` (preserving foreign key integrity)
- Filter inactive channels from template/game creation dropdowns
- Update sync response to show both new and updated channel counts
- Maintain simple manual sync pattern without caching complexity

## Research Summary

### Project Files

- services/api/routes/guilds.py - Guild and channel API endpoints
- services/api/services/guild_service.py - Guild sync business logic
- shared/schemas/guild.py - Response schemas
- shared/discord/client.py - Discord API client

### External References

- #file:../research/20260205-channel-lazy-loading-guild-setup-research.md - Complete implementation guidance with decision rationale
- Discord API: GET /guilds/{guild_id}/channels returns current channel list
- Rate limits: Manual sync operation, 50 requests/second not a concern

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python conventions
- #file:../../.github/instructions/api-authorization.instructions.md - Authorization patterns
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Service layer conventions

## Implementation Checklist

### [x] Phase 1: Backend - Channel Sync Helper

- [x] Task 1.1: Create `_sync_guild_channels()` helper function
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 15-80)

### [x] Phase 2: Backend - Extend sync_user_guilds

- [x] Task 2.1: Update `sync_user_guilds()` to process existing guilds
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 82-140)

### [x] Phase 3: Backend - Schema and Response Updates

- [x] Task 3.1: Add `updated_channels` field to GuildSyncResponse schema
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 142-170)

- [x] Task 3.2: Update sync_guilds endpoint to return new response format
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 172-200)

### [x] Phase 4: Backend - Filter Inactive Channels

- [x] Task 4.1: Filter channels by `is_active=True` in list_guild_channels endpoint
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 202-245)

### [x] Phase 5: Frontend - UI Updates

- [x] Task 5.1: Update sync button label to "Sync guilds and channels"
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 247-280)

- [x] Task 5.2: Update success message to display updated channel count
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 282-315)

### [ ] Phase 6: Testing and Validation

- [ ] Task 6.1: Write integration tests for channel sync operations
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 317-360)

- [ ] Task 6.2: Validate foreign key integrity and inactive channel behavior
  - Details: .copilot-tracking/details/20260205-channel-sync-via-guild-sync-button-details.md (Lines 362-390)

## Dependencies

- Existing `get_guild_channels()` method in DiscordAPIClient
- Existing `channel_service.create_channel_config()` method
- Existing `queries.get_channels_by_guild()` method
- Existing `queries.get_guild_by_discord_id()` method
- Existing `queries.require_guild_by_id()` method

## Success Criteria

- New Discord channels appear in dropdowns after clicking sync
- Deleted Discord channels are hidden from dropdowns but preserved in database
- Existing guilds receive channel refreshes during sync operation
- Sync response shows accurate counts for new guilds, new channels, and updated channels
- Frontend displays clear success message with channel update information
- Foreign key integrity maintained (no orphaned games/templates)
- All integration tests pass
- No breaking changes to existing games/templates with inactive channels
