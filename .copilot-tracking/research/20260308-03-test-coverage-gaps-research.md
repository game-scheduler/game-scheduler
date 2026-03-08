<!-- markdownlint-disable-file -->

# Task Research Notes: Coverage Collection Infrastructure Fix

## Research Executed

### File Analysis

- `scripts/coverage-report.sh`
  - Combines three files: `.coverage.unit`, `coverage/.coverage.integration`, `coverage/.coverage.e2e`
- `docker/test.Dockerfile`
  - Only container that installs `coverage`; only container with `COVERAGE_PROCESS_START` semantics
- `compose.int.yaml` and `compose.e2e.yaml`
  - `./coverage:/app/coverage:rw` volume and `COVERAGE_FILE` env var present **only** on the test runner services (`integration-tests`, `e2e-tests`), not on any application service
- `docker/api.Dockerfile`, `docker/bot.Dockerfile`, `docker/scheduler.Dockerfile`, `docker/retry.Dockerfile`
  - Zero coverage instrumentation; no `sitecustomize.py`, no `COVERAGE_PROCESS_START`
- `tests/integration/conftest.py`, `tests/e2e/conftest.py`
  - Both use `httpx.AsyncClient(base_url=api_base_url)` — HTTP over the Docker network to the real service containers
- `pyproject.toml` `[tool.coverage.run]`
  - `coverage` not listed in `[project.dependencies]`; therefore not installed in any service image

### Code Search Results

