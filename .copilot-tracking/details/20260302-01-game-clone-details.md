<!-- markdownlint-disable-file -->

# Task Details: Game Clone Feature

## Research Reference

**Source Research**: #file:../research/20260302-01-game-clone-research.md

---

## Phase 1: Foundation (safe, no behaviour change)

### Task 1.1: Create `ParticipantActionSchedule` model stub + empty Alembic migration

Create the SQLAlchemy model class and a new Alembic migration file. The migration `upgrade()` and `downgrade()` bodies can be empty at this stage — they will be filled in Task 1.3. The model should exactly match the schema from research.

- **Files**:
  - `shared/models/participant_action_schedule.py` — new model: `id`, `game_id` (FK cascade), `participant_id` (FK cascade, UNIQUE), `action` (String 50), `action_time` (indexed datetime), `processed` (bool, server_default false), `created_at`
  - `alembic/versions/<rev>_add_participant_action_schedule.py` — new migration (empty upgrade/downgrade stubs)
  - `shared/models/__init__.py` — import new model so Alembic autogenerate sees it
- **Success**:
  - Model class importable without error
  - Migration file discoverable by Alembic (`alembic history` shows new revision)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 100-115) — `ParticipantActionSchedule` model definition
  - #file:../research/20260302-01-game-clone-research.md (Lines 30-38) — `GameStatusSchedule` as structural reference
- **Dependencies**:
  - None

### Task 1.2: Write xfail integration tests for migration

Write integration tests marked `@pytest.mark.xfail` asserting that after `alembic upgrade head` the `participant_action_schedule` table exists with all expected columns, and that `alembic downgrade -1` removes it cleanly.

- **Files**:
  - `tests/integration/test_participant_action_schedule_migration.py` — new test module
- **Success**:
  - Tests collected and run as expected failures (xfail) without error
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 186-197) — migration test requirements
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Implement migration body; remove xfail markers

Fill in `upgrade()` (create table with all columns, indexes, FK constraints, UNIQUE on `participant_id`) and `downgrade()` (drop table). Remove `xfail` markers from Task 1.2 tests.

- **Files**:
  - `alembic/versions/<rev>_add_participant_action_schedule.py` — implement `upgrade` + `downgrade`
  - `tests/integration/test_participant_action_schedule_migration.py` — remove `xfail` markers only; do not change assertions
- **Success**:
  - All migration tests pass
  - `alembic upgrade head` and `alembic downgrade -1` succeed in integration environment
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 100-115) — exact column spec
  - #file:../research/20260302-01-game-clone-research.md (Lines 168-172) — UNIQUE constraint requirement for `participant_id`
- **Dependencies**:
  - Task 1.2 complete

### Task 1.4: Refactor `GameService.create_game` — extract `_persist_and_publish` stub

Add a private `_persist_and_publish(game, participants, resolved_fields)` method to `GameService` that raises `NotImplementedError`. Do not yet change `create_game` to call it. The goal is to establish the method signature.

- **Files**:
  - `services/api/services/games.py` — add `_persist_and_publish` stub method
- **Success**:
  - `_persist_and_publish` exists on `GameService`; raises `NotImplementedError` when called; `create_game` unchanged
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 53-64) — steps 5–8 of `create_game` to extract
- **Dependencies**:
  - Task 1.3 complete

### Task 1.5: Write xfail unit tests for `_persist_and_publish`

Write unit tests marked `@pytest.mark.xfail` that call `_persist_and_publish` with representative inputs and assert it produces the same DB state and RabbitMQ events as the original `create_game` steps 5–8 did.

- **Files**:
  - `tests/unit/services/test_game_service_persist_and_publish.py` — new test module
- **Success**:
  - Tests collected and run as expected failures (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 53-64) — create_game steps 5–8 semantics
- **Dependencies**:
  - Task 1.4 complete

### Task 1.6: Implement `_persist_and_publish`; wire into `create_game`; remove xfail

Move `create_game` steps 5–8 into `_persist_and_publish`. Update `create_game` to call `_persist_and_publish`. Remove `xfail` from Task 1.5 tests. All existing `create_game` tests must continue to pass without modification.

