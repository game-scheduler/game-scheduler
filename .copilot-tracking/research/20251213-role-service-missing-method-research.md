<!-- markdownlint-disable-file -->
# Task Research Notes: Missing has_any_role Method in RoleVerificationService

## Research Executed

### Error Analysis
- api.log shows `AttributeError: 'RoleVerificationService' object has no attribute 'has_any_role'`
- Error occurs in `services/api/dependencies/permissions.py` line 192
- Called from `services/api/routes/games.py` line 170 in `get_game` endpoint
- Error triggered when accessing a game with allowed_player_role_ids configured

### File Analysis
- services/api/auth/roles.py
  - RoleVerificationService class exists with methods:
    - `get_user_role_ids(user_id, guild_id, force_refresh)` - Get user's role IDs with caching
    - `has_permissions(user_id, guild_id, access_token, *permissions)` - Check permission flags
    - `check_game_host_permission(...)` - Check if user can host games
    - `check_bot_manager_permission(...)` - Check Bot Manager role
    - `invalidate_user_roles(...)` - Cache invalidation
  - **Missing**: `has_any_role()` method
  
- services/api/dependencies/permissions.py (lines 185-200)
  - `verify_game_access()` helper calls `role_service.has_any_role()` at line 192
  - Expected signature based on call: `has_any_role(user_discord_id, guild_id, access_token, role_ids_list)`
  - Purpose: Check if user has any of the specified role IDs in a guild

### Code Search Results
- `has_any_role` usage found in 8 locations:
  - 1 implementation call: services/api/dependencies/permissions.py:192
  - 5 test mocks: tests/services/api/test_negative_authorization.py (lines 240, 263, 301, 652)
  - 2 test assertions: tests/services/api/dependencies/test_permissions.py (lines 529, 540, 560)

### Test Analysis
- tests/services/api/dependencies/test_permissions.py lines 520-550
  - Tests mock `has_any_role` with signature: `has_any_role(user_id, guild_id, access_token, role_ids_list)`
  - Expected return: boolean (True if user has any of the specified roles)
  - Test case: `test_verify_game_access_role_check_passes`
  ```python
  mock_role_service.has_any_role.return_value = True
  # ...
  mock_role_service.has_any_role.assert_called_once_with(
      "user123", "guild123", "test_token", ["role1", "role2"]
  )
  ```

### Git History Analysis
- Searched for `has_any_role` in services/api/auth/roles.py history - **never existed**
- Method call added in commit `5c40e4b5` (REST security audit phase 1)
- That commit added `verify_game_access()` helper which calls `has_any_role()`
- **Root cause**: Implementation was added to permissions.py that calls a method that was never implemented in roles.py

### Project Conventions
- Standards referenced: .github/instructions/python.instructions.md
- Redis caching pattern: Existing `get_user_role_ids()` method uses cache with TTL
- Service singleton pattern: `get_role_service()` function at end of roles.py

## Key Discoveries

### Implementation Gap
The REST API authorization audit (commit 5c40e4b5, December 4, 2025) introduced `verify_game_access()` which calls `role_service.has_any_role()`, but the corresponding method was never added to `RoleVerificationService`. Tests mock this method, so unit tests pass, but runtime fails.

### Existing Building Blocks
`RoleVerificationService` already has `get_user_role_ids()` which:
- Fetches user's role IDs from Discord API
- Caches results in Redis with TTL
- Includes @everyone role (guild_id)
- Returns list of role IDs

### Required Functionality
`has_any_role()` needs to:
1. Get user's role IDs (can use existing `get_user_role_ids()`)
2. Check if any role ID in user's roles matches any in the provided list
3. Return boolean result

### Complete Implementation Pattern
```python
async def has_any_role(
    self,
    user_id: str,
    guild_id: str,
    access_token: str,  # Not used but kept for signature compatibility
    role_ids: list[str],
) -> bool:
    """
    Check if user has any of the specified roles in a guild.
    
    Args:
        user_id: Discord user ID
        guild_id: Discord guild ID
        access_token: User's OAuth2 access token (unused, kept for compatibility)
        role_ids: List of role IDs to check for
        
    Returns:
        True if user has at least one of the specified roles
    """
    if not role_ids:
        return False
        
    user_role_ids = await self.get_user_role_ids(user_id, guild_id)
    return any(role_id in role_ids for role_id in user_role_ids)
```

## Recommended Approach

Add the missing `has_any_role()` method to `RoleVerificationService` class in `services/api/auth/roles.py`:

1. **Method signature**: Match the signature expected by tests and usage in permissions.py
2. **Implementation**: Leverage existing `get_user_role_ids()` for role fetching and caching
3. **Logic**: Simple set intersection check - return True if user has any of the specified roles
4. **Placement**: Add after `has_permissions()` method (around line 140) to maintain logical grouping

### Implementation Details
- **File**: services/api/auth/roles.py
- **Location**: After `has_permissions()` method (line ~140)
- **Dependencies**: Uses existing `get_user_role_ids()` method
- **Caching**: Inherits caching behavior from `get_user_role_ids()`
- **Error handling**: Inherits error handling from `get_user_role_ids()`

