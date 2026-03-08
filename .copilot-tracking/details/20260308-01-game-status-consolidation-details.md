<!-- markdownlint-disable-file -->

# Task Details: GameStatus Enum Consolidation

## Research Reference

**Source Research**: #file:../research/20260308-01-game-status-consolidation-research.md

## Phase 1: Add `display_name` to `status_transitions.py` (TDD)

### Task 1.1: Add `display_name` stub to `GameStatus` in `status_transitions.py`

Add a `display_name` property stub to `GameStatus` in `shared/utils/status_transitions.py` that raises `NotImplementedError`, establishing the interface before writing tests.

- **Files**:
  - `shared/utils/status_transitions.py` — add stub `display_name` property after the enum values (currently lines 27–33)
- **Success**:
  - `display_name` property exists on `GameStatus` but raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260308-01-game-status-consolidation-research.md (Lines 67–79) — `display_name` implementation specification
- **Dependencies**:
  - None

### Task 1.2: Write xfail tests for `display_name` (RED)

Write tests for all four `GameStatus` values' `display_name` property in the existing or new test file for `status_transitions.py`, marked with `@pytest.mark.xfail` so they can be committed while the stub raises `NotImplementedError`.

- **Files**:
  - `tests/unit/shared/utils/test_status_transitions.py` (create if absent) — add xfail tests for each status
- **Success**:
  - Tests run and are recorded as expected failures (xfail)
  - No unexpected test passes
- **Research References**:
  - #file:../research/20260308-01-game-status-consolidation-research.md (Lines 67–79) — expected display values
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Implement `display_name` and remove xfail markers (GREEN)

Replace the stub body with the real implementation and remove all `@pytest.mark.xfail` markers. Do **not** modify test assertions.

- **Files**:
  - `shared/utils/status_transitions.py` — replace stub with implementation
  - `tests/unit/shared/utils/test_status_transitions.py` — remove xfail markers only
- **Success**:
  - All `display_name` tests pass (no xfail, no skip)
  - `GameStatus.SCHEDULED.display_name == "Scheduled"` etc.
- **Research References**:
  - #file:../research/20260308-01-game-status-consolidation-research.md (Lines 67–79) — exact display strings
- **Dependencies**:
  - Task 1.2 complete

## Phase 2: Consolidate `game.py`

### Task 2.1: Replace local `GameStatus` in `game.py` with import from `status_transitions`

Delete the `class GameStatus(StrEnum)` block (including `display_name`) from `shared/models/game.py` and add `from shared.utils.status_transitions import GameStatus` to its imports. Remove the now-unused `from enum import StrEnum` if nothing else in the file uses it.

- **Files**:
  - `shared/models/game.py` — remove class definition (currently lines 43–64) and the `StrEnum` import (line 25); add import from utils
- **Success**:
  - `grep -r "class GameStatus" .` returns exactly one match (in `status_transitions.py`)
  - `python -c "from shared.models.game import GameStatus"` succeeds
  - All pre-existing tests still pass
- **Research References**:
  - #file:../research/20260308-01-game-status-consolidation-research.md (Lines 47–64) — affected files and migration approach
- **Dependencies**:
  - Phase 1 complete

## Phase 3: Update Consumer Import Paths

### Task 3.1: Replace `from shared.models.game import GameStatus` in all consumer files

Update the 7 consumer files to use the package-level `from shared.models import GameStatus`, keeping any `GameSession` imports from `shared.models.game` as-is.

- **Files** (all 7 require an import-line change):
  - `services/bot/formatters/game_message.py` (line 43)
  - `tests/integration/test_clone_game_endpoint.py` (line 40)
  - `tests/integration/test_games_route_guild_isolation.py` (line 39) — also imports `GameSession`, keep that import
  - `tests/e2e/test_game_status_transitions.py` (line 53)
  - `tests/services/scheduler/test_event_builders.py` (line 34)
  - `tests/services/bot/events/test_handlers.py` (line 36) — also imports `GameSession`, keep that import
  - `tests/unit/bot/handlers/test_participant_drop_handler.py` (line 39) — also imports `GameSession`, keep that import
- **Success**:
  - `grep -r "from shared.models.game import GameStatus" .` returns zero results
  - All tests pass
- **Research References**:
  - #file:../research/20260308-01-game-status-consolidation-research.md (Lines 30–45) — affected files table
- **Dependencies**:
  - Phase 2 complete

## Dependencies

- Python 3.12+
- pytest (existing)
- No new packages required

## Success Criteria

- `grep -r "class GameStatus" .` returns exactly one result (in `status_transitions.py`)
- `grep -r "from shared.models.game import GameStatus" .` returns zero results
- All existing tests pass after each phase
- `GameStatus.SCHEDULED.display_name == "Scheduled"` works when imported from `shared.models`
