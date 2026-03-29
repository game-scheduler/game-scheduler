<!-- markdownlint-disable-file -->

# Task Details: GitHub Actions CI/CD Pipeline

## Research Reference

**Source Research**: #file:../research/20260329-01-github-actions-ci-cd-research.md

---

## Phase 1: Extend Scripts for CI Compatibility (TDD)

### Task 1.1: Write Failing Tests for `check_commit_duplicates.py --compare-branch`

Add a new test module `tests/unit/scripts/test_check_commit_duplicates.py` covering the new `--compare-branch` behaviour. Tests must be written first and must fail (xfail or ImportError) before Task 1.2 implements the feature.

- **Files**:
  - `tests/unit/scripts/test_check_commit_duplicates.py` — new test file (create `tests/unit/scripts/__init__.py` if needed)
- **Test Cases to Cover**:
  - `get_changed_line_ranges()` called with `compare_branch="origin/main"` invokes `git diff origin/main...HEAD --unified=0` (not `--cached`)
  - `get_changed_line_ranges()` called without `compare_branch` still invokes `git diff --cached --unified=0`
  - `main()` accepts `compare_branch` optional parameter and passes it through
  - Empty diff (no changed lines) returns empty dict successfully (exit 0)
- **Success**:
  - Tests exist and fail (or are `xfail`) before implementation
  - Tests pass after Task 1.2 implementation
- **Research References**:
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 27-32) — `get_changed_line_ranges()` hardcodes `--cached`; `main()` signature
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 268-302) — implementation guidance
- **Dependencies**:
  - None; this is the first task

### Task 1.2: Implement `--compare-branch` in `check_commit_duplicates.py`

Modify `scripts/check_commit_duplicates.py` to accept an optional `--compare-branch <ref>` CLI argument and an optional `compare_branch` parameter on `main()`.

- **Files**:
  - `scripts/check_commit_duplicates.py` — add argparse argument; update `get_changed_line_ranges()`; update `main()` signature
- **Behaviour**:
  - When `--compare-branch origin/main` is passed: execute `git diff origin/main...HEAD --unified=0`
  - When absent: execute `git diff --cached --unified=0` (unchanged pre-commit behaviour)
  - `main(report_file: str, compare_branch: str | None = None)` — backward-compatible signature
  - Empty diff must not raise; return `{}` and exit 0
- **Success**:
  - All tests from Task 1.1 pass
  - Pre-commit hook invocation (no `--compare-branch`) continues to work correctly
- **Research References**:
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 27-32) — current implementation details
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 95-105) — `--compare-branch` spec
- **Dependencies**:
  - Task 1.1 tests written and failing

### Task 1.3: Write Failing Tests for `check_lint_suppressions.py --compare-branch` and `--ci`

Add a new test module `tests/unit/scripts/test_check_lint_suppressions.py` covering the new arguments. Tests must fail before Task 1.4 implements the feature.

- **Files**:
  - `tests/unit/scripts/test_check_lint_suppressions.py` — new test file
- **Test Cases to Cover**:
  - `_get_added_lines()` with `compare_branch="origin/main"` invokes `git diff origin/main...HEAD --unified=0`
  - `_get_added_lines()` without `compare_branch` invokes `git diff --cached --unified=0`
  - `--ci` flag: when COUNTED patterns found, outputs `SUPPRESSION_COUNT=N` to stdout and exits 0
  - `--ci` flag absent: COUNTED patterns cause non-zero exit (existing pre-commit behaviour)
  - BLOCKED patterns always cause exit 1 regardless of `--ci`
  - Zero suppressions with `--ci`: outputs `SUPPRESSION_COUNT=0` and exits 0
- **Success**:
  - Tests exist and fail (or are `xfail`) before implementation
  - Tests pass after Task 1.4 implementation
- **Research References**:
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 33-42) — `_get_added_lines()` hardcode; BLOCKED/COUNTED pattern lists
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 103-125) — `--compare-branch` and `--ci` spec
- **Dependencies**:
  - Task 1.2 complete

### Task 1.4: Implement `--compare-branch` and `--ci` in `check_lint_suppressions.py`

Modify `scripts/check_lint_suppressions.py` to accept `--compare-branch <ref>` and `--ci` optional CLI arguments.

- **Files**:
  - `scripts/check_lint_suppressions.py` — add argparse; update `_get_added_lines()`; update exit logic
