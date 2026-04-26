<!-- markdownlint-disable-file -->

# Task Details: Test Quality Pre-commit Gate

## Research Reference

**Source Research**: #file:../research/20260422-02-test-quality-precommit-gate-research.md

## Phase 1: TDD RED — Stub and failing tests

### Task 1.1: Create `scripts/check_test_assertions.py` stub

Create a minimal Python script that defines all public function signatures but raises
`NotImplementedError` in each body. This lets the test file import and call the functions
while proving tests can detect missing implementation. Do NOT add the pre-commit hook in
this phase — committing with a broken hook entry would block the Phase 1 commit.

- **Files**:
  - `scripts/check_test_assertions.py` — new file; stub out `has_assertion`,
    `get_unasserted_named_mocks`, `get_modified_line_ranges`, `get_staged_test_files`,
    `check_file`, and `main` with `raise NotImplementedError` bodies
- **Success**:
  - File is importable via `importlib.util.spec_from_file_location`
  - Each function raises `NotImplementedError` when called
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 221–275) — full implementation spec with exact function signatures
- **Dependencies**:
  - None

### Task 1.2: Write xfail unit tests

Create `tests/unit/scripts/test_check_test_assertions.py` following the same module-import
pattern as `test_check_lint_suppressions.py` (use `importlib.util.spec_from_file_location`).
Mark all test functions `@pytest.mark.xfail(strict=True)`.

Test cases to cover:

**`has_assertion()` — parse small source snippets with `ast.parse` and `ast.walk`:**

- source with `assert x == 1` → returns `True`
- source with `mock_obj.assert_called_once_with(42)` → returns `True`
- source with `mock_obj.assert_awaited_once()` → returns `True`
- source with `pytest.raises(ValueError)` as call → returns `True`
- source with only `result = fn()` and no assertion → returns `False`

**`get_unasserted_named_mocks()` — parse `with` blocks:**

- `with patch(...) as mock_x:` with no `mock_x.assert_*` call → returns `["mock_x"]`
- `with patch(...) as mock_x:` followed by `mock_x.assert_called_once()` → returns `[]`
- function body with no `with ... as` context → returns `[]`

**`check_file()` — use `tmp_path` pytest fixture to write real test files:**

- full mode: function with no assertions → returns one `(lineno, message)` tuple
- full mode: function with assertion → returns empty list
- diff-only mode with mocked `get_modified_line_ranges` returning empty set: function skipped
- diff-only mode with mocked ranges including function line: violation reported

**`main()` — mock `subprocess.run` for `git diff` output, use `tmp_path` for test files:**

- staged clean test file (all assertions present) → exits 0
- staged test file with zero-assertion function → exits 1
- `--diff-only` in `sys.argv` with function outside diff range → exits 0

- **Files**:
  - `tests/unit/scripts/test_check_test_assertions.py` — new file
- **Success**:
  - `uv run pytest tests/unit/scripts/test_check_test_assertions.py -v` shows all `xfailed`
  - No test shows as ERROR or skipped
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 89–140) — AST assertion detection spec
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 141–165) — named-mock rule spec
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 165–195) — diff-only scoping spec
- **Dependencies**:
  - Task 1.1 complete (stub must be importable)

## Phase 2: TDD GREEN — Implement and wire up hook

### Task 2.1: Implement `scripts/check_test_assertions.py`

Replace each `NotImplementedError` stub body with the full implementation from the research
spec. Implement each function in the order listed (helpers first, `main` last):

- `get_staged_test_files()`: subprocess `git diff --cached --name-only --diff-filter=ACM`,
  filter to paths matching `tests/` prefix and `.py` suffix
- `get_modified_line_ranges(filepath)`: subprocess `git diff --cached -U0 <filepath>`,
  parse `@@` hunks to extract line ranges as a `set[int]`
- `has_assertion(func_node)`: walk AST for `ast.Assert`; call-verification attr names
  (`assert_called`, `assert_awaited`, `assert_any_call`, `assert_not_called`); and
  `pytest.raises` attribute call
- `get_unasserted_named_mocks(func_node)`: walk for `ast.With` items with `optional_vars`,
  collect alias names, then verify each has an `alias.assert_*` call somewhere in the function
- `check_file(filepath, diff_only)`: parse file AST, iterate `test_*` functions, apply diff
  scoping when `diff_only=True`, check both violation types
- `main()`: parse `--diff-only` from `sys.argv`, collect staged files, print violations,
  return 1 if any found else 0

- **Files**:
  - `scripts/check_test_assertions.py` — replace stub with full implementation
- **Success**:
  - `uv run python scripts/check_test_assertions.py` exits without traceback
  - All xfail tests now pass (markers still present; they should show as `xpassed` briefly)
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 221–275) — complete implementation code block
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Add hook to `.pre-commit-config.yaml`

Insert the `check-test-assertions` hook immediately after the closing line of the
`check-lint-suppressions` block (after the `pass_filenames: false` line at ~line 251 in
`.pre-commit-config.yaml`). Use `--diff-only` for Phase 1 rollout.

Hook definition to insert:

```yaml
# Block test functions with zero assertions in staged test files (diff-only for Phase 1 rollout)
- id: check-test-assertions
  name: Check test functions have assertions
  entry: python scripts/check_test_assertions.py --diff-only
  language: python
  pass_filenames: false
  files: ^tests/.*\.py$
```

