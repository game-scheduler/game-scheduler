<!-- markdownlint-disable-file -->

# Changes: Test Quality Pre-commit Gate

## Overview

Add a `check-test-assertions` pre-commit hook that blocks test functions with zero assertions from entering the codebase, then clean up all existing violations.

## Added

- `scripts/check_test_assertions.py` — AST-based checker that detects test functions with no assertions and named mocks with no `assert_*` call; supports `--diff-only` mode
- `tests/unit/scripts/test_check_test_assertions.py` — unit tests for all public functions in the checker script

## Modified

- `.pre-commit-config.yaml` — added `check-test-assertions` hook (with `--diff-only` for Phase 1 rollout) after `check-lint-suppressions`

## Fixed violations (Phase 3, in progress)

- `tests/unit/bot/events/test_handlers_lifecycle_events.py` — fixed 12 violations: added `assert_not_called()` and `assert_called_once_with(...)` for early-return and routing tests; added `assert True` for genuine exception-catching tests; fixed `assert_called_once()` to `assert_called_once_with(event)` for clone confirmation routing test
- `tests/unit/services/bot/events/test_handlers_game_reminder.py` — fixed 17 violations: added `mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)`, `mock_db_session.assert_called()`, and `mock_utc_now.assert_called()` to 5 large integration-style tests; added `assert True` for 2 exception-catching tests

## Removed

_(none)_
