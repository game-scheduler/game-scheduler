---
applyTo: '.copilot-tracking/changes/20260329-01-github-actions-ci-cd-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: GitHub Actions CI/CD Pipeline

## Overview

Replace the existing `ci-cd.yml` workflow with a complete, pre-commit-parity pipeline that adds diff-aware PR checks, a lint-suppression environment gate, build-only Docker jobs on `main`, and the missing `retry` image.

## Objectives

- All pre-commit hooks (excluding manual-stage and file-mutating fixers) enforced in CI
- Diff coverage ≥ 90% on PRs (Python and TypeScript)
- BLOCKED lint suppressions fail immediately; COUNTED suppressions trigger human review gate
- `retry` Docker image built and published alongside the other five images
- Build-only Docker check runs on every push to `main`
- Scripts `check_commit_duplicates.py` and `check_lint_suppressions.py` work correctly in CI context

## Research Summary

### Project Files

- `.pre-commit-config.yaml` — authoritative source of all quality gates CI must replicate
- `.github/workflows/ci-cd.yml` — existing workflow to be replaced
- `scripts/check_commit_duplicates.py` — needs `--compare-branch` arg
- `scripts/check_lint_suppressions.py` — needs `--compare-branch` and `--ci` args
- `pyproject.toml` — correct pytest invocation settings (`testpaths`, `addopts`)
- `frontend/package.json` — `test:ci`, `test:coverage`, `lint`, `format:check`, `type-check` scripts
- `.jscpd.json` — duplication config (`threshold: 2`, full scan uses `--threshold 100`)
- `docker/*.Dockerfile` — 6 images including `retry` (currently missing from workflow matrix)

### External References

- #file:../research/20260329-01-github-actions-ci-cd-research.md — full verified research
- #file:../../.github/instructions/github-actions-ci-cd-best-practices.instructions.md — workflow conventions

## Implementation Checklist

### [ ] Phase 1: Extend Scripts for CI Compatibility (TDD)

- [ ] Task 1.1: Write failing tests for `check_commit_duplicates.py --compare-branch`
  - Details: .copilot-tracking/planning/details/20260329-01-github-actions-ci-cd-details.md (Lines 13-52)

- [ ] Task 1.2: Implement `--compare-branch` in `check_commit_duplicates.py`
  - Details: .copilot-tracking/planning/details/20260329-01-github-actions-ci-cd-details.md (Lines 53-74)

- [ ] Task 1.3: Write failing tests for `check_lint_suppressions.py --compare-branch` and `--ci`
  - Details: .copilot-tracking/planning/details/20260329-01-github-actions-ci-cd-details.md (Lines 75-95)

- [ ] Task 1.4: Implement `--compare-branch` and `--ci` in `check_lint_suppressions.py`
  - Details: .copilot-tracking/planning/details/20260329-01-github-actions-ci-cd-details.md (Lines 96-97)

### [ ] Phase 2: Rewrite GitHub Actions Workflow

- [ ] Task 2.1: Replace `.github/workflows/ci-cd.yml` with the complete new workflow
  - Details: .copilot-tracking/planning/details/20260329-01-github-actions-ci-cd-details.md (Lines 100-266)

- [ ] Task 2.2: Document `lint-suppression-review` environment prerequisite
  - Details: .copilot-tracking/planning/details/20260329-01-github-actions-ci-cd-details.md (Lines 267-286)

## Dependencies

- Python 3.13 (`uv python install 3.13`)
- Node.js 24 LTS (`actions/setup-node@v4` with `node-version: '24'`)
- `uv` via `astral-sh/setup-uv@v3`
- `autocopyright` available after `uv sync --dev`
- `diff-cover` available after `uv sync --dev`
- `complexipy`, `lizard`, `ruff`, `mypy` all in dev deps
- `jscpd` available via `npx`
- GitHub Environment `lint-suppression-review` must be created in repository settings before the workflow runs

## Success Criteria

- All hooks in `.pre-commit-config.yaml` (excluding `manual` stage) have a corresponding enforcement step in CI
- PR merge is blocked when: any BLOCKED suppression exists, diff coverage < 90%, new duplicates overlap changed lines, any fixer would modify a file
- `retry` image is built in `docker-build` and published in `build-and-publish`
- `suppression-gate` job uses `lint-suppression-review` environment and requires human approval when `suppression_count > 0`
- Existing unit, integration, and frontend test jobs continue to pass
