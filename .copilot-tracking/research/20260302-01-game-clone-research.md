<!-- markdownlint-disable-file -->

# Task Research Notes: Game Clone Feature

## Research Executed

### File Analysis

- `shared/models/game.py`
  - `GameSession` fields: `id`, `title`, `description`, `signup_instructions`, `scheduled_at`, `where`, `max_players`, `template_id`, `guild_id`, `channel_id`, `host_id`, `reminder_minutes`, `notify_role_ids`, `allowed_player_role_ids`, `expected_duration_minutes`, `status`, `signup_method`, `thumbnail_id`, `banner_image_id`
  - `GameStatus` enum: `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`
  - No existing clone/recurrence mechanism

- `shared/models/participant.py`
  - `GameParticipant` fields: `id`, `game_session_id`, `user_id`, `display_name`, `joined_at`, `position_type`, `position`
  - `ParticipantType`: `HOST_ADDED = 8000`, `SELF_ADDED = 24000` (sort keys)
  - Participants with `position <= max_players` are active players; the rest are the waitlist
  - No gaps in ordering: the top N by sort order fill the player slots

- `shared/models/notification_schedule.py`
  - `NotificationSchedule` fields: `game_id`, `participant_id` (nullable), `notification_type`, `notification_time`, `sent`, `game_scheduled_at`, `reminder_minutes`
  - Current `notification_type` values: `"reminder"` (game-wide) and `"join_notification"` (per-participant, delayed 60s)
  - `UniqueConstraint` on `(game_id, reminder_minutes)` — per-game, not per-participant

- `shared/models/game_status_schedule.py`
  - `GameStatusSchedule` fields: `game_id`, `target_status`, `transition_time`, `processed`
  - Used for timed game status transitions (e.g., auto IN_PROGRESS at start time)

- `services/scheduler/generic_scheduler_daemon.py`
  - `SchedulerDaemon` — reusable, parameterised with `model_class`, `time_field`, `status_field`, `event_builder`, `notify_channel`
  - Two current instantiations: `notification_daemon_wrapper.py` (NotificationSchedule) and `status_transition_daemon_wrapper.py` (GameStatusSchedule)
  - Explicitly designed as a template for new schedule types

- `services/api/dependencies/permissions.py`
  - `can_manage_game(game_host_id, guild_id, current_user, role_service, db) -> bool`
  - Returns `True` if user is the game host (by Discord ID), a maintainer (`is_maintainer` in session), or a bot manager (by role)
  - This is the single central place for host-level access — the clone endpoint should use this function directly

- `shared/message_formats.py`
  - `DMFormats` class with static methods: `promotion`, `removal`, `join_with_instructions`, `join_simple`, `reminder_host`, ...
  - DMs are sent by bot service in response to `NOTIFICATION_DUE` events routed via RabbitMQ

- `services/bot/handlers/join_game.py`
  - On join: creates `GameParticipant`, then creates a `NotificationSchedule` record (60s delay, type `"join_notification"`) — the daemon fires it, the bot sends the DM
  - Publishes `GAME_UPDATED` event to refresh the Discord message

- `services/api/services/games.py` — `GameService.create_game()` pipeline
  - Steps 1–4 are template/request-specific: load template+guild+channel, resolve host + check host permissions, resolve template field overrides, resolve `@mention` strings for initial participants
  - Steps 5–8 are generic: `_build_game_session` (construct object), flush + `_create_participant_records`, `_setup_game_schedules` (join notifications + reminders + status transitions), reload + publish `GAME_CREATED`
  - Steps 5–8 can be extracted into `_persist_and_publish(game, participants, resolved_fields)` and shared with `clone_game`
  - `clone_game` will be a new method on the same `GameService` class; steps 1–4 are replaced by loading the source game and copying its fields directly — no template resolution, no `@mention` parsing

### Code Search Results

- `can_manage_game` in `permissions.py` line 591
  - Covers host + maintainer + bot manager in one place — no new permission checks needed anywhere
