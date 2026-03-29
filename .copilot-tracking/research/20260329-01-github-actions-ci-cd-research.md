<!-- markdownlint-disable-file -->

# Task Research Notes: GitHub Actions CI/CD Pipeline

## Research Executed

### File Analysis

- [.pre-commit-config.yaml](../../../.pre-commit-config.yaml)
  - Authoritative source for all quality checks; CI must replicate every non-diff-mutating hook
  - Hooks using `git diff --cached`: `check-copyright-headers`, `jscpd-diff`, `check-lint-suppressions` — require special CI treatment
  - Hooks that modify files (fixers): `autocopyright-python`, `autocopyright-typescript`, `autocopyright-shell`, `ruff-format` (with `--fix`), `ruff` (with `--fix`), `eslint` (with `--fix`), `prettier` (with `--write`) — run as check-only in CI
  - Hooks that are diff-aware by design: `diff-coverage`, `diff-coverage-frontend`, `jscpd-diff`, `check-lint-suppressions`
  - Manual-only hooks (`stages: [manual]`): `pytest-all`, `vitest-all`, `jscpd-full`, `ci-cd-workflow` — not replicated in CI
- [.github/workflows/ci-cd.yml](../../../.github/workflows/ci-cd.yml)
  - Existing workflow: `unit-tests`, `integration-tests`, `lint`, `frontend-test`, `build-and-publish`
  - `unit-tests` runs `pytest tests/services/ tests/shared/` — wrong; `pyproject.toml` sets `testpaths = ["tests"]`
  - `lint` job missing: `python-compile`, `complexipy`, `lizard-typescript`, `jscpd`, `check-lint-suppressions`, `check-copyright-headers`
  - `build-and-publish` matrix: api, bot, scheduler, frontend, init — missing `retry`; no build-only job on push
- [scripts/check_commit_duplicates.py](../../../scripts/check_commit_duplicates.py)
  - `get_changed_line_ranges()` hardcodes `git diff --cached --unified=0`
  - `main(report_file: str)` takes only one argument; no `--compare-branch` support yet
  - Needs a new optional arg so CI can pass `origin/main` as comparison base
- [scripts/check_lint_suppressions.py](../../../scripts/check_lint_suppressions.py)
  - `_get_added_lines()` hardcodes `git diff --cached --unified=0`
  - No CLI argument support at all; needs `--compare-branch` and `--ci` mode added
  - BLOCKED patterns: `# noqa` (bare), `# ruff: noqa`, `# type: ignore` (bare), `#lizard forgive global`, `// @ts-ignore`, `// eslint-disable` (block), `/* eslint-disable */`
  - COUNTED patterns: `# noqa: <code>`, `# type: ignore[...]`, `#lizard forgives`, `// @ts-expect-error`, `// eslint-disable-next-line <rule>`
- [pyproject.toml](../../../pyproject.toml)
  - `testpaths = ["tests"]`, `addopts = "-m 'not e2e and not integration' --strict-markers"` — correct pytest invocation; CI should use these, not hardcoded paths
  - `[tool.complexipy]` `max-complexity-allowed = 15`, `paths = ["services", "shared", "scripts"]`
  - Dev deps include: `autocopyright~=1.1.0`, `diff-cover~=9.2.0`, `complexipy`, `lizard`, `ruff`, `mypy`
- [.jscpd.json](../../../.jscpd.json)
  - `"threshold": 2` — 2% duplication threshold for full scan
  - `jscpd-generate` in pre-commit uses `--threshold 100` (never fails itself); the Python script does the overlap gating
  - CI approach: run `jscpd --threshold 100 --reporters json` then call `check_commit_duplicates.py --compare-branch origin/main`
- [docker/\*.Dockerfile](../../../docker/)
  - 6 Dockerfiles: `api.Dockerfile`, `bot.Dockerfile`, `scheduler.Dockerfile`, `frontend.Dockerfile`, `init.Dockerfile`, `retry.Dockerfile`
  - `retry` is present but missing from the existing `build-and-publish` matrix