### Why This Approach
1. **Correctness**: Fixes the AttributeError causing API crashes
2. **Consistency**: Uses existing patterns and methods in the service
3. **Minimal**: Single method addition, no refactoring needed
4. **Tested**: Tests already exist and mock this method signature
5. **Performance**: Leverages existing Redis caching via `get_user_role_ids()`

## Why Tools Didn't Catch This

### MyPy Configuration Issues

**Tool Capability**: MyPy **DOES** detect this error correctly:
```bash
$ uv run mypy services/api/dependencies/permissions.py
services/api/dependencies/permissions.py:192: error: "RoleVerificationService" has no attribute "has_any_role"  [attr-defined]
```

**Root Cause**: CI/CD pipeline configuration at `.github/workflows/ci-cd.yml` line 172:
```yaml
- name: Run mypy type checker
  run: uv run mypy shared/ services/
  continue-on-error: true  # ← This allows mypy failures to be ignored
```

The `continue-on-error: true` setting means:
- MyPy runs and detects the error
- The error is logged but doesn't fail the build
- CI passes even with type errors
- Developers don't see failed CI status

### Why Unit Tests Didn't Catch This

Tests use mocks that create the missing method:
```python
# tests/services/api/dependencies/test_permissions.py
mock_role_service.has_any_role.return_value = True
```

Mocking creates attributes dynamically, so:
- Unit tests pass because mock provides `has_any_role`
- Tests verify the **calling** code behavior, not the service implementation
- Integration/E2E tests would catch this, but only if they exercise this code path

### What Would Catch This

1. **Remove `continue-on-error: true`** from mypy CI step
   - Makes type checking a hard requirement
   - Prevents merging code with type errors
   
2. **Run mypy locally before committing**
   - Already configured in `pyproject.toml`
   - Need to establish pre-commit workflow
   
3. **Integration tests without mocks**
   - Test actual service implementations
   - Would fail at runtime when calling missing method
   
4. **Stricter mypy configuration**
   - Current: `ignore_missing_imports = true`, `strict_optional = false`
   - Could enable `--strict` mode for stronger checking

### Recommended Configuration Changes

1. **Immediate**: Remove `continue-on-error: true` from CI mypy step
2. **Short-term**: Add pre-commit hook to run mypy locally
3. **Long-term**: Gradually enable stricter mypy options as codebase allows

## Additional Type Errors Found

Running mypy across the entire codebase revealed 4 total errors:

### 1. Missing `has_any_role` method (PRIMARY ISSUE)
- **File**: services/api/dependencies/permissions.py:192
- **Error**: `"RoleVerificationService" has no attribute "has_any_role"`
- **Impact**: Runtime AttributeError when accessing games with role restrictions

### 2. Unexpected `channel_id` parameter
- **File**: services/api/dependencies/permissions.py:463
- **Error**: `Unexpected keyword argument "channel_id" for "check_game_host_permission"`
- **Method signature**: `check_game_host_permission(user_id, guild_id, db, allowed_host_role_ids, access_token)`
- **Call site passes**: `channel_id=channel_id` (not in signature)
- **Impact**: Would cause runtime TypeError if this code path is executed

### 3. RabbitMQ queue arguments type mismatch
- **File**: shared/messaging/consumer.py:83
- **Error**: `Argument "arguments" has incompatible type "dict[str, str | int]"; expected "dict[str, FieldValue]"`
- **Root cause**: `PRIMARY_QUEUE_ARGUMENTS` defined as `dict[str, str | int]` but aio-pika expects `dict[str, FieldValue]`
- **Impact**: Type annotation mismatch only - runtime works due to duck typing

### 4. Unexpected `guild_id` parameter in GuildConfigResponse
- **File**: services/api/routes/guilds.py:167
- **Error**: `Unexpected keyword argument "guild_id" for "GuildConfigResponse"`
- **Schema has**: `id`, `guild_name`, `bot_manager_role_ids`, `require_host_role`, `created_at`, `updated_at`
- **Call passes**: `guild_id=guild_config.guild_id` (should be just assigning from model attribute)
- **Impact**: Would cause runtime ValidationError from Pydantic

### Error Priority Analysis

**Critical (will cause runtime failures)**:
1. Missing `has_any_role` method - **confirmed runtime crash**
2. Unexpected `channel_id` parameter - **will crash if code path executed**
4. Unexpected `guild_id` parameter - **will crash on guild config create**

**Low priority (type annotation only)**:
3. RabbitMQ arguments type - works at runtime, just type mismatch

## Implementation Guidance

- **Objectives**: 
  - Fix AttributeError in game access verification
  - Enable player role restrictions for games
  - Restore API functionality for games with allowed_player_role_ids
  - Fix CI configuration to prevent similar issues

- **Key Tasks**:
  1. Add `has_any_role()` method to RoleVerificationService class
  2. Remove `continue-on-error: true` from mypy CI step
  3. Verify tests pass (existing tests already mock this method)
  4. Test runtime behavior with actual game access

- **Dependencies**: 
  - Existing `get_user_role_ids()` method
  - Redis cache infrastructure

- **Success Criteria**:
  - API no longer crashes with AttributeError
  - Games with allowed_player_role_ids enforce role restrictions
  - Users with correct roles can access games
  - Users without correct roles receive 403 Forbidden
  - All existing tests continue to pass
  - MyPy type checking fails CI on type errors
