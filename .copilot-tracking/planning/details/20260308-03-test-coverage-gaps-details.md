<!-- markdownlint-disable-file -->

# Task Details: Test Coverage Gaps

## Research Reference

**Source Research**: #file:../research/20260308-03-test-coverage-gaps-research.md

---

## Phase 1: Bot Handler E2E/Integration Tests (Priorities 1–3)

### Task 1.1: Write e2e/integration tests for `button_handler.py` (lines 55–78)

The uncovered lines in `services/bot/handlers/button_handler.py` (lines 55–78) are the
handler dispatch paths that route button-interaction payloads to the join/leave handlers.
The research identifies this as Priority 1 because it is the gateway for all interactive
join/leave flows. Tests must drive real Discord button interactions in the e2e suite or
simulate them via direct handler invocation in integration tests.

- **Files**:
  - `services/bot/handlers/button_handler.py` — source under test (lines 55–78)
  - `tests/e2e/test_button_handler.py` — new or extended e2e test file
- **Test scenarios**:
  - Button interaction for an open game triggers join flow
  - Button interaction for a full game returns the correct user-facing response
  - Button interaction with an unrecognised custom-id is handled gracefully
  - Button interaction from a user already in the game returns the correct response
- **Success**:
  - Lines 55–78 of `button_handler.py` reach 100% coverage in the e2e run
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-206) — prioritized
    gap table and exact missing-line ranges
- **Dependencies**:
  - Existing e2e infrastructure (Docker compose, `tests/e2e/conftest.py`)

### Task 1.2: Write e2e/integration tests for `join_game.py` (lines 63–118, 143–162)

The uncovered lines in `services/bot/handlers/join_game.py` represent the core join flow:
UUID parse → DB write → publish `game_updated` event (research: Priority 2, 42 missed stmts).
End-to-end tests covering a Discord user joining a game exercise this path; integration tests
that directly invoke the handler with a mock interaction object cover the remaining error paths.

- **Files**:
  - `services/bot/handlers/join_game.py` — source under test (lines 63–118, 143–162)
  - `tests/e2e/test_join_game.py` — new or extended e2e test file
  - `tests/integration/test_join_game.py` — new or extended integration test file (error paths)
- **Test scenarios**:
  - Successful join: Discord user joins an open game; DB participant row created; event published
  - Join attempt on a game that is full returns user-facing error
  - Join attempt with malformed UUID in the interaction payload returns error
  - Join attempt by a user already registered for the game returns duplicate-registration error
  - DB write failure propagates correct error response (integration, mock DB)
  - Event publish failure is handled gracefully (integration, mock event bus)
- **Success**:
  - Lines 63–118 and 143–162 of `join_game.py` show measurable coverage increase
  - All new tests pass in both e2e and integration suites
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-206) — gap table and missing lines
- **Dependencies**:
  - Task 1.1 complete (button_handler routes to join_game)
  - Existing e2e game fixtures that create joinable games

### Task 1.3: Write e2e/integration tests for `leave_game.py` (lines 59–93, 116–143)

The uncovered lines in `services/bot/handlers/leave_game.py` mirror the join flow but for
deletion: delete participant row → publish `game_updated` event (research: Priority 3, 37 missed
stmts). Same testing strategy as Task 1.2.

- **Files**:
  - `services/bot/handlers/leave_game.py` — source under test (lines 59–93, 116–143)
  - `tests/e2e/test_leave_game.py` — new or extended e2e test file
  - `tests/integration/test_leave_game.py` — new or extended integration test file (error paths)
- **Test scenarios**:
  - Successful leave: registered user leaves a game; participant row deleted; event published
  - Leave attempt by a user not registered for the game returns user-facing error
  - Leave attempt on a game that has already started / closed returns relevant error
  - DB delete failure propagates correct error response (integration, mock DB)
- **Success**:
  - Lines 59–93 and 116–143 of `leave_game.py` show measurable coverage increase
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-206) — gap table and missing lines
- **Dependencies**:
  - Task 1.1 complete
  - Existing e2e fixtures that register a user for a game

---

## Phase 2: Bot Auth and Utility Unit Tests (Priorities 4, 7, 9)

### Task 2.1: Write unit tests for `role_checker.py` (lines 85–86, 96–101, 117–206)

The uncovered lines in `services/bot/auth/role_checker.py` (28 missed stmts) are the Discord
API error paths — `NotFound` and `Forbidden` exceptions raised when checking member roles
(research: Priority 4, security impact). Unit tests with mocked Discord API calls are the
appropriate test type.

