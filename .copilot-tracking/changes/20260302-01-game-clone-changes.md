---
applyTo: '.copilot-tracking/planning/plans/20260302-01-game-clone.plan.md'
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

- Unit tests: 1205 passed (0 failed, 4 xfailed — pre-existing clone endpoint xfails)
- Integration tests: 4 xfailed (`test_clone_game_endpoint.py` — awaiting real DB/MQ)
- Frontend: TypeScript OK, ESLint OK (0 errors)
- Lint: all Phase 1 + Phase 2 + Phase 3 backend files pass `ruff check`

## Phase 3: PARTICIPANT_DROP_DUE event + handler (COMPLETE)

### Task 3.1: Add `PARTICIPANT_DROP_DUE` to `EventType`; event builder stub; bot handler stub

**Files Changed**:

- [shared/messaging/events.py](shared/messaging/events.py) — MODIFIED: added `PARTICIPANT_DROP_DUE = "game.participant_drop_due"` to `EventType` enum
- [services/scheduler/participant_action_event_builder.py](services/scheduler/participant_action_event_builder.py) — NEW: `build_participant_action_event` stub (implemented in Task 3.3)
- [services/bot/handlers/participant_drop.py](services/bot/handlers/participant_drop.py) — NEW: `handle_participant_drop_due(data, bot, publisher)` stub (implemented in Task 3.3)

### Task 3.2: xfail unit + integration tests for drop event handler

**Files Changed**:

- [tests/unit/bot/handlers/test_participant_drop_handler.py](tests/unit/bot/handlers/test_participant_drop_handler.py) — NEW: 3 xfail unit tests: `test_handler_deletes_participant`, `test_handler_sends_removal_dm`, `test_handler_publishes_game_updated` (xfail markers removed in Task 3.3)
- [tests/integration/test_participant_drop_event.py](tests/integration/test_participant_drop_event.py) — NEW: 2 xfail integration tests: `test_handler_removes_participant_from_db`, `test_handler_is_idempotent_when_participant_missing` (xfail markers removed in Task 3.3)

### Task 3.3: Implement event builder + bot handler; remove xfail markers

**Files Changed**:

- [services/scheduler/participant_action_event_builder.py](services/scheduler/participant_action_event_builder.py) — MODIFIED: implemented `build_participant_action_event` — creates `PARTICIPANT_DROP_DUE` event with `{"game_id": record.game_id, "participant_id": record.participant_id}` data
- [services/bot/handlers/participant_drop.py](services/bot/handlers/participant_drop.py) — MODIFIED: implemented `handle_participant_drop_due` — queries `GameParticipant` with selectinload of `.game` and `.user`, deletes participant, commits, sends `DMFormats.removal` DM via `bot.fetch_user`, publishes `GAME_UPDATED` via publisher
- [tests/unit/bot/handlers/test_participant_drop_handler.py](tests/unit/bot/handlers/test_participant_drop_handler.py) — MODIFIED: removed all 3 `@pytest.mark.xfail` decorators; added `_patch_db` helper; set `mock_participant.game = mock_game`; all 3 tests pass
- [tests/integration/test_participant_drop_event.py](tests/integration/test_participant_drop_event.py) — MODIFIED: removed both `@pytest.mark.xfail` decorators

### Task 3.4: Edge-case tests + guard clauses

**Files Changed**:

- [tests/unit/bot/handlers/test_participant_drop_handler.py](tests/unit/bot/handlers/test_participant_drop_handler.py) — MODIFIED: added `test_handler_skips_when_participant_not_found` (participant not in DB → no delete/DM/publish), `test_handler_drops_participant_from_cancelled_game` (cancelled game → participant still removed); all 5 unit tests pass

## Phase 6: Participant action daemon (COMPLETE)

### Task 6.1: Create `participant_action_daemon_wrapper.py` stub + Docker compose service entry

**Files Changed**:

