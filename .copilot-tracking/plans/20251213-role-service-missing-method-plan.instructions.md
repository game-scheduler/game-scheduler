---
applyTo: ".copilot-tracking/changes/20251213-role-service-missing-method-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Fix Type Errors Found by MyPy

## Overview

Fix 4 type errors discovered by mypy that were previously hidden due to `continue-on-error: true` in CI configuration. Three are critical runtime issues, one is a type annotation mismatch.

## Objectives

- Fix 4 type errors discovered by mypy analysis
- Fix critical AttributeError causing API service crashes when accessing games with role restrictions
- Fix incorrect parameter passing in check_game_host_permission calls
- Fix incorrect parameter in GuildConfigResponse instantiation
- Fix type annotation for RabbitMQ queue arguments
- Remove `continue-on-error: true` from CI mypy configuration

## Research Summary

### Project Files

- services/api/auth/roles.py - RoleVerificationService class missing `has_any_role()` method
- services/api/dependencies/permissions.py - Line 192 calls the missing method in `verify_game_access()`
- services/api/routes/games.py - Line 170 triggers the error in `get_game` endpoint

### External References

- #file:../research/20251213-role-service-missing-method-research.md - Complete error analysis and implementation guidance
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards

### Standards References

- #file:../../.github/instructions/coding-best-practices.instructions.md - Core coding principles
- Git commit 5c40e4b5 - REST security audit that added the method call without implementation

## Implementation Checklist

### [ ] Phase 1: Fix Critical Runtime Errors

- [ ] Task 1.1: Add `has_any_role()` method to RoleVerificationService

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 1-35)

- [ ] Task 1.2: Remove invalid `channel_id` parameter from check_game_host_permission call

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 37-55)

- [ ] Task 1.3: Fix invalid `guild_id` parameter in GuildConfigResponse

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 57-75)

- [ ] Task 1.4: Verify method signature matches usage

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 77-90)

### [ ] Phase 2: Fix Type Annotation Issues

- [ ] Task 2.1: Fix RabbitMQ queue arguments type annotation

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 92-110)

### [ ] Phase 3: Testing and Verification

- [ ] Task 3.1: Write unit tests for `has_any_role()` method

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 112-135)

- [ ] Task 3.2: Run all unit tests

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 137-150)

- [ ] Task 3.3: Verify API service starts without errors

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 152-165)

- [ ] Task 3.4: Run integration tests

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 167-180)

### [ ] Phase 4: CI Configuration Fix

- [ ] Task 4.1: Remove continue-on-error from mypy CI step

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 182-200)

### [ ] Phase 5: Code Quality Verification

- [ ] Task 5.1: Run mypy and verify all errors are fixed

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 202-215)

- [ ] Task 5.2: Run linters

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 217-225)

- [ ] Task 5.3: Verify no compile or runtime errors

  - Details: .copilot-tracking/details/20251213-role-service-missing-method-details.md (Lines 227-240)

## Dependencies

- Existing `get_user_role_ids()` method in RoleVerificationService
- Redis cache infrastructure for role caching
- Existing test mocks in test_permissions.py and test_negative_authorization.py

## Success Criteria

- All 4 mypy type errors are resolved
- API service starts without AttributeError
- All existing tests continue to pass
- Games with `allowed_player_role_ids` enforce role restrictions correctly
- Guild configuration create/update works correctly
- RabbitMQ messaging works without type errors
- Users with required roles can access games (200 response)
- Users without required roles receive 403 Forbidden response
- `uv run mypy shared/ services/` returns 0 errors
- CI mypy step fails on type errors (no more continue-on-error)
- No lint or runtime errors remain
