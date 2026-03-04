---
applyTo: '.copilot-tracking/plans/20260302-01-game-clone.plan.md'
---

<!-- markdownlint-disable-file -->

# Changes Record: Game Clone Feature

## Summary

Implementing the game clone feature allowing hosts to clone an existing game session
with optional participant carry-over and deadline-based auto-drop confirmation.

## Phase 1: Foundation (COMPLETE)

### Task 1.1: ParticipantActionSchedule model + empty Alembic migration

**Files Changed**:

- [shared/models/participant_action_schedule.py](shared/models/participant_action_schedule.py) — NEW: `ParticipantActionSchedule` SQLAlchemy model with `id`, `game_id` (FK cascade), `participant_id` (FK cascade, UNIQUE), `action`, `action_time` (indexed), `processed`, `created_at`
- [alembic/versions/f3a2c1d8e9b7_add_participant_action_schedule.py](alembic/versions/f3a2c1d8e9b7_add_participant_action_schedule.py) — NEW: Alembic migration (Task 1.1 stub; upgrade/downgrade implemented in Task 1.3)
- [shared/models/**init**.py](shared/models/__init__.py) — MODIFIED: added `ParticipantActionSchedule` import + `__all__` entry

### Task 1.2: xfail integration tests for migration

**Files Changed**:

- [tests/integration/test_participant_action_schedule_migration.py](tests/integration/test_participant_action_schedule_migration.py) — NEW: 5 integration tests verifying table existence, column types, action_time index, participant_id UNIQUE constraint, and alembic version (xfail markers removed in Task 1.3)

### Task 1.3: Implement migration body; remove xfail

**Files Changed**:

- [alembic/versions/f3a2c1d8e9b7_add_participant_action_schedule.py](alembic/versions/f3a2c1d8e9b7_add_participant_action_schedule.py) — MODIFIED: `upgrade()` creates table with all columns, FK constraints, UNIQUE constraint, action_time index; `downgrade()` drops index then table
- [tests/integration/test_participant_action_schedule_migration.py](tests/integration/test_participant_action_schedule_migration.py) — MODIFIED: removed all `@pytest.mark.xfail` decorators

### Task 1.4: `_persist_and_publish` stub

**Files Changed**:

- [services/api/services/games.py](services/api/services/games.py) — MODIFIED (line ~690): added `_persist_and_publish` stub method raising `NotImplementedError`

### Task 1.5: xfail unit tests for `_persist_and_publish`

**Files Changed**:

- [tests/unit/services/test_game_service_persist_and_publish.py](tests/unit/services/test_game_service_persist_and_publish.py) — NEW: 5 xfail unit tests verifying db.add/flush called, participant records created, schedules set up, GAME_CREATED event published, reloaded game returned (xfail markers removed in Task 1.6)

### Task 1.6: Implement `_persist_and_publish`; wire into `create_game`; remove xfail

**Files Changed**:

- [services/api/services/games.py](services/api/services/games.py) — MODIFIED: `_persist_and_publish` implemented (db.add, flush, `_create_participant_records`, reload with selectinload, `_setup_game_schedules`, `get_game`, `_publish_game_created`); `create_game` steps 5-8 replaced with `return await self._persist_and_publish(...)`
- [tests/unit/services/test_game_service_persist_and_publish.py](tests/unit/services/test_game_service_persist_and_publish.py) — MODIFIED: removed all `@pytest.mark.xfail` decorators; all 5 tests pass

### Task 1.7: `CarryoverOption` enum + `CloneGameRequest` schema stub

**Files Changed**:

- [services/api/schemas/**init**.py](services/api/schemas/__init__.py) — NEW: package init for api-specific schemas
- [services/api/schemas/clone_game.py](services/api/schemas/clone_game.py) — NEW: `CarryoverOption` StrEnum (YES, YES_WITH_DEADLINE, NO) and `CloneGameRequest` Pydantic model with `model_validator` stub (initially raising `NotImplementedError`, implemented in Task 1.9)

### Task 1.8: xfail unit tests for `CloneGameRequest` validation

**Files Changed**:

- [tests/unit/schemas/test_clone_game_schema.py](tests/unit/schemas/test_clone_game_schema.py) — NEW: 7 xfail tests: NO/YES valid, YES_WITH_DEADLINE+future_deadline valid, YES_WITH_DEADLINE missing deadline rejected, YES_WITH_DEADLINE past deadline rejected (×2 for player and waitlist) (xfail markers removed in Task 1.9)

### Task 1.9: Implement `CloneGameRequest` validators; remove xfail

**Files Changed**:

- [services/api/schemas/clone_game.py](services/api/schemas/clone_game.py) — MODIFIED: implemented `validate_deadlines` model_validator and `_check_deadline` static helper; raises `ValueError` (wrapped to `ValidationError` by Pydantic) when YES_WITH_DEADLINE has missing or past deadline
- [tests/unit/schemas/test_clone_game_schema.py](tests/unit/schemas/test_clone_game_schema.py) — MODIFIED: removed all `@pytest.mark.xfail` decorators; all 7 tests pass

## Phase 2: Clone with YES/NO carryover

### Task 2.1: `clone_game` service stub + 501 route

**Files Changed**:

- [services/api/services/games.py](services/api/services/games.py) — MODIFIED: added `CloneGameRequest` import; added `clone_game` stub method (raises `NotImplementedError`) after `get_game`, before `list_games`
- [services/api/routes/games.py](services/api/routes/games.py) — MODIFIED: added `CloneGameRequest` import; added `POST /{game_id}/clone` route stub returning HTTP 501 between `delete_game` and `join_game`

### Task 2.2: xfail unit + integration tests for clone

**Files Changed**:

- [tests/unit/services/test_clone_game.py](tests/unit/services/test_clone_game.py) — NEW: 6 xfail unit tests: `test_clone_game_copies_source_fields`, `test_clone_game_yes_player_carryover_creates_participants`, `test_clone_game_no_carryover_creates_no_participants`, `test_clone_game_yes_with_deadline_raises_value_error`, `test_clone_game_source_not_found_raises_value_error`, `test_clone_game_non_host_raises_value_error`
- [tests/integration/test_clone_game_endpoint.py](tests/integration/test_clone_game_endpoint.py) — NEW: 4 xfail integration tests: `test_clone_game_endpoint_returns_201_with_new_game`, `test_clone_game_endpoint_non_host_receives_403`, `test_clone_game_endpoint_publishes_game_created_event`, `test_clone_game_endpoint_yes_carryover_copies_new_game_participants`

### Task 2.3: Implement `clone_game` + route; remove xfail markers

**Files Changed**:

- [services/api/services/games.py](services/api/services/games.py) — MODIFIED: added `CarryoverOption` to clone_game import; implemented `clone_game` body: loads source game, checks `can_manage_game`, rejects `YES_WITH_DEADLINE`, partitions source participants, creates new `GameSession` (copies all fields except id/message_id/status/scheduled_at), `db.add`+`flush`, creates `GameParticipant` records directly preserving `position_type`, reloads with participants, `_setup_game_schedules`, reloads via `get_game`, `_publish_game_created`, returns
- [services/api/routes/games.py](services/api/routes/games.py) — MODIFIED: replaced 501 stub with real call to `game_service.clone_game`; handles `ValueError` with `not found` check (404) vs permission (403)
- [tests/unit/services/test_clone_game.py](tests/unit/services/test_clone_game.py) — MODIFIED: removed all 6 `@pytest.mark.xfail` decorators; fixed `source_game` fixture `max_players=1` so one player is confirmed and one is overflow

### Task 2.4: Edge-case unit tests

**Files Changed**:

- [tests/unit/services/test_clone_game.py](tests/unit/services/test_clone_game.py) — MODIFIED: added `test_clone_game_yes_carryover_empty_participant_list`, `test_clone_game_max_players_zero_does_not_raise`, `test_clone_game_clones_cancelled_source_game`

### Task 2.5: Frontend Clone button + pre-filled form

**Files Changed**:

- [frontend/src/pages/CloneGame.tsx](frontend/src/pages/CloneGame.tsx) — NEW: `CloneGame` page with `DateTimePicker` pre-filled to source `scheduled_at + 14 days`, player_carryover and waitlist_carryover `Select` dropdowns (YES/NO), POSTs to `/api/v1/games/{gameId}/clone`, navigates to new game on success
- [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) — MODIFIED: added "Clone Game" button in `{isHost}` action block, navigates to `/games/{gameId}/clone`
- [frontend/src/App.tsx](frontend/src/App.tsx) — MODIFIED: imported `CloneGame`, added route `/games/:gameId/clone`

## Test Results

- Unit tests: 113 passed (0 failed, 0 xfailed)
- Integration tests: 4 xfailed (`test_clone_game_endpoint.py` — awaiting real DB/MQ)
- Frontend: TypeScript OK, ESLint OK (0 errors)
- Lint: all Phase 1 + Phase 2 backend files pass `ruff check`

## Pending Phases

- Phase 2: Clone with YES/NO carryover
- Phase 3: PARTICIPANT_DROP_DUE event + handler
- Phase 4: clone_confirmation DM format + bot view
- Phase 5: clone_confirmation notification type wired into notification daemon
- Phase 6: Participant action daemon
- Phase 7: Frontend YES_WITH_DEADLINE + remove 422 guard