- **Files**:
  - `services/api/services/games.py` — implement `_persist_and_publish`; update `create_game` to call it
  - `tests/unit/services/test_game_service_persist_and_publish.py` — remove `xfail` markers only
- **Success**:
  - All existing `create_game` tests pass unchanged
  - `_persist_and_publish` unit tests pass
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 53-64) — steps to move
- **Dependencies**:
  - Task 1.5 complete

### Task 1.7: Add `CarryoverOption` enum + `CloneGameRequest` schema stub

Add the `CarryoverOption` `StrEnum` and a `CloneGameRequest` Pydantic model. Include a `model_validator` stub that raises `NotImplementedError` for the cross-field deadline validation.

- **Files**:
  - `services/api/schemas/clone_game.py` — new module with `CarryoverOption` and `CloneGameRequest`
- **Success**:
  - Classes importable; `CloneGameRequest(scheduled_at=..., player_carryover="NO")` instantiates; validator raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 116-128) — `CloneGameRequest` schema definition
- **Dependencies**:
  - Task 1.6 complete

### Task 1.8: Write xfail unit tests for `CloneGameRequest` validation

Write tests marked `@pytest.mark.xfail` asserting: (a) `YES_WITH_DEADLINE` without `player_deadline` is rejected; (b) `YES_WITH_DEADLINE` with a past deadline is rejected; (c) valid `YES`, `NO`, and `YES_WITH_DEADLINE` (with future deadline) are accepted.

- **Files**:
  - `tests/unit/schemas/test_clone_game_schema.py` — new test module
- **Success**:
  - Tests collected and run as expected failures (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 116-128) — schema validation requirements
- **Dependencies**:
  - Task 1.7 complete

### Task 1.9: Implement `CloneGameRequest` validators; remove xfail

Implement the `model_validator` for `CloneGameRequest`. Remove `xfail` from Task 1.8 tests.

- **Files**:
  - `services/api/schemas/clone_game.py` — implement validator
  - `tests/unit/schemas/test_clone_game_schema.py` — remove `xfail` markers only
- **Success**:
  - All `CloneGameRequest` validation tests pass
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 116-128) — validation rules
- **Dependencies**:
  - Task 1.8 complete

---

## Phase 2: Clone with YES/NO carryover

### Task 2.1: Add `clone_game` stub to `GameService` + clone route stub returning 501

Add `clone_game(source_game_id, clone_data, current_user, db)` to `GameService` (raises `NotImplementedError`). Add `POST /api/games/{game_id}/clone` route returning HTTP 501.

- **Files**:
  - `services/api/services/games.py` — add `clone_game` stub
  - `services/api/routes/games.py` — add clone route returning 501
- **Success**:
  - `POST /api/games/{game_id}/clone` with valid auth returns 501
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 130-147) — clone endpoint spec
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Write xfail unit + integration tests for clone endpoint and service method

Write tests marked `@pytest.mark.xfail` covering: (a) `clone_game` copies all fields except `id`, `status`, `created_at`, `updated_at`, `message_id`; (b) `YES` carries over participants in original order with recalculated positions; (c) `NO` creates no participants; (d) `YES_WITH_DEADLINE` raises at service layer (422); (e) `can_manage_game` enforced — non-host non-manager receives 403; (f) integration: `POST` creates new `GameSession` in DB, `join_notification` schedule records created, `GAME_CREATED` event published to RabbitMQ.

- **Files**:
  - `tests/unit/services/test_clone_game.py` — unit tests for `clone_game` service method
  - `tests/integration/test_clone_game_endpoint.py` — integration tests for clone route
- **Success**:
  - Tests collected and run as expected failures (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 205-223) — Phase 2 test requirements
  - #file:../research/20260302-01-game-clone-research.md (Lines 130-147) — clone behaviour spec
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Implement `clone_game` + route; enforce 422 for YES_WITH_DEADLINE; remove xfail

Implement `clone_game`:

