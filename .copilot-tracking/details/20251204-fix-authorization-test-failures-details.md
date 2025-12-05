<!-- markdownlint-disable-file -->
# Task Details: Fix Authorization Test Failures

## Research Reference

**Source Research**: #file:../research/20251204-fix-authorization-test-failures-research.md

## Phase 1: Fix Role Service Tests

### Task 1.1: Update role ID assertion tests

Fix `test_get_user_role_ids_from_api` and `test_get_user_role_ids_force_refresh` tests to account for automatic guild_id appending.

- **Files**:
  - tests/services/api/auth/test_roles.py (Lines 67-95) - Two role ID tests
- **Success**:
  - Both tests pass with updated assertions
  - Assertions verify guild_id is included in returned role list
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 21-41) - Root cause analysis for role list tests
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 140-148) - Pattern 1 for updating role ID assertions
- **Dependencies**:
  - None

### Task 1.2: Update check_game_host_permission tests

Fix three tests using old `check_game_host_permission` signature to use new signature with `allowed_host_role_ids` instead of `channel_id`.

- **Files**:
  - tests/services/api/auth/test_roles.py (Lines 118-154) - Three permission check tests
- **Success**:
  - All three tests pass with new signature
  - Tests properly use `allowed_host_role_ids` parameter
  - Tests no longer pass unused `channel_id` parameter
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 43-68) - Root cause analysis for permission check tests
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 150-165) - Pattern 2 for updating check_game_host_permission calls
- **Dependencies**:
  - None

## Phase 2: Fix Template Service Tests

### Task 2.1: Update get_templates_for_user test calls

Update all four template service tests to use new `get_templates_for_user` signature with `role_service` mock.

- **Files**:
  - tests/services/api/services/test_template_service.py (Lines 63-167) - Four template filtering tests
- **Success**:
  - All four tests pass with new signature
  - Tests properly mock `role_service.check_game_host_permission`
  - Mock returns appropriate values for each test scenario
  - Tests verify correct template filtering behavior
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 106-133) - Root cause analysis for template service tests
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 167-191) - Pattern 3 for updating get_templates_for_user calls
- **Dependencies**:
  - None

## Phase 3: Fix Game Service Tests

### Task 3.1: Add role service mock infrastructure

Create `role_service` fixture and update test setup to provide proper mocking infrastructure.

- **Files**:
  - tests/services/api/services/test_games.py - Add fixture near other fixtures
- **Success**:
  - `mock_role_service` fixture created
  - Fixture provides AsyncMock with `check_game_host_permission` method
  - Method mocked to return True by default
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 86-104) - Root cause analysis for game service tests
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 193-204) - Pattern 4 for adding role service mock
- **Dependencies**:
  - None

### Task 3.2: Update game creation test calls

Update all five game creation tests to use role service mocking with proper patching.

- **Files**:
  - tests/services/api/services/test_games.py - Five game creation tests
- **Success**:
  - All five tests pass with proper role service mocking
  - Tests use patch for `get_role_service` to inject mock
  - Mock properly simulates successful permission checks
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 86-104) - Root cause analysis for game service tests
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 193-204) - Pattern 4 implementation example
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Fix Guild Route Tests

### Task 4.1: Investigate and fix guild route authorization tests

Analyze and fix six guild route tests failing with 404 instead of expected 403 errors.

- **Files**:
  - tests/services/api/routes/test_guilds.py - Six guild route tests
- **Success**:
  - All six tests pass with correct error codes
  - Authorization flow properly handles non-member access
  - Tests properly mock guild membership verification
  - Mock setup aligns with `can_manage_game` changes
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 70-84) - Root cause analysis for guild route tests
- **Dependencies**:
  - None

## Phase 5: Fix Remaining Tests

### Task 5.1: Fix guild service test

Investigate and fix `test_update_guild_config_ignores_none_values` test failure.

- **Files**:
  - tests/services/api/services/test_guild_service.py (Line 103) - Single guild service test
- **Success**:
  - Test passes with proper mock setup
  - Test accurately reflects guild config update behavior
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 135-138) - Root cause analysis for guild service test
- **Dependencies**:
  - None

## Phase 6: Verification

### Task 6.1: Run full test suite and verify all pass

Execute complete test suite to verify all fixes are successful.

- **Files**:
  - All test files modified in previous phases
- **Success**:
  - All 21 previously failing tests now pass
  - No new test failures introduced
  - Test execution time remains acceptable
  - All tests accurately reflect authorization behavior changes
- **Research References**:
  - #file:../research/20251204-fix-authorization-test-failures-research.md (Lines 223-230) - Success criteria
- **Dependencies**:
  - All previous phases completed

## Dependencies

- pytest
- Python testing infrastructure
- Existing test fixtures and mocks

## Success Criteria

- All 21 previously failing tests now pass
- No new test failures introduced
- Test execution time remains acceptable
- Tests accurately reflect authorization behavior changes
