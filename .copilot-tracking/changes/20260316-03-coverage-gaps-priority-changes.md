<!-- markdownlint-disable-file -->

# Change Record: Coverage Gap Priority Improvements

Source plan: `.copilot-tracking/planning/plans/20260316-03-coverage-gaps-priority.plan.md`

## Summary

Fix a coverage-reporting bug that hides real test results, then add targeted unit and integration
tests for correctness-critical and security-critical code paths.

## Completed Tasks

### Phase 1: Fix Signal Test Coverage Bug

#### Task 1.1: Fix `test_signal_sets_shutdown_flag` to stop corrupting coverage

**File:** `tests/unit/services/scheduler/test_daemon_runner_run.py`

**Change:** Wrapped `sigterm_handler(signal.SIGTERM, None)` with a `patch` context that returns
`None` from `_coverage.Coverage.current()`, preventing the signal handler from calling
`cov.stop()` + `cov.save()` on the live pytest-cov instance.

**Root cause:** `daemon_runner._signal_handler` calls `_coverage.Coverage.current()` and, if a
coverage instance is active, stops and saves it. The test was invoking the handler outside the
`patch("signal.signal")` context but inside a real test run, so the handler saw the real coverage
instance. Because `test_signal_sets_shutdown_flag` is test #1232 in the fixed ordering (via
`-p no:randomly`), tests #1233–#1281+ (including all notification service tests) ran with no
active coverage measurement, producing the false 30% reading for `notification_service.py`.

## Pending Tasks

### Phase 2: High-Priority Unit Tests (P1–P5)

- [ ] Task 2.1: Add `get_current_user` error branch tests (`auth.py` → 100%)
- [ ] Task 2.2: Cover `status_transitions.py` invalid-input branches (→ 100%)
- [ ] Task 2.3: Cover `guild_queries.py` empty-input validation guards (→ 100%)
- [ ] Task 2.4: Cover `event_builders.py` TTL calculation branches (→ 100%)
- [ ] Task 2.5: Cover `generic_scheduler_daemon.py` error paths (→ ≥85%)

### Phase 3: Redis and Infrastructure Error Paths (P7–P9)

- [ ] Task 3.1: Cover `cache/client.py` exception branches (→ ≥90%)
- [ ] Task 3.2: Cover `guild_sync.py` refresh channel scenarios (→ ≥90%)
- [ ] Task 3.3: Cover `shared/discord/client.py` HTTP error branches (→ ≥95%)

### Phase 4: Integration Tests (P6, P10, P11)

- [ ] Task 4.1: Cover `services/api/routes/auth.py` error paths (→ ≥90%)
- [ ] Task 4.2: Cover `services/api/routes/games.py` error responses (→ ≥93%)
- [ ] Task 4.3: Cover `services/api/routes/templates.py` error paths (→ ≥93%)

### Phase 5: Utility and Minor Gap Fill (P12–P19)

- [ ] Task 5.1: Cover `shared/utils/timezone.py` functions (→ 100%)
- [ ] Task 5.2: Cover `shared/utils/discord.py` utility functions (→ ≥95%)
- [ ] Task 5.3: Cover `bot/utils/discord_format.py` error branches (→ ≥92%)