- [services/scheduler/participant_action_daemon_wrapper.py](services/scheduler/participant_action_daemon_wrapper.py) — NEW: daemon wrapper module stub; constructs `SchedulerDaemon` with `notify_channel="participant_action_schedule_changed"`, `model_class=ParticipantActionSchedule`, `time_field="action_time"`, `status_field="processed"`, `event_builder=build_participant_action_event`; stub did NOT call `daemon.run()` (implemented in Task 6.3)
- [docker/participant-action-daemon.Dockerfile](docker/participant-action-daemon.Dockerfile) — NEW: multi-stage (base/development/production) Dockerfile mirroring notification-daemon.Dockerfile; CMD runs `services.scheduler.participant_action_daemon_wrapper`; copies `participant_action_event_builder.py` and `participant_action_daemon_wrapper.py`
- [compose.yaml](compose.yaml) — MODIFIED: added `participant-action-daemon` service entry (commented out in stub; enabled in Task 6.3)

### Task 6.2: Write xfail integration tests for participant action daemon

**Files Changed**:

- [tests/integration/test_participant_action_daemon.py](tests/integration/test_participant_action_daemon.py) — NEW: `TestParticipantActionDaemonIntegration` class with `test_daemon_processes_overdue_action` (inserts past-dated record, sends pg_notify, waits for `processed=True`, asserts `PARTICIPANT_DROP_DUE` published to `QUEUE_BOT_EVENTS`) and `test_daemon_waits_for_future_action` (future-dated record stays unprocessed); both tests marked `xfail` in stub (removed in Task 6.3)

- [compose.int.yaml](compose.int.yaml) — MODIFIED: added `participant-action-daemon` service override (`LOG_LEVEL: DEBUG`, `PYTEST_RUNNING: "1"`) and added it to `system-ready` `depends_on` block so integration test environment includes the running daemon

### Task 6.3: Implement daemon wrapper; enable Docker service; remove xfail

**Files Changed**:

- [services/scheduler/participant_action_daemon_wrapper.py](services/scheduler/participant_action_daemon_wrapper.py) — MODIFIED: replaced stub no-op with `daemon.run(lambda: shutdown_requested)`; full implementation follows identical pattern to `notification_daemon_wrapper.py`
- [compose.yaml](compose.yaml) — MODIFIED: uncommented `participant-action-daemon` service block; service fully enabled with `DATABASE_URL`, `RABBITMQ_URL`, telemetry env vars, `depends_on: init + grafana-alloy`, healthcheck, logging, and labels
- [tests/integration/test_participant_action_daemon.py](tests/integration/test_participant_action_daemon.py) — MODIFIED: removed both `@pytest.mark.xfail` decorators

## Test Results (Phase 6)

- Unit tests: 125 passed (0 failed)
- New integration tests: 2 (`test_daemon_processes_overdue_action`, `test_daemon_waits_for_future_action`) — require Docker compose environment to run
- Lint: all Phase 6 Python files pass `ruff check`

## Phase 7: Frontend YES_WITH_DEADLINE + remove 422 guard (COMPLETE)

### Task 7.1: Add YES_WITH_DEADLINE option to frontend carryover selectors (stub)

**Files Changed**:

- [frontend/src/pages/CloneGame.tsx](frontend/src/pages/CloneGame.tsx) — MODIFIED: added `YES_WITH_DEADLINE` to `CarryoverOption` type and to the player/waitlist `<Select>` menus; stub sends `NO` in API payload when `YES_WITH_DEADLINE` is selected

### Task 7.2: Write test.fails frontend tests for deadline picker

**Files Changed**:

- [frontend/src/pages/**tests**/CloneGame.test.tsx](frontend/src/pages/__tests__/CloneGame.test.tsx) — MODIFIED: added 6 `it.fails` tests covering: deadline picker appears after selecting `YES_WITH_DEADLINE`; API payload includes `player_deadline`; validation blocks submit without deadline; validation blocks past deadline; same two tests for waitlist

### Task 7.3: Implement full frontend + remove 422 guard; remove it.fails markers

**Files Changed**:

