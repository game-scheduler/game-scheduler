<!-- markdownlint-disable-file -->
# Task Research Notes: Signup Instructions DM on Game Entry

## Research Executed

### File Analysis

- `shared/schemas/game.py` (Lines 118-122)
  - `signup_instructions: str | None` field exists on GameResponse
  - Max length 1000 characters, optional field
- `services/bot/formatters/game_message.py` (Lines 118-169)
  - Signup instructions currently displayed in embed on game announcement card
  - Shown as "Signup Instructions" field in Discord embed, truncated to 400 chars
- `frontend/src/pages/GameDetails.tsx` (Lines 189-210)
  - Frontend displays signup_instructions in info box on game detail page
  - Blue info box with "ℹ️ Signup Instructions" header
- `services/bot/events/handlers.py` (Lines 425-468)
  - `_send_dm(user_discord_id, message)` method available for sending DMs
  - Handles discord.Forbidden (DMs disabled) and discord.HTTPException gracefully
  - Returns bool indicating success/failure
- `services/api/services/games.py` (Lines 806-884)
  - `join_game()` creates participant, commits to DB, publishes game.updated event
  - No DM sending logic currently present
- `services/bot/handlers/join_game.py` (Lines 78-96)
  - Bot handler creates participant in DB on button click
  - Publishes game.updated event after successful join
  - Sends success DM but not signup instructions

### Code Search Results

- `waitlist|overflow` searches
  - Participants beyond max_players are considered "overflow" (waitlist)
  - Logic in bot formatters splits participants into confirmed vs overflow
  - No automatic promotion notification currently exists when moving from waitlist to confirmed
- `add_participant|remove_participant` patterns
  - `_remove_participants()` in games.py service publishes participant.removed events
  - `_add_new_mentions()` resolves @mentions and creates GameParticipant records
  - Pre-filled participants created with `pre_filled_position` field
  - Events published: `game.player_removed`, `game.updated`
- Current DM sending patterns
  - Game reminders: `_handle_game_reminder_due()` sends DMs to all participants
  - Player removed: `_handle_player_removed()` sends DM "❌ You were removed from **{title}**"
  - Both use existing `_send_dm(user_discord_id, message)` helper

### Event System Research

- **RabbitMQ Event Types** (`shared/messaging/events.py`)
  - `GAME_UPDATED = "game.updated"` - Published when game changes
  - `PLAYER_REMOVED = "game.player_removed"` - Published when participant removed
  - `GAME_REMINDER_DUE = "game.reminder_due"` - Published when reminder time reached
  - `NOTIFICATION_SEND_DM = "notification.send_dm"` - Individual DM event (deprecated pattern)
  - `WAITLIST_ADDED = "game.waitlist_added"` - Event type exists but not used
  - `WAITLIST_REMOVED = "game.waitlist_removed"` - Event type exists but not used

### Current Messaging Architecture

**Direct Integration Pattern** (Currently Used):
- Bot handlers send DMs synchronously when processing events
- No intermediate queuing for DM delivery
- Example: `_handle_player_removed()` calls `_send_dm()` directly
- Example: Join button handler sends success DM immediately

**Delayed Execution Capabilities**:
- No Celery currently (was removed in favor of database-backed scheduler)
- Generic scheduler daemon (`services/scheduler/generic_scheduler_daemon.py`) for scheduled events
- Database-backed schedules with PostgreSQL LISTEN/NOTIFY for efficiency
- RabbitMQ delayed message exchange plugin NOT installed
- No APScheduler integration

### Three Scenarios for Signup Instructions DM

#### Scenario 1: Host Adds Participant (Pre-filled)
- **Trigger**: API call to `update_game()` with `initial_participants` containing @mentions
- **Current Flow**:
  1. `services/api/services/games.py::_add_new_mentions()` creates participants
  2. Each created with `pre_filled_position` field set
  3. `game.updated` event published to RabbitMQ
  4. Bot refreshes Discord message via `_handle_game_updated()`
- **No removal tracking**: User might be removed before 1-minute delay expires