- `SchedulerDaemon` instantiated in two wrapper modules
  - Third instantiation for participant auto-drop will follow exact same pattern
- `notification_type` values
  - Current: `"reminder"`, `"join_notification"`
  - New required: `"clone_confirmation"` (per-participant DM with confirm/decline buttons)
- `EventType` enum in `shared/messaging/events.py`
  - Current participant events: `PLAYER_JOINED`, `PLAYER_LEFT`, `PLAYER_REMOVED`, `WAITLIST_ADDED`, `WAITLIST_REMOVED`
  - New required: `PARTICIPANT_DROP_DUE` (or reuse `PLAYER_REMOVED` with source flag)

### Project Conventions

- Standards referenced: TDD applies (Python); scheduler daemon pattern; `DMFormats` for message strings; `can_manage_game` for host-level authorization
- Instructions followed: minimal changes, surgical edits, self-documenting code, no linter suppressions

## Key Discoveries

### Project Structure

The codebase is microservices-based: API service handles HTTP, bot service handles Discord I/O, scheduler daemons handle timed events, all connected via RabbitMQ. The `SchedulerDaemon` is already a generic, reusable template — adding a new timed action type requires a new model, a new event type, a new event handler in the bot, and a new daemon wrapper. The bot can send DMs with buttons (Discord supports this in DMs from bots sharing a server with the user).

### Implementation Patterns

The join flow is the exact model for carry-over:

1. Add participant to DB
2. Create `NotificationSchedule` record → daemon fires → bot sends DM
3. Publish `GAME_UPDATED`

The only new wrinkle for "confirm by deadline" is:

- The DM includes confirm/decline buttons (new Discord view)
- A `ParticipantActionSchedule` record is created alongside the participant
- On confirm: delete the `ParticipantActionSchedule` record, send `notification_schedule_changed` NOTIFY
- On decline or deadline expiry: daemon fires `PARTICIPANT_DROP_DUE` → bot executes normal drop (existing `PLAYER_REMOVED` path)

### Complete Examples

```python
# New model: ParticipantActionSchedule
class ParticipantActionSchedule(Base):
    __tablename__ = "participant_action_schedule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("game_participants.id", ondelete="CASCADE"), unique=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # "drop"
    action_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
```

```python
# New API schema: CloneGameRequest
class CarryoverOption(StrEnum):
    YES = "YES"
    YES_WITH_DEADLINE = "YES_WITH_DEADLINE"
    NO = "NO"

class CloneGameRequest(BaseModel):
    scheduled_at: datetime = Field(..., description="New game start time (ISO 8601 UTC)")
    player_carryover: CarryoverOption = Field(default=CarryoverOption.NO)
    player_deadline: datetime | None = Field(None, description="Required when player_carryover=YES_WITH_DEADLINE")
    waitlist_carryover: CarryoverOption = Field(default=CarryoverOption.NO)
    waitlist_deadline: datetime | None = Field(None, description="Required when waitlist_carryover=YES_WITH_DEADLINE")
```

```python
# New EventType
PARTICIPANT_DROP_DUE = "game.participant_drop_due"
```

### API and Schema Documentation

Clone endpoint: `POST /api/games/{game_id}/clone`

- Auth: `can_manage_game` (host + bot manager + maintainer)
- Returns: the new `GameSession` response (same schema as game creation)
- Behaviour:
  1. Load source game and its participants (ordered by `position_type`, `position`)
  2. Create new `GameSession` copying all fields except `id`, `status`, `created_at`, `updated_at`, `message_id`; set `scheduled_at` from request
  3. Add carried-over participants in order (same `position_type`, recalculated `position`) — exactly as if they had clicked join
  4. For each carried-over participant: create `NotificationSchedule` (join_notification, existing mechanism)
  5. For `YES_WITH_DEADLINE` participants: also create `ParticipantActionSchedule` (action=`"drop"`, action_time=deadline)
  6. Publish `GAME_CREATED` event

### Configuration Examples

New daemon wrapper (`participant_action_daemon_wrapper.py`):

