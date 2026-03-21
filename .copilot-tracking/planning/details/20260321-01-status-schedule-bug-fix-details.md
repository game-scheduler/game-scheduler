<!-- markdownlint-disable-file -->

# Task Details: Status Schedule Not Updated for IN_PROGRESS and COMPLETED Games

## Research Reference

**Source Research**: #file:../research/20260321-01-status-schedule-bug-fix-research.md

## Phase 1: Write Failing Integration Tests (TDD Red Phase)

### Task 1.1: Create integration test file with five failing tests

Create `tests/integration/test_status_schedule_updates.py` with five tests covering the bug scenarios.
All tests should be marked with `@pytest.mark.xfail(strict=True, reason="Expected to fail before fix")`.

The five tests:

1. `test_expected_duration_change_updates_completed_schedule_for_scheduled_game` — Create a SCHEDULED
   game, update `expected_duration_minutes` via the API, and verify the COMPLETED `GameStatusSchedule`
   row has an updated `transition_time` matching the new duration.

2. `test_expected_duration_change_updates_completed_schedule_for_in_progress_game` — Create a game,
   transition it to IN_PROGRESS in the DB, update `expected_duration_minutes` via the API, and verify
   the COMPLETED schedule row is updated (not deleted).

3. `test_api_update_in_progress_game_preserves_completed_schedule` — Update a non-duration field
   (e.g. `description`) on an IN_PROGRESS game and verify the COMPLETED schedule row still exists.

4. `test_api_update_completed_game_preserves_archived_schedule` — Set a game to COMPLETED with
   `archive_delay_seconds`, manually insert an ARCHIVED schedule row, update the game via API, and
   verify the ARCHIVED schedule was not deleted.

5. `test_api_update_completed_game_creates_archived_schedule` — Set a game to COMPLETED with
   `archive_delay_seconds` but no ARCHIVED schedule row, update the game via API, and verify an
   ARCHIVED schedule row is created.

- **Files**:
  - `tests/integration/test_status_schedule_updates.py` - new integration test file
- **Success**:
  - All five tests are collected by pytest and xfail (confirming they fail before the fix)
- **Research References**:
  - #file:../research/20260321-01-status-schedule-bug-fix-research.md (Lines 157-165) - integration test specs
- **Dependencies**:
  - Existing integration test infrastructure and fixtures

## Phase 2: Fix the Bug (TDD Green Phase)

### Task 2.1: Set status_schedule_needs_update on expected_duration_minutes change

In `services/api/services/games.py`, in `_update_remaining_fields()` (~line 1117), add
`status_schedule_needs_update = True` in the block that assigns `game.expected_duration_minutes`.

The existing code only triggers the flag on `status` field changes. Changing duration also affects the
COMPLETED transition time, so the flag must also be raised here.

- **Files**:
  - `services/api/services/games.py` — `_update_remaining_fields()` method (~line 1117)
- **Success**:
  - `status_schedule_needs_update = True` is set when `expected_duration_minutes` is assigned
- **Research References**:
  - #file:../research/20260321-01-status-schedule-bug-fix-research.md (Lines 70-76) - duration trigger fix
  - #file:../research/20260321-01-status-schedule-bug-fix-research.md (Lines 37-65) - bug explanation
- **Dependencies**:
  - Task 1.1 completion (xfailing tests must exist before making fixes)

### Task 2.2: Expand \_update_status_schedules() for IN_PROGRESS and COMPLETED states

In `services/api/services/games.py`, in `_update_status_schedules()` (~line 1403), replace the bare
`else:` branch with three new branches:

- `elif game.status == GameStatus.IN_PROGRESS.value:` — call `_ensure_completed_schedule()` and
  delete any stale IN_PROGRESS schedule row
- `elif game.status == GameStatus.COMPLETED.value:` — call `_ensure_archived_schedule_if_configured()`
  and delete any stale COMPLETED schedule row
- Final `else:` (ARCHIVED, CANCELLED) — keep the existing delete-all logic

- **Files**:
  - `services/api/services/games.py` — `_update_status_schedules()` method (~line 1403)
- **Success**:
  - The method has `elif` branches for IN_PROGRESS and COMPLETED states
  - The final `else` branch handles ARCHIVED and CANCELLED cleanup
- **Research References**:
  - #file:../research/20260321-01-status-schedule-bug-fix-research.md (Lines 78-103) - expanded method code
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Add \_ensure_archived_schedule_if_configured() helper method

Add a new private method `_ensure_archived_schedule_if_configured()` to the game service class in
`services/api/services/games.py`. Place it near `_ensure_completed_schedule()` for co-location.

The method returns early if `game.archive_delay_seconds` is None, then upserts a `GameStatusSchedule`
row targeting ARCHIVED status — updating `transition_time` if a row already exists, or inserting new.

- **Files**:
  - `services/api/services/games.py` — new `_ensure_archived_schedule_if_configured()` method
- **Success**:
  - Method exists and follows the same upsert pattern as `_ensure_completed_schedule()`
  - Returns early if `archive_delay_seconds` is None
- **Research References**:
  - #file:../research/20260321-01-status-schedule-bug-fix-research.md (Lines 105-131) - helper implementation
- **Dependencies**:
  - Task 2.2 completion (the method is called from the new elif branch)

## Phase 3: Verify and Promote (TDD Green → Passing)

### Task 3.1: Remove xfail markers and confirm all tests pass

Remove all `@pytest.mark.xfail` markers from `tests/integration/test_status_schedule_updates.py`
and run the integration test suite to confirm the five new tests pass.

- **Files**:
  - `tests/integration/test_status_schedule_updates.py` — remove xfail markers
- **Success**:
  - All five new integration tests pass without xfail markers
  - No regressions in existing integration tests
- **Research References**:
  - #file:../research/20260321-01-status-schedule-bug-fix-research.md (Lines 157-165) - test specs
- **Dependencies**:
  - Tasks 2.1, 2.2, and 2.3 complete

## Dependencies

- No schema migration required
- No frontend changes required
- Existing integration test infrastructure (fixtures, DB setup)

## Success Criteria

- Editing `expected_duration_minutes` on any game state always updates the COMPLETED schedule
- Editing an IN_PROGRESS game does not destroy its COMPLETED schedule
- Editing a COMPLETED game does not destroy its ARCHIVED schedule
- ARCHIVED/CANCELLED games still have all schedules cleaned up
- All five new integration tests pass
