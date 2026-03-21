---
applyTo: '.copilot-tracking/changes/20260321-01-status-schedule-bug-fix-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Status Schedule Not Updated for IN_PROGRESS and COMPLETED Games

## Overview

Fix the bug where editing an IN_PROGRESS or COMPLETED game silently destroys its pending status
schedule rows, and where changing `expected_duration_minutes` never triggers a schedule update.

## Objectives

- Ensure `status_schedule_needs_update` is set when `expected_duration_minutes` changes
- Ensure `_update_status_schedules()` preserves and updates schedules for IN_PROGRESS and COMPLETED games
- Add the missing `_ensure_archived_schedule_if_configured()` helper to the API game service
- Cover all three fix scenarios with new integration tests (TDD)

## Research Summary

### Project Files

- `services/api/services/games.py` - contains `_update_remaining_fields()` and `_update_status_schedules()`, the two methods requiring fixes
- `tests/integration/` - existing integration test directory where the new test file belongs
- `shared/models/game_status_schedule.py` - `GameStatusSchedule` model used by the helper method

### External References

- #file:../research/20260321-01-status-schedule-bug-fix-research.md - full bug analysis, fix code, and test specs

### Standards References

- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - service layer and DB session patterns
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology
- #file:../../.github/instructions/integration-tests.instructions.md - integration test conventions

## Implementation Checklist

### [ ] Phase 1: Write Failing Integration Tests (TDD Red Phase)

- [ ] Task 1.1: Create `tests/integration/test_status_schedule_updates.py` with five xfail tests
  - Details: .copilot-tracking/planning/details/20260321-01-status-schedule-bug-fix-details.md (Lines 11-43)

### [ ] Phase 2: Fix the Bug (TDD Green Phase)

- [ ] Task 2.1: Set `status_schedule_needs_update = True` when `expected_duration_minutes` changes in `_update_remaining_fields()`
  - Details: .copilot-tracking/planning/details/20260321-01-status-schedule-bug-fix-details.md (Lines 48-65)

- [ ] Task 2.2: Expand `_update_status_schedules()` with `elif` branches for IN_PROGRESS and COMPLETED
  - Details: .copilot-tracking/planning/details/20260321-01-status-schedule-bug-fix-details.md (Lines 66-86)

- [ ] Task 2.3: Add `_ensure_archived_schedule_if_configured()` helper method
  - Details: .copilot-tracking/planning/details/20260321-01-status-schedule-bug-fix-details.md (Lines 87-106)

### [ ] Phase 3: Verify and Promote (TDD Green → Passing)

- [ ] Task 3.1: Remove xfail markers and confirm all five integration tests pass
  - Details: .copilot-tracking/planning/details/20260321-01-status-schedule-bug-fix-details.md (Lines 107-120)

## Dependencies

- `services/api/services/games.py` (existing service file — no new modules needed)
- Existing integration test fixtures and DB setup
- No schema migrations required
- No frontend changes required

## Success Criteria

- Editing `expected_duration_minutes` on any non-terminal game state always updates the COMPLETED schedule
- Editing an IN_PROGRESS game preserves its COMPLETED schedule
- Editing a COMPLETED game preserves or creates its ARCHIVED schedule
- ARCHIVED/CANCELLED games still have all schedules cleaned up
- All five new integration tests pass with no regressions
