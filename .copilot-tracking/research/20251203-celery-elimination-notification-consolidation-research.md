<!-- markdownlint-disable-file -->
# Task Research Notes: Complete Celery Elimination and Notification System Consolidation

## Research Executed

### Current State Analysis

#### Remaining Celery Usage
- **services/scheduler/celery_app.py**
  - Celery application configuration
  - Single task: `update_game_status.update_game_statuses`
  - Beat schedule: runs every 60 seconds (STATUS_UPDATE_INTERVAL_SECONDS)
  - Purpose: Mark games as IN_PROGRESS when scheduled_at time passes

#### Existing Notification Infrastructure (Already Migrated)
- **notification_schedule table** (migration 012)
  - Stores pre-calculated notification times for game reminders
  - Fields: id, game_id, reminder_minutes, notification_time, sent, created_at
  - PostgreSQL trigger sends NOTIFY events on changes
  - Partial index on notification_time WHERE sent = FALSE

- **notification_daemon.py**
  - Event-driven daemon using PostgreSQL LISTEN/NOTIFY
  - MIN() query pattern for next due notification
  - Publishes EventType.GAME_REMINDER_DUE to RabbitMQ
  - Already successfully replaced polling-based game reminder notifications

#### Event Types Currently in Use
- #file:shared/messaging/events.py (Lines 33-58)
  - EventType.GAME_CREATED = "game.created"
  - EventType.GAME_UPDATED = "game.updated"
  - EventType.GAME_CANCELLED = "game.cancelled"
  - EventType.GAME_STARTED = "game.started" (published by Celery task)
  - EventType.GAME_COMPLETED = "game.completed"
  - EventType.PLAYER_JOINED = "game.player_joined"
  - EventType.PLAYER_LEFT = "game.player_left"
  - EventType.PLAYER_REMOVED = "game.player_removed"
  - EventType.WAITLIST_ADDED = "game.waitlist_added"
  - EventType.WAITLIST_REMOVED = "game.waitlist_removed"
  - EventType.GAME_REMINDER_DUE = "game.reminder_due" (notification daemon)
  - EventType.NOTIFICATION_SEND_DM = "notification.send_dm"
  - EventType.NOTIFICATION_SENT = "notification.sent"
  - EventType.NOTIFICATION_FAILED = "notification.failed"

### Notification Types Classification

#### Time-Based Notifications (Scheduled)
1. **Game Reminders** (ALREADY MIGRATED)
   - Trigger: X minutes before game.scheduled_at
   - Event: EventType.GAME_REMINDER_DUE
   - Handler: services/bot/events/handlers.py:_handle_game_reminder_due
   - Current: notification_schedule table + notification_daemon

2. **Game Start Status Transition** (NEEDS MIGRATION)
   - Trigger: When game.scheduled_at passes
   - Event: EventType.GAME_STARTED
   - Handler: Updates game.status to IN_PROGRESS, publishes to RabbitMQ
   - Current: Celery beat task (update_game_status.py)

#### Event-Driven Notifications (Immediate)
These do NOT need scheduling - they are triggered immediately by user actions:
- EventType.GAME_CREATED - Published by API on game creation
- EventType.GAME_UPDATED - Published by API on game modification
- EventType.GAME_CANCELLED - Published by API on game cancellation
- EventType.PLAYER_JOINED - Published by API on participant add
- EventType.PLAYER_LEFT - Published by API on participant remove
- All these already use RabbitMQ directly, no Celery involvement

### Architectural Pattern Analysis

#### Current notification_schedule Schema
```sql
CREATE TABLE notification_schedule (
    id VARCHAR(36) PRIMARY KEY,
    game_id VARCHAR(36) NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    reminder_minutes INTEGER NOT NULL,
    notification_time TIMESTAMP NOT NULL,
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(game_id, reminder_minutes)
);
```

**Limitations for Generic Notifications:**
- `reminder_minutes` field is specific to game reminders
- No type field to distinguish different notification types
- No payload storage for type-specific data
- UNIQUE constraint assumes one notification per game per reminder time

#### notification_daemon.py Architecture
- Single-purpose: processes game reminder notifications
- Queries: `SELECT MIN(notification_time) WHERE sent = FALSE`
- Processing: Publishes GameReminderDueEvent with game_id + reminder_minutes
- Pattern: One daemon, one query, one event type

### Selected Approach: Separate game_status_schedule Table

**New Schema:**
```sql
CREATE TABLE game_status_schedule (
    id VARCHAR(36) PRIMARY KEY,
    game_id VARCHAR(36) NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    target_status VARCHAR(20) NOT NULL,     -- 'IN_PROGRESS', 'COMPLETED'
    transition_time TIMESTAMP NOT NULL,
    executed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(game_id, target_status)
);
```