```python
daemon = SchedulerDaemon(
    database_url=BASE_DATABASE_URL,
    rabbitmq_url=rabbitmq_url,
    notify_channel="participant_action_schedule_changed",
    model_class=ParticipantActionSchedule,
    time_field="action_time",
    status_field="processed",
    event_builder=build_participant_action_event,
    _process_dlq=False,
)
```

New notification type for confirmation DM:

```python
schedule = NotificationSchedule(
    game_id=str(new_game.id),
    participant_id=participant.id,
    notification_type="clone_confirmation",
    notification_time=utc_now() + timedelta(seconds=60),
    sent=False,
    game_scheduled_at=new_game.scheduled_at,
    reminder_minutes=0,
)
```

### Technical Requirements

- `NotificationSchedule` has `UniqueConstraint("game_id", "reminder_minutes")` — this will conflict since multiple participants on the same game all have `reminder_minutes=0` for join notifications. Either the constraint needs updating or `reminder_minutes` must be nullable (it already is for `join_notification` based on the existing join handler setting it to `None`). Verify before writing the migration.
- `ParticipantActionSchedule.participant_id` should be `UNIQUE` — only one pending auto-drop per participant at a time.
- The confirmation DM button handler (bot service) must delete the `ParticipantActionSchedule` record on confirm and notify the postgres channel to wake the daemon.
- `participant_action_schedule_changed` NOTIFY must be sent when records are inserted or deleted (trigger or application code, consistent with existing pattern).

## Recommended Approach

Single "Clone Game" feature implemented as:

1. **New model** `ParticipantActionSchedule` + Alembic migration
2. **Refactor `GameService`** — extract `_persist_and_publish(game, participants, resolved_fields)` from `create_game` steps 5–8; add `clone_game(source_game_id, clone_data, host_user_id)` method that handles clone-specific setup then calls the same helper
3. **New API endpoint** `POST /api/games/{game_id}/clone` using `CloneGameRequest`, authorised via existing `can_manage_game`
4. **New `notification_type`** `"clone_confirmation"` handled by bot as a DM with confirm/decline buttons — bot view in `services/bot/views/`
5. **New `EventType`** `PARTICIPANT_DROP_DUE` + event builder + bot handler (executes existing drop logic)
6. **New daemon wrapper** `participant_action_daemon_wrapper.py` + Docker service entry
7. **Frontend** "Clone" button on game detail page → opens game creation form pre-filled + clone-specific options (carryover selectors, deadline pickers)
8. **`DMFormats`** additions for `"clone_confirmation"` message text
9. **No permission system changes** — `can_manage_game` already covers host + bot manager + maintainer

## Implementation Guidance

- **Objectives**: Allow hosts to repeat games with optional participant carry-over, minimising new code by reusing existing scheduler, notification, participant, and drop mechanisms
- **Dependencies**: No new external libraries required

### Phase 1 — Foundation (safe, no behaviour change)

All existing tests pass unchanged. Dev environment fully runnable.

- New Alembic migration adding `ParticipantActionSchedule` table (unused by application code yet)
- Refactor `GameService.create_game` to extract `_persist_and_publish` helper — pure internal restructuring, no observable behaviour change
- `CarryoverOption` enum + `CloneGameRequest` schema

**Tests**:

- _Unit_: `_persist_and_publish` helper behaves identically to the original `create_game` steps it replaced
- _Integration_: migration applies and rolls back cleanly; `ParticipantActionSchedule` table exists in schema
- All existing tests pass unchanged

### Phase 2 — Clone with `YES`/`NO` carryover

Fully functional and end-to-end testable. Dev environment runnable. `YES_WITH_DEADLINE` is not yet exposed anywhere.

- `GameService.clone_game` using the extracted helper
- `POST /api/games/{game_id}/clone` route (accepts `YES` and `NO` only; `YES_WITH_DEADLINE` accepted by schema but rejected with 422 at the service layer)
- Frontend: Clone button on game detail page → pre-filled game creation form with carryover selectors offering `YES` and `NO` only (deadline option not rendered)

**Tests**:

