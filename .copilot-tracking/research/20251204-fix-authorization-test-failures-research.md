<!-- markdownlint-disable-file -->
# Research: Fix Authorization Test Failures from Commit 0526958

## Overview

Research findings for fixing 21 test failures introduced in commit 0526958405a7bdde55810001816bfd96bb14d014, which enhanced template role restrictions in game creation.

## Commit Analysis

### Changes Made (commit 0526958)

The commit made significant authorization improvements:

1. **Enhanced `get_user_role_ids` in `services/api/auth/roles.py` (Lines 75-85)**:
   - Now automatically adds guild_id as @everyone role
   - Discord doesn't include @everyone in roles array but every member has it
   - This breaks tests expecting exact role matches

2. **Refactored `check_game_host_permission` in `services/api/auth/roles.py` (Lines 137-175)**:
   - Changed signature from `(user_id, guild_id, db, channel_id, access_token)` to `(user_id, guild_id, db, allowed_host_role_ids, access_token)`
   - Removed `channel_id` parameter (unused)
   - Added `allowed_host_role_ids` parameter for template-based restrictions
   - Bot managers can always host
   - If no roles specified (None or []), only managers can host
   - Non-managers must have one of the specified roles

3. **Refactored `get_templates_for_user` in `services/api/services/template_service.py` (Lines 40-92)**:
   - Changed signature from `(guild_id, user_role_ids, is_admin)` to `(guild_id, user_id, discord_guild_id, role_service, access_token)`
   - Now uses centralized permission checking via `role_service.check_game_host_permission`
   - Iterates through templates and filters based on actual permission checks

4. **Updated `create_game` in `services/api/services/games.py` (Lines 115-135)**:
   - Now calls `role_service.check_game_host_permission` with template's `allowed_host_role_ids`
   - Uses centralized permission logic instead of inline role checking

5. **Simplified `can_manage_game` in `services/api/dependencies/permissions.py` (Lines 239-265)**:
   - Now uses `check_bot_manager_permission` directly
   - Removed redundant admin permission check

## Test Failure Categories

### Category 1: Role List Tests (2 failures)

**Files**: `tests/services/api/auth/test_roles.py`

**Affected Tests**:
- `test_get_user_role_ids_from_api` (Line 67-78)
- `test_get_user_role_ids_force_refresh` (Line 82-95)

**Root Cause**: Tests expect `["role1", "role2", "role3"]` but get `["role1", "role2", "role3", "guild456"]` because guild_id is now automatically appended.

**Fix Strategy**: Update assertions to include guild_id in expected results.

### Category 2: check_game_host_permission Tests (3 failures)

**Files**: `tests/services/api/auth/test_roles.py`

**Affected Tests**:
- `test_check_game_host_permission_with_manage_guild` (Line 118-128)
- `test_check_game_host_permission_without_token` (Line 132-140)
- `test_check_game_host_permission_no_permission` (Line 144-154)

**Root Cause**: Tests still pass `channel_id` parameter and don't pass `allowed_host_role_ids`.

**Fix Strategy**: Update test calls to use new signature with `allowed_host_role_ids` instead of `channel_id`.

### Category 3: Guild Route Tests (6 failures)

**Files**: `tests/services/api/routes/test_guilds.py`

**Affected Tests**:
- `TestListGuilds::test_list_guilds_success`
- `TestGetGuild::test_get_guild_success`
- `TestGetGuild::test_get_guild_not_member`
- `TestCreateGuildConfig::test_create_guild_success`
- `TestUpdateGuildConfig::test_update_guild_success`
- `TestListGuildChannels::test_list_channels_not_member`

**Root Cause**: Tests fail with 404 errors where 403 was expected. This suggests the authorization flow has changed in how it handles non-member access.

**Fix Strategy**: Review and update mock setup to align with new permission checking flow. The `can_manage_game` changes may have affected how guild membership is verified.

### Category 4: Game Creation Tests (5 failures)