**Benefits of This Approach:**
- No changes to existing notification_schedule table
- Type-safe: each table has specific columns
- Independent scaling and tuning
- Easier to understand (explicit purpose)
- Simpler UNIQUE constraints
- Can optimize indexes per notification type
- Domain separation: status changes vs notifications
- Failure isolation between daemons

**Accepted Trade-offs:**
- Two separate daemons to maintain (acceptable for domain clarity)
- Some infrastructure duplication (LISTEN/NOTIFY triggers, MIN() queries)
- Two daemon services to deploy (matches existing pattern)
- Future notification types require separate evaluation

### Game Status Transition Requirements

#### Current Implementation (Celery)
- #file:services/scheduler/tasks/update_game_status.py (Lines 36-110)
  - Runs every 60 seconds via Celery beat
  - Queries all games WHERE status='SCHEDULED' AND scheduled_at <= NOW()
  - Updates status to 'IN_PROGRESS'
  - Publishes EventType.GAME_STARTED event
**Schema Design:**tion schedule, immediate check-and-update pattern

#### Migration to Database-Backed Pattern

**Trigger Points:**
1. Game created with scheduled_at → Insert status transition schedule
2. Game scheduled_at updated → Update status transition schedule
3. Game cancelled/deleted → Delete status transition schedule
4. scheduled_at passes → Execute status transition + publish event

**Differences from Game Reminders:**
- Only ONE transition per game (SCHEDULED → IN_PROGRESS)
- No "reminder_minutes" offset, transition at exact scheduled_at time
- Must update game.status in database (not just publish event)
- Requires database write transaction, not just event publish

### Integration Patterns

#### Pattern 1: Unified Daemon with Type Dispatching
```python
def _process_notification(self, notification: NotificationSchedule) -> None:
    if notification.notification_type == "game.reminder":
        self._process_game_reminder(notification)
    elif notification.notification_type == "game.status_transition":
        self._process_status_transition(notification)
    else:
        logger.error(f"Unknown notification type: {notification.notification_type}")
```

#### Pattern 2: Separate Specialized Daemons
```python
# notification_daemon.py - Game reminders only
class NotificationDaemon:
    def _process_notification(self, notification: NotificationSchedule):
        # Publishes EventType.GAME_REMINDER_DUE
        pass

# status_transition_daemon.py - Game status transitions only
class StatusTransitionDaemon:
    def _process_transition(self, transition: GameStatusSchedule):
        # Updates game.status, publishes EventType.GAME_STARTED
        pass
```

### Database Transaction Considerations

#### Game Reminders (Current)
- Read-only from game database perspective
- Publishes event to RabbitMQ
- Marks notification as sent
- Simple transaction: UPDATE notification_schedule SET sent = TRUE

#### Status Transitions (New)
- Must UPDATE game_sessions.status
- Must UPDATE game_sessions.updated_at
- Must publish EventType.GAME_STARTED
- Must mark transition as executed
- Complex transaction: Multiple tables + event publish + error handling

**Transaction Pattern:**
```python
with db.begin():
    # 1. Update game status
    game.status = 'IN_PROGRESS'
    game.updated_at = utc_now()
    
    # 2. Mark transition executed
    transition.executed = True
    
    # 3. Publish event (outside transaction for reliability)
    
db.commit()
publisher.publish_event(EventType.GAME_STARTED, {...})
```

### Architectural Decision Factors

#### Favor Single Table If:
- Expect to add many more scheduled notification types
- Want unified monitoring and error handling
- Prefer operational simplicity (one daemon)
- Notifications have similar processing patterns
- Need to query "all pending notifications" across types

#### Favor Separate Tables If:
- Only these two notification types foreseeable
- Types have very different processing requirements
- Want independent scaling and optimization
- Prefer type safety and explicit schemas
- Easier to reason about specific notification purposes

### Project Context Analysis

#### Existing Patterns
- #file:services/scheduler/notification_daemon.py
  - Already single-purpose daemon for game reminders
  - Clean separation of concerns
  - Tested and working

#### Deployment Infrastructure
- #file:docker-compose.base.yml (Lines 210-236)
  - notification-daemon already deployed as separate service
  - Adding status-transition-daemon would be similar pattern
  - Both use same database and RabbitMQ connections

#### Codebase Philosophy
- #file:.github/instructions/coding-best-practices.instructions.md
  - "Modularity: discrete components where change to one has minimal impact"
  - "Readability: code should be easy to understand"
  - "Don't Repeat Yourself" - argues against duplicate daemon code