- `grep -n "coverage"` in `compose.int.yaml` → lines 91–93 only (the `integration-tests` service)
- `grep -n "coverage"` in `compose.e2e.yaml` → lines 110–112 only (the `e2e-tests` service)
- `grep -n "sitecustomize|COVERAGE_PROCESS_START"` in all 4 service Dockerfiles → no results
- `python3 -c "import coverage"` → coverage is installed in the **dev container** but not in service images (it's not in `pyproject.toml` `[project.dependencies]`)

### Project Conventions

- Standards referenced: `.github/instructions/containerization-docker-best-practices.instructions.md`
- Service Dockerfiles: multi-stage with `python:3.13-slim AS base`; packages installed via `uv pip install --system .`

---

## Key Discoveries

### Root Cause

Integration and e2e tests run in a separate test runner container that makes real HTTP calls via `httpx.AsyncClient` to the `api`, `bot`, `scheduler`, and `retry-daemon` service containers over the Docker bridge network. Code executing inside the service containers is in separate processes with no coverage instrumentation. The test runner container's `.coverage.integration` and `.coverage.e2e` files contain only measurements of test harness code (fixtures, helper functions in `tests/`), not service execution code.

**All integration and e2e coverage percentages for service modules are essentially zero — the reported numbers are artifacts of mock-based unit test runs being combined with empty integration measurements.**

### Activation Mechanism

`coverage.py` subprocess tracking requires two things in each process to be instrumented:

1. `sitecustomize.py` on the Python path containing `import coverage; coverage.process_startup()`
2. `COVERAGE_PROCESS_START` env var pointing to the config file (e.g., `/app/pyproject.toml`)

When both are present, coverage starts automatically at Python interpreter startup, before any application code runs. No application code changes are needed.

### Why `parallel = true` Is Not Needed

Each service container writes to its own uniquely named `COVERAGE_FILE` (e.g., `.coverage.api.integration`, `.coverage.bot.integration`). There is no collision risk. `parallel = true` adds a suffix to avoid collisions within a single process — not needed here since names are already unique.

---

## Historical Gap Data (INVALID — Collected With Broken Instrumentation)

These numbers were generated before the instrumentation fix. They are retained for historical reference only. Re-run `scripts/coverage-report.sh` after the fix is applied to get reliable data.

### Summary at Time of Collection

| Test Type   | Coverage   | Tests  |
|-------------|------------|--------|
| Unit        | 84.98%     | 1,623  |
| Integration | 44.40%     | 200    |
| E2E         | 36.01%     | 74     |
| **Combined**| **85.64%** | —      |

### Modules With Reported Low Coverage

| File | Combined % | Notes |
|---|---|---|
| `services/api/routes/auth.py` | 26.37% | Coverage gap analysis deferred — numbers unreliable |
| `services/bot/handlers/join_game.py` | 30.65% | " |
| `services/bot/handlers/leave_game.py` | 27.45% | " |
| `services/bot/handlers/button_handler.py` | 31.03% | " |
| `services/api/routes/games.py` | 57.32% | " |
| `services/scheduler/services/notification_service.py` | 0% | " |
| `services/retry/retry_daemon_wrapper.py` | 0% | " |

---

## Recommended Approach

Apply changes in this order. Each step is independent except that step 4 requires step 3.

### Step 1 — Add `coverage` to project dependencies

In `pyproject.toml`, add `coverage` to `[project.dependencies]`. This ensures `uv pip install --system .` (already called in all 4 service Dockerfiles) installs it without any Dockerfile modifications.

### Step 2 — Install `sitecustomize.py` in each service Dockerfile

Add one `RUN` line to the `base` stage of `api.Dockerfile`, `bot.Dockerfile`, `scheduler.Dockerfile`, and `retry.Dockerfile`:

```dockerfile
RUN python -c "import site; open(site.getsitepackages()[0] + '/sitecustomize.py', 'w').write('import coverage\ncoverage.process_startup()\n')"
```

This installs the hook that coverage uses to auto-start in every Python process. It has no effect in production because `COVERAGE_PROCESS_START` is not set there.

### Step 3 — Add volume mounts to service containers in compose.int.yaml

For `api`, `bot`, `scheduler`, and `retry-daemon` in `compose.int.yaml`, add:

```yaml
volumes:
  - ./coverage:/app/coverage:rw
environment:
  COVERAGE_PROCESS_START: /app/pyproject.toml
  COVERAGE_FILE: /app/coverage/.coverage.<service>.integration
```

Use distinct names per service: `.coverage.api.integration`, `.coverage.bot.integration`, `.coverage.scheduler.integration`, `.coverage.retry.integration`.

### Step 4 — Add volume mounts to service containers in compose.e2e.yaml

Same pattern as step 3 for `api`, `bot`, and `scheduler` in `compose.e2e.yaml`. Use `.coverage.api.e2e`, `.coverage.bot.e2e`, `.coverage.scheduler.e2e`.

(`retry-daemon` does not appear in `compose.e2e.yaml` service list.)

### Step 5 — Update coverage-report.sh to combine new files

`scripts/coverage-report.sh` currently expects `.coverage.unit`, `coverage/.coverage.integration`, and `coverage/.coverage.e2e`. After the fix, additional files will appear in `coverage/`. Verify the combine command picks them up (glob patterns or explicit list).

---

## Implementation Guidance

- **Objectives**: Make integration and e2e coverage measurements reflect actual service code execution
- **Key Tasks**:
  - Add `coverage` to `[project.dependencies]` in `pyproject.toml`
  - Add `sitecustomize.py` `RUN` line to 4 service Dockerfiles
  - Add `COVERAGE_PROCESS_START`, `COVERAGE_FILE`, and volume mount to 7 service entries across the two compose override files
  - Verify `coverage-report.sh` combines all new `.coverage.*` files
- **Dependencies**: Steps 1 and 2 must be done before steps 3/4 (coverage must be installed before sitecustomize.py can import it)
- **Success Criteria**:
  - After running `scripts/run-integration-tests.sh`, new files appear in `./coverage/`: `.coverage.api.integration`, `.coverage.bot.integration`, `.coverage.scheduler.integration`, `.coverage.retry.integration`
  - `scripts/coverage-report.sh` produces a combined report where service modules show non-zero integration coverage
  - The combined coverage report can be used as the starting point for a new gap analysis
