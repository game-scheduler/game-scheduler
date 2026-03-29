# Changes: GitHub Actions CI/CD Pipeline

Tracks changes made while implementing `.copilot-tracking/planning/plans/20260329-01-github-actions-ci-cd.plan.md`.

---

## Added

- `tests/unit/scripts/test_check_commit_duplicates.py` — new unit tests covering `get_changed_line_ranges()` diff-source selection and `main()` `compare_branch` passthrough (Task 1.1)
- `tests/unit/scripts/test_check_lint_suppressions.py` — added Task 1.3 tests: `_get_added_lines(compare_branch=...)` diff-source selection, `--ci` flag exit/output behaviour for COUNTED and BLOCKED patterns, `--compare-branch` forwarding through `main()` (Tasks 1.3)

## Modified

- `pyproject.toml` — added `pathspec>=0.12.0` to `[dependency-groups] dev` (required by `check_commit_duplicates.py` script used in pre-commit)
- `scripts/check_commit_duplicates.py` — added optional `compare_branch` parameter to `get_changed_line_ranges()` and `main()`; added `--compare-branch` argparse argument to `__main__` entry point (Task 1.2)
- `scripts/check_lint_suppressions.py` — added `argparse` with `--compare-branch` and `--ci` arguments; updated `_get_added_lines()` to accept optional `compare_branch` parameter; updated `main()` to: pass `compare_branch` to `_get_added_lines()`, output `SUPPRESSION_COUNT=N` to stdout and exit 0 when `--ci` and COUNTED patterns found, always exit 1 for BLOCKED patterns regardless of `--ci` (Task 1.4)
- `tests/unit/scripts/test_check_lint_suppressions.py` — added `sys` import and `sys.argv` mock to `_run_main()` helper to isolate argparse from pytest's own arguments (required after Task 1.4 added argparse)
