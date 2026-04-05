# CI/CD Pipeline

## Overview

The CI/CD pipeline runs on every push to `main`/`develop`, on pull requests targeting those branches, and on version tag pushes. It mirrors all pre-commit quality gates and adds diff-aware coverage and duplication checks for PRs. Build, integration-test, and image publish behavior is consolidated into the `build-test-publish` job rather than separate `integration-tests`, `docker-build`, and `build-and-publish` jobs.

## Jobs

| Job                  | Triggers                      | Description                                                                 |
| -------------------- | ----------------------------- | --------------------------------------------------------------------------- |
| `code-quality`       | all                           | Copyright headers, Python/TS linting, formatting, type checking, complexity |
| `unit-tests`         | all                           | pytest with coverage; uploads `coverage.xml` artifact                       |
| `diff-coverage`      | PR only                       | Fails if diff coverage < 90% for changed Python files                       |
| `frontend-tests`     | all                           | vitest coverage + build; diff coverage check on PRs                         |
| `build-test-publish` | push/PR/tag (behavior varies) | Consolidated full-stack build/test job; publishes images on version tags    |
| `check-suppressions` | PR only                       | Scans PR diff for counted lint suppressions; outputs count                  |
| `suppression-gate`   | PR only (count > 0)           | Pauses for human reviewer approval via GitHub Environment                   |
| `jscpd-check`        | PR only                       | Detects duplicated code overlapping changed lines                           |

## Required Setup: `lint-suppression-review` Environment

The `suppression-gate` job uses a [GitHub Environment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment) named `lint-suppression-review` to require human approval before merging PRs that add counted lint suppressions (e.g., `# noqa: E501`, `# type: ignore[attr-defined]`).

**This environment must be created manually before the workflow functions correctly.**

### Setup Steps

1. Go to the repository **Settings** → **Environments** → **New environment**
2. Name: `lint-suppression-review`
3. Under **Deployment protection rules**, enable **Required reviewers**
4. Add the team members who are authorized to approve suppression use
5. Click **Save protection rules**

### How It Works

When a PR adds any [COUNTED suppression pattern](../../.github/instructions/quality-check-overrides.instructions.md), the `check-suppressions` job outputs the count. If `suppression_count > 0`, the `suppression-gate` job activates the environment, pausing the pipeline until a designated reviewer approves or rejects via the GitHub UI. The approval is logged with reviewer identity and timestamp.

PRs with zero suppressions skip the gate entirely — it only activates when needed.

### Blocked vs. Counted Suppressions

- **Blocked** (bare/blanket): `# noqa`, `# type: ignore`, `// @ts-ignore`, etc. — rejected unconditionally; the `code-quality` job fails immediately.
- **Counted** (specific): `# noqa: E501`, `# type: ignore[attr-defined]`, `// @ts-expect-error` — allowed with reviewer approval via the environment gate.

See [quality-check-overrides.instructions.md](../../.github/instructions/quality-check-overrides.instructions.md) for full policy details.