#### Scenario 2: User Clicks Join Button
- **Trigger**: Discord button interaction
- **Current Flow**:
  1. `services/bot/handlers/join_game.py::handle_join_game()` creates participant
  2. Commits to database with `user_id` (not pre-filled, no position)
  3. Publishes `game.updated` event to RabbitMQ
  4. Sends immediate success DM: "✅ You've joined **{game.title}**!"
  5. Bot refreshes Discord message

#### Scenario 3: Promotion from Waitlist
- **Current Behavior**: No explicit promotion detection or notification
- **Implicit Promotion**: Happens when confirmed participant leaves OR max_players increased
- **No Event**: System does not track or publish waitlist → confirmed transitions
- **Research Note**: Task 12.19 in original plan (Lines 1757-1792) addressed promotion notifications but may not be fully implemented

## Key Discoveries

### Delayed Task Execution Options

**Option 1: RabbitMQ Message TTL + Delayed Queue**
- Requires RabbitMQ delayed message exchange plugin (NOT currently installed)
- Plugin is deprecated, "badly needs new design" per README
- Introduces complexity and single point of failure (Mnesia table)

**Option 2: Database Schedule Table**
- Create `signup_instruction_schedule` table similar to `notification_schedule`
- Use existing scheduler daemon pattern with PostgreSQL LISTEN/NOTIFY
- Highly efficient, scalable, reliable (proven pattern in codebase)
- Natural cancellation: delete schedule record if participant removed

**Option 3: In-Process Timer**
- Schedule task 60 seconds in future when participant added
- Fragile: loses all pending DMs on bot restart/crash
- Not suitable for production reliability requirements

**Option 4: Celery with ETA**
- Celery was removed from project architecture
- Would require re-introducing entire Celery infrastructure
- Research shows project moved to database-backed scheduler intentionally

### Participant Addition Complexity

**Multiple Addition Paths**:
1. API service: `games.py::_add_new_mentions()` for pre-filled participants
2. Bot handler: `join_game.py::handle_join_game()` for button clicks
3. API service: `games.py::join_game()` for web UI joins

**Removal Before Delay**:
- User might be removed (via API or button) before 1-minute delay expires
- Schedule must track participant_id to enable cancellation
- On removal, corresponding schedule entry must be deleted
- `_remove_participants()` already handles removal events

**Waitlist Promotion Detection**:
- No explicit event currently fired for waitlist → confirmed promotion
- Would need to compare participant lists before/after game updates
- Complex logic: confirmed list determined by sorting + max_players cutoff
- Research reference: `.copilot-tracking/details/20251114-discord-game-scheduling-system-details.md` (Lines 1757-1792)

## Recommended Approach: Unified Notification System with Delayed Join Notification

### Extend Existing `notification_schedule` Table

**SELECTED APPROACH**: Reuse existing notification daemon and schedule table by adding two columns to support both game-wide reminders and participant-specific notifications. **Key simplification**: Replace immediate join notification with single delayed notification that conditionally includes signup instructions.

**Current `notification_schedule` Schema:**
- `id` (UUID primary key)
- `game_id` (FK to game_sessions)
- `reminder_minutes` (int, for game reminders)
- `notification_time` (timestamp, indexed)
- `game_scheduled_at` (timestamp, for TTL calculation)
- `sent` (boolean)

**Proposed Schema Changes (2 new columns):**
- `participant_id` (nullable FK to game_participants, CASCADE delete)
  - NULL = game-wide reminder (existing behavior)
  - UUID = participant-specific notification (new: join notification)
- `notification_type` (enum string: 'reminder', 'join_notification')
  - Distinguishes notification purpose
  - Defaults to 'reminder' for backward compatibility

**Event Payload Enhancement:**
```python
# Rename: GAME_REMINDER_DUE → NOTIFICATION_DUE
class NotificationDueEvent(BaseModel):
    """Generalized notification event for reminders and join notifications."""
    game_id: UUID
    notification_type: str  # 'reminder' or 'join_notification'
    reminder_minutes: int | None  # populated for reminders, null for join
    participant_id: str | None    # null for reminders, populated for join
```

