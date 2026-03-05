<!-- markdownlint-disable-file -->

# Task Research Notes: Scheduler Daemon Consolidation

## Research Executed

### File Analysis

- `services/scheduler/generic_scheduler_daemon.py`
  - Full `SchedulerDaemon` implementation: PostgreSQL LISTEN/NOTIFY loop, single-item MIN() query pattern, configurable via constructor params; no shared mutable state between instances
- `services/scheduler/notification_daemon_wrapper.py`
  - ~10-line wrapper instantiating `SchedulerDaemon` for `NotificationSchedule`; PG channel `notification_schedule_changed`, time field `notification_time`
- `services/scheduler/status_transition_daemon_wrapper.py`
  - ~10-line wrapper instantiating `SchedulerDaemon` for `GameStatusSchedule`; PG channel `game_status_schedule_changed`, time field `transition_time`
- `services/scheduler/participant_action_daemon_wrapper.py`
  - ~10-line wrapper instantiating `SchedulerDaemon` for `ParticipantActionSchedule`; PG channel `participant_action_schedule_changed`, time field `action_time` (approximate)
- `services/scheduler/daemon_runner.py`
  - Shared `run_daemon()`: registers SIGTERM/SIGINT handlers, calls `daemon.run(shutdown_flag)`, flushes telemetry on exit; single-daemon model, not thread-aware
- `services/scheduler/postgres_listener.py`
  - `PostgresNotificationListener`: each instance holds its own psycopg2 connection; stateless across instances; thread-safe to run N independent instances
- `services/retry/retry_daemon.py`
  - Architecturally different: time-based polling of RabbitMQ DLQs, no PostgreSQL LISTEN; intentionally kept separate
- `docker/notification-daemon.Dockerfile`, `docker/status-transition-daemon.Dockerfile`, `docker/participant-action-daemon.Dockerfile`
  - Three nearly identical multi-stage Dockerfiles differing only in the `CMD` module path and which wrapper file is `COPY`'d