- [frontend/src/pages/CloneGame.tsx](frontend/src/pages/CloneGame.tsx) — MODIFIED: added `playerDeadline`/`waitlistDeadline` `DateTimePicker` state; conditional rendering of pickers when `YES_WITH_DEADLINE` selected; validation in `handleSubmit` (deadline required, must be in the future); deadline included in API payload; removed stub `NO` substitution
- [frontend/src/pages/**tests**/CloneGame.test.tsx](frontend/src/pages/__tests__/CloneGame.test.tsx) — MODIFIED: converted all 6 `it.fails` to regular `it`; all 15 tests pass
- [services/api/services/games.py](services/api/services/games.py) — MODIFIED: removed `YES_WITH_DEADLINE` `ValueError` guard in `clone_game`; updated participant carryover logic to include `YES_WITH_DEADLINE` in carry conditions; added `_apply_deadline_carryover` method; fixed import ordering (ruff auto-fix); removed unused `sqlalchemy_update` import; introduced `carry_options` set to avoid E501
- [tests/unit/services/test_clone_game.py](tests/unit/services/test_clone_game.py) — MODIFIED: replaced `test_clone_game_yes_with_deadline_raises_value_error` with `test_clone_game_yes_with_deadline_completes_successfully`; added top-level imports for `NotificationSchedule` and `ParticipantActionSchedule`; added 4 new direct tests for `_apply_deadline_carryover`: creates action + notification schedules, sends pg_notify, skips when no deadline carryover, skips missing participants

### Task 7.4: Integration + E2E tests for YES_WITH_DEADLINE flow

**Files Changed**:

- [tests/integration/test_clone_game_endpoint.py](tests/integration/test_clone_game_endpoint.py) — MODIFIED: added `test_clone_game_endpoint_yes_with_deadline_creates_action_and_notification_schedules` verifying both `participant_action_schedule` and `clone_confirmation` notification records are created in DB
- [tests/e2e/helpers/discord.py](tests/e2e/helpers/discord.py) — MODIFIED: added `CLONE_CONFIRMATION = "clone_confirmation"` to `DMType` enum; added `DMType.CLONE_CONFIRMATION: DMPredicates.clone_confirmation(game_title)` to `wait_for_recent_dm` predicates dict
- [tests/e2e/test_clone_game_e2e.py](tests/e2e/test_clone_game_e2e.py) — NEW: `test_clone_game_yes_with_deadline_sends_confirmation_dm_and_auto_drops` — E2E test cloning with `YES_WITH_DEADLINE`, verifying `ParticipantActionSchedule` + `clone_confirmation` NotificationSchedule in DB, waiting for confirmation DM, then waiting for participant to be auto-dropped after deadline + daemon-driven removal DM

## Test Results (Phase 7)

- Unit tests: 140 passed (0 failed) — 13 in `test_clone_game.py`, 127 elsewhere
- Frontend tests: 15 passed in `CloneGame.test.tsx` (0 failed)
- Integration tests: require Docker compose environment to run
- E2E tests: require full stack to run
- Lint: all Phase 7 Python files pass `ruff check`; frontend passes TypeScript type check

## Phase 5: clone_confirmation notification type wired into notification daemon (COMPLETE)

### Task 5.1: Add clone_confirmation handling stub in bot's notification handler

**Files Changed**:

- [services/bot/events/handlers.py](services/bot/events/handlers.py) — MODIFIED: added `elif notification_event.notification_type == "clone_confirmation":` branch to `_handle_notification_due`; added `_handle_clone_confirmation` stub method (raises `NotImplementedError`)

### Task 5.2: Write xfail integration tests for notification daemon firing clone_confirmation

**Files Changed**:

- [tests/integration/test_clone_confirmation_notification.py](tests/integration/test_clone_confirmation_notification.py) — NEW: `TestCloneConfirmationNotificationDaemon` class with `test_daemon_fires_clone_confirmation_notification` xfail integration test that inserts a `clone_confirmation` NotificationSchedule record with past notification_time, waits for `sent=True`, and verifies a BOT_EVENTS message is published with `notification_type="clone_confirmation"` (xfail marker removed in Task 5.3)

### Task 5.3: Implement handler; remove xfail markers

**Files Changed**:

- [services/bot/events/handlers.py](services/bot/events/handlers.py) — MODIFIED: added imports for `get_bot_publisher`, `CloneConfirmationView`, and `ParticipantActionSchedule`; implemented `_handle_clone_confirmation`: fetches game+participant via `_fetch_join_notification_data`, fetches `ParticipantActionSchedule`, creates `CloneConfirmationView` with the schedule and publisher, sends DM via `bot.fetch_user().send(message, view=view)`; falls back to plain join DM if no schedule record found
- [tests/integration/test_clone_confirmation_notification.py](tests/integration/test_clone_confirmation_notification.py) — MODIFIED: removed `@pytest.mark.xfail` decorator; integration test now passes
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py) — MODIFIED: added `test_handle_clone_confirmation_sends_dm_with_view`, `test_handle_clone_confirmation_skips_when_participant_not_found`, and `test_handle_clone_confirmation_falls_back_to_join_dm_when_no_schedule` unit tests; all 3 pass