**Bot Handler Routing Logic:**
```python
async def _handle_notification_due(self, data: dict[str, Any]) -> None:
    """Route to appropriate handler based on notification type."""
    event = NotificationDueEvent(**data)

    if event.notification_type == 'reminder':
        # Existing: query game, iterate all participants, send reminders
        await self._send_game_reminders(event.game_id, event.reminder_minutes)

    elif event.notification_type == 'join_notification':
        # New: send delayed join notification (with signup instructions if present)
        await self._send_join_notification(event.game_id, event.participant_id)
```

**Join Notification Message Format:**
```python
# If signup_instructions exist:
message = (
    f"✅ **You've joined {game.title}**\n\n"
    f"📋 **Signup Instructions**\n"
    f"{game.signup_instructions}\n\n"
    f"Game starts <t:{int(game.scheduled_at.timestamp())}:R>"
)

# If no signup_instructions:
message = f"✅ You've joined **{game.title}**!"
```

**Advantages**:
✅ **Single notification** - user receives only one DM when joining (after 60 second delay)
✅ **Conditional content** - includes signup instructions when present, generic message when absent
✅ **Single daemon** - no new infrastructure, reuse existing notification daemon
✅ **Single schedule table** - unified data model, simpler schema
✅ **Same LISTEN/NOTIFY channel** - efficient PostgreSQL notifications
✅ **Same RabbitMQ routing** - one event type handles both use cases
✅ **Backward compatible** - existing reminders continue working unchanged
✅ **Natural cancellation** - CASCADE delete when participant removed
✅ **Proven reliability** - leverages battle-tested scheduler infrastructure
✅ **TTL support** - inherits game_scheduled_at for message expiration
✅ **Unified testing** - one daemon, one event flow to test
✅ **Simplified flow** - removes immediate DM, only sends delayed notification

**Key Behavior Changes:**
- ❌ **Remove**: Immediate "✅ You've joined" DM sent by join handlers
- ✅ **Add**: 60-second delayed notification schedule created on join
- ✅ **Add**: Notification includes signup instructions if available
- ✅ **Keep**: Generic "You've joined" message if no signup instructions
- ✅ **Cancellation**: No notification sent if user removed before 60 seconds

**Participant Addition Hook Points**:
- API: `services/api/services/games.py::_add_new_mentions()` - after participant creation
- Bot: `services/bot/handlers/join_game.py::handle_join_game()` - **REMOVE immediate DM**, create schedule
- API: `services/api/services/games.py::join_game()` - **REMOVE immediate success message**, create schedule

**Schedule Creation Example:**
```python
# When participant added (replaces immediate DM):
schedule = NotificationSchedule(
    game_id=game_id,
    participant_id=participant_id,
    notification_type='join_notification',
    notification_time=utc_now() + timedelta(seconds=60),
    sent=False,
    game_scheduled_at=game.scheduled_at,  # for TTL calculation
    reminder_minutes=None  # not applicable for join notifications
)
```

**Participant Removal Hook Points**:
- API: `services/api/services/games.py::_remove_participants()` - CASCADE handles cleanup
- Explicit deletion optional but provides clearer logging

**Waitlist Promotion**:
- Phase 1: Skip waitlist promotion (focus on explicit additions)
- Phase 2 (optional): Add promotion detection logic
  - Compare previous vs current confirmed participant lists
  - Identify newly promoted participants
  - Create schedule entries for promoted participants only

## Alternative Approaches (Not Selected)

### Immediate DM Without Delay

Send DM immediately when user joins, include signup instructions if present.

**Disadvantages**:
- ❌ Does not satisfy "1-minute delay" requirement
- ❌ Users who join then immediately leave still receive DM
- ❌ Cannot be cancelled once sent
- ❌ Creates notification spam if user changes mind quickly

**Why Not Selected**: User explicitly requested delayed notification to avoid spam and allow cancellation window.

### Separate Event Type for Signup Instructions

Create `SIGNUP_INSTRUCTIONS_DUE` event type separate from join notification.

**Disadvantages**:
- ❌ Creates two notifications: immediate "You've joined" + delayed "Here are instructions"
- ❌ More complex: requires two event types, two handlers, two message formats
- ❌ User receives two DMs instead of one unified notification

