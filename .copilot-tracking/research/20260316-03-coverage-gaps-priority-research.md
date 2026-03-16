<!-- markdownlint-disable-file -->

# Task Research Notes: Coverage Gap Priority Analysis

## Research Executed

### Coverage Data Collection

- `uv run coverage combine --keep coverage/*` → combined all 10 coverage files including `runner.integration` and `runner.e2e` (hidden-file bug from prior research already fixed)
- `uv run coverage report -m --sort=cover` → full report with missing line ranges; total **88.89%** (7255 stmts, 806 miss)

### File Analysis

Examined source code for all files with <86% coverage to understand what the uncovered lines represent:

- `services/api/dependencies/auth.py` (76%) — missing lines 69, 72, 79-84 are the four `raise HTTPException(401)` branches in `get_current_user`: no-cookie, session-not-found, token-expired, user-not-in-DB
- `services/api/routes/auth.py` (77%) — missing lines are error paths in `login`, `callback`, `refresh`, and `get_user_info`
- `services/api/routes/games.py` (83%) — missing lines are all error/permission branches across game CRUD and join/leave operations
- `shared/data_access/guild_queries.py` (75%) — **every** missing pair is a `raise ValueError` guard for empty `guild_id` or `game_id` (e.g., lines 62-63, 97-98, 129-130, etc.)
- `shared/utils/status_transitions.py` (74%) — missing: `ValueError`/`KeyError` handling in `is_valid_transition` and the `get_next_status` body lines 98-102
- `services/scheduler/generic_scheduler_daemon.py` (16%) — `connect()`, `_process_loop_iteration()`, `_get_next_due_item()`, `_process_item()`, `_cleanup()` nearly entirely untested
- `services/scheduler/event_builders.py` (42%) — `build_notification_event()` TTL calculation (lines 55-84) and `build_status_transition_event()` body (100-111) uncovered
- `shared/cache/client.py` (64%) — every operation's exception branch plus `connect()` failure path and the `SyncRedisClient` error branches
- `services/bot/guild_sync.py` (71%) — `_expand_rls_context_for_guilds()` (78-80) and `_refresh_guild_channels()` (195-252) entirely uncovered
- `shared/discord/client.py` (85%) — error-handling branches in ~17 async Discord API methods (HTTP 4xx/5xx, connection errors)
- `shared/utils/timezone.py` (41%) — all utility functions except `utcnow()`: `to_utc`, `to_unix_timestamp`, `from_unix_timestamp`, `to_iso_string`, `from_iso_string`
- `shared/utils/discord.py` (57%) — `format_user_mention`, `format_channel_mention`, `format_role_mention`, `has_permission`, `build_oauth_url` bodies; `DiscordPermissions` constants
- `services/bot/utils/discord_format.py` (70%) — `get_member_display_info` not-found/error branches, `_build_avatar_url` ValueError fallback, `format_game_status_emoji` unknown-status case
- `shared/messaging/sync_publisher.py` (75%) — `connect()` reconnection path, `publish()` serialize/delivery errors, `close()` error path
- `shared/messaging/consumer.py` (76%) — reconnect logic, error dispatch during message processing
- `services/scheduler/postgres_listener.py` (74%) — connection error paths and `wait_for_notification` edge cases
- `services/scheduler/scheduler_daemon_wrapper.py` (42%) — `main()` thread wiring and `_run_daemon` exception handler
- `shared/telemetry.py` (47%) — intentionally bypassed via `PYTEST_RUNNING` guard; OTel init code never runs in tests
- `services/scheduler/services/notification_service.py` (30% reported) — tests exist and pass at 100% in isolation; 30% in combined report is caused by `test_signal_sets_shutdown_flag` calling `cov.stop()` on the live pytest-cov instance before notification tests execute in the fixed ordering

### Code Search Results

- `grep -n "raise ValueError\|raise HTTPException" shared/data_access/guild_queries.py` → confirmed every uncovered pair is an empty-string guard
- `grep -n "raise HTTPException" services/api/dependencies/auth.py` → four auth guard conditions, none covered by existing tests
- `grep -n "class SchedulerDaemon\|def " services/scheduler/generic_scheduler_daemon.py` → seven methods, `__init__` only one covered