- [frontend/package.json](../../../frontend/package.json)
  - `"lint": "eslint ."` — runs without `--fix`
  - `"format:check": "prettier --check ..."` — check-only variant already exists
  - `"type-check": "tsc --noEmit"` — already exists
  - `"test:ci": "vitest --run"` — CI-appropriate test command
  - `"test:coverage": "vitest --coverage"`

### Code Search Results

- `git diff --cached` in scripts/
  - `check_commit_duplicates.py:get_changed_line_ranges()` — needs `--compare-branch` arg
  - `check_lint_suppressions.py:_get_added_lines()` — needs `--compare-branch` and `--ci` flag
- `build-and-publish` matrix in ci-cd.yml
  - `[api, bot, scheduler, frontend, init]` — missing `retry`
- `pytest tests/services/ tests/shared/` in ci-cd.yml
  - Explicit path restriction bypasses `pyproject.toml` config, misses `tests/unit/`

### External Research

- #fetch:https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment
  - GitHub Environments with required reviewers available on **public repos** at no cost
  - `environment: <name>` in a job triggers the protection rules before the job runs
  - Required reviewers can approve or reject via the GitHub UI; full audit trail of who approved and when
  - A job that uses an environment but is **skipped** (`if: false`) does not consume the protection gate — branch protection can treat skipped as satisfied
- #fetch:https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
  - "Require status checks to pass before merging" — required checks that are **skipped** can be treated as passing if "Allow skipping for required status checks" is configured (or by leaving the check non-required when suppression-gate is skipped)
  - Alternatively: use a "pass-through" job that always runs and depends on suppression-gate when it ran, or is a no-op when it was skipped

### Project Conventions

- Standards referenced: `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
- Python version: 3.13 throughout
- Node version: frontend/package.json engines `"node": ">=24.0.0"`; pre-commit default_language_version node `22.11.0` (for isolated hook envs only — actual project uses 24)
- `uv` for all Python dependency and venv management (`setup-uv` action v3)
- `npm ci` for frontend (uses `package-lock.json`)

## Key Discoveries

### Hooks Requiring Special CI Treatment

| Hook                      | Pre-commit behavior                            | CI equivalent                                                                                                  |
| ------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `autocopyright-*`         | Modifies files if header missing               | Run autocopyright, then `git diff --exit-code`                                                                 |
| `ruff-format`             | Rewrites files                                 | `uv run ruff format --check .`                                                                                 |
| `ruff`                    | Fixes and rewrites                             | `uv run ruff check .` (no `--fix`)                                                                             |
| `prettier`                | Rewrites files                                 | `npm run format:check`                                                                                         |
| `eslint`                  | Fixes in place                                 | `npm run lint` (already no `--fix`)                                                                            |
| `check-copyright-headers` | Only checks newly staged files                 | Not replicated; autocopyright check covers it                                                                  |
| `jscpd-diff`              | Checks staged diff overlap                     | `jscpd --threshold 100 --reporters json` + `check_commit_duplicates.py --compare-branch origin/main` (PR only) |
| `check-lint-suppressions` | Scans staged diff; APPROVED_OVERRIDES env gate | BLOCKED: scan all files always; COUNTED: environment gate (PR only)                                            |
| `diff-coverage`           | Staged diff vs origin/main                     | `diff-cover coverage.xml --compare-branch=origin/main --fail-under=90` (PR only)                               |
| `diff-coverage-frontend`  | Same for lcov                                  | `diff-cover frontend/coverage/lcov.info --compare-branch=origin/main --fail-under=90` (PR only)                |
| `pytest-random`           | Randomized order, no coverage                  | Replaced by unified pytest job                                                                                 |
| `pytest-coverage`         | Fixed order, with coverage                     | `uv run pytest --timeout=30 -p no:randomly --cov --cov-report=xml -qq`                                         |
| `vitest-coverage`         | Frontend coverage                              | `npm run test:coverage`                                                                                        |

### Script Modifications Required

**`scripts/check_commit_duplicates.py`** — add `--compare-branch <ref>` optional argument:

- When present: `git diff <ref>...HEAD --unified=0` replaces `git diff --cached --unified=0`
- When absent: behavior unchanged (pre-commit compatibility preserved)
- `main()` signature changes to accept `compare_branch: str | None = None`

**`scripts/check_lint_suppressions.py`** — add `--compare-branch <ref>` and `--ci` optional arguments:

- `--compare-branch`: switches diff source same as above
- `--ci`: changes exit behavior for COUNTED patterns — outputs count to stdout as `SUPPRESSION_COUNT=N` and exits 0 (count is consumed by the workflow to conditionally trigger the environment gate)
- Without `--ci`: COUNTED patterns still fail with non-zero exit (pre-commit behavior unchanged)

### GitHub Environment Gate Design

```
check-suppressions (runs on pull_request)
  ├── fetches git diff origin/main...HEAD
  ├── BLOCKED patterns → exit 1 immediately (job fails)
  └── COUNTED patterns → outputs SUPPRESSION_COUNT=N, exits 0
          ↓ (if SUPPRESSION_COUNT > 0)
