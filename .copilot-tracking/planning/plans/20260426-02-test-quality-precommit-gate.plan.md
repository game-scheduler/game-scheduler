---
applyTo: '.copilot-tracking/changes/20260426-02-test-quality-precommit-gate-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Test Quality Pre-commit Gate

## Overview

Add a `check-test-assertions` pre-commit hook that blocks test functions with zero
assertions from entering the codebase, then clean up all 90 existing violations.

## Objectives

- Prevent new "coverage theater" tests (no assertions) from being committed
- Catch tests that configure a named mock but never verify it with `assert_*`
- Deploy in diff-only mode first to avoid blocking existing violations
- Clean up all 90 existing zero-assertion test functions
- Switch to full enforcement mode once violations are resolved

## Research Summary

### Project Files

- `scripts/check_lint_suppressions.py` — model for custom pre-commit checker pattern
- `tests/unit/scripts/test_check_lint_suppressions.py` — model for testing scripts via `importlib.util`
- `.pre-commit-config.yaml` (line 238) — `check-lint-suppressions` is the insertion point; new hook goes after it
- `tests/unit/bot/events/` — highest concentration of zero-assertion violations

### External References

- #file:../research/20260422-02-test-quality-precommit-gate-research.md — full implementation spec, AST detection patterns, and violation inventory

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/unit-tests.instructions.md — unit test quality standards

## Implementation Checklist

### [x] Phase 1: TDD RED — Stub and failing tests

- [x] Task 1.1: Create `scripts/check_test_assertions.py` stub with `NotImplementedError` on all public functions
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 11–29)

- [x] Task 1.2: Write xfail unit tests in `tests/unit/scripts/test_check_test_assertions.py`
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 30–72)

### [x] Phase 2: TDD GREEN — Implement and wire up hook

- [x] Task 2.1: Implement all functions in `scripts/check_test_assertions.py` per research spec
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 75–103)

- [x] Task 2.2: Add `check-test-assertions` hook to `.pre-commit-config.yaml` with `--diff-only`
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 104–130)

- [x] Task 2.3: Remove xfail markers from tests and verify full suite passes
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 131–145)

### [x] Phase 3: Fix the 90 existing zero-assertion violations

- [x] Task 3.1: Enumerate all violations by staging test files and running the script
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 148–169)

- [ ] Task 3.2: Fix violations in `tests/unit/bot/events/` (largest concentration)
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 170–199)

- [ ] Task 3.3: Fix violations in remaining unit test files
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 200–217)

### [ ] Phase 4: Switch to full enforcement mode

- [ ] Task 4.1: Remove `--diff-only` from the hook entry in `.pre-commit-config.yaml`
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 220–242)

- [ ] Task 4.2: Verify `pre-commit run check-test-assertions` exits 0 on the full test suite
  - Details: .copilot-tracking/planning/details/20260426-02-test-quality-precommit-gate-details.md (Lines 243–260)

## Dependencies

- Python stdlib only (`ast`, `subprocess`, `sys`, `pathlib`) — no new packages
- `tests/unit/scripts/` directory (already exists)

## Success Criteria

- `pre-commit run check-test-assertions` exits 0 on main branch without `--diff-only` flag
- All newly committed test functions contain at least one assertion
- Named mocks captured via `with ... as mock_x:` are verified with `assert_*` calls
