<!-- markdownlint-disable-file -->

# Release Changes: Remove channel_name from Database

**Related Plan**: 20251201-remove-channel-name-from-database-plan.instructions.md
**Implementation Date**: 2025-12-01

## Summary

Removed `channel_name` column from `channel_configurations` table and implemented dynamic fetching from Discord API with Redis caching. This eliminates staleness issues when Discord channel names change while maintaining backward compatibility in API responses.

## Changes

### Added

- alembic/versions/017_remove_channel_name.py - Database migration to drop channel_name column from channel_configurations table

### Modified

- shared/models/channel.py (Lines 1-63) - Removed channel_name field from ChannelConfiguration model
- shared/schemas/channel.py (Lines 1-75) - Removed channel_name from create and update request schemas, kept in response schema for API backward compatibility
- services/api/routes/channels.py (Lines 1-213) - Updated all endpoints to fetch channel names dynamically from Discord API with error handling
- services/api/services/config.py (Lines 1-300) - Removed channel_name parameter from create_channel_config method
- services/bot/commands/config_channel.py (Lines 1-312) - Removed channel_name logic from /config-channel command
- tests/services/api/services/test_config.py (Lines 58-75, 212-224) - Removed channel_name from test fixtures
- tests/services/bot/commands/test_config_channel.py (Lines 86-99) - Removed channel_name from test fixtures

### Removed

### Notes

- All unit tests pass (29/29 tests)
- All integration tests pass (10/10 tests) after container rebuild
- Docker containers build successfully (api, bot, integration-tests, init)
- Integration test containers needed rebuild to apply latest database migrations