**Why Not Selected**: User requested single consolidated notification, not separate messages.

## Implementation Guidance

### Recommended: Unified Notification System with Delayed Join Notification

**Phase 1: Extend notification_schedule Schema**

1. **Create Alembic Migration** (`alembic/versions/0XX_add_notification_type_participant_id.py`)
   ```python
   """Add notification_type and participant_id to notification_schedule."""

   def upgrade() -> None:
       # Add notification_type column
       op.add_column(
           'notification_schedule',
           sa.Column('notification_type', sa.String(50), nullable=False,
                    server_default='reminder')
       )

       # Add participant_id column (nullable, CASCADE delete)
       op.add_column(
           'notification_schedule',
           sa.Column('participant_id', sa.String(36), nullable=True)
       )

       # Add foreign key constraint
       op.create_foreign_key(
           'fk_notification_schedule_participant_id',
           'notification_schedule',
           'game_participants',
           ['participant_id'],
           ['id'],
           ondelete='CASCADE'
       )

       # Add index for participant_id lookups
       op.create_index(
           'ix_notification_schedule_participant_id',
           'notification_schedule',
           ['participant_id']
       )

       # Add composite index for efficient queries
       op.create_index(
           'ix_notification_schedule_type_time',
           'notification_schedule',
           ['notification_type', 'notification_time']
       )

   def downgrade() -> None:
       op.drop_index('ix_notification_schedule_type_time')
       op.drop_index('ix_notification_schedule_participant_id')
       op.drop_constraint('fk_notification_schedule_participant_id',
                         'notification_schedule', type_='foreignkey')
       op.drop_column('notification_schedule', 'participant_id')
       op.drop_column('notification_schedule', 'notification_type')
   ```

2. **Update Model** (`shared/models/notification_schedule.py`)
   ```python
   class NotificationSchedule(Base):
       # ... existing fields ...

       notification_type: Mapped[str] = mapped_column(
           String(50),
           nullable=False,
           default='reminder',
           server_default=text("'reminder'")
       )

       participant_id: Mapped[str | None] = mapped_column(
           ForeignKey("game_participants.id", ondelete="CASCADE"),
           nullable=True,
           index=True
       )

       participant: Mapped["GameParticipant"] = relationship(
           "GameParticipant",
           foreign_keys=[participant_id]
       )
   ```

3. **Rename Event Type** (`shared/messaging/events.py`)
   ```python
   # Replace GAME_REMINDER_DUE with NOTIFICATION_DUE
   class EventType(str, Enum):
       # ... other events ...
       NOTIFICATION_DUE = "game.notification_due"  # was: game.reminder_due

   class NotificationDueEvent(BaseModel):
       """Generalized notification event."""
       game_id: UUID
       notification_type: str  # 'reminder' or 'signup_instructions'
       participant_id: str | None = None
   ```

   **Note**: `reminder_minutes` removed from event payload - kept only in database for unique constraint and schedule management. Bot handlers don't need it for formatting.

4. **Update Event Builder** (`services/scheduler/event_builders.py`)
   ```python
   def build_notification_event(
       notification: NotificationSchedule
   ) -> tuple[Event, int | None]:
       """Build NOTIFICATION_DUE event with TTL support."""

       event_data = NotificationDueEvent(
           game_id=UUID(notification.game_id),
           notification_type=notification.notification_type,
           participant_id=notification.participant_id,
       )

       event = Event(
           event_type=EventType.NOTIFICATION_DUE,
           data=event_data.model_dump(),
       )

       # Calculate TTL (same logic as before)
       expiration_ms = None
       if notification.game_scheduled_at:
           time_until_game = (
               notification.game_scheduled_at - utc_now()
           ).total_seconds()
           expiration_ms = int(time_until_game * 1000) if time_until_game > 60 else 60000

       return event, expiration_ms
   ```

5. **Update Daemon Wrapper** (`services/scheduler/notification_daemon_wrapper.py`)
   ```python
   # Change event_builder reference from:
   event_builder=build_game_reminder_event
   # To:
   event_builder=build_notification_event
   ```