### Project Conventions

- Unit tests: `tests/unit/` — run locally, no external services
- Integration tests: `tests/integration/` — Docker stack without bot service; bot interactions mocked via `fake_discord_app`
- E2E tests: `tests/e2e/` — full Docker stack with live bot service; no mocks

---

## Key Discoveries

### notification_service.py Coverage Discrepancy — Root Cause

Tests in `tests/unit/services/scheduler/test_notification_service.py` pass at 100% in isolation but show 30% in the combined report. The data is **not stale** — it is current from the latest run. The cause is a bug in `test_daemon_runner_run.py::TestRunDaemon::test_signal_sets_shutdown_flag`.

That test captures the SIGTERM handler while `signal.signal` is patched, but then calls the handler **after** the `patch` context exits. At that point `_coverage.Coverage.current()` returns the real pytest-cov instance. The handler calls `cov.stop()` + `cov.save()`, which halts coverage measurement for all tests that follow in the fixed (`-p no:randomly`) ordering used by `coverage-report.sh`.

`test_signal_sets_shutdown_flag` is test #1232 in the fixed order; the notification service tests start at #1281 — they run after coverage is already stopped, so their execution never lands in `coverage/unit`.

The covered lines for `notification_service.py` in the unit data file are `[22, 24, 25, 27, 28, 30, 33, 34, 36, 40, 42, 43, 44, 104]` — only the import/class-definition/`def` signature lines. The method bodies are never measured because coverage is off.

**Fix required:** In `test_signal_sets_shutdown_flag`, the call to the captured handler must happen while `Coverage.current` is patched to return `None` (or a mock), so the real coverage instance is never touched. The simplest fix:

```python
def test_signal_sets_shutdown_flag(self, mock_flush):
    ...
    with patch("services.scheduler.daemon_runner._coverage.Coverage.current", return_value=None):
        sigterm_handler(signal.SIGTERM, None)

    assert captured_handler["fn"]() is True
```

### Guild Queries Validation Pattern

Every uncovered line in `guild_queries.py` follows this pattern:

```python
if not guild_id:
    msg = "guild_id cannot be empty"
    raise ValueError(msg)
```

These guards exist on every query function and prevent empty strings from being used as RLS context. Tested only via unit parametrization over all query functions.

### SchedulerDaemon Architecture

`SchedulerDaemon` is a synchronous class (not async) that uses `psycopg2` blocking connections and `pika` blocking AMQP. All its dependencies (`PostgresNotificationListener`, `SyncEventPublisher`, `SyncSessionLocal`) are fully mockable. The `connect()` and `run()` paths are already exercised by integration tests but that coverage doesn't appear in the combined unit data because it lands in `scheduler.integration`.

### `_refresh_guild_channels` gap

This function handles all three channel sync scenarios (new channel, reactivate, deactivate) but exists entirely within the 71%-covered `guild_sync.py`. It was added when channel refresh was separated from initial guild creation. E2E tests exercise `sync_all_bot_guilds` at startup but not the refresh code path.

---

## Recommended Approach

### Prioritized Coverage Gap Table

Ordered by value to codebase quality and correctness, not by ease of coverage gain.

