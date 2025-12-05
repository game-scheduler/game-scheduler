---
applyTo: '.copilot-tracking/changes/20251204-fix-authorization-test-failures-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: Fix Authorization Test Failures

## Overview

Fix 21 test failures introduced by commit 0526958 which enhanced template role restrictions in game creation.

## Objectives

- Fix all failing tests to work with new authorization patterns
- Maintain test coverage and accuracy
- Ensure tests reflect actual system behavior
- No changes to production code

## Research Summary

### Project Files
- tests/services/api/auth/test_roles.py - Role verification tests
- tests/services/api/routes/test_guilds.py - Guild route tests
- tests/services/api/services/test_games.py - Game service tests
- tests/services/api/services/test_template_service.py - Template service tests
- tests/services/api/services/test_guild_service.py - Guild service tests

### External References
- #file:../research/20251204-fix-authorization-test-failures-research.md - Comprehensive failure analysis

### Standards References
- #file:../../.github/instructions/python.instructions.md - Python testing conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Testing best practices

## Implementation Checklist

### [x] Phase 1: Fix Role Service Tests

- [x] Task 1.1: Update role ID assertion tests
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 15-30)

- [x] Task 1.2: Update check_game_host_permission tests
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 32-48)

### [x] Phase 2: Fix Template Service Tests

- [x] Task 2.1: Update get_templates_for_user test calls
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 50-80)

### [x] Phase 3: Fix Game Service Tests

- [x] Task 3.1: Add role service mock infrastructure
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 82-100)

- [x] Task 3.2: Update game creation test calls
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 102-120)

### [x] Phase 4: Fix Guild Route Tests

- [x] Task 4.1: Investigate and fix guild route authorization tests
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 122-145)

### [x] Phase 5: Fix Remaining Tests

- [x] Task 5.1: Fix guild service test
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 147-160)

### [x] Phase 6: Verification

- [x] Task 6.1: Run full test suite and verify all pass
  - Details: .copilot-tracking/details/20251204-fix-authorization-test-failures-details.md (Lines 162-175)

## Dependencies

- pytest
- Python testing infrastructure
- Existing test fixtures and mocks

## Success Criteria

- All 21 previously failing tests now pass
- No new test failures introduced
- Test execution time remains acceptable
- Tests accurately reflect authorization behavior changes