- _Unit_: `clone_game` copies all fields correctly; `YES` carries over participants in order; `NO` discards them; `YES_WITH_DEADLINE` raises at service layer; `can_manage_game` enforced
- _Integration_: `POST /api/games/{game_id}/clone` creates new game in DB with correct participants; `join_notification` schedule records created for carried-over participants; RabbitMQ receives `GAME_CREATED` event; host/bot-manager/maintainer access verified
- _E2E_: clone a game via API, verify new game announcement appears in Discord channel, verify carried-over participants receive join DMs (mirrors existing `test_join_notification.py` pattern)

### Phase 3 — Drop event + handler

`PARTICIPANT_DROP_DUE` event type, event builder, and bot handler that executes the existing drop logic. Nothing fires it in production yet — exercised by unit/integration tests only.

**Tests**:

- _Unit_: bot handler correctly removes participant and publishes `GAME_UPDATED` when `PARTICIPANT_DROP_DUE` received; removal DM sent via `DMFormats.removal`
- _Integration_: publish `PARTICIPANT_DROP_DUE` event to RabbitMQ queue directly; verify participant record removed from DB and `GAME_UPDATED` event published (mirrors existing `test_player_removal` integration pattern)

### Phase 4 — Confirmation DM format + bot view

`DMFormats` entries for confirmation DM text + bot DM view with confirm/decline buttons. The decline button triggers the drop handler from Phase 3. The confirm button deletes the `ParticipantActionSchedule` record. `YES_WITH_DEADLINE` still not reachable in production (422 guard still in place).

**Tests**:

- _Unit_: `DMFormats` confirmation message formats correctly with game title and deadline; confirm button interaction deletes `ParticipantActionSchedule` record; decline button interaction triggers drop handler from Phase 3

### Phase 5 — `clone_confirmation` notification type

Wire `"clone_confirmation"` as a handled `notification_type` in the bot's notification handler, using the DM view from Phase 4. The notification daemon already fires `join_notification` and `reminder` — this adds a third type.

**Tests**:

- _Integration_: insert `clone_confirmation` `NotificationSchedule` record directly into DB; verify notification daemon fires it; verify `NOTIFICATION_SEND_DM` event published to RabbitMQ with correct payload (mirrors `TestNotificationDaemonIntegration` pattern in `test_notification_daemon.py`)

### Phase 6 — Participant action daemon

`participant_action_daemon_wrapper.py` + Docker compose service entry. This is what fires `PARTICIPANT_DROP_DUE` at the deadline in production. Full `YES_WITH_DEADLINE` flow now works end-to-end in a dev environment.

**Tests**:

- _Integration_: insert `ParticipantActionSchedule` record with past `action_time`; verify daemon fires `PARTICIPANT_DROP_DUE` event to RabbitMQ; verify `processed` flag set (mirrors `TestNotificationDaemonIntegration` pattern)

### Phase 7 — Frontend + remove 422 guard

Add `YES_WITH_DEADLINE` option and deadline datetime picker to the frontend carryover selectors. Remove the 422 guard from the service layer. The feature is now fully exposed to users.

**Tests**:

- _Unit_: `clone_game` service correctly creates `ParticipantActionSchedule` records when `YES_WITH_DEADLINE` selected
- _Integration_: `POST /api/games/{game_id}/clone` with `YES_WITH_DEADLINE` creates both participant records and `ParticipantActionSchedule` records in DB
- _E2E_: clone a game with `YES_WITH_DEADLINE`; verify carried-over participants receive confirmation DM containing confirm/decline buttons; verify participant is auto-dropped after deadline expires (daemon-driven path, no user interaction required). Button interaction (confirm path) cannot be e2e tested as real user credentials are not available in the test environment — covered by unit tests in Phase 4 instead.

### Overall Success Criteria

- Host can clone a game from any status
- Players/waitlist carried over in original order, treated as normal participants from that point
- Bot managers and maintainers can clone any game (via existing `can_manage_game`)
- All existing game mechanics (waitlist promotion, cap enforcement, reminders) work unchanged on the cloned game