suppression-gate
  └── environment: lint-suppression-review
      ← pauses; designated reviewer approves/rejects in GitHub UI
      ← audit trail: who approved, timestamp, PR context
          ↓ approved
[downstream jobs proceed]
```

When `SUPPRESSION_COUNT == 0`, `suppression-gate` is skipped via `if: env.SUPPRESSION_COUNT > 0` — branch protection treats skipped as non-blocking since the gate only matters when suppressions exist.

### Complete Examples

```yaml
# Passing SUPPRESSION_COUNT between jobs via output
check-suppressions:
  outputs:
    suppression_count: ${{ steps.scan.outputs.suppression_count }}
  steps:
    - id: scan
      run: |
        count=$(uv run python scripts/check_lint_suppressions.py --compare-branch origin/main --ci)
        echo "suppression_count=$count" >> "$GITHUB_OUTPUT"

suppression-gate:
  needs: check-suppressions
  if: needs.check-suppressions.outputs.suppression_count > 0
  environment: lint-suppression-review
  steps:
    - run: echo "Suppression gate passed by reviewer"
```

### Node version for CI frontend jobs

The `frontend/package.json` engines field requires Node >= 24. The pre-commit `default_language_version: node: "22.11.0"` applies only to isolated pre-commit hook environments (separate from the project's actual Node). CI should use Node 24 (LTS as of 2026).

### Recommended Version: Node.js

**Software**: Node.js
**Recommended Version**: 22.x
**Type**: LTS (Jod)
**Support Until**: April 2027 (Maintenance LTS)
**Reasoning**: `package.json` engines requires `>=24.0.0`; Node 24 became LTS in October 2025 and is supported until April 2028 — longer than Node 22 maintenance. Use Node 24.
**Source**: https://github.com/nodejs/release#release-schedule

**Alternative Considered**:

- Node 22.x LTS: Support until April 2027

## Recommended Approach

Replace the existing `ci-cd.yml` entirely with a new workflow structured as follows.

### Triggers

```yaml
on:
  push:
    branches: [main, develop]
    tags: ['v*.*.*']
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
```

### Job Dependency Graph

```
code-quality ─────┐
unit-tests ────────┤──► docker-build   (push to main only)
frontend-tests ────┤
integration-tests ─┘──► build-and-publish  (tag push only)

unit-tests ──────────► diff-coverage     (PR only)
frontend-tests ──────► (inline diff-coverage, PR only)

check-suppressions ──► suppression-gate  (PR only, count > 0)
jscpd-check                              (PR only)
```

### Job Definitions

**`code-quality`** — runs on every trigger

- `uv sync --dev`
- `cd frontend && npm ci`
- Copyright: run `autocopyright` on all source dirs → `git diff --exit-code`
- `uv run python -m compileall -q services shared tests`
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy shared/ services/`
- `npm run format:check` (prettier --check)
- `npm run lint` (eslint, no --fix)
- `npm run type-check` (tsc --noEmit)
- `uv run complexipy .`
- `uv run lizard -l typescript frontend/src/ --CCN 15 --warnings_only`
- Scan all non-test `.py/.ts/.tsx` files for BLOCKED suppression patterns (grep)
- `trailing-whitespace`, `end-of-file-fixer` checks via grep/find
- `check-merge-conflict` via grep
- `detect-private-key` via grep