1. Load source game and its participants ordered by `(position_type, position)`
2. Create new `GameSession` copying all fields except `id`, `status`, `created_at`, `updated_at`, `message_id`; set `scheduled_at` from request, `status=SCHEDULED`
3. If `player_carryover=YES`: add active players in order; if `waitlist_carryover=YES`: add waitlist participants in order
4. Create `join_notification` `NotificationSchedule` for each carried-over participant
5. Call `_persist_and_publish`; return new game response
6. Raise HTTP 422 if `YES_WITH_DEADLINE` is requested (guard removed in Phase 7)

Remove `xfail` from Task 2.2 tests.

- **Files**:
  - `services/api/services/games.py` — implement `clone_game`
  - `services/api/routes/games.py` — implement clone route (wire to `clone_game`, auth via `can_manage_game`)
  - `tests/unit/services/test_clone_game.py` — remove `xfail` markers only
  - `tests/integration/test_clone_game_endpoint.py` — remove `xfail` markers only
- **Success**:
  - All clone unit and integration tests pass
  - Existing tests pass unchanged
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 130-147) — full clone algorithm
  - #file:../research/20260302-01-game-clone-research.md (Lines 55-62) — `can_manage_game` usage
- **Dependencies**:
  - Task 2.2 complete

### Task 2.4: Refactor + add edge-case tests

Add edge-case tests: cloning a game whose `max_players` is 0, cloning with an empty participant list, cloning a `CANCELLED` game. Refactor `clone_game` internals if any duplication is visible.

- **Files**:
  - `tests/unit/services/test_clone_game.py` — additional test cases
  - `services/api/services/games.py` — refactoring only (no behaviour change)
- **Success**:
  - All tests pass; coverage for edge cases
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 253-262) — overall success criteria
- **Dependencies**:
  - Task 2.3 complete

### Task 2.5: Frontend — Clone button + pre-filled form with YES/NO carryover selectors

Add a "Clone" button to the game detail page. Clicking it navigates to the game creation form pre-filled with source game fields and adds two carryover selector dropdowns (player and waitlist), each offering `YES` and `NO` only. On submit, call `POST /api/games/{game_id}/clone`.

- **Files**:
  - `frontend/src/components/GameDetail.tsx` (or equivalent) — add Clone button
  - `frontend/src/pages/CloneGame.tsx` — new page with pre-filled form + carryover selectors
  - `frontend/src/api/games.ts` (or equivalent) — add `cloneGame` API function
- **Success**:
  - Clone button visible to host/manager; clicking opens pre-filled form
  - Submitting form calls clone endpoint and navigates to new game detail
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 204-208) — Phase 2 frontend spec
- **Dependencies**:
  - Task 2.3 complete

---

## Phase 3: PARTICIPANT_DROP_DUE event + handler

### Task 3.1: Add `PARTICIPANT_DROP_DUE` to `EventType`; create event builder stub; create bot handler stub

Add the new event type constant. Add a stub `build_participant_action_event` function (returns `NotImplementedError`). Add a stub bot handler for `PARTICIPANT_DROP_DUE` (raises `NotImplementedError`).

- **Files**:
  - `shared/messaging/events.py` — add `PARTICIPANT_DROP_DUE = "game.participant_drop_due"`
  - `services/scheduler/participant_action_event_builder.py` — new: `build_participant_action_event` stub
  - `services/bot/handlers/participant_drop.py` — new: bot handler stub
- **Success**:
  - All three stubs importable without error
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 79-84) — `PARTICIPANT_DROP_DUE` spec
  - #file:../research/20260302-01-game-clone-research.md (Lines 148-165) — daemon event builder reference
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Write xfail unit + integration tests for drop event handler

Write tests marked `@pytest.mark.xfail` asserting: (a) bot handler removes participant record; (b) sends `DMFormats.removal` DM; (c) publishes `GAME_UPDATED`. Integration test: publish `PARTICIPANT_DROP_DUE` to RabbitMQ queue directly; verify participant record removed and `GAME_UPDATED` event published.

- **Files**:
  - `tests/unit/bot/handlers/test_participant_drop_handler.py` — unit tests
  - `tests/integration/test_participant_drop_event.py` — integration tests
- **Success**:
  - Tests collected and run as expected failures (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 224-234) — Phase 3 test requirements
- **Dependencies**:
  - Task 3.1 complete

