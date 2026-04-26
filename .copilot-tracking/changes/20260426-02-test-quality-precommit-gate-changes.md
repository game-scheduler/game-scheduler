<!-- markdownlint-disable-file -->

# Changes: Test Quality Pre-commit Gate

## Overview

Add a `check-test-assertions` pre-commit hook that blocks test functions with zero assertions from entering the codebase, then clean up all existing violations.

## Added

- `scripts/check_test_assertions.py` — AST-based checker that detects test functions with no assertions and named mocks with no `assert_*` call; supports `--diff-only` mode
- `tests/unit/scripts/test_check_test_assertions.py` — unit tests for all public functions in the checker script

## Modified

- `.pre-commit-config.yaml` — added `check-test-assertions` hook (with `--diff-only` for Phase 1 rollout) after `check-lint-suppressions`

## Removed

_(none)_
