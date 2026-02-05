<!-- markdownlint-disable-file -->

# Release Changes: Channel Sync via Guild Sync Button

**Related Plan**: 20260205-channel-sync-via-guild-sync-button-plan.instructions.md
**Implementation Date**: 2026-02-05

## Summary

Extend existing guild sync operation to refresh channel lists for existing guilds, marking new channels as active and deleted channels as inactive.

## Changes

### Added

### Modified

- services/api/services/guild_service.py - Added `_sync_guild_channels()` helper function to sync channels from Discord to database (get-or-create pattern with is_active flag, relies on ORM change tracking)
- services/api/services/guild_service.py - Updated `sync_user_guilds()` to process existing guilds and sync their channels, returning updated_channels count in addition to new_guilds and new_channels
- tests/services/api/services/test_guild_service.py - Added comprehensive unit tests for `_sync_guild_channels()` covering all scenarios (new channels, reactivation, deactivation, no changes)
- tests/services/api/services/test_guild_service.py - Added unit tests for updated `sync_user_guilds()` covering existing guild sync, new guild creation, and mixed scenarios
- shared/schemas/guild.py - Added `updated_channels` field to GuildSyncResponse schema to track channels synced for existing guilds
- services/api/routes/guilds.py - Updated `sync_guilds()` endpoint to return `updated_channels` in response and updated docstring to reflect channel sync functionality
- services/api/routes/guilds.py - Updated `list_guild_channels()` endpoint to filter channels by is_active=True, hiding deleted Discord channels from dropdowns (docstring updated to reflect active-only filtering)
- frontend/src/api/guilds.ts - Added `updated_channels` field to GuildSyncResponse interface to match backend schema
- frontend/src/pages/GuildListPage.tsx - Updated sync button labels from "Refresh Servers" to "Sync Servers and Channels" to reflect that both guilds and channels are synced
- frontend/src/pages/GuildListPage.tsx - Updated sync success message to display counts for new guilds, new channels, and updated channels with proper pluralization

### Removed