### Task 3.3: Implement event builder + bot handler; remove xfail

Implement `build_participant_action_event` to produce a `PARTICIPANT_DROP_DUE` event from a `ParticipantActionSchedule` record. Implement the bot handler to remove the participant (reusing existing drop logic) and send `DMFormats.removal`. Remove `xfail` markers.

- **Files**:
  - `services/scheduler/participant_action_event_builder.py` — implement event builder
  - `services/bot/handlers/participant_drop.py` — implement handler (reuse existing drop logic)
  - `tests/unit/bot/handlers/test_participant_drop_handler.py` — remove `xfail` only
  - `tests/integration/test_participant_drop_event.py` — remove `xfail` only
- **Success**:
  - All drop event tests pass
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 88-97) — drop flow description
- **Dependencies**:
  - Task 3.2 complete

### Task 3.4: Refactor; add edge-case tests (participant already removed, game cancelled)

Add edge-case tests: handler receives `PARTICIPANT_DROP_DUE` for a participant that no longer exists (idempotent), and for a game that is cancelled. Refactor handler if needed.

- **Files**:
  - `tests/unit/bot/handlers/test_participant_drop_handler.py` — edge cases
  - `services/bot/handlers/participant_drop.py` — guard clauses if needed
- **Success**:
  - Edge cases handled without crash; tests pass
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 253-262) — success criteria
- **Dependencies**:
  - Task 3.3 complete

---

## Phase 4: clone_confirmation DM format + bot view

### Task 4.1: Add `DMFormats.clone_confirmation` stub + bot DM view stub

Add `DMFormats.clone_confirmation(game_title, deadline)` returning `NotImplementedError`. Create a discord.py `View` subclass with confirm and decline `Button` stubs (each raising `NotImplementedError`).

- **Files**:
  - `shared/message_formats.py` — add `clone_confirmation` stub static method
  - `services/bot/views/clone_confirmation_view.py` — new: `CloneConfirmationView(discord.ui.View)` with button stubs
- **Success**:
  - Stubs importable; `View` instantiable without error
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 47-52) — `DMFormats` pattern
  - #file:../research/20260302-01-game-clone-research.md (Lines 93-97) — confirm/decline button behaviour
- **Dependencies**:
  - Phase 3 complete

### Task 4.2: Write xfail unit tests for message format and button interactions

Write tests marked `@pytest.mark.xfail` asserting: (a) `clone_confirmation` message includes game title and formatted deadline; (b) confirm button interaction deletes `ParticipantActionSchedule` record and sends NOTIFY; (c) decline button interaction calls drop handler from Phase 3.

- **Files**:
  - `tests/unit/test_clone_confirmation_dm.py` — message format tests
  - `tests/unit/bot/views/test_clone_confirmation_view.py` — button interaction tests
- **Success**:
  - Tests collected and run as expected failures (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 238-247) — Phase 4 test requirements
- **Dependencies**:
  - Task 4.1 complete

### Task 4.3: Implement `DMFormats.clone_confirmation` + bot DM view; remove xfail

Implement the message format method. Implement confirm button (delete `ParticipantActionSchedule`, send pg NOTIFY `participant_action_schedule_changed`). Implement decline button (call existing drop handler). Remove `xfail` markers.

- **Files**:
  - `shared/message_formats.py` — implement `clone_confirmation`
  - `services/bot/views/clone_confirmation_view.py` — implement both buttons
  - `tests/unit/test_clone_confirmation_dm.py` — remove `xfail` only
  - `tests/unit/bot/views/test_clone_confirmation_view.py` — remove `xfail` only
- **Success**:
  - All DM format and view tests pass
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 172-177) — NOTIFY requirement
- **Dependencies**:
  - Task 4.2 complete

### Task 4.4: Refactor; add unit tests for declined path

Add explicit unit tests for the decline path end-to-end (decline → drop handler → participant removed → `GAME_UPDATED` published). Refactor view if any duplication is visible.

- **Files**:
  - `tests/unit/bot/views/test_clone_confirmation_view.py` — decline path integration unit test
- **Success**:
  - All tests pass
- **Dependencies**:
  - Task 4.3 complete