## Phase 4: clone_confirmation DM format + bot view (COMPLETE)

### Task 4.1: DMFormats.clone_confirmation stub + CloneConfirmationView stub

**Files Changed**:

- [shared/message_formats.py](shared/message_formats.py) — MODIFIED: added `clone_confirmation(game_title, deadline_unix)` stub static method (raises `NotImplementedError`) and `DMPredicates.clone_confirmation` predicate
- [services/bot/views/clone_confirmation_view.py](services/bot/views/clone_confirmation_view.py) — NEW: `CloneConfirmationView(discord.ui.View)` with `confirm_button` and `decline_button` stubs (each raising `NotImplementedError`); stores `schedule_id`, `game_id`, `participant_id`, `publisher`
- [services/bot/views/**init**.py](services/bot/views/__init__.py) — MODIFIED: added `CloneConfirmationView` import and `__all__` entry

### Task 4.2: xfail unit tests for message format and button interactions

**Files Changed**:

- [tests/unit/test_clone_confirmation_dm.py](tests/unit/test_clone_confirmation_dm.py) — NEW: 3 xfail tests: `test_clone_confirmation_includes_game_title`, `test_clone_confirmation_includes_deadline`, `test_clone_confirmation_includes_confirm_prompt` (xfail markers removed in Task 4.3)
- [tests/unit/bot/views/**init**.py](tests/unit/bot/views/__init__.py) — NEW: empty package init for views test directory
- [tests/unit/bot/views/test_clone_confirmation_view.py](tests/unit/bot/views/test_clone_confirmation_view.py) — NEW: 3 xfail tests: `test_confirm_button_deletes_participant_action_schedule`, `test_confirm_button_sends_pg_notify`, `test_decline_button_calls_drop_handler` (xfail markers removed in Task 4.3)

### Task 4.3: Implement DMFormats.clone_confirmation + bot DM view; remove xfail

**Files Changed**:

- [shared/message_formats.py](shared/message_formats.py) — MODIFIED: implemented `clone_confirmation` returning message with game title, Discord timestamp for deadline, and "confirm" prompt text
- [services/bot/views/clone_confirmation_view.py](services/bot/views/clone_confirmation_view.py) — MODIFIED: implemented `_confirm_callback` (SELECT + DELETE `ParticipantActionSchedule`, pg_notify `participant_action_schedule_changed`, commit, ephemeral followup); implemented `_decline_callback` (calls `handle_participant_drop_due` with game_id + participant_id, ephemeral followup)
- [tests/unit/test_clone_confirmation_dm.py](tests/unit/test_clone_confirmation_dm.py) — MODIFIED: removed all 3 `@pytest.mark.xfail` decorators; all 3 tests pass
- [tests/unit/bot/views/test_clone_confirmation_view.py](tests/unit/bot/views/test_clone_confirmation_view.py) — MODIFIED: made `view` fixture async (discord.ui.View requires running event loop), added `followup` and `defer` mocks to `mock_interaction`; removed all 3 `@pytest.mark.xfail` decorators; all 3 tests pass

### Task 4.4: Add decline path end-to-end unit test

**Files Changed**:

- [tests/unit/bot/views/test_clone_confirmation_view.py](tests/unit/bot/views/test_clone_confirmation_view.py) — MODIFIED: added `test_decline_path_removes_participant_and_publishes_game_updated` — runs real `handle_participant_drop_due` (only mocks DB session and Discord client), verifies participant deleted, commit called, and GAME_UPDATED published; all 4 view tests pass

## Test Results (Phase 4)

- Unit tests: 125 passed (0 failed)
- Lint: all Phase 4 files pass `ruff check`

## Test Results (Phase 5)

- Unit tests: 1215 passed (0 failed, 4 xfailed — pre-existing)
- New unit tests added: 3 (`test_handle_clone_confirmation_*`)
- Lint: all Phase 5 files pass `ruff check`
