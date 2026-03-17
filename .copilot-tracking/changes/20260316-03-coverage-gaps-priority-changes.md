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

### Phase 2: High-Priority Unit Tests (P1–P5)

- [x] Task 2.1: Add `get_current_user` error branch tests (`auth.py` → 100%)
- [x] Task 2.2: Cover `status_transitions.py` invalid-input branches (→ 100%)
- [x] Task 2.3: Cover `guild_queries.py` empty-input validation guards (→ 100%)
- [x] Task 2.4: Cover `event_builders.py` TTL calculation branches (→ 100%)
- [x] Task 2.5: Cover `generic_scheduler_daemon.py` error paths (→ ≥85%)

### Phase 3: Redis and Infrastructure Error Paths (P7–P9)

- [x] Task 3.1: Cover `cache/client.py` exception branches (→ ≥90%)
- [x] Task 3.2: Cover `guild_sync.py` refresh channel scenarios (→ ≥90%)
- [x] Task 3.3: Cover `shared/discord/client.py` HTTP error branches (→ ≥95%)

### Phase 4: Integration Tests (P6, P10, P11)

- [x] Task 4.1: Cover `services/api/routes/auth.py` error paths (→ ≥90%)
- [x] Task 4.2: Cover `services/api/routes/games.py` error responses (→ ≥93%)
- [x] Task 4.3: Cover `services/api/routes/templates.py` error paths (→ ≥93%)

### Phase 5: Utility and Minor Gap Fill (P12–P19)

- [x] Task 5.1: Cover `shared/utils/timezone.py` functions (→ 100%)
  - Already at 100% from prior phases; no new tests needed.
- [x] Task 5.2: Cover `shared/utils/discord.py` utility functions (→ ≥95%)
  - Already at 100% from prior phases; no new tests needed.
- [x] Task 5.3: Cover `bot/utils/discord_format.py` error branches (→ 100%)
  - Added `TestBuildAvatarUrl`, `TestFormatRulesSection`, `TestGetMemberDisplayInfo` classes to `tests/unit/services/bot/utils/test_discord_format.py`.
  - Covers `get_member_display_info` success, not-found, `DiscordAPIError`, `KeyError`, and unexpected exception paths; `_build_avatar_url` all avatar priority branches; `format_rules_section` None/empty/truncate branches.
- [x] Task 5.4: Cover `shared/messaging/sync_publisher.py` and `consumer.py` error paths (→ 100% each)
  - Added `TestSyncEventPublisherConnect` and `TestSyncEventPublisherClose` to `tests/unit/shared/messaging/test_sync_publisher.py`; covers reconnect-on-closed-channel and close() cleanup.
  - Added `TestEventConsumerConnect`, `TestEventConsumerRegisterHandler`, `TestEventConsumerProcessMessage`, `TestEventConsumerClose` to `tests/unit/shared/messaging/test_consumer.py`; covers full message lifecycle including handler exception and invalid JSON body.
- [x] Task 5.5: Cover `services/scheduler/postgres_listener.py` and `scheduler_daemon_wrapper.py` gaps
  - Added tests to `tests/unit/services/scheduler/test_postgres_listener.py`: channel re-listen on reconnect, `_execute_listen` RuntimeError, `wait_for_notification` RuntimeError, invalid JSON payload fallback, empty notifies after poll.
  - `postgres_listener.py` → 100%; `scheduler_daemon_wrapper.py` → 96.77% (`if __name__ == "__main__"` guard only remaining gap).
- [x] Task 5.6: Cover `shared/utils/discord_tokens.py` error paths (→ 100%)
  - Fixed `test_extract_bot_discord_id_with_padding` to use `"1234"` (encodes to `MTIzNA==`) so the padding-addition branch on line 56 is actually exercised.
  - Added `test_extract_bot_discord_id_non_utf8_bytes` to cover the `decode("utf-8")` failure path.

## Final Result

- Combined coverage (unit + integration): **95.16%** (target: ≥92%)
- All 1840 unit tests pass (4 xfailed as expected)
