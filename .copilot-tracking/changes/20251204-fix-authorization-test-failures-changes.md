<!-- markdownlint-disable-file -->

# Release Changes: Fix Authorization Test Failures

**Related Plan**: 20251204-fix-authorization-test-failures-plan.instructions.md
**Implementation Date**: 2025-12-04

## Summary

Fixed 21 test failures introduced by commit 0526958 which enhanced template role restrictions in game creation. Updated test mocks and assertions to align with new authorization patterns without modifying production code.

## Changes

### Added

### Modified

- tests/services/api/auth/test_roles.py - Updated role ID assertions to include guild_id, fixed check_game_host_permission test signatures to mock check_bot_manager_permission instead of has_permissions, and added get_user_role_ids mocking
- tests/services/api/services/test_template_service.py - Updated get_templates_for_user test calls to use new signature with role_service mock
- tests/services/api/services/test_games.py - Added role_service mock fixture, updated all game creation tests to patch get_role_service, and fixed mock_db.execute side_effect order (host_result before channel_result)
- tests/services/api/routes/test_guilds.py - Updated guild route tests to use correct response field names (id instead of guild_id), expect 404 instead of 403 for non-member access, and added get_guild_name mocking to avoid Redis calls
- tests/services/api/services/test_guild_service.py - Fixed test_update_guild_config_ignores_none_values to match actual service behavior (None values are set, not ignored)

### Removed

## Release Summary

**Total Files Affected**: 5

### Files Created (0)

None

### Files Modified (5)

- tests/services/api/auth/test_roles.py - Fixed role ID assertions and permission check test mocking to align with new authorization flow
- tests/services/api/services/test_template_service.py - Updated template service tests to use new get_templates_for_user signature
- tests/services/api/services/test_games.py - Added role service mocking and fixed database query order in game creation tests
- tests/services/api/routes/test_guilds.py - Updated response field assertions and added missing mocks for Redis-dependent calls
- tests/services/api/services/test_guild_service.py - Corrected test expectations to match actual service behavior

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None

### Deployment Notes

No deployment changes required. All fixes are test-only changes that align tests with authorization enhancements introduced in commit 0526958.