- **Files**:
  - `services/bot/auth/role_checker.py` — source under test (lines 85–86, 96–101, 117–206)
  - `tests/unit/bot/auth/test_role_checker.py` — new or extended unit test file
- **Test scenarios**:
  - `NotFound` raised by Discord API → correct fallback / denial behaviour (lines 85–86)
  - `Forbidden` raised by Discord API → correct error handling (lines 96–101)
  - All branches in the large block lines 117–206: member has role, member lacks role,
    guild not found, multiple roles checked in sequence
- **Success**:
  - Lines 85–86, 96–101, and 117–206 fully covered
  - All new tests pass in the unit suite
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-206) — gap table
- **Dependencies**:
  - `discord.py` mock patterns used in existing unit tests

### Task 2.2: Write unit tests for `utils.py` (lines 78–81, 91–94)

The 8 uncovered lines in `services/bot/handlers/utils.py` are error return paths shared by
all handlers (research: Priority 7). These can be exercised with simple unit tests that pass
invalid/error-triggering inputs.

- **Files**:
  - `services/bot/handlers/utils.py` — source under test (lines 78–81, 91–94)
  - `tests/unit/bot/handlers/test_utils.py` — new or extended unit test file
- **Test scenarios**:
  - Function producing error path at lines 78–81 is called with an input that triggers it
  - Function producing error path at lines 91–94 is called with an input that triggers it
- **Success**:
  - Lines 78–81 and 91–94 of `utils.py` fully covered
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-206) — gap table and missing lines
- **Dependencies**:
  - None beyond existing unit test infrastructure

### Task 2.3: Write unit tests for `cache.py` (lines 51, 140–142, 158–159)

The 6 uncovered lines in `services/bot/auth/cache.py` are Redis error and expiry paths
(research: Priority 9). Unit tests with a mocked Redis client exercise these paths without
needing a real Redis connection.

- **Files**:
  - `services/bot/auth/cache.py` — source under test (lines 51, 140–142, 158–159)
  - `tests/unit/bot/auth/test_cache.py` — new or extended unit test file
- **Test scenarios**:
  - Redis raises an exception on `get` → line 51 error path executed
  - TTL expiry path at lines 140–142 triggered by simulating an expired key
  - Error path at lines 158–159 triggered by the appropriate Redis error condition
- **Success**:
  - Lines 51, 140–142, and 158–159 of `cache.py` fully covered
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-206) — gap table and missing lines
- **Dependencies**:
  - Existing Redis mock patterns in unit tests

---

## Phase 3: API Route Integration Tests (Priorities 5, 6, 8)

### Task 3.1: Write integration tests for `channels.py` (lines 73–84, 104–118, 137)

The entirely uncovered lines in `services/api/routes/channels.py` are the
`create_channel_config` and `update_channel_config` request bodies (research: Priority 5,
11 missed stmts). Integration tests using `httpx.AsyncClient` against the real API service
(existing pattern in `tests/integration/conftest.py`) are the appropriate type.

- **Files**:
  - `services/api/routes/channels.py` — source under test (lines 73–84, 104–118, 137)
  - `tests/integration/test_channels.py` — new or extended integration test file
- **Test scenarios**:
  - `POST /channels/{id}/config` with a valid payload creates the config → lines 73–84
  - `PUT /channels/{id}/config` with a valid payload updates the config → lines 104–118
  - `POST` or `PUT` with a missing required field returns 422 → line 137 (validation path)
  - Attempt to create/update config for a channel that does not belong to the actor's guild
    returns 403/404
- **Success**:
  - Lines 73–84, 104–118, and 137 of `channels.py` fully covered
  - All new tests pass in the integration suite
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-210) — gap table and missing lines
- **Dependencies**:
  - Existing integration test guild/channel fixtures

### Task 3.2: Write integration tests for `templates.py` (lines 123–128, 254, 282, 297, 311–354)

The uncovered mutation endpoints in `services/api/routes/templates.py` — `update_template`,
`delete_template`, `set_default_template`, `reorder_templates` — account for 24 missed stmts
(research: Priority 6). Integration tests covering each mutating HTTP method are needed.

- **Files**:
  - `services/api/routes/templates.py` — source under test
    (lines 123–128, 254, 282, 297, 311–354)
  - `tests/integration/test_templates.py` — new or extended integration test file
- **Test scenarios**:
  - `PATCH /templates/{id}` with valid body updates template fields → lines 123–128
  - `DELETE /templates/{id}` removes template and returns 204 → line 254
  - `POST /templates/{id}/set-default` marks template as default → line 282
  - `POST /templates/reorder` with valid ordering reorders templates → line 297
  - `POST /templates/reorder` request body bulk (lines 311–354)
  - Attempt to mutate another guild's template returns 403/404
