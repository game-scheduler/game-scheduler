<!-- markdownlint-disable-file -->

# Task Details: Coverage Gap Priority Improvements

## Research Reference

**Source Research**: #file:../research/20260316-03-coverage-gaps-priority-research.md

---

## Phase 1: Fix Signal Test Coverage Bug

### Task 1.1: Fix `test_signal_sets_shutdown_flag` to Stop Corrupting Coverage

`test_signal_sets_shutdown_flag` in `test_daemon_runner_run.py` captures the SIGTERM handler while
`signal.signal` is patched, then calls it after the patch exits. At that point `_coverage.Coverage.current()`
returns the real pytest-cov instance; the handler calls `cov.stop()` + `cov.save()`, halting coverage
measurement for all tests that follow in the fixed run order. `notification_service.py` tests start after
test #1232 in the fixed order and so land without active measurement, producing the spurious 30% report.

Patch `_coverage.Coverage.current` to return `None` inside the handler call so the real coverage instance
is never touched.

- **File**:
  - `tests/unit/services/scheduler/test_daemon_runner_run.py` — add `patch("services.scheduler.daemon_runner._coverage.Coverage.current", return_value=None)` context around the `sigterm_handler(signal.SIGTERM, None)` call in `test_signal_sets_shutdown_flag`
- **Success**:
  - `uv run coverage report -m` for `services/scheduler/services/notification_service.py` reports ≥95%
  - `test_signal_sets_shutdown_flag` still passes
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 50-90) — root cause analysis and fix code example
- **Dependencies**:
  - None; this is a standalone test fix

---

## Phase 2: High-Priority Unit Tests (P1–P5)

### Task 2.1: Add `get_current_user` Error Branch Tests

`services/api/dependencies/auth.py` `get_current_user` has four uncovered `401 Unauthorized` branches:
no session cookie present, session not found in Redis, JWT token expired, and user not found in DB.
Each branch raises `HTTPException(status_code=401)`. Mock `tokens.*` and `db.execute` via
`AsyncMock`/`MagicMock` to trigger each path. Add tests to the existing auth dependencies test file or
create `tests/unit/services/api/dependencies/test_auth_dependency.py` if none is suitable.

- **Files**:
  - `tests/unit/services/api/dependencies/test_auth_dependency.py` — new file, or extend `test_api_permissions.py` if auth.py is already imported there
  - `services/api/dependencies/auth.py` — source under test (read-only)
- **Success**:
  - `services/api/dependencies/auth.py` coverage reaches 100%
  - Four new test cases: `test_get_current_user_no_cookie`, `test_get_current_user_session_not_found`, `test_get_current_user_token_expired`, `test_get_current_user_user_not_in_db`
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 15-18) — identifies the four missing branches and their line numbers
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 113-114) — priority 1 entry, mocking guidance
- **Dependencies**:
  - Phase 1 should be complete first to get accurate baseline coverage numbers

### Task 2.2: Cover `status_transitions.py` Invalid-Input Branches

`shared/utils/status_transitions.py` `is_valid_transition` has an uncovered `ValueError`/`KeyError`
branch triggered by garbage status strings, and `get_next_status` body (lines 98-102) is entirely
uncovered. Add parametrized tests for invalid status strings and for each valid next-status scenario.

- **Files**:
  - `tests/unit/shared/utils/test_utils_status_transitions.py` — add test cases to existing file
  - `shared/utils/status_transitions.py` — source under test (read-only)
- **Success**:
  - `shared/utils/status_transitions.py` coverage reaches 100%
  - Tests cover: `is_valid_transition` with unknown status strings, `get_next_status` for each legal current status
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 20-21) — identifies missing lines 98-102
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 116-117) — priority 2 entry
- **Dependencies**:
  - None; pure-function tests, no mocks needed

### Task 2.3: Cover `guild_queries.py` Empty-Input Validation Guards

Every query function in `shared/data_access/guild_queries.py` has an empty-string guard for `guild_id`
and/or `game_id` (e.g., lines 62-63, 97-98, 129-130). All guards raise `ValueError`. Use a single
parametrized test that calls each query function with an empty string and asserts `ValueError` is raised.

- **Files**:
  - `tests/unit/shared/data_access/test_guild_queries_unit.py` — add parametrized test to existing file
  - `shared/data_access/guild_queries.py` — source under test (read-only)
- **Success**:
  - `shared/data_access/guild_queries.py` coverage reaches 100%
  - One parametrized test covers all empty-input guards across all query functions
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 22-23) — confirms missing lines follow empty-guard pattern
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 79-86) — guild queries validation pattern section
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 118-119) — priority 3 entry
- **Dependencies**:
  - None; guards are pure validation before any DB call

