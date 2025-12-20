<!-- markdownlint-disable-file -->

# Release Changes: Discord API Client Consolidation

**Related Plan**: 20251220-discord-client-consolidation-plan.instructions.md
**Implementation Date**: 2025-12-20

## Summary

Consolidation of Discord API client from API service to shared layer, enabling cache sharing across API and bot services to reduce Discord API rate limit consumption.

## Changes

### Added

- [shared/discord/__init__.py](shared/discord/__init__.py) - Shared Discord API client module initialization and exports
- [shared/discord/client.py](shared/discord/client.py) - DiscordAPIClient moved from API service for cross-service usage
- [tests/shared/discord/__init__.py](tests/shared/discord/__init__.py) - Test package initialization for shared Discord tests
- [tests/shared/discord/test_client.py](tests/shared/discord/test_client.py) - Comprehensive unit tests for DiscordAPIClient (39 test cases covering all methods, error handling, caching, and concurrency)
- [services/api/dependencies/discord.py](services/api/dependencies/discord.py) - API service singleton for DiscordAPIClient using API service credentials
- [services/bot/dependencies/__init__.py](services/bot/dependencies/__init__.py) - Bot service dependency injection package initialization
- [services/bot/dependencies/discord_client.py](services/bot/dependencies/discord_client.py) - Bot service singleton for DiscordAPIClient using bot service credentials

### Modified

- tests/services/api/services/test_games_edit_participants.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/services/test_participant_resolver.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/services/test_games.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/auth/test_roles.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/auth/test_discord_client.py - Reduced to only test API-specific singleton pattern, removed 11 redundant tests that duplicate shared/discord/test_client.py coverage
- tests/services/api/services/test_display_names.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/routes/test_templates.py - Updated patch paths from services.api.auth.discord_client to services.api.dependencies.discord.get_discord_client and shared.discord.client.fetch_channel_name_safe
- tests/services/api/routes/test_guilds.py - Updated patch path from services.api.auth.discord_client.fetch_channel_name_safe to shared.discord.client.fetch_channel_name_safe
- tests/services/api/auth/test_oauth2.py - Updated all patch paths from services.api.auth.oauth2.discord_client.get_discord_client to services.api.dependencies.discord.get_discord_client
- services/api/auth/roles.py - Updated discord_client import from services.api.auth to shared.discord and get_discord_client from services.api.dependencies.discord
- services/api/auth/__init__.py - Removed discord_client from exports since it moved to shared layer
- services/api/auth/oauth2.py - Updated discord_client import from services.api.auth to services.api.dependencies.discord.get_discord_client
- services/api/services/guild_service.py - Updated discord_client import from services.api.auth to services.api.dependencies.discord.get_discord_client
- services/api/services/participant_resolver.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/services/games.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/services/display_names.py - Updated discord_client import from services.api.auth to shared.discord and get_discord_client from services.api.dependencies.discord
- services/api/services/calendar_export.py - Updated discord_client helper function imports from services.api.auth.discord_client to shared.discord.client
- services/api/routes/guilds.py - Updated discord_client imports from services.api.auth to services.api.dependencies.discord.get_discord_client and shared.discord.client helper functions
- services/api/routes/templates.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/routes/channels.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/routes/games.py - Updated discord_client and fetch_channel_name_safe imports from services.api.auth to services.api.dependencies.discord.get_discord_client and shared.discord.client
### Modified

- tests/services/api/services/test_games_edit_participants.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/services/test_participant_resolver.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/services/test_games.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/auth/test_roles.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/auth/test_discord_client.py - Reduced to only test API-specific singleton pattern, removed 11 redundant tests that duplicate shared/discord/test_client.py coverage
- tests/services/api/services/test_display_names.py - Updated discord_client import from services.api.auth to shared.discord
- tests/services/api/routes/test_templates.py - Updated patch paths from services.api.auth.discord_client to services.api.dependencies.discord.get_discord_client and shared.discord.client.fetch_channel_name_safe
- tests/services/api/routes/test_guilds.py - Updated patch path from services.api.auth.discord_client.fetch_channel_name_safe to shared.discord.client.fetch_channel_name_safe
- tests/services/api/auth/test_oauth2.py - Updated all patch paths from services.api.auth.oauth2.discord_client.get_discord_client to services.api.dependencies.discord.get_discord_client
- services/api/auth/roles.py - Updated discord_client import from services.api.auth to shared.discord and get_discord_client from services.api.dependencies.discord
- services/api/auth/__init__.py - Removed discord_client from exports since it moved to shared layer
- services/api/auth/oauth2.py - Updated discord_client import from services.api.auth to services.api.dependencies.discord.get_discord_client
- services/api/services/guild_service.py - Updated discord_client import from services.api.auth to services.api.dependencies.discord.get_discord_client
- services/api/services/participant_resolver.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/services/games.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/services/display_names.py - Updated discord_client import from services.api.auth to shared.discord and get_discord_client from services.api.dependencies.discord
- services/api/services/calendar_export.py - Updated discord_client helper function imports from services.api.auth.discord_client to shared.discord.client
- services/api/routes/guilds.py - Updated discord_client imports from services.api.auth to services.api.dependencies.discord.get_discord_client and shared.discord.client helper functions
- services/api/routes/templates.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/routes/channels.py - Updated discord_client import from services.api.auth to shared.discord
- services/api/routes/games.py - Updated discord_client and fetch_channel_name_safe imports from services.api.auth to services.api.dependencies.discord.get_discord_client and shared.discord.client
- shared/discord/client.py - Added helper functions fetch_channel_name_safe, fetch_user_display_name_safe, and fetch_guild_name_safe with optional client parameter
- services/bot/utils/discord_format.py - Updated get_member_display_info() to use DiscordAPIClient with caching instead of discord.py bot client; added _build_avatar_url() helper function for consistent avatar URL generation
- services/bot/auth/role_checker.py - Replaced 13 uncached bot.fetch_guild() and guild.fetch_member() calls with cached DiscordAPIClient equivalents; updated 5 permission checking methods; added _has_permission() helper function for Discord permission checking
- services/bot/events/handlers.py - Replaced 4 uncached bot.fetch_channel() and bot.fetch_user() calls with cached DiscordAPIClient equivalents; updated event handlers for game lifecycle and participant changes

### Removed

- services/api/auth/discord_client.py - Deleted old location after moving to shared layer
