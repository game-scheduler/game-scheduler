# Docker Compose Service Dependencies

**Date:** December 24, 2025

## Overview

This document describes the service dependency structure across all Docker Compose environments and how to use the debugging features added to test environments.

## Service Architecture

The application consists of:

- **Infrastructure**: postgres, rabbitmq, redis, grafana-alloy
- **Initialization**: init (database migrations, RabbitMQ setup)
- **Application Services**: api, bot, frontend
- **Background Daemons**: notification-daemon, status-transition-daemon, retry-daemon
- **Test Services**: e2e-tests, integration-tests
- **Debug Helper**: system-ready (test environments only)

## Changes Made

### 1. Fixed Test Environment Dependencies

**Problem:** Test services were missing dependencies on critical daemons, allowing tests to run before the system was fully operational.

**Solution:** Added `system-ready` service that depends on all required services, then made tests depend on `system-ready`.

#### E2E Tests ([compose.e2e.yaml](../compose.e2e.yaml))
```yaml
system-ready:
  depends_on:
    - init (completed)
    - postgres (healthy)
    - rabbitmq (healthy)
    - redis (healthy)
    - api (started)
    - bot (started)
    - notification-daemon (started)
    - status-transition-daemon (started)
    - retry-daemon (started)

e2e-tests:
  depends_on:
    - system-ready (started)  # Single dependency point
```

#### Integration Tests ([compose.int.yaml](../compose.int.yaml))
```yaml
system-ready:
  depends_on:
    - init (completed)
    - postgres (healthy)
    - rabbitmq (healthy)
    - redis (healthy)
    - retry-daemon (started)
    - notification-daemon (started)
    - status-transition-daemon (started)

integration-tests:
  depends_on:
    - system-ready (started)  # Single dependency point
```

**Benefits:**
- Single source of truth for "system is ready"
- Eliminates duplicate dependency declarations
- Tests semantically depend on "system ready" state

### 2. Test Environment Telemetry Configuration

**Added:** `PYTEST_RUNNING: "1"` environment variable to all Python services in test environments to disable telemetry collection during tests.

**Services configured:**
- init
- api
- bot
- notification-daemon
- status-transition-daemon
- retry-daemon

**Effect:** Prevents OpenTelemetry data from polluting Grafana Cloud during automated test runs.

### 3. Production/Staging Reliability

**Problem:** In production, daemons could fail silently without preventing the system from appearing "ready".

**Solution:** Made frontend depend on all daemons being healthy in production and staging environments.

#### Production ([compose.prod.yaml](../compose.prod.yaml))
```yaml
frontend:
  depends_on:
    api:
      condition: service_healthy
    notification-daemon:
      condition: service_healthy
    status-transition-daemon:
      condition: service_healthy
    retry-daemon:
      condition: service_healthy
```

#### Staging ([compose.staging.yaml](../compose.staging.yaml))
Same dependency structure as production.

#### Development ([compose.override.yaml](../compose.override.yaml))
**Unchanged** - Frontend only depends on API, allowing faster iteration and independent frontend development.

### 4. Test Debugging Support

**Problem:** When tests run and shut down, service logs are lost, making debugging difficult.

**Solution:** Added `system-ready` pseudo-service to test environments. This Alpine container simply sleeps, keeping all dependent services running for manual inspection and testing.

## Usage Guide

### Running Tests Normally

**E2E Tests:**
```bash
./scripts/run-e2e-tests.sh
./scripts/run-e2e-tests.sh tests/e2e/test_game_reminder.py -v
```

**Integration Tests:**
```bash
./scripts/run-integration-tests.sh
./scripts/run-integration-tests.sh tests/integration/test_retry_daemon.py -v
```

Services start, tests run, services shut down (normal behavior).

### Debugging Tests with Persistent Services

**1. Start services (without running tests):**

```bash
# E2E environment
docker compose -f compose.yaml -f compose.e2e.yaml \
  --env-file env/env.e2e \
  up -d system-ready

# Integration environment
docker compose -f compose.yaml -f compose.int.yaml \
  --env-file env/env.int \
  up -d system-ready
```

The `system-ready` container will start and wait, keeping all services running.

**2. Run tests manually:**

```bash
# E2E - specific test
docker compose -f compose.yaml -f compose.e2e.yaml \
  run --rm e2e-tests tests/e2e/test_game_reminder.py -v

# E2E - all tests
docker compose -f compose.yaml -f compose.e2e.yaml \
  run --rm e2e-tests tests/e2e/ -v

# Integration - specific test
docker compose -f compose.yaml -f compose.int.yaml \
  run --rm integration-tests tests/integration/test_retry_daemon.py -v

# Integration - all tests
docker compose -f compose.yaml -f compose.int.yaml \
  run --rm integration-tests tests/integration/ -v
```