- **Behaviour**:
  - `--compare-branch`: switches diff source as in Task 1.2
  - `--ci`: when COUNTED patterns are found, print `SUPPRESSION_COUNT=N` to stdout and exit 0 (workflow captures with `$()`)
  - Without `--ci`: COUNTED patterns behave exactly as today (non-zero exit)
  - BLOCKED patterns always exit 1, `--ci` has no effect on BLOCKED
  - Output must go to stdout (not stderr) for `$(...)` shell capture
- **Success**:
  - All tests from Task 1.3 pass
  - Pre-commit hook invocation (no new args) continues unchanged
- **Research References**:
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 103-125) — full spec
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 130-153) — CI yaml usage example showing `$()` capture
- **Dependencies**:
  - Task 1.3 tests written and failing

---

## Phase 2: Rewrite GitHub Actions Workflow

### Task 2.1: Replace `.github/workflows/ci-cd.yml`

Overwrite the existing workflow file with the complete new workflow. All jobs below must be present.

- **Files**:
  - `.github/workflows/ci-cd.yml` — full replacement

#### Triggers

```yaml
on:
  push:
    branches: [main, develop]
    tags: ['v*.*.*']
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
```

#### Top-level env

```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

#### `code-quality` job (runs on every trigger)

- `runs-on: ubuntu-latest`
- Steps:
  1. `actions/checkout@v4`
  2. `astral-sh/setup-uv@v3`
  3. `uv python install 3.13`
  4. `actions/setup-node@v4` with `node-version: '24'`
  5. `uv sync --dev`
  6. `cd frontend && npm ci`
  7. Run `autocopyright` on `services/ shared/ scripts/ tests/` then `git diff --exit-code`
  8. `uv run python -m compileall -q services shared tests`
  9. `uv run ruff format --check .`
  10. `uv run ruff check .`
  11. `uv run mypy shared/ services/`
  12. `cd frontend && npm run format:check`
  13. `cd frontend && npm run lint`
  14. `cd frontend && npm run type-check`
  15. `uv run complexipy .`
  16. `uv run lizard -l typescript frontend/src/ --CCN 15 --warnings_only`
  17. Scan for BLOCKED suppression patterns in all non-test `.py/.ts/.tsx` files (use scripts/check_lint_suppressions.py without --ci for always-blocking check)
  18. `grep -rn 'trailing whitespace\|<<<.*HEAD' --include='*.py' --include='*.ts' --include='*.tsx'` or equivalent checks for trailing-whitespace/merge-conflict/detect-private-key

#### `unit-tests` job (runs on every trigger)

- `runs-on: ubuntu-latest`
- Steps:
  1. Checkout, setup-uv, `uv python install 3.13`, `uv sync --dev`
  2. `uv run pytest --timeout=30 -p no:randomly --cov --cov-report=xml -qq`
  3. `actions/upload-artifact@v4` — uploads `coverage.xml` named `python-coverage`

#### `diff-coverage` job (PR only, needs `unit-tests`)

```yaml
if: github.event_name == 'pull_request'
needs: unit-tests
```

- Steps:
  1. Checkout with `fetch-depth: 0`
  2. Setup uv, `uv sync --dev`
  3. `actions/download-artifact@v4` for `python-coverage`
  4. `uv run diff-cover coverage.xml --compare-branch=origin/main --fail-under=90 --ignore-whitespace`

#### `frontend-tests` job (runs on every trigger)

- `runs-on: ubuntu-latest`
- Steps:
  1. Checkout with `fetch-depth: 0` (need full history for PR diff-cover)
  2. `actions/setup-node@v4` with `node-version: '24'`
  3. `cd frontend && npm ci`
  4. `cd frontend && npm run test:coverage`
  5. `cd frontend && npm run build`
  6. PR only (`if: github.event_name == 'pull_request'`): setup-uv, `uv sync --dev`, then `uv run diff-cover frontend/coverage/lcov.info --compare-branch=origin/main --fail-under=90`

#### `integration-tests` job (runs on every trigger)

- Keep existing postgres (18-alpine), redis (valkey/valkey:9.0.1-alpine), rabbitmq service containers
- `uv run pytest tests/integration/ -m integration`

#### `check-suppressions` job (PR only)

```yaml
if: github.event_name == 'pull_request'
outputs:
  suppression_count: ${{ steps.scan.outputs.suppression_count }}
