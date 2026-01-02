---
description: "Game Scheduler Integration and E2E tests"
applyTo: "**/tests/integration**.py, **/tests/e2e**.py"
---

## General Instructions

- Integration and e2e tests run inside of docker compose with wrapper scripts:
  - `scripts/run-integration-tests.sh` for integration tests
  - `scripts/run-e2e-tests.sh` for e2e tests
- These scripts start with clean environments and are best used for full runs to verify changes

## Output Collection Best Practices

- Integration and e2e tests take a relatively long time to run
- When collecting output, use a minimum of 75 lines to avoid needing to rerun tests
- Always send raw results to `tee` so additional output is available without rerunning if needed
- While reducing output with tools like `tail` is acceptable, removing too much adds significant time if tests must be rerun

## Reducing Test Cycle Time for Debugging

When debugging individual tests, you can reduce cycle time with this workflow:

### 1. Start Infrastructure Once

```bash
# For integration tests
docker compose --env-file config/env.int up -d --build system-ready

# For e2e tests
docker compose --env-file config/env.e2e up -d --build system-ready
```

### 2. Run Tests Iteratively

```bash
# For integration tests
docker compose --env-file config/env.int run --build --rm integration-tests [pytest-options]

# For e2e tests
docker compose --env-file config/env.e2e run --build --rm integration-tests [pytest-options]
```

**Important notes:**
- The container entrypoint is `pytest`, so you can pass any pytest options or specific test paths
- Keep the `--build` option to pick up code changes
- Use `--no-deps` to prevent restarting system services
- If you make changes to system services, rebuild them separately:
  ```bash
  docker compose --env-file config/env.<type> up -d --build system-ready
  ```