## Key Discoveries

### Critical Insight: Domain Separation
**Game reminders** and **status transitions** are fundamentally different operations:
- Reminders: Notification-only, no state change, fan-out to participants
- Transitions: State mutation, transactional integrity, single game update

This suggests separate tables with specialized schemas optimized for each purpose.

### PostgreSQL LISTEN/NOTIFY Reusability
Both approaches can reuse the LISTEN/NOTIFY pattern:
- Single table: One trigger, one channel
- Separate tables: Two triggers, two channels (or same channel with type filtering)

### Celery Elimination Straightforward
The update_game_status Celery task is simple enough that either approach easily replaces it:
- Pattern is identical to game reminders (time-based scheduling)
- No complex Celery features being used
- Database-backed pattern proven by notification_daemon success

## Recommended Approach

### Separate Tables with Specialized Daemons (SELECTED)

**Decision**: User selected separate tables approach on 2025-12-03

**Rationale:**
1. **Domain Clarity**: Status transitions are game state changes, not notifications
2. **Type Safety**: game_status_schedule.target_status is explicit, no generic payload
3. **Independent Evolution**: Can optimize each without affecting the other
4. **Simpler Testing**: Each daemon has focused responsibility
5. **Code Clarity**: No type dispatching logic, straightforward processing
6. **Failure Isolation**: Problem with status transitions doesn't affect reminders

**Trade-off Acceptance:**
- Code duplication in daemon infrastructure is acceptable given clear domain separation
- Two daemons are manageable and already match deployment pattern
- Adding future notification types can be evaluated case-by-case

### Migration Strategy

#### Phase 1: Create game_status_schedule Table
- New migration: 020_add_game_status_schedule.sql
- Schema with game_id, target_status, transition_time, executed
- PostgreSQL trigger for LISTEN/NOTIFY on 'game_status_changed'
- Indexes: partial index on transition_time WHERE executed = FALSE

#### Phase 2: Create Status Transition Daemon
- New file: services/scheduler/status_transition_daemon.py
- Copy structure from notification_daemon.py
- Modify to update game.status instead of publishing reminders
- Publish EventType.GAME_STARTED after successful transition

#### Phase 3: Integrate with API
- Update games service to populate game_status_schedule on game creation
- Update schedule on game.scheduled_at changes
- Delete schedule on game cancellation/deletion

#### Phase 4: Deploy and Validate
- Add status-transition-daemon to docker-compose.yml
- Test alongside notification-daemon (both running)
- Verify status transitions work correctly
- Monitor for missed transitions or errors

#### Phase 5: Remove Celery
- Delete services/scheduler/celery_app.py
- Delete services/scheduler/tasks/update_game_status.py
- Remove scheduler and scheduler-beat services from docker-compose
- Remove Celery from pyproject.toml dependencies
- Update README to reflect architecture change

## Implementation Guidance

### Objectives
- Eliminate Celery completely from the codebase
- Migrate game status transitions to database-backed scheduling
- Maintain reliability and <10 second latency for status updates
- Reuse proven LISTEN/NOTIFY pattern from notification_daemon

### Key Tasks
1. Create game_status_schedule table and migration
2. Create PostgreSQL trigger for status schedule changes
3. Implement status_transition_daemon.py
4. Integrate schedule population in API game service
5. Add status-transition-daemon to Docker deployment
6. Test status transition accuracy and timing
7. Remove all Celery code and configuration
8. Update documentation

### Dependencies
- Existing notification_daemon.py as reference implementation
- PostgreSQL LISTEN/NOTIFY support (already in use)
- RabbitMQ for EventType.GAME_STARTED events (existing)
- shared.database synchronous session support (existing)

### Success Criteria
- Game status transitions from SCHEDULED to IN_PROGRESS within 10 seconds of scheduled_at
- EventType.GAME_STARTED published correctly after status update
- Status transition daemon survives restart without losing scheduled transitions
- No Celery dependencies remain in codebase
- Both notification_daemon and status_transition_daemon run reliably
- All existing tests pass with new architecture
- Documentation updated to reflect Celery removal

### Alternative Rejected: Single notification_schedule Table

**Rejected on 2025-12-03** in favor of separate tables approach.

**Reasons for Rejection:**
- Mixing notifications (read-only) with state transitions (write-heavy) violates separation of concerns
- Generic payload JSONB reduces type safety
- Complicates UNIQUE constraints (game_id, notification_type, notification_time)
- Single daemon must handle heterogeneous processing logic
- Harder to optimize indexes for mixed workload
- Breaking change to existing notification_schedule schema
- User preference for domain clarity and independent evolution