**3. Inspect logs while services are running:**

```bash
# E2E logs
docker compose -f compose.yaml -f compose.e2e.yaml logs -f notification-daemon
docker compose -f compose.yaml -f compose.e2e.yaml logs -f status-transition-daemon
docker compose -f compose.yaml -f compose.e2e.yaml logs api bot

# Integration logs
docker compose -f compose.yaml -f compose.int.yaml logs -f retry-daemon
docker compose -f compose.yaml -f compose.int.yaml logs postgres rabbitmq
```

**4. Clean up:**

```bash
# E2E
docker compose -f compose.yaml -f compose.e2e.yaml down -v

# Integration
docker compose -f compose.yaml -f compose.int.yaml down -v
```

### Deployment Environments

**Development:**
```bash
docker compose up
# Or explicitly: docker compose -f compose.yaml -f compose.override.yaml up
```

**Staging:**
```bash
docker compose --env-file env/env.staging up -d
```

**Production:**
```bash
docker compose --env-file env/env.prod up -d
```

## Dependency Chain Summary

### Development (compose.override.yaml)
```
Infrastructure (postgres, rabbitmq, redis, grafana-alloy)
  ↓
init
  ↓
├─ api ────────────────────┐
├─ bot                     │
├─ notification-daemon     │
├─ status-transition-daemon│  (independent)
└─ retry-daemon            │
                           ↓
                        frontend
```

### Production/Staging
```
Infrastructure (postgres, rabbitmq, redis, grafana-alloy)
  ↓
init
  ↓
├─ api ────────────────────┐
├─ bot                     │
├─ notification-daemon ────┤
├─ status-transition-daemon┤
└─ retry-daemon ───────────┤
                           ↓
                        frontend (waits for ALL)
```

### E2E Tests
```
Infrastructure (postgres, rabbitmq, redis)
  ↓
init
  ↓
├─ api ─────────────────────┐
├─ bot ─────────────────────┤
├─ notification-daemon ─────┤
├─ status-transition-daemon ┤
└─ retry-daemon ────────────┤
                            ↓
                      system-ready
                            ↓
                        e2e-tests
```

### Integration Tests
```
Infrastructure (postgres, rabbitmq, redis)
  ↓
init
  ↓
├─ notification-daemon ─────┐
├─ status-transition-daemon ┤
└─ retry-daemon ────────────┤
                            ↓
                      system-ready
                            ↓
                    integration-tests
```

## Benefits

### Reliability
- Production systems won't appear "ready" if critical daemons fail
- Frontend depends on fully operational backend in production/staging
- Tests wait for complete system initialization via `system-ready` service

### Development Speed
- Development environment unchanged - fast iteration
- Frontend can start independently of daemons during dev work

### Debugging
- Keep test services running for log inspection via `system-ready` target
- Run tests repeatedly against same environment
- Inspect database and message queue state between test runs
- No need to rebuild/restart services for each test attempt

### Maintainability
- Single source of truth for "system ready" state
- No duplicate dependency declarations between `system-ready` and test services
- Semantic clarity: tests depend on "system ready" conceptually

## Troubleshooting

**Services won't start in production:**
- Check health of: notification-daemon, status-transition-daemon, retry-daemon
- Frontend blocks until all daemons are healthy
- Review daemon logs: `docker compose logs notification-daemon`

**Tests fail immediately:**
- Verify all dependencies are healthy before test starts
- Check init completed successfully: `docker compose logs init`
- Verify RabbitMQ queues created: `docker compose exec rabbitmq rabbitmqctl list_queues`

**Debug profile not working:**
- Target `system-ready` by name: `docker compose -f compose.yaml -f compose.e2e.yaml up -d system-ready`
- Verify system-ready container started: `docker compose -f compose.yaml -f compose.e2e.yaml ps system-ready`
- Check system-ready logs: `docker compose -f compose.yaml -f compose.e2e.yaml logs system-ready`
- Ensure all dependent services are healthy before system-ready starts

**Telemetry appearing in test runs:**
- Verify `PYTEST_RUNNING: "1"` is set for all Python services in test compose files
- Check service logs for OpenTelemetry initialization messages
- Services should log "Skipping telemetry setup - running in pytest" if configured correctly