### Task 2.4: Cover `event_builders.py` TTL Calculation Branches

`services/scheduler/event_builders.py` `build_notification_event` has three TTL branches (lines 55-84):
`game_scheduled_at is None` (no TTL set), game already started (minimal TTL applied), game >1 min away
(calculated TTL). `build_status_transition_event` body (lines 100-111) is also entirely uncovered.
All are pure functions — no mocks needed beyond constructing appropriate input objects.

- **Files**:
  - `tests/unit/services/scheduler/test_event_builders.py` — add test cases to existing file
  - `services/scheduler/event_builders.py` — source under test (read-only)
- **Success**:
  - `services/scheduler/event_builders.py` coverage reaches 100%
  - Three TTL branch tests for `build_notification_event`; at least one test for `build_status_transition_event`
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 26-27) — identifies missing line ranges 55-84 and 100-111
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 120-121) — priority 4 entry, TTL branch descriptions
- **Dependencies**:
  - None; pure functions

### Task 2.5: Cover `generic_scheduler_daemon.py` Error Paths

`services/scheduler/generic_scheduler_daemon.py` is only 16% covered — `connect()`, `_process_loop_iteration()`,
`_get_next_due_item()`, `_process_item()`, `_cleanup()` are nearly untested. Mock
`PostgresNotificationListener`, `SyncEventPublisher`, and `SyncSessionLocal`. Priority error paths:
DB query failure with session recreation, publish failure with rollback, listener close error during
cleanup. Integration tests cover the happy path; unit tests must cover the error branches.

- **Files**:
  - `tests/unit/services/scheduler/test_generic_scheduler_daemon.py` — add test cases to existing file
  - `services/scheduler/generic_scheduler_daemon.py` — source under test (read-only)
- **Success**:
  - `services/scheduler/generic_scheduler_daemon.py` coverage reaches ≥85%
  - Error path coverage: `connect()` failure, `_get_next_due_item()` DB exception, `_process_item()` publish failure + rollback, `_cleanup()` listener close error
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 28-30) — lists seven methods with only `__init__` covered
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 88-96) — SchedulerDaemon architecture and mockable dependencies
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 122-123) — priority 5 entry with mocking guidance
- **Dependencies**:
  - Phase 1 fix helps validate coverage numbers are accurate before targeting 85%

---

## Phase 3: Redis and Infrastructure Error Paths (P7–P9)

### Task 3.1: Cover `cache/client.py` Error Branches

`shared/cache/client.py` is at 64% — every operation's exception branch plus `connect()` failure path
and `SyncRedisClient` error branches are uncovered. Mock `redis.asyncio.Redis` and `redis.Redis` to
raise `redis.RedisError` in each operation (`get`, `set`, `delete`, `exists`, `expire`, `ttl`);
verify sentinel return values. Also test JSON decode error in `get_json` and `connect()` raising
on failure.

- **Files**:
  - `tests/unit/shared/cache/test_cache_client.py` — add error-path test cases to existing file
  - `shared/cache/client.py` — source under test (read-only)
- **Success**:
  - `shared/cache/client.py` coverage reaches ≥90%
  - All async and sync operation error branches covered; `connect()` failure; JSON decode error
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 31-32) — identifies exception branches in every operation
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 128-130) — priority 7 entry with mocking guidance
- **Dependencies**:
  - None; mock-based, no external services

### Task 3.2: Cover `guild_sync.py` Refresh Channel Scenarios

`services/bot/guild_sync.py` `_refresh_guild_channels` (lines 195-252) handles new channel, reactivate,
and deactivate scenarios — entirely uncovered. `_expand_rls_context_for_guilds` (lines 78-80) also
uncovered. Mock `AsyncSession` and `DiscordAPIClient`. Test the three channel scenarios independently:
existing-channel-becomes-active, existing-channel-becomes-inactive, brand-new-channel-registration.

- **Files**:
  - `tests/unit/services/bot/test_guild_sync.py` — add test cases to existing file
  - `services/bot/guild_sync.py` — source under test (read-only)
- **Success**:
  - `services/bot/guild_sync.py` coverage reaches ≥90%
  - Three channel scenario tests; `_expand_rls_context_for_guilds` covered
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 33-34) — identifies the two uncovered functions
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 98-103) — \_refresh_guild_channels gap section
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 131-133) — priority 8 entry
- **Dependencies**:
  - None; mock-based unit tests

### Task 3.3: Cover `shared/discord/client.py` HTTP Error Branches

