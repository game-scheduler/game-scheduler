<!-- markdownlint-disable-file -->

# Task Details: Lint Suppression Scanner Pre-commit Hook

## Research Reference

**Source Research**: #file:../research/20260301-02-lint-suppression-scanner-research.md

---

## Phase 1: Script with TDD

### Task 1.1: Create stub `scripts/check_lint_suppressions.py`

Create a minimal stub that defines the two-category pattern structure but raises `NotImplementedError` for the main logic. Use compiled `re.Pattern` lists as module-level constants so tests can import and inspect them.

- **Files**:
  - `scripts/check_lint_suppressions.py` - New script; stub entry point raises `NotImplementedError`
- **Success**:
  - File is importable without error
  - `BLOCKED_PATTERNS` and `COUNTED_PATTERNS` lists exist as module-level constants with correct number of entries (see pattern matrix)
  - Running the script as `__main__` raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 46-63) - Full suppression pattern matrix with two-category split
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 116-129) - Recommended approach: two compiled `list[re.Pattern]` constants, stdlib only
- **Dependencies**:
  - None

### Task 1.2: Write failing tests — RED phase

Create `tests/unit/scripts/test_check_lint_suppressions.py` with real assertions covering all suppression patterns and edge cases. Mark each test `@pytest.mark.xfail(strict=True)` until the implementation exists.

- **Files**:
  - `tests/unit/scripts/test_check_lint_suppressions.py` - New test module
  - `tests/unit/scripts/__init__.py` - Create if not present
- **Success**:
  - All tests are collected by pytest and reported as `xfail` (not `xpass`, not errors)
  - Test cases cover:
    - Each pattern in `BLOCKED_PATTERNS` triggers immediate failure output and non-zero exit
    - Each pattern in `COUNTED_PATTERNS` triggers failure when `APPROVED_OVERRIDES` is `0`
    - `APPROVED_OVERRIDES=1` allows exactly one counted suppression
    - `APPROVED_OVERRIDES=1` does NOT allow a bare suppression
    - Clean diff produces exit code `0`
    - Mixed bare + counted: bare causes failure, counted does not affect bare block
    - Diff `+++` header lines are NOT counted as suppressions
    - Lines with `-` prefix (removals) are NOT counted
- **Research References**:
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 84-93) - Scanning logic: `+`-prefix only, excluding `+++`, two-phase evaluation
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 131-139) - Success criteria list to drive test cases
- **Dependencies**:
  - Task 1.1 completion (patterns importable)

### Task 1.3: Implement scanning logic, remove xfail markers — GREEN phase

Implement `main()` in `scripts/check_lint_suppressions.py` using the research-specified algorithm. Remove `@pytest.mark.xfail` decorators from all tests without modifying assertions. Do not add new tests in this task.

- **Files**:
  - `scripts/check_lint_suppressions.py` - Full implementation replacing the `NotImplementedError` stub
- **Success**:
  - All previously-xfail tests now pass (reported as `PASSED`, not `xpass`)
  - No test assertions modified — only xfail decorators removed
  - Implementation uses only `re`, `subprocess`, `sys`, `os` (stdlib)
  - Algorithm:
    1. `subprocess.run(["git", "diff", "--cached", "--unified=0"], capture_output=True, text=True)`
    2. Track current filename from `+++ b/` lines
    3. Collect `+`-prefixed lines (skip `+++` headers)
    4. Phase 1: match `BLOCKED_PATTERNS` → collect violations → print each with file:line, exit nonzero
    5. Phase 2: count `COUNTED_PATTERNS` matches → compare to `int(os.environ.get("APPROVED_OVERRIDES", 0))` → print count message, exit nonzero if exceeded
    6. Exit 0
  - Error messages match the exact templates in research (Lines 67-82)
- **Research References**:
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 65-82) - Error message templates (copy verbatim)
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 84-93) - Scanning logic detail
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 116-129) - Reference to `check_commit_duplicates.py` pattern
- **Dependencies**:
  - Task 1.2 completion (all xfail tests written)

### Task 1.4: Refactor and add comprehensive edge case tests — REFACTOR phase

Clean up the implementation for readability and add edge case tests that exercise boundary conditions not covered in Task 1.2.

- **Files**:
  - `scripts/check_lint_suppressions.py` - Refactored for clarity (no logic changes)
  - `tests/unit/scripts/test_check_lint_suppressions.py` - Additional edge case tests (no xfail)