- **Success**:
  - All listed missing lines show coverage in the integration run
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-210) — gap table and missing lines
- **Dependencies**:
  - Existing integration test guild/template fixtures

### Task 3.3: Write integration tests for `guilds.py` (lines 88, 158, 242, 255, 293, 377–415)

The uncovered paths in `services/api/routes/guilds.py` include guild setup admin routes
(lines 377–415, 21 missed stmts, research: Priority 8). Several scattered error/edge-case
lines also need coverage.

- **Files**:
  - `services/api/routes/guilds.py` — source under test
    (lines 88, 158, 242, 255, 293, 377–415)
  - `tests/integration/test_guilds.py` — new or extended integration test file
- **Test scenarios**:
  - Admin setup endpoints (lines 377–415): POST/PUT requests that initialize guild configuration
  - Error path at line 88: request with invalid input or unauthorized caller
  - Error path at line 158: missing or conflicting resource
  - Error paths at lines 242, 255, 293: boundary conditions in guild management flows
  - Unauthorized caller to admin routes returns 403
- **Success**:
  - All listed missing lines show coverage in the integration run
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-210) — gap table and missing lines
- **Dependencies**:
  - Existing integration test admin-user fixtures

---

## Phase 4: Service Layer and Permissions Tests (Priority 10 + Extras)

### Task 4.1: Write integration/unit tests for `games.py` scattered error paths

`services/api/services/games.py` has 41 missed lines scattered across error paths
(research: Priority 10). A mix of integration tests (for DB-dependent paths) and unit tests
(for logic branches with mocked dependencies) is appropriate.

- **Files**:
  - `services/api/services/games.py` — source under test (41 scattered missed lines)
  - `tests/integration/test_games_service.py` — new or extended integration test file
  - `tests/unit/api/services/test_games.py` — new or extended unit test file
- **Test scenarios**:
  - Identify all 41 missed lines using `coverage report --show-missing services/api/services/games.py`
  - For DB-dependent error paths: integration tests that exercise the relevant API endpoints
    with inputs designed to trigger those paths
  - For pure-logic error branches: unit tests with mocked repository layer
- **Success**:
  - Significant reduction in missed statements for `games.py`
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 183-210) — gap table
- **Dependencies**:
  - Phase 3 complete (API route tests may already cover some service paths)

### Task 4.2: Write integration/unit tests for `permissions.py` (lines 316, 524–525, 564, 627, 719)

Five scattered lines in `services/api/dependencies/permissions.py` remain uncovered. These
are authorization boundary checks; each likely corresponds to a specific HTTP verb + role
combination not yet tested.

- **Files**:
  - `services/api/dependencies/permissions.py` — source under test
    (lines 316, 524–525, 564, 627, 719)
  - `tests/integration/test_permissions.py` — new or extended integration test file
- **Test scenarios**:
  - For each target line, identify the route that uses the permission check and craft a request
    from a caller whose role triggers that specific branch
  - Test at least one forbidden-caller scenario per uncovered line
- **Success**:
  - Lines 316, 524–525, 564, 627, 719 of `permissions.py` covered
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 207-215) — missing lines table
- **Dependencies**:
  - Phase 3 complete (route tests may share fixtures)

### Task 4.3: Write unit tests for `guild_queries.py` (lines 512–513)

Two lines in `shared/data_access/guild_queries.py` remain uncovered — a small, focused target
requiring a single unit test that triggers the relevant boundary condition.

- **Files**:
  - `shared/data_access/guild_queries.py` — source under test (lines 512–513)
  - `tests/unit/shared/data_access/test_guild_queries.py` — new or extended unit test file
- **Test scenarios**:
  - Call the function containing lines 512–513 with inputs that exercise both branches
- **Success**:
  - Lines 512–513 of `guild_queries.py` fully covered
  - All new tests pass
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 207-215) — missing lines table
- **Dependencies**:
  - None beyond existing unit test DB mock infrastructure

---

## Dependencies

- Coverage collection infrastructure fix already applied (sitecustomize.py, COVERAGE_FILE env vars, volume mounts)
- Existing test fixtures in `tests/e2e/conftest.py`, `tests/integration/conftest.py`, `tests/unit/conftest.py`
- `scripts/run-integration-tests.sh` and `scripts/run-e2e-tests.sh` for validating coverage after each phase

## Success Criteria

- All 10 prioritized files show measurably increased combined coverage vs. the 87.31% baseline
- All new tests pass without modifying production code
- `scripts/coverage-report.sh` produces an updated combined report confirming improvements
