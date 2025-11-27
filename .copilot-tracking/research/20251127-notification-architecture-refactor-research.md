<!-- markdownlint-disable-file -->
# Task Research Notes: Notification Architecture Refactor

## Research Executed

### Current Notification Flow Analysis
- **services/scheduler/tasks/check_notifications.py**
  - Scheduler queries `GameSession` with `selectinload(participants)`
  - Iterates through each participant individually (lines 106-130)
  - Creates one Celery task per participant per reminder time
  - Tracks notifications with Redis keys like `{game_id}_{user_id}_{reminder_min}`
  
- **services/scheduler/tasks/send_notification.py**
  - Receives individual participant notification task
  - Queries database for both game and user
  - Creates `NotificationSendDMEvent` with pre-formatted message
  - Publishes one RabbitMQ event per participant

- **services/scheduler/services/notification_service.py** (lines 45-75)
  - Formats message: `"Your game '{game_title}' starts <t:{game_time_unix}:R> (in {reminder_minutes} minutes)"`
  - Creates `NotificationSendDMEvent` with user_id, game details, pre-built message
  - Publishes to RabbitMQ with routing key `notification.send_dm`

### Bot's Existing Participant Logic
- **services/bot/events/handlers.py** (lines 395-405)
  - Bot already queries games with `selectinload(GameSession.participants).selectinload(GameParticipant.user)`
  - Uses `participant_sorting.sort_participants()` to order by `pre_filled_position` then `joined_at`
  - Splits into confirmed vs overflow based on `max_players`
  - Example: `confirmed = sorted[:max_players]`, `overflow = sorted[max_players:]`

- **shared/models/participant.py**
  - `pre_filled_position: int | None` - For host-specified ordering
  - `user_id: str | None` - When NULL, it's a placeholder participant
  - `display_name: str | None` - For placeholder entries only
  - Constraint: Either `user_id` is set OR `display_name` is set, never both

- **services/bot/formatters/game_message.py**
  - Receives separate lists: `participant_ids` (active) and `overflow_ids` (waitlist)
  - Formats with sections "👥 Players (X/Y)" and "🎫 Waitlist (Z)"

## Key Discoveries

### Architecture Problems Identified

1. **Duplicated Business Logic**
   - Scheduler queries participants to determine who gets notifications
   - Bot queries participants to determine game roster and waitlist status
   - Both services understand participant lists, but only bot has sorting logic

2. **Inefficient Messaging**
   - For game with 10 participants and 2 reminder times (60min, 15min):
   - Current: 20 Celery tasks + 20 RabbitMQ messages
   - Proposed: 2 Celery tasks + 2 RabbitMQ messages (one per reminder time)