**`unit-tests`** — runs on every trigger

- `uv sync --dev`
- `uv run pytest --timeout=30 -p no:randomly --cov --cov-report=xml -qq`
- Upload `coverage.xml` as artifact

**`diff-coverage`** — PR only, needs `unit-tests`

- `fetch-depth: 0` (full history needed)
- Download `coverage.xml` artifact
- `uv run diff-cover coverage.xml --compare-branch=origin/main --fail-under=90 --ignore-whitespace`

**`frontend-tests`** — runs on every trigger

- Node 24, `npm ci`
- `npm run test:coverage` (vitest with coverage → lcov)
- Fix lcov paths if needed
- `npm run build`
- PR only: `uv run diff-cover frontend/coverage/lcov.info --compare-branch=origin/main --fail-under=90`

**`integration-tests`** — runs on every trigger

- Keep existing postgres/redis/rabbitmq service containers
- `uv run pytest tests/integration/ -m integration` (explicit marker)

**`check-suppressions`** — PR only

- `fetch-depth: 0`
- `uv sync --dev`
- Run `check_lint_suppressions.py --compare-branch origin/main --ci` → capture count
- Output `suppression_count` as job output

**`suppression-gate`** — PR only, only if `suppression_count > 0`

- `environment: lint-suppression-review`
- Single step confirming approval

**`jscpd-check`** — PR only

- `fetch-depth: 0`
- `npx jscpd services shared frontend/src --config .jscpd.json --threshold 100 --reporters json --output .jscpd-report`
- `uv run python scripts/check_commit_duplicates.py .jscpd-report/jscpd-report.json --compare-branch origin/main`

**`docker-build`** — push to `main` only, needs `code-quality`, `unit-tests`, `frontend-tests`

- Matrix: `[api, bot, scheduler, frontend, init, retry]`
- `docker/setup-buildx-action@v3`
- `docker/build-push-action@v5` with `push: false`

**`build-and-publish`** — tag push only, needs `code-quality`, `unit-tests`, `frontend-tests`, `integration-tests`

- Matrix: `[api, bot, scheduler, frontend, init, retry]` (adds `retry` vs current)
- Login to ghcr.io, extract semver tags, push

## Implementation Guidance

- **Objectives**: Replace existing `ci-cd.yml` with a complete workflow that mirrors pre-commit quality gates; add diff-aware checks on PRs; add build-only Docker job on main push; fix retry omission
- **Key Tasks**:
  1. Add `--compare-branch` arg to `scripts/check_commit_duplicates.py`
  2. Add `--compare-branch` and `--ci` args to `scripts/check_lint_suppressions.py`
  3. Create GitHub Environment `lint-suppression-review` (manual step in GitHub UI — documented as prerequisite)
  4. Rewrite `.github/workflows/ci-cd.yml` with all jobs above
- **Dependencies**:
  - `check-lint-suppressions.py --ci` must output count to stdout (not stderr) for `$()` capture in workflow
  - `check_commit_duplicates.py --compare-branch` must handle empty diff gracefully (return 0)
  - `fetch-depth: 0` required for all jobs using `origin/main` comparison
  - `autocopyright` binary available after `uv sync --dev` (it's in dev deps)
  - `diff-cover` available after `uv sync --dev` (it's in dev deps)
  - jscpd available via `npx` (no install needed, or pin via `npm ci` in frontend)
- **Success Criteria**:
  - All hooks in `.pre-commit-config.yaml` (excluding manual-stage and diff-mutating fixers) have a corresponding CI enforcement step
  - PR merge blocked when: any BLOCKED suppression present, diff coverage < 90%, new duplicates overlapping changed lines, any fixer would modify a file
  - `retry` image built and published on tag push
  - Build-only Docker check runs on every push to main
  - `suppression-gate` env gate requires human approval for COUNTED suppressions on PRs