6. **Update RabbitMQ Infrastructure** (`shared/messaging/infrastructure.py` and `scripts/init_rabbitmq.py`)
   - Change binding from `"game.reminder_due"` to `"game.notification_due"`
   - Or keep both during migration period for backward compatibility

**Phase 2: Schedule Creation on Participant Addition**

1. **Add Schedule Helper Function** (`services/api/services/notification_schedule.py` - new file)
   ```python
   """Helper functions for managing notification schedules."""
   from datetime import timedelta
   from sqlalchemy.ext.asyncio import AsyncSession
   from shared.models import NotificationSchedule, GameSession
   from shared.models.base import utc_now

   async def schedule_join_notification(
       db: AsyncSession,
       game_id: str,
       participant_id: str,
       game_scheduled_at,
       delay_seconds: int = 60
   ) -> NotificationSchedule:
       """Create schedule entry to send join notification after delay."""
       send_time = utc_now() + timedelta(seconds=delay_seconds)

       schedule = NotificationSchedule(
           game_id=game_id,
           participant_id=participant_id,
           notification_type='join_notification',
           notification_time=send_time,
           game_scheduled_at=game_scheduled_at,  # for TTL
           sent=False,
           reminder_minutes=None  # not applicable
       )
       db.add(schedule)
       await db.flush()
       return schedule
   ```

   **Note**: Leverage CASCADE Delete for automatic cleanup
   - Foreign key `ON DELETE CASCADE` automatically removes schedules when participant deleted
   - No explicit deletion code needed in `_remove_participants()`
   - More reliable than manual cleanup (atomic with participant deletion)

2. **Update API Service** (`services/api/services/games.py`)
   ```python
   from .notification_schedule import schedule_join_notification

   async def _add_new_mentions(self, game, new_mentions):
       """Add pre-filled participants and schedule join notifications."""
       # ... existing mention creation logic ...
       for participant in created_participants:
           # Schedule join notification (replaces immediate notification)
           await schedule_join_notification(
               self.db,
               game.id,
               participant.id,
               game.scheduled_at
           )

   async def join_game(self, game_id: str, user_discord_id: str):
       """Join game and schedule delayed join notification."""
       # ... existing join logic ...
       await self.db.commit()
       await self.db.refresh(participant)

       # Schedule join notification (replaces immediate success DM)
       await schedule_join_notification(
           self.db,
           game.id,
           participant.id,
           game.scheduled_at
       )

       return participant
   ```

3. **Update Bot Button Handler** (`services/bot/handlers/join_game.py`)
   ```python
   async def handle_join_game(interaction, game_id: UUID):
       """Handle join game button click."""
       # ... existing participant creation logic ...
       await db.commit()

       # REMOVE: Old immediate success DM
       # success_dm = f"✅ You've joined **{game.title}**!"
       # await _send_dm(user_discord_id, success_dm)

       # NEW: Schedule delayed join notification
       from shared.models import NotificationSchedule
       from datetime import timedelta
       from shared.models.base import utc_now

       schedule = NotificationSchedule(
           game_id=str(game_id),
           participant_id=participant.id,
           notification_type='join_notification',
           notification_time=utc_now() + timedelta(seconds=60),
           game_scheduled_at=game.scheduled_at,
           sent=False,
           reminder_minutes=None
       )
       db.add(schedule)
       await db.commit()

       # Update button response (no DM, just visual confirmation)
       await interaction.response.edit_message(view=updated_view)
   ```

**Phase 3: Update Bot Event Handler**