3. **Tight Coupling**
   - Scheduler needs to know about user_id vs display_name distinction
   - Scheduler builds notification message format (duplicates bot's formatting logic)
   - Scheduler makes participant-level decisions outside its responsibility

4. **Redis Key Management**
   - Current: `notification_sent:{game_id}_{user_id}_{reminder_min}` (per participant)
   - Proposed: `notification_sent:{game_id}_{reminder_min}` (per game)
   - Simpler deduplication with 90% fewer Redis keys

### Participant Types and Filtering

From analysis of the models and bot code:
- **Real Participants**: `user_id IS NOT NULL` - Can receive notifications
- **Placeholder Participants**: `user_id IS NULL, display_name IS NOT NULL` - Cannot receive notifications
- **Waitlist Participants**: Position > max_players (bot determines this dynamically)

The scheduler currently filters with:
```python
participants = [p for p in game_session.participants if p.user_id is not None]
```

This logic belongs in the bot, which already has this knowledge for message formatting.

## Recommended Approach

### New Event Schema

Create new event type `GAME_REMINDER_DUE` to replace `NOTIFICATION_SEND_DM`:

```python
class EventType(str, Enum):
    # ... existing events ...
    GAME_REMINDER_DUE = "game.reminder_due"  # NEW
    NOTIFICATION_SEND_DM = "notification.send_dm"  # Keep for individual DMs

class GameReminderDueEvent(BaseModel):
    """Payload for game.reminder_due event."""
    game_id: UUID
    reminder_minutes: int
```

### Refactored Architecture

**Scheduler Responsibilities (Simplified)**:
1. Check for games in notification window
2. Determine reminder times based on game/channel/guild settings
3. Schedule one Celery task per reminder per game
4. Publish one `game.reminder_due` event per reminder
5. Track with simple Redis key: `notification_sent:{game_id}_{reminder_min}`

**Bot Responsibilities (Enhanced)**:
1. Receive `game.reminder_due` event
2. Query game with participants (already does this)
3. Sort participants by `pre_filled_position` and `joined_at` (already does this)
4. Filter to only real participants (`user_id IS NOT NULL`)
5. Determine active vs waitlist based on `max_players` (already does this)
6. Format and send DM to each eligible participant
7. Handle Discord API errors per-user (Forbidden, NotFound, etc.)

### Implementation Steps

1. **Add New Event Type** (`shared/messaging/events.py`)
   - Add `GAME_REMINDER_DUE` to `EventType` enum
   - Create `GameReminderDueEvent` model with `game_id` and `reminder_minutes`

2. **Simplify Scheduler** (`services/scheduler/tasks/check_notifications.py`)
   - Remove participant iteration loop (lines 106-130)
   - Schedule one task per game per reminder time instead of per participant
   - Update Redis key format to `{game_id}_{reminder_min}` (remove user_id)
   - Remove participant loading from query (no longer needed)

3. **Update Scheduler Notification Task** (`services/scheduler/tasks/send_notification.py`)
   - Rename to `send_game_reminder_due` or similar
   - Change signature: `(game_id: str, reminder_minutes: int)` (remove user_id)
   - Remove user lookup logic
   - Publish `GAME_REMINDER_DUE` event instead of `NOTIFICATION_SEND_DM`

4. **Update Scheduler Service** (`services/scheduler/services/notification_service.py`)
   - Rename method to `send_game_reminder_due`
   - Remove user-specific parameters (user_id, game_title, game_time_unix)
   - Remove message formatting (bot will handle)
   - Publish simple `GameReminderDueEvent` with just game_id and reminder_minutes

5. **Add Bot Handler** (`services/bot/events/handlers.py`)
   - Add `EventType.GAME_REMINDER_DUE` to handler registration
   - Create `_handle_game_reminder_due(data)` method
   - Query game with participants (reuse `_get_game_with_participants`)
   - Sort participants (reuse existing sorting logic)
   - Filter to real participants with `user_id IS NOT NULL`
   - Iterate and send DM to each with existing Discord error handling
   - Format message similar to current scheduler format but with bot's formatting logic

6. **Update Tests**
   - Scheduler tests: Verify one task per game per reminder
   - Bot tests: Add tests for new handler with participant filtering and sorting
   - Integration tests: Verify end-to-end notification flow

## Implementation Guidance

**Objectives**:
- Decouple scheduler from participant-level decisions
- Reduce message volume by 90%+ (one per game vs one per participant)
- Centralize participant logic in bot service
- Simplify Redis tracking (one key per game/reminder vs per participant)

**Key Tasks**:
1. Add `GAME_REMINDER_DUE` event type and schema
2. Refactor scheduler to publish game-level events
3. Add bot handler to process participants and send DMs
4. Update all related tests
5. Remove obsolete `NOTIFICATION_SEND_DM` after migration (optional)

**Dependencies**:
- No new external dependencies required
- Reuses existing participant sorting and filtering logic from bot
- Reuses existing Discord DM sending with error handling

**Success Criteria**:
- Scheduler publishes one event per game per reminder time (not per participant)
- Bot correctly identifies active vs waitlist vs placeholder participants
- All eligible participants receive notifications
- Placeholders never receive notifications
- Redis keys simplified to game-level tracking
- All tests pass with new architecture