**Files**: `tests/services/api/services/test_games.py`

**Affected Tests**:
- `test_create_game_without_participants`
- `test_create_game_with_where_field`
- `test_create_game_with_valid_participants`
- `test_create_game_with_invalid_participants`
- `test_create_game_timezone_conversion`

**Root Cause**: `create_game` now requires `role_service` mock and calls `check_game_host_permission` with new parameters.

**Fix Strategy**: 
- Add `role_service` mock to test fixtures
- Mock `role_service.check_game_host_permission` to return True for valid tests
- Update test setup to provide proper mocking infrastructure

### Category 5: Template Service Tests (4 failures)

**Files**: `tests/services/api/services/test_template_service.py`

**Affected Tests**:
- `test_get_templates_for_user_admin` (Line 63-86)
- `test_get_templates_for_user_with_role_filtering` (Line 90-116)
- `test_get_templates_for_user_no_matching_roles` (Line 120-141)
- `test_get_templates_for_user_empty_allowed_roles` (Line 145-167)

**Root Cause**: `get_templates_for_user` signature changed from `(guild_id, user_role_ids, is_admin)` to `(guild_id, user_id, discord_guild_id, role_service, access_token)`.

**Fix Strategy**:
- Update all calls to use new signature
- Add `role_service` mock to fixture
- Mock `role_service.check_game_host_permission` to return appropriate values for each test scenario

### Category 6: Guild Service Test (1 failure)

**Files**: `tests/services/api/services/test_guild_service.py`

**Affected Test**:
- `test_update_guild_config_ignores_none_values` (Line 103)

**Root Cause**: Needs investigation - may be related to mock setup changes.

**Fix Strategy**: Review test and update mocking as needed.

## Implementation Guidelines

### Pattern 1: Updating Role ID Assertions

**Before**:
```python
assert role_ids == ["role1", "role2", "role3"]
```

**After**:
```python
assert role_ids == ["role1", "role2", "role3", "guild456"]
```

### Pattern 2: Updating check_game_host_permission Calls

**Before**:
```python
can_host = await role_service.check_game_host_permission(
    "user123", "guild456", mock_db, "channel789", "access_token"
)
```

**After**:
```python
can_host = await role_service.check_game_host_permission(
    "user123", "guild456", mock_db, ["role1", "role2"], "access_token"
)
```

### Pattern 3: Updating get_templates_for_user Calls

**Before**:
```python
templates = await template_service.get_templates_for_user(
    guild_id="guild-uuid-1",
    user_role_ids=["role3"],
    is_admin=True,
)
```

**After**:
```python
mock_role_service = AsyncMock()
mock_role_service.check_game_host_permission.return_value = True

templates = await template_service.get_templates_for_user(
    guild_id="guild-uuid-1",
    user_id="user123",
    discord_guild_id="123456789",
    role_service=mock_role_service,
    access_token="access_token",
)
```

### Pattern 4: Adding Role Service Mock to Game Tests

**Add to fixtures**:
```python
@pytest.fixture
def mock_role_service():
    """Create mock role service."""
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    return role_service
```

**Update create_game calls with patch**:
```python
with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
    game = await game_service.create_game(...)
```

## Test Files to Update

1. `tests/services/api/auth/test_roles.py` - 5 tests
2. `tests/services/api/routes/test_guilds.py` - 6 tests
3. `tests/services/api/services/test_games.py` - 5 tests
4. `tests/services/api/services/test_template_service.py` - 4 tests
5. `tests/services/api/services/test_guild_service.py` - 1 test

## Success Criteria

- All 21 failing tests pass
- No new test failures introduced
- Tests accurately reflect new authorization behavior
- Mock setup follows project testing conventions
- Changes are minimal and focused on test updates only

## References

- Failing commit: 0526958405a7bdde55810001816bfd96bb14d014
- Modified files: `services/api/auth/roles.py`, `services/api/dependencies/permissions.py`, `services/api/services/games.py`, `services/api/services/template_service.py`
