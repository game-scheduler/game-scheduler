---
applyTo: '.copilot-tracking/changes/20260305-01-scheduler-daemon-consolidation-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Scheduler Daemon Consolidation

## Overview

Consolidate three separate scheduler daemon containers (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) into a single `scheduler` container running all three `SchedulerDaemon` instances as threads.

## Objectives

- Reduce operational surface from 3 containers to 1 without changing scheduling behaviour
- Add required `service_name` parameter to `SchedulerDaemon` for log and OTel attribution
- Create unified `scheduler_daemon_wrapper.py` with thread lifecycle and signal handling
- Replace three Dockerfiles with one `docker/scheduler.Dockerfile`
- Update all compose files to use the single `scheduler` service

## Research Summary

### Project Files

- `services/scheduler/generic_scheduler_daemon.py` — core `SchedulerDaemon` implementation to be extended with `service_name`
- `services/scheduler/notification_daemon_wrapper.py` — thin wrapper to be deleted after consolidation
- `services/scheduler/status_transition_daemon_wrapper.py` — thin wrapper to be deleted
- `services/scheduler/participant_action_daemon_wrapper.py` — thin wrapper to be deleted
- `services/scheduler/daemon_runner.py` — single-daemon lifecycle helper; NOT used by new unified wrapper
- `docker/notification-daemon.Dockerfile`, `docker/status-transition-daemon.Dockerfile`, `docker/participant-action-daemon.Dockerfile` — three nearly-identical Dockerfiles to be replaced
- `compose.yaml` — primary compose file with three service definitions to replace

### External References

- #file:../research/20260305-01-scheduler-daemon-consolidation-research.md — full research with code sketches, compose examples, and technical requirements

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md — Dockerfile best practices
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md — commenting style

## Implementation Checklist

### [x] Phase 1: Update `SchedulerDaemon` with `service_name`

- [x] Task 1.1: Add `service_name: str` stub parameter to `SchedulerDaemon.__init__`
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 13-26)

- [x] Task 1.2: Write xfail tests for `service_name` log prefix and OTel span attribute (RED)
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 27-39)

- [x] Task 1.3: Implement `service_name` in log messages and OTel spans; remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 40-54)

- [x] Task 1.4: Update existing wrapper callers to pass `service_name`
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 55-72)

### [ ] Phase 2: Create Unified `scheduler_daemon_wrapper.py`

- [ ] Task 2.1: Create stub `scheduler_daemon_wrapper.py` with `main()` raising `NotImplementedError`
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 76-88)

- [ ] Task 2.2: Write xfail unit tests for thread startup and shutdown signal handling (RED)
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 89-101)

- [ ] Task 2.3: Implement full wrapper with thread lifecycle and signal handling; remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 102-117)

- [ ] Task 2.4: Add edge-case tests (thread crash isolation, graceful shutdown, LOG_LEVEL default)
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 118-131)

### [ ] Phase 3: Create `docker/scheduler.Dockerfile`

- [ ] Task 3.1: Create `docker/scheduler.Dockerfile` consolidating all three daemon file copies
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 135-150)

### [ ] Phase 4: Update Compose Files

- [ ] Task 4.1: Update `compose.yaml` — replace 3 daemon services with single `scheduler` service
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 153-167)

- [ ] Task 4.2: Update `compose.prod.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.staging.yaml`, `compose.override.yaml`
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 168-186)

### [ ] Phase 5: Delete Old Files

- [ ] Task 5.1: Delete three old wrapper `.py` files, their unit tests, and three old Dockerfiles atomically
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 190-215)

### [ ] Phase 6: Update Documentation

- [ ] Task 6.1: Update CI/CD workflow — replace `notification-daemon` with `scheduler` in the service build matrix
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 216-228)

- [ ] Task 6.2: Update `docs/` and `config/` env var references — replace per-daemon log level vars with `SCHEDULER_LOG_LEVEL`
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 229-243)

- [ ] Task 6.3: Update in-code comments and docstrings across `services/`, `shared/`, and `tests/`
  - Details: .copilot-tracking/details/20260305-01-scheduler-daemon-consolidation-details.md (Lines 244-277)

## Dependencies

- Python `threading` (stdlib — no new packages required)
- `pytest` with `xfail` marker support (already in project)
- Docker CLI available for build validation

## Success Criteria

- All three scheduling behaviours pass integration tests against a single `scheduler` container
- Old service names (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) absent from all compose files and Dockerfiles
- `docker compose up` starts one `scheduler` container, not three
- CI/CD workflow references `scheduler` service, not `notification-daemon`
- Per-daemon log level env vars replaced by `SCHEDULER_LOG_LEVEL` in all config files
- In-code comments and docstrings updated across `services/`, `shared/`, and `tests/`
- Full `pytest` suite passes with no regressions