| Priority | Module / Routine                                                                                            | Current %                    | Miss | Test Type   | Notes                                                                                                                                                                                                                                                                                                                                                                                |
| -------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------- | ---- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1        | `services/api/dependencies/auth.py` — `get_current_user` error branches                                     | 76%                          | 6    | Unit        | Four `401 Unauthorized` paths: no session cookie, session not in Redis, token expired, user not in DB. These guard every authenticated endpoint. Small file, straightforward to mock `tokens.*` and `db.execute`.                                                                                                                                                                    |
| 2        | `shared/utils/status_transitions.py` — `is_valid_transition` invalid-input branches, `get_next_status` body | 74%                          | 7    | Unit        | State machine for game lifecycle. `ValueError`/`KeyError` branch in `is_valid_transition` (called with garbage status strings) and the `get_next_status` body are untested. Bugs here allow illegal transitions to silently succeed or crash.                                                                                                                                        |
| 3        | `shared/data_access/guild_queries.py` — empty-input validation branches                                     | 75%                          | 44   | Unit        | Every query function has an empty-string guard for `guild_id`/`game_id`. Untested validation means the guards could be removed or changed without detection. Parametrize a single test over all functions.                                                                                                                                                                           |
| 4        | `services/scheduler/event_builders.py` — `build_notification_event` TTL calculation                         | 42%                          | 14   | Unit        | Three TTL branches: `game_scheduled_at is None` (no TTL), game already started (minimal TTL), game >1 min away (calculated TTL). Wrong TTL causes silent notification loss. Pure functions, no mocks needed.                                                                                                                                                                         |
| 5        | `services/scheduler/generic_scheduler_daemon.py` — all methods                                              | 16%                          | 102  | Unit        | `connect()`, `_process_loop_iteration()`, `_get_next_due_item()`, `_process_item()`, `_cleanup()` are the core scheduling engine. Mock `PostgresNotificationListener`, `SyncEventPublisher`, `SyncSessionLocal`. Integration tests cover the happy path; unit tests needed for error paths: DB query failure + session recreation, publish failure + rollback, listener close error. |
| 6        | `services/api/routes/auth.py` — error paths in all five endpoints                                           | 77%                          | 21   | Integration | OAuth URL generation failure (login), maintainer-check exception (callback), refresh-token not found (refresh), session-expired + fetch failure (get_user_info). All return specific HTTP status codes; integration tests with mocked OAuth2 verify correct codes.                                                                                                                   |
| 7        | `shared/cache/client.py` — all error paths in `RedisClient` and `SyncRedisClient`                           | 64%                          | 48   | Unit        | `connect()` failure raises and logs, each operation (`get`, `set`, `delete`, `exists`, `expire`, `ttl`) returns sentinel on exception, JSON decode error in `get_json`. Bot auth session caching uses this; silent failures mask auth issues. Mock `redis.asyncio.Redis` and `redis.Redis`.                                                                                          |
| 8        | `services/bot/guild_sync.py` — `_refresh_guild_channels`, `_expand_rls_context_for_guilds`                  | 71%                          | 26   | Unit        | `_refresh_guild_channels` handles new/reactivate/deactivate channel scenarios; entirely unexercised. `_expand_rls_context_for_guilds` sets SQL context for multi-guild operations. Mock `AsyncSession` and `DiscordAPIClient`. E2E for startup exists; unit tests for refresh scenarios cover correctness.                                                                           |
| 9        | `shared/discord/client.py` — HTTP error branches                                                            | 85%                          | 47   | Unit        | ~17 async Discord API methods each have uncovered error branches. Mock `aiohttp.ClientSession` to return 403, 404, 500 responses and verify `DiscordAPIError` is raised with correct status codes. The client is used by both bot and guild_sync.                                                                                                                                    |
| 10       | `services/api/routes/games.py` — error responses                                                            | 83%                          | 43   | Integration | Missing: 403/404/422 paths for game create (permission denied, minimum-players violation), game update (not-found, forbidden), game delete (not-found), clone/join/leave error paths. Integration tests with mocked Discord verify correct HTTP status codes.                                                                                                                        |
| 11       | `services/api/routes/templates.py` — error paths                                                            | 83%                          | 18   | Integration | Update/delete/reorder failure cases. Lower priority than games.py since templates are less frequently exercised and errors are less user-visible.                                                                                                                                                                                                                                    |
| 12       | `shared/utils/timezone.py` — all functions                                                                  | 41%                          | 10   | Unit        | Pure functions with zero dependencies. `to_utc` for naive/aware inputs, `to_unix_timestamp`, `from_unix_timestamp`, `to_iso_string`, `from_iso_string`. Datetime conversion bugs are subtle and hard to diagnose.                                                                                                                                                                    |
| 13       | `shared/utils/discord.py` — utility functions                                                               | 57%                          | 12   | Unit        | `format_user_mention`, `format_channel_mention`, `format_role_mention`, `has_permission`, `build_oauth_url`. All pure. `parse_mention` edge cases (non-ID content, `<@!>` format).                                                                                                                                                                                                   |
| 14       | `shared/messaging/sync_publisher.py` — error paths                                                          | 75%                          | 14   | Unit        | `connect()` reconnect on existing-open connection, `publish()` serialization and delivery errors.                                                                                                                                                                                                                                                                                    |
| 15       | `services/bot/utils/discord_format.py` — error branches                                                     | 70%                          | 22   | Unit        | `get_member_display_info` not-found/API-error/parse-error returns, `_build_avatar_url` fallback to default index on `ValueError`, `format_game_status_emoji` unknown status.                                                                                                                                                                                                         |
| 16       | `shared/messaging/consumer.py` — error paths                                                                | 76%                          | 18   | Unit        | Reconnect logic, exception dispatch during message handling.                                                                                                                                                                                                                                                                                                                         |
| 17       | `services/scheduler/postgres_listener.py` — error paths                                                     | 74%                          | 16   | Unit        | Connection error paths, notification parsing errors. An existing test file exists but doesn't cover these branches.                                                                                                                                                                                                                                                                  |
| 18       | `services/scheduler/scheduler_daemon_wrapper.py` — `main()`                                                 | 42%                          | 18   | Unit        | Thread creation wiring. `_run_daemon` exception handler is uncovered. Mock `SchedulerDaemon` and `threading.Thread`. Lower priority than the daemon itself since this is mostly wiring.                                                                                                                                                                                              |
| 19       | `shared/utils/discord_tokens.py` — error branches                                                           | 72%                          | 5    | Unit        | `extract_bot_id`: invalid-format path and base64 decode failure. Security-adjacent but not on the critical auth path.                                                                                                                                                                                                                                                                |
| 20       | `shared/telemetry.py` — OTel init code                                                                      | 47%                          | 31   | —           | Intentionally skipped via `PYTEST_RUNNING` env guard. Testing the production path requires a live OTLP endpoint. No meaningful unit test available; coverage gap is by design.                                                                                                                                                                                                       |
| —        | `services/scheduler/services/notification_service.py`                                                       | 30% (affected by signal bug) | —    | —           | Tests exist and pass at 100% in isolation. Coverage is cut short by `test_signal_sets_shutdown_flag` stopping the coverage instance mid-run. Fix that test to restore correct reporting.                                                                                                                                                                                             |
| —        | `services/scheduler/config.py`, `shared/database_objects.py`, `shared/setup.py`                             | 0%                           | —    | —           | Configuration constants and packaging metadata. No logic to test.                                                                                                                                                                                                                                                                                                                    |

---

## Implementation Guidance

- **Objectives**: Improve test quality on correctness-critical and security-critical paths, not just coverage breadth
- **Key Tasks**:
  1. Fix stale `notification_service.py` coverage by re-running full report after confirming test file exists
  2. Add unit tests for Priority 1–5 (auth dependency, status transitions, guild query validation, event builder TTL, scheduler daemon methods)
  3. Add integration tests for Priority 6, 10, 11 (auth routes, games route errors, templates errors)
  4. Add unit tests for Priority 7–9 (Redis client errors, guild sync refresh, Discord client HTTP errors)
  5. Fill remaining utility function gaps (Priority 12–19) as low-effort improvements
- **Dependencies**: Priorities 1–5 and 7–9 are all independent unit tests; no inter-dependencies
- **Success Criteria**:
  - `services/api/dependencies/auth.py` → 100%
  - `shared/utils/status_transitions.py` → 100%
  - `shared/data_access/guild_queries.py` → 100%
  - `services/scheduler/event_builders.py` → 100%
  - `services/scheduler/generic_scheduler_daemon.py` → ≥85%
  - Combined total → ≥92%