- `compose.yaml`
  - Three services (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`), each with `restart: always`, identical `depends_on`, identical healthcheck (`python -c "import sys; sys.exit(0)"`)
  - Separate env vars: `NOTIFICATION_DAEMON_LOG_LEVEL`, `STATUS_TRANSITION_DAEMON_LOG_LEVEL`, `PARTICIPANT_ACTION_DAEMON_LOG_LEVEL`
  - Separate OTEL service names per container
- `compose.prod.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.staging.yaml`, `compose.override.yaml`
  - All contain per-daemon service stubs; `compose.staging.yaml` missing `participant-action-daemon` (gap resolved by consolidation)

### Code Search Results

- `restart: always` — confirmed on all three daemon services in `compose.yaml`; Docker is the failure recovery mechanism
- `SchedulerDaemon.__init__` parameters — `database_url`, `rabbitmq_url`, `notify_channel`, `model_class`, `time_field`, `status_field`, `event_builder`, `max_timeout`, `_process_dlq`; no `service_name` parameter currently exists
- Tests found:
  - `tests/unit/services/test_participant_action_daemon_wrapper.py`
  - `tests/integration/test_notification_daemon.py`
  - `tests/integration/test_participant_action_daemon.py`
  - `tests/integration/test_status_transitions.py`
  - `tests/services/scheduler/test_generic_scheduler_daemon.py`
  - `tests/e2e/test_game_status_transitions.py`

### Project Conventions

- Standards referenced: daemon wrapper pattern (thin instantiation wrapper + `daemon_runner.run_daemon()`), Python thread model (GIL acceptable for IO-bound workloads), `service_name` used in OTEL via `init_telemetry()` and `OTEL_SERVICE_NAME` env var
- Instructions followed: minimalist changes, self-documenting code, TDD methodology applies (Python files)

## Key Discoveries

### Project Structure

Three `SchedulerDaemon` instances currently run in separate containers. The real logic is already unified in `generic_scheduler_daemon.py`. The duplication is entirely operational: 3 Dockerfiles, 3 compose services, 3 env var sets.

Each `SchedulerDaemon` instance is independently stateful (own DB session, own PG listener connection, own RabbitMQ publisher). No shared mutable state. Instances are safe to run concurrently in threads.

The daemons are IO-bound (`select()` on PostgreSQL, RabbitMQ publish). Python's GIL is not an obstacle.

`daemon_runner.py` handles single-daemon signal lifecycle. It cannot be used as-is for the multi-thread case.

### Implementation Patterns

The new wrapper will:

1. Instantiate all three `SchedulerDaemon` objects
2. Start each in a `threading.Thread(daemon=True)`
3. Register SIGTERM/SIGINT on the main thread only, setting a shared shutdown flag
4. Main thread joins all worker threads (with timeout), then flushes telemetry

On thread crash: the thread exits; the process continues running the other two schedulers. Docker `restart: always` will restart the container if the process itself dies (e.g., from a truly unrecoverable failure or OOM), which is acceptable given all operations are idempotent.

`service_name` added to `SchedulerDaemon` as a **required** parameter. Used in:

- Logger prefix (e.g., `"Starting scheduler daemon [notification]"`)
- OTel span attributes (`scheduler.service_name`)

### Complete Examples

```python
# New scheduler_daemon_wrapper.py (sketch)
import logging
import signal
import threading

from shared.database import BASE_DATABASE_URL
from shared.models import GameStatusSchedule, NotificationSchedule, ParticipantActionSchedule
from shared.telemetry import flush_telemetry, init_telemetry

from .daemon_runner import run_daemon  # NOT used — inlined below for thread model
from .event_builders import build_notification_event, build_status_transition_event
from .generic_scheduler_daemon import SchedulerDaemon
from .participant_action_event_builder import build_participant_action_event

def main() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=getattr(logging, log_level), ...)
    init_telemetry("scheduler-daemon")

    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    shutdown_requested = False

    daemons = [
        SchedulerDaemon(service_name="notification", database_url=..., notify_channel="notification_schedule_changed", ...),
        SchedulerDaemon(service_name="status-transition", database_url=..., notify_channel="game_status_schedule_changed", ...),
        SchedulerDaemon(service_name="participant-action", database_url=..., notify_channel="participant_action_schedule_changed", ...),
    ]

    def _signal_handler(_signum, _frame):
        nonlocal shutdown_requested
        shutdown_requested = True

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    threads = [threading.Thread(target=d.run, args=(lambda: shutdown_requested,), daemon=True) for d in daemons]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    flush_telemetry()
```

### Configuration Examples

```yaml
# compose.yaml — after consolidation
scheduler:
  build:
    context: .
    dockerfile: docker/scheduler.Dockerfile
  container_name: ${CONTAINER_PREFIX:-gamebot}-scheduler
  restart: always
  environment:
    DATABASE_URL: ${BOT_DATABASE_URL}
    RABBITMQ_URL: ${RABBITMQ_URL}
    LOG_LEVEL: ${SCHEDULER_LOG_LEVEL:-INFO}
    OTEL_SERVICE_NAME: scheduler-daemon
    OTEL_EXPORTER_OTLP_ENDPOINT: http://grafana-alloy:4318
    OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
    OTEL_TRACES_EXPORTER: otlp
    OTEL_METRICS_EXPORTER: otlp
    OTEL_LOGS_EXPORTER: otlp
  depends_on:
    init:
      condition: service_healthy
    grafana-alloy:
      condition: service_started
  healthcheck:
    test: ['CMD', 'python', '-c', 'import sys; sys.exit(0)']
    interval: 30s
    timeout: 10s
    retries: 3
  networks:
    - app-network
