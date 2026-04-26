# Changes: Test Quality Pre-commit Gate

## Summary

Add a `check-test-assertions` pre-commit hook that detects test functions with zero
assertions, then clean up all existing violations.

## Added

- `scripts/check_test_assertions.py` — AST-based checker that detects test functions with no assertions or unverified named mocks; supports `--diff-only` and `--all` flags, and `# assert-no-args` escape hatch
- `tests/unit/scripts/test_check_test_assertions.py` — unit tests for all checker functions covering detection, escape hatch, and CLI behavior

## Modified

- `.pre-commit-config.yaml` — added `check-test-assertions` hook after `check-lint-suppressions` block with `--diff-only` for Phase 2 rollout

## Phase 3 Progress

### Task 3.1: Violation enumeration (complete)

Ran `uv run python scripts/check_test_assertions.py --all`; found 645 violation lines across ~30 files.
Highest-violation file: `tests/unit/services/bot/formatters/test_game_message.py` with 50 violations.

### Task 3.2 partial: test_game_message.py (50 violations fixed)

- `tests/unit/services/bot/formatters/test_game_message.py` — added `ANY` import; added
  `mock_embed_class.assert_called_once_with(...)`, `mock_view_class.from_game_data.assert_called_once_with(...)`,
  `mock_color.<method>.assert_called_once_with()  # assert-no-args`, `mock_config.assert_called_once_with()  # assert-no-args`,
  `mock_formatter_class.assert_called_once_with()  # assert-no-args`, `mock_get_config.assert_called_once_with()  # assert-no-args`,
  and strengthened two `set_footer.assert_called_once()` to `assert_called_once_with(text="Status: Scheduled")`.
  All 50 violations resolved; 2220 unit tests pass.
