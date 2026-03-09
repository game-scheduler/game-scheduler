---
applyTo: '.copilot-tracking/changes/20260308-03-coverage-collection-infrastructure-fix-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Coverage Collection Infrastructure Fix

## Overview

Fix integration and e2e coverage instrumentation so that `.coverage.integration` and `.coverage.e2e` files reflect actual service code execution instead of only test harness code.

## Objectives

- Add `coverage` to project dependencies so service images install it via `uv pip install --system .`
- Install `sitecustomize.py` in all four service Dockerfiles to auto-start coverage in every Python process
- Add `COVERAGE_PROCESS_START`, `COVERAGE_FILE`, and volume mounts to service entries in `compose.int.yaml` and `compose.e2e.yaml`
- Verify `scripts/coverage-report.sh` combines all new per-service `.coverage.*` files

## Research Summary

### Project Files

- `pyproject.toml` - Python project dependencies; `coverage` must be added to `[project.dependencies]`
- `docker/api.Dockerfile` - Service Dockerfile; needs `sitecustomize.py` RUN line
- `docker/bot.Dockerfile` - Service Dockerfile; needs `sitecustomize.py` RUN line
- `docker/scheduler.Dockerfile` - Service Dockerfile; needs `sitecustomize.py` RUN line
- `docker/retry.Dockerfile` - Service Dockerfile; needs `sitecustomize.py` RUN line
- `compose.int.yaml` - Integration test compose; needs coverage env/volumes on api, bot, scheduler, retry-daemon
- `compose.e2e.yaml` - E2E test compose; needs coverage env/volumes on api, bot, scheduler
- `scripts/coverage-report.sh` - Combines coverage files; must pick up new per-service files

### External References

- #file:../research/20260308-03-test-coverage-gaps-research.md - Comprehensive research on the root cause and fix approach

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker configuration best practices
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting style

## Implementation Checklist

### [x] Phase 1: Add `coverage` to project dependencies

- [x] Task 1.1: Add `coverage` to `[project.dependencies]` in `pyproject.toml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 14-35)

### [x] Phase 2: Install `sitecustomize.py` in service Dockerfiles

- [x] Task 2.1: Add `sitecustomize.py` RUN line to `docker/api.Dockerfile`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 38-65)

- [x] Task 2.2: Add `sitecustomize.py` RUN line to `docker/bot.Dockerfile`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 68-84)

- [x] Task 2.3: Add `sitecustomize.py` RUN line to `docker/scheduler.Dockerfile`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 87-103)

- [x] Task 2.4: Add `sitecustomize.py` RUN line to `docker/retry.Dockerfile`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 106-122)

### [x] Phase 3: Add coverage env/volumes to compose.int.yaml

- [x] Task 3.1: Add coverage instrumentation to `api` service in `compose.int.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 125-152)

- [x] Task 3.2: Add coverage instrumentation to `bot` service in `compose.int.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 155-172)

- [x] Task 3.3: Add coverage instrumentation to `scheduler` service in `compose.int.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 175-192)

- [x] Task 3.4: Add coverage instrumentation to `retry-daemon` service in `compose.int.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 195-212)

### [x] Phase 4: Add coverage env/volumes to compose.e2e.yaml

- [x] Task 4.1: Add coverage instrumentation to `api` service in `compose.e2e.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 215-237)

- [x] Task 4.2: Add coverage instrumentation to `bot` service in `compose.e2e.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 240-257)

- [x] Task 4.3: Add coverage instrumentation to `scheduler` service in `compose.e2e.yaml`
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 260-277)

### [x] Phase 5: Verify coverage-report.sh combines new files

- [x] Task 5.1: Update `scripts/coverage-report.sh` to include all per-service coverage files
  - Details: .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md (Lines 280-310)

## Dependencies

- Docker Compose v2 (`docker compose`)
- `coverage[toml]` Python package
- Existing `./coverage/` host directory (already present for integration test runner)

## Success Criteria

- After running `scripts/run-integration-tests.sh`, the following files appear in `./coverage/`: `.coverage.api.integration`, `.coverage.bot.integration`, `.coverage.scheduler.integration`, `.coverage.retry.integration`
- After running `scripts/run-e2e-tests.sh`, `.coverage.api.e2e`, `.coverage.bot.e2e`, `.coverage.scheduler.e2e` appear in `./coverage/`
- `scripts/coverage-report.sh` produces a combined report where service modules (e.g., `services/api/routes/*.py`) show non-zero integration and e2e coverage percentages
- No production behaviour is changed — `COVERAGE_PROCESS_START` is absent from production compose files so coverage never activates there