```

### Technical Requirements

- `service_name` must be a required positional-or-keyword param added to `SchedulerDaemon.__init__`
- All existing callers (wrappers, tests) must be updated to pass `service_name`
- `daemon_runner.run_daemon()` is **not** used by the new wrapper; it may remain for potential future single-daemon use but is not called from production code after this change
- Three Dockerfiles deleted; one `docker/scheduler.Dockerfile` created (copies all scheduler module files)
- All compose files updated: remove 3-service stubs, add 1 `scheduler` service
- Env vars `NOTIFICATION_DAEMON_LOG_LEVEL`, `STATUS_TRANSITION_DAEMON_LOG_LEVEL`, `PARTICIPANT_ACTION_DAEMON_LOG_LEVEL` removed; replaced by single `SCHEDULER_LOG_LEVEL` (falling back to `LOG_LEVEL`)
- `compose.staging.yaml` gap (missing `participant-action-daemon`) resolved automatically by consolidation

## Recommended Approach

Single `scheduler` container running three `SchedulerDaemon` instances in threads:

1. Add `service_name: str` (required) to `SchedulerDaemon.__init__`; use in log messages and OTel span attributes
2. Create `services/scheduler/scheduler_daemon_wrapper.py` as the unified entry point; inlines thread lifecycle + signal handling (does not reuse `daemon_runner.run_daemon()`)
3. Create `docker/scheduler.Dockerfile` combining the file copies from all three existing Dockerfiles
4. Delete `notification_daemon_wrapper.py`, `status_transition_daemon_wrapper.py`, `participant_action_daemon_wrapper.py`, `notification-daemon.Dockerfile`, `status-transition-daemon.Dockerfile`, `participant-action-daemon.Dockerfile`
5. Update `compose.yaml`: replace three service definitions with one `scheduler` service
6. Update all compose override files: replace per-daemon stubs with single `scheduler` stub
7. Update tests: wrapper unit tests replaced by a test for the new unified wrapper; `test_generic_scheduler_daemon.py` gains coverage for `service_name` param

## Implementation Guidance

- **Objectives**: Reduce operational surface from 3 containers to 1 without changing scheduling behavior
- **Key Tasks**:
  1. Update `SchedulerDaemon` — add required `service_name` param, update log/span usage
  2. Write tests for updated `SchedulerDaemon` and new unified wrapper
  3. Create `scheduler_daemon_wrapper.py`
  4. Create `docker/scheduler.Dockerfile`
  5. Update `compose.yaml` and all override files
  6. Delete the three old wrapper files and three old Dockerfiles
  7. Update any CI scripts or documentation referencing old service names
- **Dependencies**: No new Python dependencies; threading is stdlib
- **Success Criteria**:
  - All three scheduling behaviors work end-to-end in integration tests against a single `scheduler` container
  - Old service names (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) no longer appear in compose files or Dockerfiles
  - `docker compose up` starts one scheduler container, not three

---

## Update: Full Old-Name Surface Audit (2026-03-05)

A follow-up grep audit across all source files revealed the complete set of locations where old daemon names surface. The original Implementation Guidance item 7 ("Update any CI scripts or documentation") was underspecified. The full scope is:

### CI/CD Workflow (functional — breaks CI if missed)

- `.github/workflows/ci-cd.yml` line 201 — `notification-daemon` appears in the service build matrix; must be replaced with `scheduler`

### Compose Files (covered by Phase 4)

All six compose files (`compose.yaml`, `compose.prod.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.staging.yaml`, `compose.override.yaml`) — covered by Phase 4 tasks.

### Python `init_telemetry()` calls (covered by Phase 5 deletions)

- `services/scheduler/notification_daemon_wrapper.py` — `init_telemetry("notification-daemon")`
- `services/scheduler/status_transition_daemon_wrapper.py` — `init_telemetry("status-transition-daemon")`
- `services/scheduler/participant_action_daemon_wrapper.py` — `init_telemetry("participant-action-daemon")`

These are eliminated when the wrapper files are deleted in Phase 5. The new `scheduler_daemon_wrapper.py` calls `init_telemetry("scheduler-daemon")`.

### Config and Docs (accuracy — no test failures)

- `config/` and `config.template/` env files — `NOTIFICATION_DAEMON_LOG_LEVEL`, `STATUS_TRANSITION_DAEMON_LOG_LEVEL`, `PARTICIPANT_ACTION_DAEMON_LOG_LEVEL`; replace with `SCHEDULER_LOG_LEVEL`
- `docs/` — any service name references

### In-Code Comments and Docstrings (accuracy — no test failures)

- `shared/schemas/events.py` — docstrings on `GameStatusChangedEvent` and `ParticipantDroppedEvent`
- `shared/models/participant_action_schedule.py` — model docstring references `participant_action_daemon`
- `shared/models/game_status_schedule.py` — model docstring references `status_transition_daemon`
- `services/api/services/games.py` — comment about `participant_action_daemon` pg_notify wake-up
- `services/retry/__init__.py` — module comment referencing "notification and status transition daemons"
- `services/scheduler/generic_scheduler_daemon.py` — module docstring references "notification and status transition daemon implementations"
- `tests/integration/test_notification_daemon.py`, `tests/integration/test_status_transitions.py`, `tests/integration/test_participant_action_daemon.py`, `tests/integration/test_clone_confirmation_notification.py`, `tests/conftest.py` — class/method docstrings referencing old container names