`shared/discord/client.py` is at 85% — ~17 async Discord API methods each have uncovered error branches.
Mock `aiohttp.ClientSession` to return 403, 404, and 500 responses; verify `DiscordAPIError` is raised
with correct status codes. Also cover connection error (`aiohttp.ClientError`) paths.

- **Files**:
  - `tests/unit/shared/discord/test_discord_api_client.py` — add error-branch test cases to existing file
  - `shared/discord/client.py` — source under test (read-only)
- **Success**:
  - `shared/discord/client.py` coverage reaches ≥95%
  - HTTP 4xx/5xx error branches covered; connection error branch covered
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 35-36) — identifies ~17 methods with uncovered error branches
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 134-136) — priority 9 entry with mocking guidance
- **Dependencies**:
  - None; mock-based unit tests

---

## Phase 4: Integration Tests (P6, P10, P11)

### Task 4.1: Cover `services/api/routes/auth.py` Error Paths

`services/api/routes/auth.py` is at 77% — error paths in `login`, `callback`, `refresh`, and
`get_user_info` are uncovered. These return specific HTTP status codes (400, 401, 403, 500) and must
be verified with integration tests that use the mocked OAuth2 setup already in place. Add test cases
for: OAuth URL generation failure (login), maintainer-check exception (callback), refresh-token not
found (refresh), session-expired + fetch failure (get_user_info).

- **Files**:
  - `tests/integration/` — identify or create appropriate auth error test file
  - `services/api/routes/auth.py` — source under test (read-only)
- **Success**:
  - `services/api/routes/auth.py` coverage reaches ≥90%
  - Correct HTTP status codes verified for each error path
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 19-20) — identifies error paths in all five endpoints
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 124-126) — priority 6 entry, integration test type confirmed
- **Dependencies**:
  - Running integration test infrastructure (`scripts/run-integration-tests.sh`)

### Task 4.2: Cover `services/api/routes/games.py` Error Responses

`services/api/routes/games.py` is at 83% with 43 missing lines — 403/404/422 paths for game CRUD,
join/leave operations. Add integration tests for: permission-denied on create (non-maintainer),
minimum-players violation on create, game-not-found on update/delete, forbidden update (non-owner),
join/leave error paths (already joined, game full, game closed).

- **Files**:
  - `tests/integration/` — identify or create appropriate games error test file
  - `services/api/routes/games.py` — source under test (read-only)
- **Success**:
  - `services/api/routes/games.py` coverage reaches ≥93%
  - 403, 404, and 422 responses verified for each identified scenario
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 25-26) — identifies 403/404/422 paths and join/leave errors
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 141-143) — priority 10 entry
- **Dependencies**:
  - Running integration test infrastructure

### Task 4.3: Cover `services/api/routes/templates.py` Error Paths

`services/api/routes/templates.py` is at 83% with 18 missing lines — update/delete/reorder failure
cases. Add integration tests for: template not found (404), forbidden update/delete (403), reorder
with invalid order values (422).

- **Files**:
  - `tests/integration/` — identify or create appropriate templates error test file
  - `services/api/routes/templates.py` — source under test (read-only)
- **Success**:
  - `services/api/routes/templates.py` coverage reaches ≥93%
  - 403, 404, 422 responses verified for each scenario
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 144-146) — priority 11 entry
- **Dependencies**:
  - Running integration test infrastructure

---

## Phase 5: Utility and Minor Gap Fill (P12–P19)

### Task 5.1: Cover `shared/utils/timezone.py` Functions

`shared/utils/timezone.py` is at 41% — all utility functions except `utcnow()` are uncovered. These
are pure functions with zero dependencies. Test: `to_utc` for both naive and aware datetime inputs,
`to_unix_timestamp`, `from_unix_timestamp`, `to_iso_string`, `from_iso_string`.

- **Files**:
  - `tests/unit/shared/utils/test_timezone.py` — add test cases to existing file
  - `shared/utils/timezone.py` — source under test (read-only)
- **Success**:
  - `shared/utils/timezone.py` coverage reaches 100%
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 38-39) — identifies all uncovered functions
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 148-149) — priority 12 entry
- **Dependencies**:
  - None; pure functions

### Task 5.2: Cover `shared/utils/discord.py` Utility Functions

`shared/utils/discord.py` is at 57% — `format_user_mention`, `format_channel_mention`,
`format_role_mention`, `has_permission`, `build_oauth_url`, and `DiscordPermissions` constants are
uncovered. All pure functions. Also cover `parse_mention` edge cases (non-ID content, `<@!>` format).