1. **Rename and Extend Handler** (`services/bot/events/handlers.py`)
   ```python
   # Rename: _handle_game_reminder_due → _handle_notification_due
   async def _handle_notification_due(self, data: dict[str, Any]) -> None:
       """
       Handle game.notification_due event.

       Routes to appropriate handler based on notification_type:
       - 'reminder': Send DMs to all game participants
1. **Rename and Extend Handler** (`services/bot/events/handlers.py`)
   ```python
   # Rename: _handle_game_reminder_due → _handle_notification_due
   async def _handle_notification_due(self, data: dict[str, Any]) -> None:
       """
       Handle game.notification_due event.

       Routes to appropriate handler based on notification_type:
       - 'reminder': Send DMs to all game participants
       - 'join_notification': Send delayed join confirmation with optional signup instructions
       """
       logger.info(f"=== Received game.notification_due event: {data} ===")

       try:
           event = NotificationDueEvent(**data)
       except Exception as e:
           logger.error(f"Invalid notification event data: {e}", exc_info=True)
           return

       # Route based on notification type
       if event.notification_type == 'reminder':
           await self._handle_game_reminder(event)
       elif event.notification_type == 'join_notification':
           await self._handle_join_notification(event)
       else:
           logger.error(f"Unknown notification_type: {event.notification_type}")

   async def _handle_game_reminder(self, event: NotificationDueEvent) -> None:
       """Send game reminders to all participants (existing logic)."""
       # Move existing _handle_game_reminder_due logic here
       # ... query game, iterate participants, send reminders ...

   async def _handle_join_notification(self, event: NotificationDueEvent) -> None:
       """Send delayed join notification with optional signup instructions."""
       async with get_db_session() as db:
           # Query game and participant
           game = await self._get_game_with_participants(db, str(event.game_id))

           participant_result = await db.execute(
               select(GameParticipant).where(
                   GameParticipant.id == event.participant_id
               )
           )
           participant = participant_result.scalar_one_or_none()

           # Verify participant still exists
           if not participant or not participant.user:
               logger.info(f"Participant {event.participant_id} no longer active")
               return

           # Check if participant is on waitlist (optional: may want to skip or send different message)
           confirmed_participants = sort_participants(
               [p for p in game.participants if p.user_id is not None]
           )[:game.max_players or 10]

           if participant not in confirmed_participants:
               logger.info(
                   f"Participant {event.participant_id} is waitlisted, "
                   "skipping join notification"
               )
               return

           # Format message based on whether signup_instructions exist
           if game.signup_instructions:
               message = (
                   f"✅ **You've joined {game.title}**\n\n"
                   f"📋 **Signup Instructions**\n"
                   f"{game.signup_instructions}\n\n"
                   f"Game starts <t:{int(game.scheduled_at.timestamp())}:R>"
               )
           else:
               message = f"✅ You've joined **{game.title}**!"

           success = await self._send_dm(participant.user.discord_id, message)
           if success:
               logger.info(
                   f"✓ Sent join notification to {participant.user.discord_id} "
                   f"for game {event.game_id}"
               )
   ```

2. **Update Handler Registration** (`services/bot/events/handlers.py`)
   ```python
   def __init__(self, bot: discord.Client):
       self.bot = bot
       self.handlers = {
           # Update registration:
           EventType.NOTIFICATION_DUE: self._handle_notification_due,
           # ... other handlers ...
       }
   ```

**Phase 4: Update Tests and Documentation**

1. **Update Existing Tests**
   - Rename test methods referencing `game.reminder_due` → `game.notification_due`
   - Update event type checks in assertions
   - Add tests for notification_type field in NotificationSchedule

2. **Add New Tests** (`tests/services/bot/events/test_handlers.py`)
   ```python
   @pytest.mark.asyncio
   async def test_handle_join_notification_with_signup_instructions(
       event_handlers, sample_game
   ):
       """Test join notification includes signup instructions when present."""
       sample_game.signup_instructions = "Join our Discord server at ..."
       participant = create_test_participant(sample_game)

       data = {
           "game_id": sample_game.id,
           "notification_type": "join_notification",
           "participant_id": participant.id,
       }

       with patch.object(event_handlers, "_send_dm", return_value=True):
           await event_handlers._handle_notification_due(data)

           # Verify DM sent with signup instructions
           event_handlers._send_dm.assert_called_once()
           message = event_handlers._send_dm.call_args[0][1]
           assert "✅ **You've joined" in message
           assert "📋 **Signup Instructions**" in message
           assert "Join our Discord server at ..." in message

   @pytest.mark.asyncio
   async def test_handle_join_notification_without_signup_instructions(
       event_handlers, sample_game
   ):
       """Test join notification uses generic message when no signup instructions."""
       sample_game.signup_instructions = None
       participant = create_test_participant(sample_game)

       data = {
           "game_id": sample_game.id,
           "notification_type": "join_notification",
           "participant_id": participant.id,
       }

       with patch.object(event_handlers, "_send_dm", return_value=True):
           await event_handlers._handle_notification_due(data)

           # Verify generic DM sent
           event_handlers._send_dm.assert_called_once()
           message = event_handlers._send_dm.call_args[0][1]
           assert message == f"✅ You've joined **{sample_game.title}**!"
           assert "Signup Instructions" not in message
   ```

3. **NO Docker Changes Needed**
   - Existing `notification-daemon` service handles both notification types
   - No new daemon, no new container
   - No compose file changes required

**Success Criteria**:
- User joins game → NO immediate DM sent
- 60 seconds later → receives single DM with join confirmation
- DM includes signup instructions if game has them
- DM uses generic "You've joined" message if no signup instructions
- User removed before 60 seconds → no DM sent (CASCADE cleanup)
**Success Criteria**:
- User joins game → NO immediate DM sent
- 60 seconds later → receives single DM with join confirmation
- DM includes signup instructions if game has them
- DM uses generic "You've joined" message if no signup instructions
- User removed before 60 seconds → no DM sent (CASCADE cleanup)
- Daemon survives restarts (schedules persist in database)
- No DM sent if participant moved to waitlist before send time

**Testing Strategy**:
1. Unit tests: Schedule creation, event building, message formatting
2. Integration tests: End-to-end flow with actual database and RabbitMQ
3. E2E tests: Real Discord bot interactions with 60-second delay timing
4. Test both scenarios: with and without signup instructions

## Alternative: Waitlist Promotion Detection

If requirement includes notifying users promoted from waitlist to confirmed:

**Detection Logic** (in `services/api/services/games.py::update_game()`):
```python
async def _detect_promoted_participants(
    self,
    game: GameSession,
    previous_participants: list[GameParticipant]
) -> list[str]:
    """Detect participants promoted from waitlist to confirmed."""
    # Get current participant state
    current_result = await self.db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == game.id)
        .where(GameParticipant.user_id.isnot(None))
    )
    current_participants = current_result.scalars().all()

    # Sort both lists
    previous_sorted = sort_participants(previous_participants)
    current_sorted = sort_participants(current_participants)

    max_players = game.max_players or 10

    # Determine previous and current confirmed sets
    previous_confirmed_ids = {p.id for p in previous_sorted[:max_players]}
    current_confirmed_ids = {p.id for p in current_sorted[:max_players]}

    # Promoted = in current confirmed but not in previous confirmed
    promoted_ids = current_confirmed_ids - previous_confirmed_ids

    return list(promoted_ids)
