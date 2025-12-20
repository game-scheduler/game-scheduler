<!-- markdownlint-disable-file -->

# Release Changes: Game Card Host Avatar Display Enhancement

**Related Plan**: 20251219-game-card-host-avatar-display-plan.instructions.md
**Implementation Date**: 2025-12-20

## Summary

Add host Discord avatar display to both web frontend GameCard component and Discord bot game embeds. This enhancement fetches avatar URLs from Discord API and displays them alongside host names for better visual identification.

## Changes

### Added

- services/api/services/display_names.py - Added `resolve_display_names_and_avatars()` method to extract Discord avatar hashes and construct CDN URLs
- services/api/services/display_names.py - Added `_build_avatar_url()` static method to construct Discord CDN URLs with proper priority (guild > user > None)
- shared/cache/keys.py - Added `display_name_avatar()` cache key method for caching display names and avatar URLs together
- tests/services/api/services/test_display_names.py - Added 8 new unit tests for avatar resolution functionality including cache, API, priority, and error handling
- frontend/src/components/__tests__/GameCard.test.tsx - Added 12 comprehensive tests for GameCard avatar display covering avatar URLs, fallback initials, layout, and accessibility
- tests/services/bot/formatters/test_game_message.py - Added 5 new tests for Discord embed author field functionality including avatar URL handling, animated avatars, and graceful fallbacks

### Modified

- frontend/src/types/index.ts - Added optional `avatar_url?: string | null` field to Participant interface for Discord CDN avatar URLs
- frontend/src/components/GameCard.tsx - Reorganized layout to display host with Avatar component at top, removed Chip from bottom, added MUI Avatar with fallback to initials

- services/api/services/display_names.py - Updated module docstring to mention avatar URL resolution
- services/api/services/display_names.py - Added json import for caching avatar data
- shared/schemas/participant.py - Added optional `avatar_url` field to ParticipantResponse schema for Discord CDN avatar URLs
- services/api/routes/games.py - Updated game detail endpoint to use `resolve_display_names_and_avatars()` and include avatar URLs in all participant and host responses
- services/api/routes/games.py - Updated join game endpoint to resolve and return avatar URLs for new participants
- services/api/services/display_names.py - Caching updated to store avatar URLs as JSON alongside display names with 5-minute TTL
- services/bot/formatters/game_message.py - Added `host_display_name` and `host_avatar_url` parameters to `create_game_embed()` method for embed author field
- services/bot/formatters/game_message.py - Added embed.set_author() call to display host with avatar at top of Discord embed using Discord's native author field
- services/bot/formatters/game_message.py - Added `host_display_name` and `host_avatar_url` parameters to `format_game_announcement()` function
- services/bot/utils/discord_format.py - Added `get_member_display_info()` async function to fetch member display name and avatar URL from Discord with proper fallback handling
- services/bot/events/handlers.py - Updated `_create_game_announcement()` to use `get_member_display_info()` helper to fetch host information from Discord guild member object
- services/bot/events/handlers.py - Made `_create_game_announcement()` async and added await to all call sites to support async member fetching

### Removed