```

- Steps:
  1. Checkout with `fetch-depth: 0`
  2. Setup uv, `uv sync --dev`
  3. Step `id: scan`:
     ```bash
     count=$(uv run python scripts/check_lint_suppressions.py --compare-branch origin/main --ci)
     echo "suppression_count=$count" >> "$GITHUB_OUTPUT"
     ```

#### `suppression-gate` job (PR only, only when count > 0)

```yaml
needs: check-suppressions
if: github.event_name == 'pull_request' && needs.check-suppressions.outputs.suppression_count > 0
environment: lint-suppression-review
```

- Single step: `echo "Suppression gate passed by reviewer"`

#### `jscpd-check` job (PR only)

```yaml
if: github.event_name == 'pull_request'
```

- Steps:
  1. Checkout with `fetch-depth: 0`
  2. Setup node 24, `npm ci` in frontend (for jscpd availability via npx)
  3. `npx jscpd services shared frontend/src --config .jscpd.json --threshold 100 --reporters json --output .jscpd-report`
  4. Setup uv, `uv sync --dev`
  5. `uv run python scripts/check_commit_duplicates.py .jscpd-report/jscpd-report.json --compare-branch origin/main`

#### `docker-build` job (push to `main` only)

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
needs: [code-quality, unit-tests, frontend-tests]
strategy:
  matrix:
    service: [api, bot, scheduler, frontend, init, retry]
```

- Steps:
  1. Checkout
  2. `docker/setup-buildx-action@v3`
  3. `docker/build-push-action@v5` with `push: false`; context/dockerfile mapped per service

#### `build-and-publish` job (tag push only)

```yaml
if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
needs: [code-quality, unit-tests, frontend-tests, integration-tests]
strategy:
  matrix:
    service: [api, bot, scheduler, frontend, init, retry]
```

- Steps:
  1. Checkout
  2. `docker/login-action@v3` to `ghcr.io`
  3. `docker/metadata-action@v5` for semver tags
  4. `docker/setup-buildx-action@v3`
  5. `docker/build-push-action@v5` with `push: true`

- **Success**:
  - Workflow syntax valid (`actionlint` or manual review)
  - All 9 jobs present: `code-quality`, `unit-tests`, `diff-coverage`, `frontend-tests`, `integration-tests`, `check-suppressions`, `suppression-gate`, `jscpd-check`, `docker-build`, `build-and-publish`
  - `retry` included in both Docker matrix definitions
- **Research References**:
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 175-265) — full job definitions
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 130-153) — suppression-gate yaml example

### Task 2.2: Document `lint-suppression-review` Environment Prerequisite

The `suppression-gate` job requires a GitHub Environment named `lint-suppression-review` with designated reviewers. This must be created manually in the repository settings before the workflow can run.

- **Files**:
  - `.github/workflows/ci-cd.yml` — add a comment at the top of the file noting the prerequisite
  - `docs/developer/` — add a brief note in relevant developer docs (or create `docs/developer/ci-cd.md`) explaining the environment setup
- **Steps to Document**:
  1. Go to repository Settings → Environments → New environment
  2. Name: `lint-suppression-review`
  3. Add Required reviewers (team members who can approve suppression use)
  4. Save environment
- **Success**:
  - Comment or documentation clearly states the manual step required before the workflow functions
- **Research References**:
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 69-80) — GitHub Environments docs summary
  - #file:../research/20260329-01-github-actions-ci-cd-research.md (Lines 109-130) — environment gate design
- **Dependencies**:
  - Task 2.1 complete

---

## Dependencies

- Python 3.13
- Node.js 24 LTS
- `uv` (`astral-sh/setup-uv@v3`)
- All Python dev deps: `autocopyright`, `diff-cover`, `complexipy`, `lizard`, `ruff`, `mypy` (in `pyproject.toml` dev deps)
- `jscpd` via `npx`
- GitHub Environment `lint-suppression-review` created in repo settings

## Success Criteria

- All pre-commit hooks (non-manual, non-fixer) have a CI equivalent enforcing them
- Script tests pass for both new CLI features
- Workflow file passes syntax validation
- `retry` image included in both Docker jobs
- PR diff coverage enforced at 90% for both Python and TypeScript