---

## Phase 5: clone_confirmation notification type wired into notification daemon

### Task 5.1: Add `clone_confirmation` handling stub in bot's notification handler

Locate the bot handler that dispatches on `notification_type`. Add a `"clone_confirmation"` branch that raises `NotImplementedError`.

- **Files**:
  - `services/bot/handlers/notification_handler.py` (or equivalent) — add `clone_confirmation` branch stub
- **Success**:
  - Stub reachable; raises `NotImplementedError` when called
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 69-76) — bot join_game handler as reference
- **Dependencies**:
  - Phase 4 complete

### Task 5.2: Write xfail integration tests for notification daemon firing clone_confirmation

Write integration test marked `@pytest.mark.xfail`: insert a `clone_confirmation` `NotificationSchedule` record with `notification_time` in the past directly into DB; trigger daemon poll; verify `NOTIFICATION_SEND_DM` event published to RabbitMQ with correct payload including `notification_type="clone_confirmation"`.

- **Files**:
  - `tests/integration/test_clone_confirmation_notification.py` — new test module
- **Success**:
  - Test collected and runs as expected failure (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 248-254) — Phase 5 test requirements
  - #file:../research/20260302-01-game-clone-research.md (Lines 155-165) — `NotificationSchedule` record for `clone_confirmation`
- **Dependencies**:
  - Task 5.1 complete

### Task 5.3: Implement handler; remove xfail

Implement the `clone_confirmation` branch in the bot notification handler: send a DM to the participant using `CloneConfirmationView` from Phase 4. Remove `xfail` markers.

- **Files**:
  - `services/bot/handlers/notification_handler.py` (or equivalent) — implement branch
  - `tests/integration/test_clone_confirmation_notification.py` — remove `xfail` only
- **Success**:
  - Integration test passes; daemon fires `clone_confirmation` records and bot sends DM with buttons
- **Dependencies**:
  - Task 5.2 complete

---

## Phase 6: Participant action daemon

### Task 6.1: Create `participant_action_daemon_wrapper.py` stub + Docker compose entry (disabled)

Create the daemon wrapper module (stub — `SchedulerDaemon` construction but not `.run()`). Add a Docker compose service entry for the daemon, initially disabled/commented.

- **Files**:
  - `services/scheduler/participant_action_daemon_wrapper.py` — stub daemon wrapper
  - `compose.yaml` (or appropriate compose file) — add `participant-action-daemon` service (disabled)
- **Success**:
  - Module importable without error; Docker service entry present
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 148-165) — daemon wrapper example
  - #file:../research/20260302-01-game-clone-research.md (Lines 39-46) — `SchedulerDaemon` pattern
- **Dependencies**:
  - Phase 5 complete

### Task 6.2: Write xfail integration tests for participant action daemon

Write integration test marked `@pytest.mark.xfail`: insert a `ParticipantActionSchedule` record with `action_time` in the past; trigger daemon poll; verify `PARTICIPANT_DROP_DUE` event published to RabbitMQ; verify `processed=True` on the record.

- **Files**:
  - `tests/integration/test_participant_action_daemon.py` — new test module
- **Success**:
  - Test collected and runs as expected failure (xfail)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 255-261) — Phase 6 test requirements
- **Dependencies**:
  - Task 6.1 complete

### Task 6.3: Implement daemon wrapper; enable Docker service; remove xfail

Implement the full `participant_action_daemon_wrapper.py` following the exact pattern of `notification_daemon_wrapper.py`. Enable the Docker compose service. Remove `xfail` markers.

- **Files**:
  - `services/scheduler/participant_action_daemon_wrapper.py` — full implementation
  - `compose.yaml` — enable `participant-action-daemon` service
  - `tests/integration/test_participant_action_daemon.py` — remove `xfail` only
- **Success**:
  - Integration test passes; daemon runs in Docker compose dev environment
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 148-165) — daemon configuration
- **Dependencies**:
  - Task 6.2 complete

---

## Phase 7: Frontend YES_WITH_DEADLINE + remove 422 guard

### Task 7.1: Add `YES_WITH_DEADLINE` option + deadline datetime picker to frontend (stub)

