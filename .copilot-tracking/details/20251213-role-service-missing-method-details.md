<!-- markdownlint-disable-file -->

# Task Details: Fix Type Errors Found by MyPy

## Research Reference

**Source Research**: #file:../research/20251213-role-service-missing-method-research.md

## Phase 1: Fix Critical Runtime Errors

### Task 1.1: Add `has_any_role()` method to RoleVerificationService

Add the missing method to `services/api/auth/roles.py` after the `has_permissions()` method (around line 135).

- **Files**:
  - services/api/auth/roles.py - Add `has_any_role()` method to RoleVerificationService class
- **Success**:
  - Method exists with correct signature: `async def has_any_role(self, user_id: str, guild_id: str, access_token: str, role_ids: list[str]) -> bool`
  - Method includes proper docstring with Args and Returns sections
  - Method uses type hints for all parameters and return value
  - Implementation leverages existing `get_user_role_ids()` method
  - Returns False for empty role_ids list
  - Uses `any()` with list comprehension for role checking
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 71-100) - Complete implementation pattern
  - #file:../../.github/instructions/python.instructions.md - Python type hints and conventions
- **Dependencies**:
  - Existing `get_user_role_ids()` method must be functional

### Task 1.2: Remove invalid `channel_id` parameter from check_game_host_permission call

Fix the incorrect parameter being passed at line 463 of permissions.py.

- **Files**:
  - services/api/dependencies/permissions.py - Line 463, remove `channel_id=channel_id,` from call
- **Success**:
  - Method call matches signature: `check_game_host_permission(user_id, guild_id, db, allowed_host_role_ids, access_token)`
  - No `channel_id` parameter passed
  - Code compiles without type errors
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 199-205) - Error #2 details
  - services/api/auth/roles.py (line 137) - Actual method signature
- **Dependencies**:
  - None

### Task 1.3: Fix invalid `guild_id` parameter in GuildConfigResponse

Fix the incorrect parameter at line 167 of guilds.py route.

- **Files**:
  - services/api/routes/guilds.py - Line 167-169, remove `guild_id=guild_config.guild_id,`
- **Success**:
  - GuildConfigResponse instantiation uses only valid fields: `id`, `guild_name`, `bot_manager_role_ids`, `require_host_role`, `created_at`, `updated_at`
  - No `guild_id` parameter passed (it's already captured as `id`)
  - Code compiles without Pydantic validation errors
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 211-218) - Error #4 details
  - shared/schemas/guild.py - GuildConfigResponse schema definition
- **Dependencies**:
  - None

### Task 1.4: Verify method signature matches usage

Ensure the implemented method signature matches all call sites.

- **Files**:
  - services/api/dependencies/permissions.py (line 192) - Verify call signature
  - tests/services/api/dependencies/test_permissions.py (lines 529, 540) - Verify test expectations
  - tests/services/api/test_negative_authorization.py (lines 240, 263, 301, 652) - Verify test mocks
- **Success**:
  - Method signature matches call in `verify_game_access()`: `role_service.has_any_role(user_discord_id, guild_id, access_token, role_ids_list)`
  - All test mocks use the same signature
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 26-43) - Test signature analysis
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Fix Type Annotation Issues

### Task 2.1: Fix RabbitMQ queue arguments type annotation

Update the type annotation for PRIMARY_QUEUE_ARGUMENTS to match aio-pika's expected type.

- **Files**:
  - shared/messaging/infrastructure.py - Line 51, change type annotation from `dict[str, str | int]` to `dict[str, Any]`
  - Add import: `from typing import Any`
- **Success**:
  - Type annotation matches aio-pika's `dict[str, FieldValue]` expectation
  - Code compiles without mypy errors
  - Runtime behavior unchanged (duck typing already works)
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 207-209) - Error #3 details
- **Dependencies**:
  - None

## Phase 3: Testing and Verification

### Task 3.1: Write unit tests for `has_any_role()` method

Create dedicated unit tests for the new method in the roles test file.

- **Files**:
  - tests/services/api/auth/test_roles.py - Create or add tests for `has_any_role()` method
