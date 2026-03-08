---
applyTo: '.copilot-tracking/changes/20260308-01-game-status-consolidation-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: GameStatus Enum Consolidation

## Overview

Eliminate the duplicate `GameStatus` enum by making `shared/utils/status_transitions.py` the single canonical definition and migrating all consumers to import via `shared.models`.

## Objectives

- Remove the redundant `class GameStatus(StrEnum)` from `shared/models/game.py`
- Move the `display_name` property into `shared/utils/status_transitions.py`
- Update all 7 consumer import sites to `from shared.models import GameStatus`
- Leave all other code and tests functionally unchanged

## Research Summary

### Project Files

- `shared/utils/status_transitions.py` — canonical home for `GameStatus`; currently has duplicate definition without `display_name`
- `shared/models/game.py` — defines duplicate `GameStatus` with `display_name`; will import from utils after consolidation
- `shared/models/__init__.py` — already re-exports `GameStatus`; no change needed
- `services/bot/formatters/game_message.py` — consumer requiring import update
- `tests/integration/test_clone_game_endpoint.py` — consumer requiring import update
- `tests/integration/test_games_route_guild_isolation.py` — consumer requiring import update
- `tests/e2e/test_game_status_transitions.py` — consumer requiring import update
- `tests/services/scheduler/test_event_builders.py` — consumer requiring import update
- `tests/services/bot/events/test_handlers.py` — consumer requiring import update
- `tests/unit/bot/handlers/test_participant_drop_handler.py` — consumer requiring import update

### External References

- #file:../research/20260308-01-game-status-consolidation-research.md — full analysis with canonical location rationale, affected files, and implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style

## Implementation Checklist

### [ ] Phase 1: Add `display_name` to `status_transitions.py` (TDD)

- [ ] Task 1.1: Add `display_name` stub to `GameStatus` in `status_transitions.py`
  - Details: .copilot-tracking/details/20260308-01-game-status-consolidation-details.md (Lines 11-23)

- [ ] Task 1.2: Write xfail tests for `display_name` (RED)
  - Details: .copilot-tracking/details/20260308-01-game-status-consolidation-details.md (Lines 24-37)

- [ ] Task 1.3: Implement `display_name` and remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260308-01-game-status-consolidation-details.md (Lines 38-52)

### [ ] Phase 2: Consolidate `game.py`

- [ ] Task 2.1: Replace local `GameStatus` in `game.py` with import from `status_transitions`
  - Details: .copilot-tracking/details/20260308-01-game-status-consolidation-details.md (Lines 55-69)

### [ ] Phase 3: Update Consumer Import Paths

- [ ] Task 3.1: Replace `from shared.models.game import GameStatus` in all 7 consumer files
  - Details: .copilot-tracking/details/20260308-01-game-status-consolidation-details.md (Lines 72-90)

## Dependencies

- Python 3.12+
- pytest (existing)
- No new packages required

## Success Criteria

- `grep -r "class GameStatus" .` returns exactly one result (in `status_transitions.py`)
- `grep -r "from shared.models.game import GameStatus" .` returns zero results
- All existing tests pass after each phase
- `GameStatus.SCHEDULED.display_name == "Scheduled"` works when imported from `shared.models`