- **Success**:
  - All existing tests still pass
  - New tests cover:
    - `APPROVED_OVERRIDES=2` with two counted suppressions passes
    - `APPROVED_OVERRIDES=2` with three counted suppressions fails
    - `#lizard forgive global` is in `BLOCKED_PATTERNS` (not counted)
    - `#lizard forgives` (bare) is in `COUNTED_PATTERNS`
    - `#lizard forgives(length)` (selective) is in `COUNTED_PATTERNS`
    - `// @ts-expect-error` is in `COUNTED_PATTERNS`
    - `/* eslint-disable */` is in `BLOCKED_PATTERNS`
    - `// eslint-disable-next-line specific-rule` is in `COUNTED_PATTERNS`
    - A line matching both categories counts only under `BLOCKED_PATTERNS` (blocked first)
  - `uv run pytest tests/unit/scripts/test_check_lint_suppressions.py -v` exits 0
- **Research References**:
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 46-63) - Full pattern matrix to verify all patterns categorized correctly
- **Dependencies**:
  - Task 1.3 completion (all tests green)

---

## Phase 2: Hook Integration and Documentation

### Task 2.1: Register hook in `.pre-commit-config.yaml`

Add a new `local` hook entry for `check-lint-suppressions` after the `jscpd-diff` hook. Mirror the structure of the existing `check-commit-duplicates` hook.

- **Files**:
  - `.pre-commit-config.yaml` - Add hook entry after `jscpd-diff`
- **Success**:
  - `pre-commit run check-lint-suppressions` executes without configuration errors
  - Hook config uses `language: python`, `pass_filenames: false`, no `additional_dependencies`
  - Hook `entry` field is `python scripts/check_lint_suppressions.py`
  - Hook fires on `commit` stage
  - `pre-commit run --all-files check-lint-suppressions` passes on the current clean working tree
- **Research References**:
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 95-100) - Hook placement: after `jscpd-diff`
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 116-129) - `language: python`, `pass_filenames: false`, no `additional_dependencies`
- **Dependencies**:
  - Task 1.3 completion (script must be functional before hook registration)

### Task 2.2: Update `.github/instructions/quality-check-overrides.instructions.md`

Add the missing suppression patterns to the Linter Suppression Comments list and add a new section documenting the `APPROVED_OVERRIDES` approval pathway.

- **Files**:
  - `.github/instructions/quality-check-overrides.instructions.md` - Two targeted updates
- **Success**:
  - Linter Suppression Comments list now includes:
    - `# noqa: complexipy` — suppresses complexipy cognitive complexity check
    - `#lizard forgives` — suppresses all lizard warnings for a function
    - `#lizard forgives(metric)` — suppresses a specific lizard metric for a function
    - `#lizard forgive global` — suppresses all lizard warnings for global code
  - New section added (after the `APPROVED_SKIP` / `SKIP` wrapper documentation or in `Prohibited Actions`) titled **`APPROVED_OVERRIDES` Environment Variable** that explains:
    - What it controls (number of specific/count-based suppressions permitted in a single commit)
    - That it does NOT apply to bare/blanket suppressions (those are always blocked)
    - That it resets per commit (no banking)
    - Example: `APPROVED_OVERRIDES=2 git commit -m "..."` to permit two specific suppressions
  - Document passes `markdownlint` (use existing document style for headers and lists)
- **Research References**:
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 30-39) - lizard and complexipy pattern details from external research
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 110-114) - Explicit list of updates needed
  - #file:../research/20260301-02-lint-suppression-scanner-research.md (Lines 40-43) - `APPROVED_OVERRIDES` / `APPROVED_SKIP` parallel pattern
- **Dependencies**:
  - Phase 1 completion (implementation defines what the pathway does)

---

## Dependencies

- Python stdlib: `re`, `subprocess`, `sys`, `os`
- `pytest` with `pytest.mark.xfail`
- `pre-commit` (already configured)

## Success Criteria

- All unit tests in `tests/unit/scripts/test_check_lint_suppressions.py` pass
- `pre-commit run check-lint-suppressions` exits 0 on a clean working tree
- Bare `# noqa` in a staged change causes hook failure with message referencing instructions file
- `APPROVED_OVERRIDES=1` permits exactly one counted suppression per commit
- `.github/instructions/quality-check-overrides.instructions.md` documents all 13+ patterns and the `APPROVED_OVERRIDES` pathway