- **Success**:
  - Test case: User has at least one of the specified roles (returns True)
  - Test case: User has none of the specified roles (returns False)
  - Test case: Empty role_ids list provided (returns False)
  - Test case: User has @everyone role (guild_id) which matches
  - Test case: Multiple roles checked, user has one (returns True)
  - All new tests use proper mocking of `get_user_role_ids()`
  - Tests follow existing test patterns in the project
  - Minimum 80% code coverage for the new method
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 71-100) - Implementation pattern
  - #file:../../.github/instructions/python.instructions.md - Testing conventions
- **Dependencies**:
  - Task 1.1 and 1.4 completion

### Task 3.2: Run all unit tests

Execute all relevant unit tests to ensure the implementation works correctly.

- **Files**:
  - tests/services/api/auth/test_roles.py - New tests for `has_any_role()`
  - tests/services/api/dependencies/test_permissions.py - 44 permission tests
  - tests/services/api/test_negative_authorization.py - 24 negative authorization tests
- **Success**:
  - All new tests pass
  - All 68 existing tests continue to pass without errors
  - Tests `test_verify_game_access_role_check_success` and `test_verify_game_access_role_check_fails` pass
  - No test failures introduced
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 144-150) - Success criteria
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Verify API service starts without errors

Restart the API service and check logs for successful startup.

- **Files**:
  - services/api/auth/roles.py - Modified file
- **Success**:
  - `docker compose restart api` completes successfully
  - API logs show "Started server process" without AttributeError
  - No errors related to `has_any_role` in logs
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 1-9) - Original error analysis
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Run integration tests

Execute integration test suite to verify system-level functionality.

- **Files**:
  - All integration test files
- **Success**:
  - Integration tests pass
  - No new failures introduced
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 144-150) - Success criteria
- **Dependencies**:
  - Task 3.3 completion

## Phase 4: CI Configuration Fix

### Task 4.1: Remove continue-on-error from mypy CI step

Update CI configuration to make mypy failures block the build.

- **Files**:
  - .github/workflows/ci-cd.yml - Line 173, remove `continue-on-error: true`
- **Success**:
  - Mypy step no longer has `continue-on-error: true`
  - CI will fail if mypy detects type errors
  - Future type errors will be caught before merge
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 145-170) - Why tools didn't catch this
- **Dependencies**:
  - Phase 3 completion (all type errors must be fixed first)

## Phase 5: Code Quality Verification

### Task 5.1: Run mypy and verify all errors are fixed

Run mypy on entire codebase and verify 0 errors.

- **Files**:
  - All modified files
- **Success**:
  - `uv run mypy shared/ services/ --show-error-codes` returns exit code 0
  - No type errors reported
  - Output shows "Success: no issues found"
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 145-170) - MyPy configuration
- **Dependencies**:
  - Phase 1, 2, and 3 completion

### Task 5.2: Run linters

Verify code meets project quality standards.

- **Files**:
  - All modified files
- **Success**:
  - `uv run ruff check .` passes with no errors
  - `uv run ruff format --check .` passes with no formatting issues
- **Research References**:
  - #file:../../.github/instructions/python.instructions.md - Python quality standards
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Verify no compile or runtime errors

Final verification that no errors remain.

- **Files**:
  - All modified files
- **Success**:
  - `get_errors` tool reports no issues in modified files
  - API service runs without errors when accessing games with role restrictions
  - Guild configuration create/update works correctly
  - RabbitMQ consumers start without errors
  - Users with required roles can access games (200 response)
  - Users without required roles receive 403 Forbidden
- **Research References**:
  - #file:../research/20251213-role-service-missing-method-research.md (Lines 220-230) - All error impacts
- **Dependencies**:
  - Task 5.2 completion

## Dependencies

- Existing `get_user_role_ids()` method in RoleVerificationService
- Redis cache infrastructure
- Docker Compose environment for API service

## Success Criteria

- AttributeError completely eliminated
- All existing tests continue to pass (68 tests)
- Role-based game access control functions correctly
- Code passes all linters and type checkers
- No new errors or warnings introduced