- **Files**:
  - `.pre-commit-config.yaml` — insert hook after `check-lint-suppressions` block
- **Success**:
  - Hook appears in `pre-commit run --list-hooks` output
  - `pre-commit run check-test-assertions` on a clean working tree exits 0
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 276–290) — hook YAML definition
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Remove xfail markers and verify

Remove `@pytest.mark.xfail(strict=True)` from every test function in
`tests/unit/scripts/test_check_test_assertions.py`. Run the full unit suite to confirm.

- **Files**:
  - `tests/unit/scripts/test_check_test_assertions.py` — remove all xfail decorators
- **Success**:
  - `uv run pytest tests/unit/scripts/test_check_test_assertions.py -v` shows all `PASSED`
  - Full unit test suite passes
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 291–310) — implementation correctness notes
- **Dependencies**:
  - Task 2.2 complete

## Phase 3: Fix the 90 existing zero-assertion violations

### Task 3.1: Enumerate all violations

Stage all unit test files and run the script in full mode (without `--diff-only`) to produce
a complete violation list. Restore staging afterward. Use this list to guide Tasks 3.2 and 3.3.

```bash
git add tests/unit/
uv run python scripts/check_test_assertions.py 2>&1 | tee /tmp/violations.txt
wc -l /tmp/violations.txt
git restore --staged tests/unit/
```

- **Files**:
  - None (diagnostic step only)
- **Success**:
  - `/tmp/violations.txt` lists all violations as `file:line: function_name: reason`
  - Count matches approximately 90 (per research baseline of April 22, 2026)
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 67–88) — known concentration in `tests/unit/bot/events/`
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Fix violations in `tests/unit/bot/events/`

The research identifies `tests/unit/bot/events/` as the largest concentration. Work through
each zero-assertion function, applying the appropriate fix pattern:

**Pattern A — named mock, no call verification**: Add `mock_x.assert_called_once_with(...)`
(or `assert_called_once()` / `assert_not_called()`) after the call under test. The typical
shape is: setup `mock_deps.service.method.return_value = ...`, call the handler, then assert
the mock was (or was not) called with expected arguments.

**Pattern B — "no exception raised" test**: If the test genuinely only verifies that code
runs without raising, add `assert True  # verifies no exception raised` per the research
escape hatch. Reserve this for cases where there is no meaningful return value or mock call
to verify.

**Pattern C — return value ignored**: Add `assert result == expected` or `assert result is None`.

- **Files**:
  - `tests/unit/bot/events/test_handlers_game_events.py` — add assertions per violation list
  - `tests/unit/bot/events/test_handlers_lifecycle_events.py` — add assertions
  - Any other `tests/unit/bot/events/` files in the violation list
- **Success**:
  - `uv run pytest tests/unit/bot/events/ -v` passes with no failures
  - Staging only `tests/unit/bot/events/` files and running the script shows zero violations
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 67–88) — example zero-assertion pattern and fix approach
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 213–220) — escape hatch guidance
- **Dependencies**:
  - Task 3.1 complete (violation list available)

### Task 3.3: Fix violations in remaining unit test files

Work through the remaining violations from `/tmp/violations.txt`, file by file, applying the
same fix patterns as Task 3.2. After fixing each file run `uv run pytest <file> -v` to
confirm tests still pass before moving to the next.

- **Files**:
  - All remaining test files listed in `/tmp/violations.txt` outside `tests/unit/bot/events/`
- **Success**:
  - Full unit test suite passes
  - Staging all unit test files and running `uv run python scripts/check_test_assertions.py`
    shows zero violations
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 67–88) — violation inventory summary
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 213–220) — escape hatch
- **Dependencies**:
  - Task 3.2 complete

## Phase 4: Switch to full enforcement mode

### Task 4.1: Remove `--diff-only` from hook

Edit `.pre-commit-config.yaml` to change the `check-test-assertions` entry line from:

```yaml
entry: python scripts/check_test_assertions.py --diff-only
```

to:

```yaml
entry: python scripts/check_test_assertions.py
```

- **Files**:
  - `.pre-commit-config.yaml` — remove `--diff-only` from the hook entry line
- **Success**:
  - Hook entry no longer contains `--diff-only`
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 196–212) — Phase 2 full mode specification
- **Dependencies**:
  - Phase 3 complete (all violations fixed)

### Task 4.2: Verify full enforcement passes

Stage all unit test files and run the hook to confirm zero violations under full mode.

```bash
git add tests/unit/
pre-commit run check-test-assertions
git restore --staged tests/unit/
```

- **Files**:
  - None (verification step)
- **Success**:
  - `pre-commit run check-test-assertions` exits 0
  - No violation output is printed
- **Research References**:
  - #file:../research/20260422-02-test-quality-precommit-gate-research.md (Lines 291–340) — success criteria
- **Dependencies**:
  - Task 4.1 complete

## Dependencies

- Python stdlib (`ast`, `subprocess`, `sys`, `pathlib`) — no new packages needed

## Success Criteria

- `pre-commit run check-test-assertions` exits 0 on main branch without `--diff-only` flag
- All newly committed test functions have at least one assertion
- Named mocks captured via `with ... as mock_x:` are verified with `assert_*` calls