Add `YES_WITH_DEADLINE` to the carryover select options and render a deadline `<input type="datetime-local">` when selected. At this stage the form submit still sends `NO` (or `YES`) — the deadline value is ignored.

- **Files**:
  - `frontend/src/pages/CloneGame.tsx` — add `YES_WITH_DEADLINE` option + conditional deadline picker
- **Success**:
  - `YES_WITH_DEADLINE` option renders; deadline picker appears when selected; form submits without error (ignores deadline)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 262-270) — Phase 7 frontend spec
- **Dependencies**:
  - Phase 6 complete

### Task 7.2: Write xfail unit tests for frontend components (TypeScript/Vitest)

Write Vitest tests marked `test.failing` asserting: (a) deadline picker renders when `YES_WITH_DEADLINE` selected; (b) form validation rejects missing/past deadline with `YES_WITH_DEADLINE`; (c) `cloneGame` API call includes `player_deadline` / `waitlist_deadline` when `YES_WITH_DEADLINE` selected.

- **Files**:
  - `frontend/src/pages/__tests__/CloneGame.test.tsx` — new test module
- **Success**:
  - Tests collected and marked as expected failures (test.failing)
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 116-128) — `CloneGameRequest` deadline rules mirrored in frontend
- **Dependencies**:
  - Task 7.1 complete

### Task 7.3: Implement full frontend behaviour; remove xfail; remove 422 guard from service layer

Wire deadline picker value into the API call. Add front-end validation (deadline required and must be in the future when `YES_WITH_DEADLINE`). Remove the 422 guard from `GameService.clone_game`. Remove `test.failing` markers.

- **Files**:
  - `frontend/src/pages/CloneGame.tsx` — wire deadline into API call + front-end validation
  - `frontend/src/pages/__tests__/CloneGame.test.tsx` — remove `test.failing` markers only
  - `services/api/services/games.py` — remove 422 guard; implement `ParticipantActionSchedule` creation for `YES_WITH_DEADLINE`
- **Success**:
  - All frontend tests pass; `YES_WITH_DEADLINE` now accepted by service layer and creates `ParticipantActionSchedule` records
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 130-147) — `YES_WITH_DEADLINE` clone algorithm
  - #file:../research/20260302-01-game-clone-research.md (Lines 100-115) — `ParticipantActionSchedule` record creation
- **Dependencies**:
  - Task 7.2 complete

### Task 7.4: Add integration + e2e tests for full YES_WITH_DEADLINE flow

Integration test: `POST /api/games/{game_id}/clone` with `YES_WITH_DEADLINE` creates both participant records and `ParticipantActionSchedule` records in DB.

E2E test: clone a game with `YES_WITH_DEADLINE`; verify announcement in Discord channel; verify carried-over participants receive confirmation DM with buttons; verify participant is auto-dropped after deadline expires (daemon-driven path, no user interaction).

Note: Button interaction (confirm path) tested only at unit level (Phase 4) — real user credentials not available in e2e environment.

- **Files**:
  - `tests/integration/test_clone_game_endpoint.py` — add `YES_WITH_DEADLINE` integration tests
  - `tests/e2e/test_clone_game_e2e.py` — new e2e test module
- **Success**:
  - Integration tests pass; e2e test verifies full daemon-driven auto-drop flow
- **Research References**:
  - #file:../research/20260302-01-game-clone-research.md (Lines 271-286) — Phase 7 e2e test spec
- **Dependencies**:
  - Task 7.3 complete

---

## Dependencies

- Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic
- discord.py with `discord.ui.View` and `discord.ui.Button` (already in bot service)
- RabbitMQ (existing messaging infrastructure)
- PostgreSQL NOTIFY/LISTEN (existing daemon wake mechanism)
- No new external libraries required

## Success Criteria

- `POST /api/games/{game_id}/clone` fully functional across all carryover modes
- All existing tests pass unchanged after Phase 1 refactor
- All new code has unit + integration tests; key paths covered by e2e tests
- `YES_WITH_DEADLINE` sends confirmation DMs; participants auto-dropped at deadline by daemon
- All pre-commit checks pass on every commit