```

**Integration Point**:
- Call after `_remove_participants()` or `_update_prefilled_participants()`
- Create signup instruction schedules for promoted participants
- Log promotion events for debugging

**Complexity**: High - requires careful state tracking and testing

## Dependencies

- PostgreSQL with LISTEN/NOTIFY support (already present)
- RabbitMQ message broker (already present)
- SQLAlchemy async (already present)
- Alembic for migrations (already present)
- Existing scheduler daemon infrastructure (already present)

## Migration Path

1. Deploy database migration (add notification_type and participant_id columns to notification_schedule)
2. Deploy API changes (schedule creation hooks, remove immediate success DMs)
3. Deploy bot changes (event handler for join_notification, remove immediate DMs)
4. Deploy daemon wrapper changes (use build_notification_event)
5. Verify with test games (manual testing with 60-second delays)
6. Monitor logs for schedule creation/processing/cancellation
7. Gradual rollout to production

## Future Enhancements

- Make delay configurable per game template (default 60 seconds)
- Add configuration option to disable delayed notifications entirely
- Support for rich text / Markdown in signup instructions DM
- Analytics: track how many users receive notifications vs drop before delay
- Retry logic if DM fails (user had DMs disabled temporarily)
- Consider promotion notifications (waitlist → confirmed) as separate feature
