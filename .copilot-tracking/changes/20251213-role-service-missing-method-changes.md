<!-- markdownlint-disable-file -->

# Release Changes: Fix Type Errors Found by MyPy

**Related Plan**: 20251213-role-service-missing-method-plan.instructions.md
**Implementation Date**: 2025-12-12

## Summary

Fixed 4 critical type errors discovered by mypy that were previously hidden due to `continue-on-error: true` in CI configuration. Added missing `has_any_role()` method to RoleVerificationService, fixed incorrect parameter passing in method calls, and corrected type annotations. Removed `continue-on-error` from mypy CI step to prevent future type errors from being silently ignored.

## Changes

### Added

### Modified

- services/api/auth/roles.py - Added missing `has_any_role()` method to RoleVerificationService class
- services/api/dependencies/permissions.py - Removed invalid `channel_id` parameter from `check_game_host_permission()` call
- services/api/routes/guilds.py - Removed invalid `guild_id` parameter from GuildConfigResponse instantiation
- shared/messaging/infrastructure.py - Changed PRIMARY_QUEUE_ARGUMENTS type annotation from `dict[str, str | int]` to `dict[str, Any]`
- tests/services/api/auth/test_roles.py - Added 5 unit tests for `has_any_role()` method
- tests/services/api/dependencies/test_permissions.py - Updated test assertions to remove `channel_id` parameter
- .github/workflows/ci-cd.yml - Removed `continue-on-error: true` from mypy type checking step

### Removed

## Release Summary

**Total Files Affected**: 8

### Files Created (0)

None

### Files Modified (8)

- services/api/auth/roles.py - Added missing `has_any_role()` method to RoleVerificationService class after `has_permissions()` method
- services/api/dependencies/permissions.py - Removed invalid `channel_id` parameter from `check_game_host_permission()` call at line 463
- services/api/routes/guilds.py - Removed invalid `guild_id` parameter from GuildConfigResponse instantiation at line 167
- shared/messaging/infrastructure.py - Changed PRIMARY_QUEUE_ARGUMENTS type annotation from `dict[str, str | int]` to `dict[str, Any]` and added `Any` import
- tests/services/api/auth/test_roles.py - Added 5 comprehensive unit tests for new `has_any_role()` method covering various scenarios
- tests/services/api/dependencies/test_permissions.py - Updated 2 test assertions to remove `channel_id` parameter expectations
- .github/workflows/ci-cd.yml - Removed `continue-on-error: true` from mypy type checking step to enforce type safety

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: CI/CD now enforces mypy type checking without allowing failures
- **Configuration Updates**: Removed `continue-on-error: true` from GitHub Actions mypy step

### Deployment Notes

This fix addresses critical runtime errors discovered by mypy analysis. All changes are backward compatible and do not require database migrations or configuration updates. The API service will start successfully without AttributeError when accessing games with role restrictions. Future type errors will now fail CI builds, preventing similar issues from reaching production.

