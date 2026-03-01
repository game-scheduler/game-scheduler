---
applyTo: '.copilot-tracking/changes/20260301-02-lint-suppression-scanner-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Lint Suppression Scanner Pre-commit Hook

## Overview

Add a pre-commit hook (`scripts/check_lint_suppressions.py`) that blocks bare/blanket lint suppressions unconditionally and enforces `APPROVED_OVERRIDES` approval for specific suppressions, then register it in `.pre-commit-config.yaml` and document the pathway in `.github/instructions/quality-check-overrides.instructions.md`.

## Objectives

- Detect and block all 13 suppression patterns (Python and TypeScript) in staged diffs via a single pre-commit hook
- Permanently block bare/blanket suppressions with no override path
- Gate specific/count-based suppressions behind `APPROVED_OVERRIDES=N` environment variable
- Document the new `APPROVED_OVERRIDES` pathway in the quality-check-overrides instructions

## Research Summary

### Project Files

- `scripts/check_commit_duplicates.py` - Reference implementation for diff-scanning hooks (`language: python`, `pass_filenames: false`, stdlib only)
- `scripts/check-copyright-precommit.sh` - Pattern for `set -e`, `git diff --cached` style pre-commit scripts
- `scripts/wrappers/git` - Established approval wrapper pattern; error messages never expose env var names
- `.pre-commit-config.yaml` - Hook ordering; new hook goes after `jscpd-diff`
- `pyproject.toml` - `[tool.ruff.lint.per-file-ignores]` shows existing legitimate suppressions
- `.github/instructions/quality-check-overrides.instructions.md` - Existing suppression policy; needs `APPROVED_OVERRIDES` section added

### External References

- #file:../research/20260301-02-lint-suppression-scanner-research.md - Complete research with suppression pattern matrix, error message design, scanning logic, and implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment style
- #file:../../.github/instructions/quality-check-overrides.instructions.md - Policy being enforced

## Implementation Checklist

### [ ] Phase 1: Script with TDD

- [ ] Task 1.1: Create stub `scripts/check_lint_suppressions.py`
  - Details: .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md (Lines 14-42)

- [ ] Task 1.2: Write failing tests (RED phase)
  - Details: .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md (Lines 44-90)

- [ ] Task 1.3: Implement scanning logic, remove xfail markers (GREEN phase)
  - Details: .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md (Lines 92-137)

- [ ] Task 1.4: Refactor and add comprehensive edge case tests (REFACTOR phase)
  - Details: .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md (Lines 139-170)

### [ ] Phase 2: Hook Integration and Documentation

- [ ] Task 2.1: Register hook in `.pre-commit-config.yaml`
  - Details: .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md (Lines 172-196)

- [ ] Task 2.2: Update `.github/instructions/quality-check-overrides.instructions.md`
  - Details: .copilot-tracking/details/20260301-02-lint-suppression-scanner-details.md (Lines 198-236)

## Dependencies

- Python stdlib only: `re`, `subprocess`, `sys`, `os`
- `pre-commit` (already installed)
- `pytest` (already used by project)

## Success Criteria

- `pre-commit run check-lint-suppressions` passes on a clean diff
- Bare `# noqa` in a staged Python file causes hook to fail with message referencing instructions file
- `# noqa: ERA001` in a staged file fails when `APPROVED_OVERRIDES` is unset or `0`
- `APPROVED_OVERRIDES=1` with exactly one `# noqa: ERA001` addition passes
- `APPROVED_OVERRIDES=1` with one bare `# noqa` still fails (bare is never permitted regardless of count)
- All TypeScript patterns (`@ts-ignore`, `eslint-disable`, etc.) are caught in the same hook run
- `#lizard forgive global` and `#lizard forgives(metric)` are detected correctly
- All unit tests pass with `uv run pytest tests/unit/scripts/test_check_lint_suppressions.py`
