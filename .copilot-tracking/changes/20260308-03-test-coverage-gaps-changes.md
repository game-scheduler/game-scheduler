<!-- markdownlint-disable-file -->

# Changes: Test Coverage Gaps

## Summary

Writing unit and integration tests to close the top 10 prioritized coverage gaps in
bot handlers, bot auth, API routes, and service layer code.

---

## Phase 1: Bot Handler E2E/Integration Tests (Priorities 1–3)

### Task 1.1: `button_handler.py` integration tests

**Status**: Complete

#### Added

- `tests/integration/test_button_handler.py` — Integration tests for
  `ButtonHandler.handle_interaction`: join/leave routing with real DB, missing `custom_id`
  guard, non-game prefix guard, exception triggers ephemeral error message. 5 tests.

  **Deviation from plan**: The plan suggested `tests/e2e/test_button_handler.py`. Integration
  tests were written instead because the handlers do not require an active Discord bot client
  or Discord token — only a real PostgreSQL database. `get_db_session` is patched once to use
  `BotAsyncSessionLocal` (BYPASSRLS) to avoid Row-Level Security blocking test data access.
  All other logic is real.

### Task 1.2: `join_game.py` integration tests

**Status**: Complete

#### Added

- `tests/integration/test_join_game.py` — Integration tests for `handle_join_game` with real
  DB: invalid UUID, game not found, non-SCHEDULED game, successful join (existing user),
  successful join (creates new user), duplicate join swallowed silently. 6 tests.

  **Deviation from plan**: Same rationale as Task 1.1.

### Task 1.3: `leave_game.py` integration tests

**Status**: Complete

#### Added

- `tests/integration/test_leave_game.py` — Integration tests for `handle_leave_game` with
  real DB: invalid UUID, game not found, COMPLETED game error, user not in DB (silent return),
  user not participant (silent return), successful leave with participant deletion. 6 tests.

  **Deviation from plan**: Same rationale as Task 1.1.

---

## Phase 2: Bot Auth and Utility Unit Tests (Priorities 4, 7, 9)

### Task 2.1: `role_checker.py` unit tests

**Status**: Complete

#### Modified

- `tests/unit/services/bot/auth/test_role_checker.py` — Added 14 new tests covering:
  `member is None` guard in `get_user_role_ids` (lines 85–86); `discord.Forbidden` and
  generic exception handlers in `get_user_role_ids` (lines 96–101); `guild is None` and
  exception paths in `get_guild_roles` (lines 117–118, 122–124); and `guild is None`,
  `member is None`, and exception paths in `check_manage_guild_permission`,
  `check_manage_channels_permission`, and `check_administrator_permission`
  (lines 140, 144, 148–150, 166, 170, 174–176, 192, 196, 200–202).
  Coverage: 68% → 100%.

### Task 2.2: `utils.py` unit tests

**Status**: Complete

#### Modified

- `tests/unit/services/bot/handlers/test_utils.py` — Added `TestSendErrorMessage` and
  `TestSendSuccessMessage` test classes (4 tests total) covering happy-path DM send and
  `discord.Forbidden` exception path for both `send_error_message` and
  `send_success_message` (lines 78–81, 91–94). Updated import to include both new
  functions. Coverage: 69% → 100%.

### Task 2.3: `cache.py` unit tests

**Status**: Complete

#### Modified

- `tests/unit/services/bot/auth/test_cache.py` — Added 3 new tests: lazy Redis client
  initialization in `get_redis()` when `_redis` is `None` (line 51); `Exception` handler
  in `get_guild_roles` (lines 140–142); `Exception` handler in `set_guild_roles`
  (lines 158–159). Added `patch` to imports. Coverage: 90% → 100%.

---

## Phase 3: API Route Integration Tests (Priorities 5, 6, 8)

_(Not yet started)_

---

## Phase 4: Service Layer and Permissions Tests (Priority 10 + Extras)

### Task 4.2: `permissions.py` unit tests

**Status**: Complete

#### Modified

- `tests/unit/services/api/dependencies/test_api_permissions.py` — Added 8 new
  tests covering all previously uncovered maintainer-bypass and success paths:
  `test_check_guild_membership_success` (line 79), `test_check_guild_membership_not_member`,
  `test_require_permission_with_maintainer_token` (line 316),
  `test_check_bot_manager_permission_success` / `_failure` (lines 521–525),
  `test_require_game_host_with_maintainer_token` (line 564),
  `test_can_manage_game_with_maintainer_token` (line 627),
  `test_require_administrator_with_maintainer_token` (line 719).
  Coverage: 92.81% → 97.12%.

---

### Task 4.3: `guild_queries.py` unit tests

**Status**: Complete

#### Modified

- `tests/unit/shared/data_access/test_guild_queries_unit.py` — Added 3 new test
  classes (7 tests total): `TestGetChannelByDiscordId` (lines 480–485, found +
  not-found paths), `TestCreateChannelConfig` (lines 511–524, success + RLS
  context set + empty guild_id error), `TestCreateDefaultTemplate` (line 545,
  success + empty guild_id error). Coverage (unit): 93.68% → 100%.

---

### Task 4.1: `games.py` unit tests

**Status**: Complete

#### Created

- `tests/unit/api/services/test_games.py` — New file with 26 tests across 9
  test classes covering all previously untested error and branch paths:
  `TestJoinGame` (game/user/config not found, game full, reload failure),
  `TestLeaveGame` (game/user not found, completed game, reload failure),
  `TestListGames` (guild_id filter, status filter, channel+status filter),
  `TestUpdateGame` (game not found, permission denied),
  `TestDeleteGame` (game not found, permission denied),
  `TestResolveGameHost` (host user not found),
  `TestApplyDeadlineCarryover` (no-carryover early return, empty participants),
  `TestScheduleJoinNotifications` (confirmed Discord participant, display-name skip),
  `TestAddNewMentions` / `TestUpdatePrefilledParticipants` (discord + display-name
  participants, validation error). Coverage (unit): 89.23% → 95.12%.
