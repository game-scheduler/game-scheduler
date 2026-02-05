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
- tests/services/api/services/test_guild_service.py - Added comprehensive unit tests for `_sync_guild_channels()` covering all scenarios (new channels, reactivation, deactivation, no changes)

### Removed
