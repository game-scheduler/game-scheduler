<!-- markdownlint-disable-file -->

# Changes: Coverage Collection Infrastructure Fix

## Overview

Fixes integration and e2e coverage instrumentation so that `.coverage.integration` and `.coverage.e2e` files reflect actual service code execution instead of only test harness code.

## Progress

### Phase 1: Add `coverage` to project dependencies

- [x] Task 1.1: Add `coverage[toml]` to `[project.dependencies]` in `pyproject.toml`

### Phase 2: Install `sitecustomize.py` in service Dockerfiles

- [x] Task 2.1: Add `sitecustomize.py` RUN line to `docker/api.Dockerfile`
- [x] Task 2.2: Add `sitecustomize.py` RUN line to `docker/bot.Dockerfile`
- [x] Task 2.3: Add `sitecustomize.py` RUN line to `docker/scheduler.Dockerfile`
- [x] Task 2.4: Add `sitecustomize.py` RUN line to `docker/retry.Dockerfile`

### Phase 3: Add coverage env/volumes to compose.int.yaml

- [x] Task 3.1: Add coverage instrumentation to `api` service in `compose.int.yaml`
- [x] Task 3.2: Add coverage instrumentation to `bot` service in `compose.int.yaml`
- [x] Task 3.3: Add coverage instrumentation to `scheduler` service in `compose.int.yaml`
- [x] Task 3.4: Add coverage instrumentation to `retry-daemon` service in `compose.int.yaml`

### Phase 4: Add coverage env/volumes to compose.e2e.yaml

- [x] Task 4.1: Add coverage instrumentation to `api` service in `compose.e2e.yaml`
- [x] Task 4.2: Add coverage instrumentation to `bot` service in `compose.e2e.yaml`
- [x] Task 4.3: Add coverage instrumentation to `scheduler` service in `compose.e2e.yaml`

### Phase 5: Verify coverage-report.sh combines new files

- [x] Task 5.1: Update `scripts/coverage-report.sh` to include all per-service coverage files

---

## Added

_(none — no new files were created)_

## Modified

- `pyproject.toml` — Added `"coverage[toml]"` to `[project.dependencies]` so all four service images install it via `uv pip install --system .`
- `docker/api.Dockerfile` — Added `RUN` instruction in the `base` stage (after package installation) that writes `sitecustomize.py` into the system site-packages to auto-start coverage on every Python process invocation
- `docker/bot.Dockerfile` — Same `sitecustomize.py` RUN instruction added to the `base` stage after package installation
- `docker/scheduler.Dockerfile` — Same `sitecustomize.py` RUN instruction added to the `base` stage after package installation
- `docker/retry.Dockerfile` — Same `sitecustomize.py` RUN instruction added to the `base` stage after package installation
- `compose.int.yaml` — Added `COVERAGE_PROCESS_START`, `COVERAGE_FILE`, and `./coverage:/app/coverage:rw` volume mount to `api`, `bot`, `scheduler`, and `retry-daemon` services
- `compose.e2e.yaml` — Added `COVERAGE_PROCESS_START`, `COVERAGE_FILE`, and `./coverage:/app/coverage:rw` volume mount to `api`, `bot`, and `scheduler` services
- `scripts/coverage-report.sh` — Updated `INT_COV` and `E2E_COV` capture blocks to glob per-service coverage files (`coverage/.coverage.*.integration`, `coverage/.coverage.*.e2e`) rather than checking for the former single-file names

## Removed

_(none)_
