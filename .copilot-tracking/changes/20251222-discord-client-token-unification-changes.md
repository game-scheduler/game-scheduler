<!-- markdownlint-disable-file -->

# Release Changes: Discord Client Token Unification

**Related Plan**: 20251222-discord-client-token-unification-plan.instructions.md
**Implementation Date**: 2025-12-22

## Summary

Unified Discord API client to accept both bot and OAuth tokens through a single consistent interface, eliminating artificial method duplication and enabling flexible token usage across all operations.

## Changes

### Added

- shared/discord/client.py - Added _get_auth_header() method for automatic token type detection (bot vs OAuth) with validation
- shared/discord/client.py - Added unified get_guilds() method that works with any token type and merges caching logic
- shared/discord/client.py - Added _fetch_guilds_uncached() helper method for non-cached guild fetching
- tests/shared/discord/test_client.py - Added TestTokenDetection class with comprehensive token type detection tests

### Modified

- shared/discord/client.py - Refactored _get_auth_header() to handle default token internally (DRY principle)
- shared/discord/client.py - Flattened control structure in _get_auth_header() (removed unnecessary else)
- shared/discord/client.py - Removed duplicate `token = token or self.bot_token` lines from all methods
- shared/discord/client.py - Updated fetch_guild() to accept optional token parameter (defaults to bot_token)
- shared/discord/client.py - Updated fetch_channel() to accept optional token parameter (defaults to bot_token)
- shared/discord/client.py - Updated fetch_user() to accept optional token parameter (defaults to bot_token)
- shared/discord/client.py - Deprecated get_bot_guilds() with delegation to get_guilds()
- shared/discord/client.py - Deprecated get_user_guilds() with delegation to get_guilds(token, user_id)
- services/api/services/guild_service.py - Updated to use get_guilds() instead of get_bot_guilds() and get_user_guilds()
- tests/shared/discord/test_client.py - Updated discord_client fixture to use proper bot token format
- tests/shared/discord/test_client.py - Updated test_guild_locks_created_per_user to use correct method name (_fetch_guilds_uncached)
- tests/shared/discord/test_client.py - Updated test to use get_guilds() instead of get_bot_guilds()
- tests/shared/discord/test_client.py - Added tests for default token behavior
- tests/shared/discord/test_client.py - Added TestUnifiedTokenFunctionality class with comprehensive bot and OAuth token tests
- tests/shared/discord/test_client.py - Updated all tests to use get_guilds() instead of deprecated methods
- tests/shared/discord/test_client.py - Renamed test methods for clarity (test_get_guilds_* instead of test_get_user_guilds_* and test_get_bot_guilds_*)

### Removed

- shared/discord/client.py - Removed _fetch_user_guilds_uncached() method (replaced by _fetch_guilds_uncached())
- shared/discord/client.py - Removed get_bot_guilds() deprecated method
- shared/discord/client.py - Removed get_user_guilds() deprecated method

## OAuth Login Bug Fix

### Issue
OAuth login was failing after the token unification implementation. Users would be redirected back to login after successful Discord authorization because:
1. `services/api/auth/oauth2.py` and `services/api/auth/roles.py` were still calling the removed `get_user_guilds()` method
2. The token format validation was incorrect, rejecting Discord's OAuth tokens which have 1 dot (not 0)

### Root Cause
Discord OAuth2 access tokens have the format "part1.part2" (1 dot), but the validation code was checking for 0 or 2 dots. Real Discord token formats:
- OAuth access token: 1 dot (e.g., "aBcD123.XyZ789")
- Bot token: 2 dots (e.g., "BASE64.TIMESTAMP.SIGNATURE")

### Solution
1. **Updated `shared/discord/client.py:_get_auth_header()`**:
   - Changed validation from "expected 0 or 2 dots" to "expected 1 or 2 dots"
   - Now correctly accepts both OAuth (1 dot) and bot (2 dots) tokens
   - Raises ValueError for invalid token formats (0, 3+, etc.)

2. **Updated `services/api/auth/oauth2.py:get_user_guilds()`**:
   - Changed from calling removed `discord.get_user_guilds()`
   - Now calls `discord.get_guilds(token=access_token, user_id=user_id)` unified method

3. **Updated `services/api/auth/roles.py:has_permissions()`**:
   - Changed from calling removed `self.discord_client.get_user_guilds()`
   - Now calls `self.discord_client.get_guilds(token=access_token, user_id=user_id)` unified method

4. **Updated test fixtures and expectations**:
   - Updated OAuth token test values from "0-dot" format to "1-dot" format
   - Updated error message expectations to reflect correct validation logic

### Testing
- All 52 Discord client tests pass ✅
- All 8 OAuth2 tests pass ✅
- All 14 roles tests pass ✅
- All 33 API auth tests pass ✅
- All 791 unit tests pass ✅
- Code coverage maintained at 78% for Discord client
- ruff linting: All checks passed
- mypy type checking: No issues found

### Impact
- OAuth login now works correctly
- Users can successfully authenticate via Discord
- Existing bot token functionality remains unchanged
- All downstream services using the Discord client continue to work properly