- **Files**:
  - `tests/unit/shared/utils/test_discord_utils.py` — add test cases to existing file
  - `shared/utils/discord.py` — source under test (read-only)
- **Success**:
  - `shared/utils/discord.py` coverage reaches ≥95%
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 40-41) — lists all uncovered functions
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 150-152) — priority 13 entry
- **Dependencies**:
  - None; pure functions

### Task 5.3: Cover `bot/utils/discord_format.py` Error Branches

`services/bot/utils/discord_format.py` is at 70% — `get_member_display_info` not-found/API-error/parse-error
returns, `_build_avatar_url` fallback to default index on `ValueError`, `format_game_status_emoji`
unknown-status case are uncovered.

- **Files**:
  - `tests/unit/services/bot/utils/test_discord_format.py` — add test cases to existing file
  - `services/bot/utils/discord_format.py` — source under test (read-only)
- **Success**:
  - `services/bot/utils/discord_format.py` coverage reaches ≥92%
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 42-43) — identifies three uncovered branches
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 154-155) — priority 15 entry
- **Dependencies**:
  - None; mock Discord API responses as needed

### Task 5.4: Cover `shared/messaging/sync_publisher.py` and `consumer.py` Errors

`shared/messaging/sync_publisher.py` (75%): cover `connect()` reconnect on already-open connection,
`publish()` serialization and delivery errors. `shared/messaging/consumer.py` (76%): cover reconnect
logic and exception dispatch during message handling. Both use pika; mock `pika.BlockingConnection`.

- **Files**:
  - `tests/unit/shared/messaging/test_sync_publisher.py` — add error-path test cases to existing file
  - `tests/unit/shared/messaging/test_consumer.py` — add error-path test cases to existing file
- **Success**:
  - `shared/messaging/sync_publisher.py` coverage reaches ≥93%
  - `shared/messaging/consumer.py` coverage reaches ≥93%
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 44-45) — sync_publisher missing paths
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 46-47) — consumer missing paths
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 156-160) — priority 14 and 16 entries
- **Dependencies**:
  - None; mock pika

### Task 5.5: Cover `postgres_listener.py` and `scheduler_daemon_wrapper.py` Gaps

`services/scheduler/postgres_listener.py` (74%): add connection error paths and notification parsing
edge cases to the existing test file. `services/scheduler/scheduler_daemon_wrapper.py` (42%): cover
thread creation wiring in `main()` and the `_run_daemon` exception handler via mocked `SchedulerDaemon`
and `threading.Thread`.

- **Files**:
  - `tests/unit/services/scheduler/test_postgres_listener.py` — add error-path tests to existing file
  - `tests/unit/services/scheduler/test_scheduler_daemon_wrapper.py` — add tests to existing file
- **Success**:
  - `services/scheduler/postgres_listener.py` coverage reaches ≥92%
  - `services/scheduler/scheduler_daemon_wrapper.py` coverage reaches ≥80%
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 48-50) — identifies connection and parsing error paths
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 161-165) — priority 17 and 18 entries
- **Dependencies**:
  - None; mock-based

### Task 5.6: Cover `shared/utils/discord_tokens.py` Error Paths

`shared/utils/discord_tokens.py` (72%): `extract_bot_id` invalid-format path and base64 decode failure
are uncovered. Add two test cases to the existing test file.

- **Files**:
  - `tests/unit/shared/utils/test_discord_tokens.py` — add two test cases to existing file
  - `shared/utils/discord_tokens.py` — source under test (read-only)
- **Success**:
  - `shared/utils/discord_tokens.py` coverage reaches 100%
- **Research References**:
  - #file:../research/20260316-03-coverage-gaps-priority-research.md (Lines 166-167) — priority 19 entry
- **Dependencies**:
  - None; pure function with no external dependencies

---

## Dependencies

- `uv` for running tests and coverage
- `pytest` with `pytest-cov` for coverage measurement
- `scripts/run-integration-tests.sh` for Phase 4
- `scripts/coverage-report.sh` to validate final combined coverage numbers
- All mock libraries already in project (`unittest.mock`, `pytest-mock`)

## Success Criteria

- `services/api/dependencies/auth.py` → 100%
- `shared/utils/status_transitions.py` → 100%
- `shared/data_access/guild_queries.py` → 100%
- `services/scheduler/event_builders.py` → 100%
- `services/scheduler/generic_scheduler_daemon.py` → ≥85%
- `services/scheduler/services/notification_service.py` → ≥95% (restored by Phase 1 fix)
- Combined total project coverage → ≥92%
