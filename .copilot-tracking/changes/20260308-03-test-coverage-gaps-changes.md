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

_(Not yet started)_

---

## Phase 3: API Route Integration Tests (Priorities 5, 6, 8)

_(Not yet started)_

---

## Phase 4: Service Layer and Permissions Tests (Priority 10 + Extras)

_(Not yet started)_
