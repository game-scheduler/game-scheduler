<!-- markdownlint-disable-file -->
# Task Research Notes: Daemon-Bot Message Reliability and Error Handling (Updated)

## Research Executed

### File Analysis
- services/scheduler/generic_scheduler_daemon.py
  - Generic daemon processes scheduled items by building events, publishing to RabbitMQ, then marking as processed
  - Current order: publish → mark processed → commit (CORRECT for preventing loss)
  - On publish failure: rollback keeps item for retry
  - On commit failure after publish: duplicate message (acceptable, better than loss)
- services/scheduler/event_builders.py
  - build_game_reminder_event() - Creates GAME_REMINDER_DUE events (user notifications)
  - build_status_transition_event() - Creates GAME_STATUS_TRANSITION_DUE events (status updates)
- shared/messaging/sync_publisher.py
  - Uses pika with delivery_mode=Persistent (durable messages)
  - No publisher confirms enabled - fire-and-forget delivery
- shared/messaging/consumer.py
  - Uses aio_pika with `async with message.process()` context manager
  - **CRITICAL ISSUE**: Message is acknowledged regardless of handler success/failure
  - If handler raises exception, message is still acknowledged and lost
- services/bot/events/handlers.py
  - _handle_game_reminder_due() - Sends DMs to participants (lines 287-395)
  - _handle_status_transition_due() - Updates game status in database (lines 541-593)
  - Both handlers can fail but message is ACKed anyway

### Code Search Results
- GAME_REMINDER_DUE events: Send reminder DMs to participants
  - Best-effort delivery acceptable (DMs may be disabled, users may have blocked bot)
  - Becomes stale after game starts - no value in infinite retries
  - Individual DM failures logged but don't fail entire handler
- GAME_STATUS_TRANSITION_DUE events: Update game status from SCHEDULED to STARTED/COMPLETED
  - Critical for data consistency - status must be updated or database state is wrong forever
  - NOT stale - must eventually succeed to maintain consistency
  - Database operation is idempotent (checking current status before update)

### External Research
- #fetch:https://aio-pika.readthedocs.io/en/latest/rabbitmq-tutorial/2-work-queues.html
  - Manual acknowledgment patterns for conditional ACK/NACK
  - Dead letter exchanges for messages that cannot be processed
- #fetch:https://www.rabbitmq.com/confirms.html
  - Publisher confirms provide delivery guarantee from publisher to broker
  - Consumer acknowledgments provide processing guarantee
  - Message TTL prevents messages from living forever in queues

### Project Conventions
- rabbitmq/definitions.json - Dead letter exchange already configured for all queues
- Queue configuration includes x-dead-letter-exchange and x-message-ttl (24 hours)

## Key Discoveries

### Critical Distinction: Two Event Types with Different Semantics

#### Type 1: User Notifications (GAME_REMINDER_DUE)
**Characteristics**:
- Send reminder DMs to game participants
- Time-sensitive: only valuable before game starts
- Best-effort delivery: user may have DMs disabled or bot blocked
- Individual failures acceptable: some users may not receive, that's okay
- Handler already handles individual DM failures gracefully
- **Becomes stale**: No value in retrying after game start time

**Current Behavior**:
- Handler sends DMs to all participants in try/except blocks
- Individual DM failures are logged but don't fail the handler
- If handler completes (even with some DM failures), message is ACKed
- If handler crashes (database error, etc.), message is ACKed and lost

**Acceptable Failures**:
- User has DMs disabled (discord.Forbidden) - logged, move on
- User blocked bot - logged, move on
- Some users get notification, others don't - acceptable

**Unacceptable Failures**:
- Handler crashes before attempting any DMs (database error, parsing error)
- Entire event lost due to transient infrastructure issue

#### Type 2: Status Transitions (GAME_STATUS_TRANSITION_DUE)
**Characteristics**:
- Update game status in database (SCHEDULED → STARTED, SCHEDULED → COMPLETED)
- Critical for data consistency
- **NEVER becomes stale**: If not executed, database state is inconsistent forever
- Must eventually succeed or database is permanently wrong
- Handler operation is idempotent (checks current status before updating)

**Current Behavior**:
- Handler updates game.status in database
- Refreshes Discord message to show new status
- If any step fails, entire transaction rolls back
- Message is ACKed regardless of success/failure

**Unacceptable Failures**:
- Database temporarily unavailable - should retry
- Discord API temporarily unavailable - should retry message refresh
- Any transient error - must retry until success

**Recovery Strategy Needed**:
- Cannot rely solely on RabbitMQ retry (message becomes stale after TTL)
- Need database-backed recovery mechanism to find missed transitions
- Periodic query or startup check to find games stuck in SCHEDULED status past their transition time

### Current Architecture Issues

#### Issue 1: Bot Consumer Always Acknowledges Messages
**Location**: `shared/messaging/consumer.py` lines 120-145

**Problem**: The `message.process()` context manager acknowledges messages on exit regardless of success/failure.

**Impact**:
- User notifications: Lost messages mean some users don't get reminders (annoying but not critical)
- Status transitions: Lost messages mean games stuck in wrong status forever (DATA CORRUPTION)

#### Issue 2: No Recovery Mechanism for Status Transitions
**Location**: No existing recovery mechanism

**Problem**: If status transition event is lost or repeatedly fails, game remains in SCHEDULED status forever.

**Impact**: Database inconsistency that cannot self-heal

### Recommended Approach: Differentiated Retry Strategy

#### Solution 1: Manual ACK with Event-Type-Specific Retry Logic

Replace `message.process()` with manual acknowledgment that considers event type:

```python
async def _process_message(self, message: AbstractIncomingMessage) -> None:
    """Process message with event-type-specific retry logic."""
    try:
        event = Event.model_validate_json(message.body)
        handlers = self._handlers.get(event.event_type.value, [])
        
        if not handlers:
            await message.ack()
            logger.warning(f"No handlers for {event.event_type}, discarding")
            return
        
        # Process handlers
        for handler in handlers:
            await handler(event)
        
        # Success - acknowledge message
        await message.ack()
        logger.debug(f"Successfully processed and ACKed {event.event_type}")
        
    except Exception as e:
        # NACK to DLQ without requeue - let daemon handle republishing
        # This prevents instant retry loops while preserving the message
        await message.nack(requeue=False)
        logger.error(f"Handler failed, sending to DLQ for daemon processing: {event.event_type}, error: {e}")
```

**Benefits**:
- Simple and reliable - all failures go to DLQ
- No instant retry loops (no requeue)
- Daemon controls retry logic based on x-death count and event type
- Message preserved for analysis in DLQ

**Why no retry limits in consumer?**:
- Notifications: Per-message TTL handles staleness (expire when game starts)
- Status transitions: Must eventually succeed, daemon handles indefinite retry
- Retry limits would just delay daemon processing without benefit

#### Solution 2: Database-Backed Recovery for Status Transitions

Add recovery mechanism to find and fix missed status transitions:

**Option A: Periodic Background Job**
```python
async def recover_missed_status_transitions():
    """Find games stuck in SCHEDULED status past their transition time."""
    async with get_db_session() as db:
        now = utc_now()
        
        # Find games in SCHEDULED status with transition time in past
        stuck_games = await db.execute(
            select(GameStatusSchedule)
            .filter(GameStatusSchedule.executed == False)
            .filter(GameStatusSchedule.transition_time < now)
            .order_by(GameStatusSchedule.transition_time.asc())
        )
        
        for schedule in stuck_games.scalars():
            logger.warning(
                f"Found missed status transition: game={schedule.game_id}, "
                f"target={schedule.target_status}, due={schedule.transition_time}"
            )
            
            # Re-process the transition
            await _handle_status_transition_due({
                'game_id': schedule.game_id,
                'target_status': schedule.target_status,
                'transition_time': schedule.transition_time
            })
```

Run this:
- On bot startup (fix anything that broke while bot was down)
- Periodically every 5-10 minutes (catch ongoing failures)

**Option B: Run-Once Container (Like Database Migration)**
```yaml
# docker-compose.yml
status-recovery:
  image: game-scheduler-bot:latest
  command: python -m services.bot.recovery.status_transitions
  depends_on:
    - postgres
  restart: "no"
```

Run manually or on deploy to fix any accumulated inconsistencies.

**Option C: Scheduled Container (Like Cron)**
```yaml
# docker-compose.yml  
status-recovery-cron:
  image: game-scheduler-bot:latest
  command: python -m services.bot.recovery.status_transitions_loop
  depends_on:
    - postgres
  restart: unless-stopped
```

Runs continuously with sleep between checks.

#### Solution 3: Combined Approach (RECOMMENDED)

Implement both:
1. Manual ACK with differentiated retry (Solution 1)
2. Startup + periodic recovery for status transitions (Solution 2, Option A)

**Rationale**:
- Manual ACK fixes the immediate message loss issue
- Recovery mechanism provides defense-in-depth for critical status transitions
- User notifications have appropriate best-effort semantics
- Status transitions guaranteed to eventually succeed
- Minimal complexity: recovery is simple query + re-process loop

## Implementation Guidance

### Phase 1: Fix Consumer Message Loss (Immediate)

- **Objectives**: 
  - Stop acknowledging messages on handler failure
  - Implement event-type-specific retry limits
  - Maintain existing handler idempotency
  
- **Key Tasks**:
  1. Update `shared/messaging/consumer.py` _process_message() to use manual ACK
  2. Check event type and apply appropriate retry limit
  3. User notifications: max 3 retries, then discard
  4. Status transitions: max 10 retries, then DLQ (recovery will fix)
  5. Add integration tests for retry behavior
  6. Verify handlers are idempotent (already are)
  
- **Success Criteria**:
  - Messages only ACKed after successful handler completion
  - User notification failures retry up to 3 times
  - Status transition failures retry up to 10 times
  - DLQ accumulates repeatedly failed messages
  - No infinite retry loops

### Phase 2: Add Status Transition Recovery (Defense in Depth)

- **Objectives**:
  - Ensure status transitions always eventually succeed
  - Recover from any message loss or repeated failures
  - Provide monitoring visibility into stuck transitions
  
- **Key Tasks**:
  1. Create recovery function that queries for missed transitions
  2. Run recovery on bot startup
  3. Run recovery periodically (every 5-10 minutes)
  4. Log warnings for recovered transitions (indicates problem upstream)
  5. Add metric/alert for number of recovered transitions
  6. Document that this is safety net, not primary mechanism
  
- **Success Criteria**:
  - Games never stuck in SCHEDULED status past transition time
  - Recovery runs automatically on startup and periodically
  - Recovered transitions are logged and visible
  - Recovery has minimal performance impact
  - System self-heals from any status transition failures

### Phase 3: Optional Enhancements

- **TTL-Based Staleness**: Set shorter TTL for user notification messages (e.g., based on game start time)
- **Publisher Confirms**: Add publisher confirms to daemon to eliminate commit-after-publish edge case
- **DLQ Monitoring**: Alert on messages accumulating in dead letter queue

## Dependencies

- RabbitMQ 3.8+ for x-delivery-count header support
- Existing dead letter exchange configuration (already present)
- Idempotent handler design (already implemented)

## Success Criteria

- Handler exceptions no longer result in message loss
- User notifications retry up to 3 times with bounded attempts
- Status transitions retry aggressively with recovery fallback
- Games never stuck in wrong status (self-healing system)
- Integration tests verify retry and recovery behavior
- System remains performant under normal and error conditions

## Dead Letter Queue Analysis: Can It Replace Database Recovery?

### Current DLQ Configuration

From `rabbitmq/definitions.json`:
- All queues have `x-dead-letter-exchange: "game_scheduler.dlx"`
- All queues have `x-message-ttl: 86400000` (24 hours)
- Dead letter exchange routes to `dead_letter_queue` with routing key `#` (catches everything)

### How Messages Reach the DLQ

Messages are dead-lettered when:
1. **Rejected without requeue**: `message.reject(requeue=False)` or `message.nack(requeue=False)`
2. **TTL expiration**: Message sits in queue for 24 hours without being consumed
3. **Queue length exceeded**: Queue hits max length limit (not configured)
4. **Delivery limit exceeded**: Quorum queues only (not using quorum queues)

### Why DLQ Alone Is Insufficient for Status Transitions

#### Problem 1: Messages Disappear from Primary Queue
Once a message is dead-lettered (either by rejection or TTL), it's **removed from the primary queue** and moved to DLQ:
- Primary consumer (bot) no longer sees it
- Must build separate DLQ consumer to re-process
- DLQ consumer would need to know which handler to route to

#### Problem 2: TTL is Too Long for Status Transitions
Current TTL is 24 hours:
- Game status should transition at `scheduled_at` time
- Waiting 24 hours for TTL expiration means games stuck in wrong status for a day
- Could shorten TTL, but then user notifications expire too quickly

#### Problem 3: Rejected Messages Don't Automatically Retry
When we reject with `requeue=False`, message goes to DLQ and stays there:
- No automatic retry mechanism
- Would need DLQ consumer to re-publish to primary queue
- Adds complexity: DLQ consumer, retry logic, tracking attempts

#### Problem 4: Loss of Event-Specific Context
DLQ receives all message types mixed together:
- User notifications (can discard after game starts)
- Status transitions (must never discard)
- Game updates (best effort)
- No easy way to differentiate in DLQ without inspecting message payload

### Could We Make DLQ Work?

**Option 1: Per-Event-Type DLQ Queues**
```json
{
  "name": "bot_events",
  "arguments": {
    "x-dead-letter-exchange": "game_scheduler.dlx",
    "x-dead-letter-routing-key": "dlq.bot_events",
    "x-message-ttl": 3600000  // 1 hour
  }
}
```

Then create separate DLQ queues:
- `dlq.user_notifications` - shorter TTL, eventually discard
- `dlq.status_transitions` - no TTL, never discard
- `dlq.game_updates` - medium TTL

**Benefits**:
- Event-specific handling in DLQ
- Can set different TTLs per event type

**Drawbacks**:
- Complex queue setup (multiple DLQs)
- Still need DLQ consumer for each queue type
- DLQ consumer duplicates handler logic
- No visibility into "current state" - only failed events

**Option 2: DLQ Consumer with Retry-to-Primary**
Build a consumer that:
1. Reads from DLQ
2. Checks event type and retry count
3. Re-publishes to primary queue if should retry
4. Discards if retry limit exceeded

**Benefits**:
- Centralized retry logic
- Can implement exponential backoff

**Drawbacks**:
- Additional service to maintain
- Complexity of tracking retry count (in message headers)
- No "recovery" - only retries messages that were explicitly rejected
- Doesn't help if message is ACKed incorrectly

### Why Database Recovery Is Superior for Status Transitions

**Recovery finds missed transitions that DLQ cannot**:

1. **Message ACKed by mistake**: If bot crashes after processing but before ACK, consumer library might auto-ACK. Message never reaches DLQ, but transition wasn't applied.

2. **Message lost before reaching queue**: Network partition between daemon and RabbitMQ after publish succeeds but before broker persists. Message never enters queue, never reaches DLQ.

3. **RabbitMQ restart/data loss**: If RabbitMQ loses messages during restart (rare but possible), they never reach DLQ.

4. **Direct visibility**: Database query shows **current state** (unexecuted transitions), not just **failed events**.

5. **Idempotency**: Recovery just re-checks "are there any unexecuted transitions past their time?" Safe to run anytime.

**Database recovery query**:
```sql
SELECT * FROM game_status_schedule 
WHERE executed = false 
  AND transition_time < NOW()
ORDER BY transition_time ASC;
```

This finds transitions that need to happen, regardless of:
- Whether message was sent
- Whether message reached queue
- Whether message was processed
- Whether message is in DLQ

### Recommended Hybrid Approach

**For User Notifications** (GAME_REMINDER_DUE):
- Use manual ACK with retry (3 attempts)
- Reject to DLQ after max retries
- DLQ is fine as final destination (stale notifications have no value)
- **No recovery needed**

**For Status Transitions** (GAME_STATUS_TRANSITION_DUE):
- Use manual ACK with aggressive retry (10 attempts)
- Reject to DLQ after max retries (for monitoring/alerting)
- **Add database recovery** as safety net:
  - Run on bot startup
  - Run periodically (every 5-10 minutes)
  - Catches any transition that slipped through

**Why both?**:
- Manual ACK handles 99% of transient failures (network blips, temporary DB unavailability)
- DLQ provides visibility into repeated failures (alerting, debugging)
- Database recovery handles the 1% edge cases where message never arrives or is lost

### DLQ Monitoring Strategy

**Instead of using DLQ for recovery, use it for monitoring**:

```python
async def monitor_dlq_depth():
    """Alert if DLQ accumulates messages (indicates systemic problem)."""
    dlq_depth = await get_queue_depth("dead_letter_queue")
    
    if dlq_depth > 10:
        logger.error(f"Dead letter queue has {dlq_depth} messages - investigate!")
        # Send alert to ops team
        
    # Optionally: Inspect messages to see what's failing
    for message in sample_dlq_messages(limit=5):
        event_type = extract_event_type(message)
        reason = message.headers.get('x-death')[0]['reason']
        logger.error(f"DLQ message: type={event_type}, reason={reason}")
```

**DLQ message inspection**:
- Check `x-death` header for failure reason
- Check `x-first-death-queue` to see origin
- Check `count` to see how many times it failed
- Use for debugging and alerting, not recovery

### Final Recommendation

**Do NOT replace database recovery with DLQ consumption**:

1. DLQ is for **monitoring failed messages**, not recovery
2. Database recovery is for **ensuring data consistency**, not message retry
3. They serve different purposes and are complementary

**Implement**:
- ✅ Manual ACK with event-type-specific retry limits
- ✅ Reject to DLQ after max retries (for visibility)
- ✅ Database recovery for status transitions (defense in depth)
- ✅ DLQ monitoring/alerting (detect systemic issues)
- ❌ Do NOT build DLQ consumer for re-processing

This gives you:
- Reliability: Messages retry automatically on transient failures
- Consistency: Database recovery ensures transitions always happen
- Observability: DLQ shows what's failing repeatedly
- Simplicity: No complex DLQ re-processing logic needed

## Exponential Backoff Analysis: Can RabbitMQ Handle Infinite Retry?

### Current RabbitMQ Retry Capabilities

**Bad News**: RabbitMQ does **NOT** provide built-in exponential backoff or configurable retry delays that scale to days.

#### What RabbitMQ NACK/Requeue Does
When you NACK with `requeue=True`:
- Message goes immediately back to the **front** of the queue (head)
- No delay whatsoever
- Instant retry = instant failure loop
- Result: CPU spinning, log flooding, wasted resources

#### Quorum Queues: Delivery Limit Feature
Quorum queues have `delivery-limit` (default 20 in RabbitMQ 4.0+):
- Tracks redelivery count in `x-delivery-count` header
- After limit reached: message dead-lettered or dropped
- **No backoff** - just a counter
- Cannot be set to infinite (-1 requires queue argument at declaration)
- Current queues are **classic queues**, not quorum queues

#### RabbitMQ Delayed Message Exchange Plugin
There IS a plugin for delayed delivery:
- https://github.com/rabbitmq/rabbitmq-delayed-message-exchange
- Allows `x-delay` header in milliseconds
- Maximum delay: `(2^32)-1` milliseconds = ~49.7 days

**BUT**:
- Requires plugin installation (not currently installed)
- "badly needs a new design and reimplementation" (per plugin README)
- Not recommended for high volume or many delayed messages
- Stores messages in Mnesia table (single node, not replicated)
- "Performance implications" - acts as proxy
- "If you don't need to delay messages, then use actual exchange"

**AND MOST CRITICALLY**:
- Would require **code changes** to implement retry logic
- Consumer would need to:
  1. Catch exception
  2. Calculate exponential backoff delay
  3. Re-publish message with `x-delay` header to delayed exchange
  4. ACK original message
- This is **more complex** than just NACKing with requeue

### Common Exponential Backoff Patterns (All Require Code)

#### Pattern 1: Retry Queues with TTL
```
Primary Queue → (reject) → Retry Queue 1 (TTL: 1s) → (expires) → Primary Queue
                → (reject) → Retry Queue 2 (TTL: 10s) → (expires) → Primary Queue  
                → (reject) → Retry Queue 3 (TTL: 60s) → (expires) → Primary Queue
                → (reject) → DLQ (manual intervention)
```

**Requires**:
- Creating multiple retry queues in RabbitMQ config
- Consumer code to track attempt count and route to correct retry queue
- TTL on each retry queue to auto-expire back to primary
- **Cannot scale to infinite retries** (need unlimited queues)
- **Requires configuration changes** to rabbitmq/definitions.json

#### Pattern 2: Application-Level Retry with Re-Publish
```python
async def _process_message(self, message):
    try:
        event = Event.model_validate_json(message.body)
        await handler(event)
        await message.ack()
    except Exception as e:
        attempt = message.headers.get('x-retry-count', 0) + 1
        delay_ms = min(1000 * (2 ** attempt), 86400000)  # Cap at 1 day
        
        if attempt >= MAX_ATTEMPTS:
            await message.reject(requeue=False)  # To DLQ
        else:
            # Re-publish with delay header
            await self.publish_delayed(event, delay_ms, attempt)
            await message.ack()  # ACK original
```

**Requires**:
- Delayed message exchange plugin installed
- Consumer code to re-publish with delay
- Tracking attempt count in message headers
- **This is code changes** - defeats "no code changes" goal

#### Pattern 3: Database-Backed Retry Queue
Consumer stores failed message to database with next_retry_time, background worker polls for due retries.

**Requires**:
- Database table for retry queue
- Background worker process
- Significantly more code than manual ACK

### Why "No Code Changes" Is Not Achievable

**The fundamental problem**:
RabbitMQ's `requeue` mechanism has **no delay parameter**. You cannot say "requeue this message, but not for 10 minutes."

Your options are:
1. **Instant requeue** (`requeue=True`) - causes hot loop
2. **Reject to DLQ** (`requeue=False`) - message disappears
3. **Complex delayed retry** - requires code changes

**For status transitions specifically**:
- Need retry delays up to days
- Need infinite retries (never give up)
- RabbitMQ's built-in mechanisms **cannot provide this**

### Recommended Reality Check

**What infinite retry with exponential backoff would require**:

1. **Install delayed-message-exchange plugin**
   - Adds operational complexity
   - Plugin has known limitations
   - Single-node storage (not replicated)

2. **Implement retry logic in consumer code**
   - Track attempt count in headers
   - Calculate exponential backoff delay
   - Re-publish to delayed exchange
   - ACK original message

3. **Handle edge cases**
   - What if re-publish fails?
   - What if delayed exchange is unavailable?
   - How to monitor retry depth?

**This is MORE code and complexity than**:
- Manual ACK with bounded retry (10 attempts)
- Database recovery as safety net

### Why Database Recovery Is Still Superior

**Database recovery provides infinite retry without complexity**:

```python
async def recover_missed_transitions():
    """Runs on startup + every 5-10 minutes."""
    async with get_db_session() as db:
        stuck = await db.execute(
            select(GameStatusSchedule)
            .filter(GameStatusSchedule.executed == False)
            .filter(GameStatusSchedule.transition_time < utc_now())
        )
        
        for schedule in stuck:
            # Process transition directly from database
            await process_status_transition(schedule)
```

**This gives you**:
- ✅ Infinite retry (runs forever, periodically)
- ✅ Natural exponential backoff (5-10 minute intervals)
- ✅ No message queue complexity
- ✅ No plugins required
- ✅ No message header tracking
- ✅ Works even if messages are lost
- ✅ Simple to reason about
- ✅ ~30 lines of code

**Versus trying to achieve this with RabbitMQ**:
- ❌ Requires plugin installation
- ❌ Requires consumer code changes
- ❌ Requires retry queue infrastructure
- ❌ More complex error handling
- ❌ Doesn't handle messages never delivered
- ❌ 100+ lines of code

### Final Verdict

**You CANNOT achieve infinite retry with exponential backoff to days using only RabbitMQ configuration changes**.

Any solution that provides this would require:
1. Code changes in the consumer
2. OR plugin installation + code changes
3. OR complex queue infrastructure setup

**The simplest, most reliable solution remains**:
- Manual ACK with bounded retry (catches 99% of transient failures)
- Database recovery (catches 100% of missed transitions, infinite retry built-in)
- DLQ monitoring (visibility into systemic issues)

This is **less code and less complexity** than trying to build infinite retry into the message queue system.

## DLQ TTL Configuration Analysis

### Current Configuration

From `rabbitmq/definitions.json`:

**Primary queues** (bot_events, api_events, etc.):
```json
{
  "arguments": {
    "x-dead-letter-exchange": "game_scheduler.dlx",
    "x-message-ttl": 86400000  // 24 hours
  }
}
```

**Dead letter queue** (dead_letter_queue):
```json
{
  "name": "dead_letter_queue",
  "arguments": {}  // NO TTL SET
}
```

### Key Finding: DLQ Has NO TTL

**The 24-hour TTL applies to PRIMARY queues, NOT the dead letter queue**.

**What this means**:
- Messages in `bot_events`, `api_events`, etc. expire after 24 hours if not consumed
- Once a message reaches `dead_letter_queue`, it has **NO TTL** (lives forever)
- DLQ messages accumulate indefinitely until manually purged

**Note on per-message TTL and DLQ**:
- Per-message TTL causes expiration in the **primary queue**, not the DLQ
- Once a message is in the DLQ, its original TTL no longer applies
- DLQ messages won't expire automatically unless the DLQ itself has a TTL configured
- Since daemon processes DLQ regularly (every 5 min), messages don't accumulate long enough for this to matter

### RabbitMQ TTL Capabilities

**Per-Queue TTL** (`x-message-ttl`):
- Can be any positive integer in milliseconds
- No maximum limit (can be years)
- 86400000 ms = 24 hours (current setting for primary queues)

**Per-Message TTL** (set by publisher):
- Can override per-queue TTL
- Also no maximum limit
- Must be string representation of milliseconds

### Implications for Status Transitions

**Current behavior**:
1. Status transition message published to `bot_events`
2. Message has 24 hours to be consumed
3. If not consumed within 24 hours → expires → dead-lettered to DLQ
4. In DLQ, message lives **forever** with no TTL

**Problem for infinite retry via TTL**:
- Once message expires (24 hours), it goes to DLQ
- DLQ has no consumer (it's a graveyard, not a retry queue)
- Message never gets re-processed
- Game stuck in wrong status forever

**Could we increase primary queue TTL?**
- Yes, can set to any duration (days, weeks, months)
- BUT: This doesn't provide retry, just extends time before message is lost
- Messages still only delivered once
- If handler fails, message is ACKed and lost (current bug)

### Why Longer TTL Doesn't Solve the Problem

**Scenario**: Set TTL to 30 days
1. Daemon publishes status transition message
2. Bot consumer receives message
3. Handler fails (database down)
4. Consumer ACKs message anyway (current bug)
5. Message is gone forever, 30-day TTL irrelevant
6. Game stuck in wrong status

**The core issue**: `message.process()` auto-ACKs on exit regardless of success

**TTL only helps if**: Message never reaches consumer (queue backlog)

**TTL doesn't help if**: Consumer receives but fails to process (our issue)

### Potential DLQ Configuration Changes

**Option 1: Set TTL on DLQ to Auto-Purge**
```json
{
  "name": "dead_letter_queue",
  "arguments": {
    "x-message-ttl": 604800000  // 7 days
  }
}
```
- Old failed messages auto-purge after 7 days
- Prevents infinite accumulation
- Doesn't help recovery (messages still lost)

**Option 2: Set TTL to Cycle Back (Not Recommended)**
```json
{
  "name": "dead_letter_queue",
  "arguments": {
    "x-message-ttl": 3600000,  // 1 hour
    "x-dead-letter-exchange": "game_scheduler"  // Cycle back!
  }
}
```
- Messages in DLQ expire after 1 hour
- Get dead-lettered back to primary exchange
- Infinite retry loop!

**Problem with Option 2**:
- Message keeps cycling forever
- No differentiation between user notifications (can discard) and status transitions (must succeed)
- No exponential backoff
- Original error might be permanent (bad data, logic error)
- Creates message storm on persistent failures

### Answer to Original Question

**Q: Is 24 hours the max TTL for the DLQ?**

**A: No. The DLQ currently has NO TTL (messages live forever).**

The 24-hour TTL is on the **primary queues** (bot_events, etc.), not the dead letter queue.

**You can set any TTL you want**:
- Milliseconds to years
- Or no TTL (current DLQ behavior)
- Or use it to cycle messages back (not recommended)

**But TTL doesn't solve the core problem**:
- Messages are being ACKed before successful processing
- TTL only matters for unconsumed messages
- Once consumed and ACKed, TTL is irrelevant
- Need manual ACK to prevent premature acknowledgment

### Recommendation

**Don't try to use TTL for retry**:
- TTL is for expiring unconsumed messages
- Retry is for reprocessing failed processing
- These are different problems

**The solution remains**:
1. Manual ACK (only ACK after successful processing)
2. NACK with requeue for transient failures
3. Database recovery for status transitions (infinite retry, naturally)

TTL configuration changes won't fix the message loss issue.

## DLQ as Database Recovery Trigger: Event-Driven Recovery

### The Insight

**Instead of periodic polling**, use DLQ message accumulation as a **trigger** to run database recovery queries.

**Logic**:
- If DLQ is empty → no failures → no need to check database
- If DLQ has messages → failures occurred → run recovery query

**Benefit**: Avoids constant polling when system is healthy.

### Implementation Approaches

#### Approach 1: DLQ Consumer as Recovery Trigger

Create a consumer that listens to DLQ and triggers recovery on any message received:

```python
class DLQRecoveryTrigger:
    """
    Consumes from DLQ to trigger database recovery checks.
    Does NOT re-process the DLQ message itself, just uses it as a signal.
    """
    
    async def start_consuming(self):
        consumer = EventConsumer(queue_name="dead_letter_queue")
        await consumer.connect()
        await consumer.bind("#")  # All messages
        
        async def on_dlq_message(message):
            # Message in DLQ = something failed
            event_type = self._extract_event_type(message)
            
            logger.warning(
                f"DLQ message received: {event_type} - triggering recovery check"
            )
            
            # Trigger recovery based on message type
            if event_type == EventType.GAME_STATUS_TRANSITION_DUE:
                await self._recover_status_transitions()
            elif event_type == EventType.GAME_REMINDER_DUE:
                # User notifications - already stale, just log
                logger.info("Stale reminder notification in DLQ, discarding")
            
            # ACK the DLQ message (it's served its purpose as a signal)
            await message.ack()
        
        await consumer.start_consuming(on_dlq_message)
    
    async def _recover_status_transitions(self):
        """Run database recovery for missed transitions."""
        async with get_db_session() as db:
            stuck = await db.execute(
                select(GameStatusSchedule)
                .filter(GameStatusSchedule.executed == False)
                .filter(GameStatusSchedule.transition_time < utc_now())
            )
            
            for schedule in stuck.scalars():
                logger.warning(
                    f"Recovering missed transition: game={schedule.game_id}"
                )
                await process_status_transition(schedule)
```

**Benefits**:
- ✅ No polling when system is healthy
- ✅ Immediate recovery trigger on failures
- ✅ DLQ messages serve dual purpose (monitoring + trigger)
- ✅ Event-driven architecture (reactive, not proactive)

**Considerations**:
- DLQ consumer adds another service component
- DLQ message doesn't contain full context (need database query anyway)
- Multiple DLQ messages might trigger redundant recovery runs
- DLQ consumer failure means no recovery triggers

#### Approach 2: Periodic Check Based on DLQ Depth

Poll DLQ depth periodically, only run recovery if depth > 0:

```python
async def recovery_loop():
    """Check DLQ depth and run recovery if needed."""
    while not shutdown_requested:
        try:
            dlq_depth = await get_queue_depth("dead_letter_queue")
            
            if dlq_depth > 0:
                logger.warning(f"DLQ has {dlq_depth} messages, running recovery")
                await recover_status_transitions()
            else:
                logger.debug("DLQ empty, no recovery needed")
            
            # Check every 5 minutes
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Recovery loop error: {e}")
            await asyncio.sleep(60)  # Retry sooner on error
```

**Benefits**:
- ✅ Simpler than DLQ consumer (no new service)
- ✅ Still avoids query when DLQ is empty
- ✅ Batches recovery (multiple DLQ messages = one recovery run)
- ✅ Less sensitive to DLQ consumer failures

**Considerations**:
- Still polling (checking DLQ depth every 5 min)
- Delay between failure and recovery (up to 5 min)
- DLQ depth API call overhead (minimal)

#### Approach 3: Hybrid - Startup + DLQ Trigger

Run recovery on bot startup, then use DLQ as trigger:

```python
class BotEventHandlers:
    async def start_consuming(self, queue_name: str = "bot_events"):
        # Run recovery on startup
        await self._startup_recovery()
        
        # Start normal event consumption
        await super().start_consuming(queue_name)
        
        # Start DLQ monitoring in background
        asyncio.create_task(self._dlq_monitor_loop())
    
    async def _startup_recovery(self):
        """Run recovery on startup to catch issues from downtime."""
        logger.info("Running startup recovery check")
        await recover_status_transitions()
    
    async def _dlq_monitor_loop(self):
        """Monitor DLQ and trigger recovery when messages appear."""
        last_depth = 0
        
        while not self.shutdown_requested:
            try:
                dlq_depth = await get_queue_depth("dead_letter_queue")
                
                # Trigger recovery when DLQ depth increases
                if dlq_depth > last_depth:
                    logger.warning(
                        f"DLQ depth increased: {last_depth} → {dlq_depth}, "
                        f"running recovery"
                    )
                    await recover_status_transitions()
                
                last_depth = dlq_depth
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"DLQ monitor error: {e}")
                await asyncio.sleep(60)
    
    async def recover_status_transitions(self):
        """Query and recover missed status transitions."""
        async with get_db_session() as db:
            stuck = await db.execute(
                select(GameStatusSchedule)
                .filter(GameStatusSchedule.executed == False)
                .filter(GameStatusSchedule.transition_time < utc_now())
            )
            
            count = 0
            for schedule in stuck.scalars():
                logger.warning(
                    f"Recovering: game={schedule.game_id}, "
                    f"target={schedule.target_status}"
                )
                await process_status_transition(schedule)
                count += 1
            
            if count > 0:
                logger.info(f"Recovered {count} missed status transitions")
```

**Benefits**:
- ✅ Startup recovery catches downtime issues
- ✅ DLQ monitoring provides ongoing recovery
- ✅ No constant polling when system healthy
- ✅ Simple implementation (no separate consumer)
- ✅ Handles both failure modes (downtime + runtime failures)

**Considerations**:
- Slightly more complex than pure periodic
- DLQ depth check still happens every minute
- Recovery triggered by depth increase (not per message)

### Critical Analysis: Does Empty DLQ Mean No Issues?

**The assumption**: `DLQ empty` → `no failures` → `no recovery needed`

**Edge cases where this assumption fails**:

1. **Message never published** (daemon crash before publish)
   - Schedule item in database
   - Daemon crashes before publishing to RabbitMQ
   - No message in queue, no message in DLQ
   - But transition still needs to happen
   - **DLQ won't help**

2. **Message lost in transit** (network partition)
   - Daemon publishes successfully (from its perspective)
   - Network partition between daemon and RabbitMQ
   - Message never reaches broker
   - No message in queue, no message in DLQ
   - **DLQ won't help**

3. **Message ACKed incorrectly** (our current bug)
   - Message delivered to consumer
   - Handler fails
   - `message.process()` ACKs anyway
   - Message never reaches DLQ (ACKed = removed)
   - But transition wasn't processed
   - **DLQ won't help**

4. **Bot was down during transition time**
   - Schedule time passes while bot offline
   - Message expires (24-hour TTL) and goes to DLQ
   - Bot comes back online
   - DLQ has message! Recovery should run
   - **DLQ DOES help** ✓

**Conclusion**: DLQ is a useful signal but **not comprehensive**.

### Recommended Hybrid Approach

**Use DLQ as a signal, but don't rely on it exclusively**:

```python
async def recovery_strategy():
    # 1. Always run on startup (catches downtime issues)
    await recover_status_transitions()
    
    # 2. Monitor DLQ for ongoing issues
    while running:
        dlq_depth = await get_queue_depth("dead_letter_queue")
        
        if dlq_depth > 0:
            # DLQ has messages = something failed recently
            await recover_status_transitions()
            await asyncio.sleep(60)  # Check again soon
        else:
            # DLQ empty = system healthy (probably)
            # But still check periodically (every 10 min) for edge cases
            await asyncio.sleep(600)
```

**Why this works**:
- Startup recovery: catches issues from bot downtime
- DLQ monitoring: catches most runtime failures
- Periodic fallback: catches edge cases (never published, lost in transit, ACKed incorrectly)
- Adaptive polling: frequent when issues detected, infrequent when healthy

### Comparison: Pure Periodic vs DLQ-Triggered

**Pure Periodic (every 5 min)**:
```python
while True:
    await recover_status_transitions()  # Always run
    await asyncio.sleep(300)
```
- Queries: 288 per day (every 5 min)
- Recovery runs even when unnecessary
- Constant database load

**DLQ-Triggered with Fallback**:
```python
while True:
    dlq_depth = await get_queue_depth("dead_letter_queue")
    
    if dlq_depth > 0:
        await recover_status_transitions()
        await asyncio.sleep(60)  # Check soon
    else:
        # Fallback check
        if time_since_last_recovery > 600:  # 10 min
            await recover_status_transitions()
        await asyncio.sleep(60)
```
- Queries: ~144 per day when healthy (every 10 min)
- Immediate recovery when DLQ has messages
- 50% reduction in unnecessary queries

### Final Recommendation

**Implement Approach 3 (Hybrid)**:

1. **Startup recovery** - Always run when bot starts
2. **DLQ-triggered recovery** - Check DLQ depth every minute
   - If depth > 0: run recovery, wait 1 min, repeat
   - If depth = 0: wait 10 min before next check
3. **Periodic fallback** - If DLQ empty for 10 min, still run recovery once (catches edge cases)

**Benefits**:
- Event-driven when failures occur (DLQ signal)
- Adaptive polling (frequent when issues, infrequent when healthy)
- Catches all edge cases (startup, lost messages, incorrect ACKs)
- Minimal overhead when system healthy
- Simple implementation (~50 lines)

**This is superior to**:
- Pure periodic (unnecessary queries)
- Pure DLQ trigger (misses edge cases)
- DLQ consumer (additional service complexity)

The DLQ serves as a useful **optimization** for recovery triggering, not a **replacement** for periodic checks.

## Recovery Loop Placement: Architectural Analysis

### Current System Architecture

**Three main service components**:
1. **Bot Service** (`services/bot/`)
   - Discord bot with Gateway connection
   - Event consumer listening to `bot_events` queue
   - Handlers process GAME_REMINDER_DUE and GAME_STATUS_TRANSITION_DUE events
   - Lifecycle: Starts on bot ready, runs continuously

2. **Notification Daemon** (`services/scheduler/notification_daemon_wrapper.py`)
   - Polls `NotificationSchedule` table periodically
   - Publishes GAME_REMINDER_DUE events to RabbitMQ
   - Generic daemon instance with notification-specific configuration

3. **Status Transition Daemon** (`services/scheduler/status_transition_daemon_wrapper.py`)
   - Polls `GameStatusSchedule` table periodically
   - Publishes GAME_STATUS_TRANSITION_DUE events to RabbitMQ
   - Generic daemon instance with transition-specific configuration

**Key Observation**: Daemons publish events, bot consumes and processes them.

### Option 1: Recovery in Bot Service

**Place recovery loop in bot alongside event consumer**:

```python
# services/bot/events/handlers.py

class EventHandlers:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.consumer = None
        self.shutdown_requested = False
        # ... existing handler setup
    
    async def start_consuming(self, queue_name: str = "bot_events"):
        """Start event consumer and recovery loop."""
        self.consumer = EventConsumer(queue_name=queue_name)
        await self.consumer.connect()
        await self.consumer.bind("#")
        
        # Run startup recovery before starting consumer
        await self._startup_recovery()
        
        # Start both tasks concurrently
        await asyncio.gather(
            self.consumer.start_consuming(self._process_event),
            self._recovery_loop(),
        )
    
    async def _startup_recovery(self):
        """Run recovery on bot startup."""
        logger.info("Running startup recovery check")
        await self._recover_status_transitions()
    
    async def _recovery_loop(self):
        """Monitor DLQ and trigger recovery adaptively."""
        last_depth = 0
        last_recovery_time = time.time()
        
        while not self.shutdown_requested:
            try:
                # Check DLQ depth (requires adding RabbitMQ management API call)
                dlq_depth = await self._get_queue_depth("dead_letter_queue")
                
                if dlq_depth > 0:
                    # DLQ has messages - run recovery frequently
                    logger.warning(
                        f"DLQ depth: {dlq_depth}, running recovery"
                    )
                    await self._recover_status_transitions()
                    last_recovery_time = time.time()
                    await asyncio.sleep(60)  # Check again in 1 min
                else:
                    # DLQ empty - check if fallback period elapsed
                    if time.time() - last_recovery_time > 600:  # 10 min
                        logger.debug("Fallback recovery check")
                        await self._recover_status_transitions()
                        last_recovery_time = time.time()
                    
                    await asyncio.sleep(60)
                    
            except Exception as e:
                logger.error(f"Recovery loop error: {e}")
                await asyncio.sleep(60)
    
    async def _recover_status_transitions(self):
        """Query database and recover missed transitions."""
        async with get_db_session() as db:
            stuck = await db.execute(
                select(GameStatusSchedule)
                .filter(GameStatusSchedule.executed == False)
                .filter(GameStatusSchedule.transition_time < utc_now())
            )
            
            count = 0
            for schedule in stuck.scalars():
                logger.warning(
                    f"Recovering missed transition: game={schedule.game_id}, "
                    f"target={schedule.target_status}"
                )
                # Call existing handler directly
                event = GameStatusTransitionDueEvent(
                    game_id=schedule.game_id,
                    target_status=schedule.target_status,
                    schedule_id=schedule.id,
                )
                await self._handle_status_transition_due(event)
                count += 1
            
            if count > 0:
                logger.info(f"Recovered {count} missed status transitions")
    
    async def _get_queue_depth(self, queue_name: str) -> int:
        """Get message count from queue via RabbitMQ Management API."""
        # Implementation using httpx to call RabbitMQ management API
        # http://rabbitmq:15672/api/queues/%2F/{queue_name}
        pass
```

**Pros**:
- ✅ **Recovery runs where processing happens** - bot is the consumer
- ✅ **Single service restart fixes both issues** - consumer bug + recovery
- ✅ **Shares database session pool** with event handlers
- ✅ **No new service/container** to deploy and monitor
- ✅ **Natural placement** - bot processes events, bot recovers failed processing

**Cons**:
- ❌ **Bot becomes more complex** - now does consumption + recovery
- ❌ **Recovery depends on bot being up** - if bot down, no recovery runs
- ❌ **Couples recovery to Discord connection** - bot lifecycle tied to Gateway

### Option 2: Recovery in Existing Daemons

**Add recovery logic to notification/status transition daemons**:

```python
# services/scheduler/status_transition_daemon_wrapper.py

def main() -> None:
    """Entry point with recovery loop."""
    # ... existing setup
    
    daemon = SchedulerDaemon(
        database_url=BASE_DATABASE_URL,
        rabbitmq_url=rabbitmq_url,
        model_class=GameStatusSchedule,
        schedule_table_name="game_status_schedule",
        time_column_name="transition_time",
        event_builder=build_status_transition_event,
        check_interval=60,
    )
    
    # Run normal daemon loop in background
    import threading
    daemon_thread = threading.Thread(target=daemon.run, args=(lambda: shutdown_requested,))
    daemon_thread.start()
    
    # Run recovery loop in main thread
    recovery_loop(daemon.session_factory)
    
    daemon_thread.join()


def recovery_loop(session_factory):
    """Check for missed transitions and republish."""
    last_recovery = 0
    
    while not shutdown_requested:
        try:
            # Every 10 minutes, check for missed items
            if time.time() - last_recovery > 600:
                with session_factory() as db:
                    stuck = db.query(GameStatusSchedule).filter(
                        GameStatusSchedule.executed == False,
                        GameStatusSchedule.transition_time < utc_now(),
                    ).all()
                    
                    for schedule in stuck:
                        logger.warning(f"Republishing missed transition: {schedule.game_id}")
                        # Reset executed flag and let daemon pick it up
                        schedule.executed = False
                        db.commit()
                
                last_recovery = time.time()
            
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Recovery error: {e}")
            time.sleep(60)
```

**Pros**:
- ✅ **Daemon already has database access** and connection pool
- ✅ **Recovery runs even if bot is down** - independent service
- ✅ **Simple addition** to existing daemon wrapper

**Cons**:
- ❌ **Wrong responsibility** - daemons publish events, they don't consume/process
- ❌ **Recovery reset** doesn't fix the root cause (failed processing in bot)
- ❌ **Creates duplicate events** - both daemon polling and recovery reset
- ❌ **Doesn't use DLQ signal** - can't check queue depth from daemon easily
- ❌ **Redundant with daemon's existing job** - daemon already publishes due items

**Critical Issue**: Daemons poll for items where `executed=False` and `time < now()`. If recovery just resets `executed=False`, the daemon will pick it up on next poll. But this creates a **race condition** and **doesn't leverage DLQ as a signal**.

### Option 3: New Recovery Daemon

**Create dedicated recovery service**:

```python
# services/scheduler/recovery_daemon.py

"""
Recovery daemon for handling failed event processing.

Monitors DLQ and database to recover from failures.
"""

import asyncio
import logging
import os
import signal
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session, BASE_DATABASE_URL
from shared.models import GameStatusSchedule
from shared.messaging.publisher import EventPublisher
from shared.schemas.events import GameStatusTransitionDueEvent, EventType
from shared.utils import utc_now

logger = logging.getLogger(__name__)

shutdown_requested = False


def signal_handler(signum: int, frame) -> None:
    global shutdown_requested
    logger.info(f"Received signal {signum}, shutting down")
    shutdown_requested = True


async def get_queue_depth(queue_name: str) -> int:
    """Get message count from RabbitMQ Management API."""
    import httpx
    
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
    rabbitmq_pass = os.getenv("RABBITMQ_PASS", "guest")
    
    url = f"http://{rabbitmq_host}:15672/api/queues/%2F/{queue_name}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            auth=(rabbitmq_user, rabbitmq_pass),
        )
        data = response.json()
        return data.get("messages", 0)


async def recover_status_transitions(publisher: EventPublisher):
    """Query database and republish missed transitions."""
    async with get_db_session() as db:
        stuck = await db.execute(
            select(GameStatusSchedule)
            .filter(GameStatusSchedule.executed == False)
            .filter(GameStatusSchedule.transition_time < utc_now())
        )
        
        count = 0
        for schedule in stuck.scalars():
            logger.warning(
                f"Recovering: game={schedule.game_id}, target={schedule.target_status}"
            )
            
            event = GameStatusTransitionDueEvent(
                game_id=schedule.game_id,
                target_status=schedule.target_status,
                schedule_id=schedule.id,
            )
            
            await publisher.publish(
                event_type=EventType.GAME_STATUS_TRANSITION_DUE,
                event_data=event.model_dump(),
                routing_key="game.status.transition.due",
            )
            
            count += 1
        
        if count > 0:
            logger.info(f"Recovered {count} missed transitions")


async def recovery_loop():
    """Main recovery loop with adaptive polling."""
    publisher = EventPublisher()
    await publisher.connect()
    
    last_recovery_time = time.time()
    
    # Run startup recovery
    logger.info("Running startup recovery")
    await recover_status_transitions(publisher)
    
    while not shutdown_requested:
        try:
            dlq_depth = await get_queue_depth("dead_letter_queue")
            
            if dlq_depth > 0:
                # DLQ has messages - run recovery
                logger.warning(f"DLQ depth: {dlq_depth}, running recovery")
                await recover_status_transitions(publisher)
                last_recovery_time = time.time()
                await asyncio.sleep(60)
            else:
                # DLQ empty - use fallback interval
                if time.time() - last_recovery_time > 600:  # 10 min
                    logger.debug("Fallback recovery check")
                    await recover_status_transitions(publisher)
                    last_recovery_time = time.time()
                
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Recovery loop error: {e}")
            await asyncio.sleep(60)
    
    await publisher.disconnect()


def main():
    """Entry point for recovery daemon."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    asyncio.run(recovery_loop())


if __name__ == "__main__":
    main()
```

**Pros**:
- ✅ **Clear separation of concerns** - dedicated recovery service
- ✅ **Independent of bot lifecycle** - runs even if bot crashes
- ✅ **Can leverage DLQ monitoring** - checks queue depth
- ✅ **Publishes recovery events** - uses existing event flow
- ✅ **Easy to scale** - can run multiple instances with coordination

**Cons**:
- ❌ **New service to deploy** - additional container, Dockerfile, compose entry
- ❌ **New infrastructure** - monitoring, logging, health checks
- ❌ **Republishes events** - creates duplicate events (recovery daemon → RabbitMQ → bot)
- ❌ **Doesn't call handlers directly** - still depends on bot consumer working

**Critical Question**: Does recovery republish to RabbitMQ or call handlers directly?
- If **republish**: Depends on bot consumer being fixed (otherwise infinite loop)
- If **call handlers directly**: Recovery daemon needs Discord bot instance (complex)

### Comparison Matrix

| Criteria | Bot Recovery | Daemon Recovery | New Recovery Service |
|----------|-------------|-----------------|---------------------|
| **Simplicity** | ✅ Add to existing | ✅ Add to existing | ❌ New service |
| **Separation of Concerns** | ⚠️ Bot does more | ❌ Wrong responsibility | ✅ Dedicated service |
| **Independence** | ❌ Requires bot up | ✅ Independent | ✅ Independent |
| **Leverages DLQ** | ✅ Can check depth | ⚠️ Harder to check | ✅ Can check depth |
| **Calls Handlers** | ✅ Direct call | ❌ Can't call bot handlers | ❌ Can't call bot handlers |
| **Republish Events** | ❌ Not needed | ⚠️ Creates duplicates | ⚠️ Creates duplicates |
| **Deployment Complexity** | ✅ No changes | ✅ No changes | ❌ New container |
| **Scalability** | ⚠️ One per bot | ⚠️ One per daemon | ✅ Can scale |

### Recommended Approach: Daemon-Based DLQ Processing

**FINAL DECISION: Add DLQ processing to existing daemons** to preserve architectural purity.

**Key insight from user**: "The existing service periodically wakes to make sure it didn't miss a message from the DB. On at least some of those wakes it could also just resend the DLQ messages"

**Why daemon-based DLQ processing is superior**:

1. **Preserves separation of concerns** - Daemons publish, bot consumes (no mixing)
2. **Daemon already wakes periodically** - Natural place to check DLQ
3. **Works during bot downtime** - RabbitMQ buffers for 24hr, daemon can republish when bot returns
4. **Architectural purity** - Bot remains purely event-driven consumer
5. **No new infrastructure** - Add ~80 lines to existing generic_scheduler_daemon.py

**How it works**:
1. **Daemon startup**: Process DLQ before starting normal loop
2. **Periodic DLQ check**: Every N iterations or on timer, consume from DLQ
3. **Event-type-specific retry limits**: 
   - Notifications: max 3 retries (use x-death header count)
   - Status transitions: max 20 retries
4. **Republish to primary queue**: Send message back through normal flow
5. **Database remains source of truth**: Daemon still polls DB for `executed=False`

**Implementation in generic_scheduler_daemon.py**:

```python
class SchedulerDaemon:
    def __init__(self, ..., process_dlq: bool = False, dlq_check_interval: int = 300):
        # ... existing init
        self.process_dlq = process_dlq
        self.dlq_check_interval = dlq_check_interval
        self.last_dlq_check = 0
    
    def run(self, shutdown_requested):
        # Process DLQ on startup
        if self.process_dlq:
            self._process_dlq_messages()
        
        # Normal loop with periodic DLQ checks
        while not shutdown_requested():
            self._process_loop_iteration()
            
            # Check if DLQ processing is due
            if self.process_dlq and time.time() - self.last_dlq_check > self.dlq_check_interval:
                self._process_dlq_messages()
                self.last_dlq_check = time.time()
    
    def _process_dlq_messages(self):
        """Consume from DLQ and republish with retry limits."""
        dlq_depth = self._get_queue_depth("dead_letter_queue")
        
        if dlq_depth == 0:
            logger.debug("DLQ empty, no recovery needed")
            return
        
        logger.warning(f"Processing {dlq_depth} messages from DLQ")
        
        # Consume from DLQ
        for message in self._consume_dlq(limit=dlq_depth):
            if self._should_retry_dlq_message(message):
                # Republish to primary queue
                event = self._extract_event(message)
                self.publisher.publish(event)
                logger.info(f"Republished from DLQ: {event.event_type}")
            else:
                # Max retries exceeded - log and discard
    def _should_retry_dlq_message(self, message) -> bool:
        """Check if message should be republished from DLQ."""
        event_type = self._extract_event_type(message)
        
        if event_type == EventType.GAME_REMINDER_DUE:
            # Notifications: Check if still valid (not expired)
            # Per-message TTL will have expired stale messages
            # If in DLQ and not expired, republish
            return True
        elif event_type == EventType.GAME_STATUS_TRANSITION_DUE:
            # Status transitions: Always republish (must eventually succeed)
            # No retry limit - keep trying indefinitely
            return True
        else:
            # Other events: Always republish
            return True
            # Default: max 3 retries
            return retry_count < 3
    
    def _get_queue_depth(self, queue_name: str) -> int:
        """Query RabbitMQ Management API for queue depth."""
        # Implementation using requests/httpx
        pass
```

**Configuration in daemon wrappers**:

```python
# services/scheduler/status_transition_daemon_wrapper.py
daemon = SchedulerDaemon(
    # ... existing config
    process_dlq=True,  # Enable DLQ processing
    dlq_check_interval=300,  # Check every 5 minutes
)

# services/scheduler/notification_daemon_wrapper.py
daemon = SchedulerDaemon(
    # ... existing config
    process_dlq=True,  # Enable DLQ processing for notifications too
    dlq_check_interval=300,  # Check every 5 minutes
)
```

**Why this is better than bot-based recovery**:

| Aspect | Bot Recovery | Daemon DLQ Processing |
|--------|-------------|----------------------|
| **Architecture** | ❌ Bot does publishing | ✅ Daemon publishes, bot consumes |
| **Bot complexity** | ❌ Adds recovery logic | ✅ Bot stays simple |
| **Bot downtime** | ❌ No recovery while down | ✅ Daemon can republish when bot returns |
| **RabbitMQ buffering** | ⚠️ Limited by bot lifecycle | ✅ Uses full 24hr TTL window |
| **Separation of concerns** | ⚠️ Blurred | ✅ Clean |

**User requirements captured**:
- ✅ "The daemons should run the DLQ as part of startup"
- ✅ "On at least some of those wakes it could also just resend the DLQ messages"
- ✅ Bot remains purely event-driven
- ✅ No new services/containers

### Implementation Checklist

**Phase 1: Fix Bot Consumer** (~5 lines)
- [ ] Update `shared/messaging/consumer.py` to use manual ACK/NACK
- [ ] Success → ACK, failure → NACK to DLQ (no requeue)
- [ ] Simple approach: all failures go to DLQ for daemon processing

**Phase 2: Add DLQ Processing to Daemon** (~40 lines)
- [ ] Add `process_dlq` flag to SchedulerDaemon.__init__()
- [ ] Implement `_process_dlq_messages()` method
  - Simple logic: republish all messages without TTL
  - No x-death header checking needed
  - Bot handler checks staleness defensively
- [ ] Implement `_get_queue_depth()` using RabbitMQ Management API
- [ ] Call `_process_dlq_messages()` on startup
- [ ] Call `_process_dlq_messages()` periodically in main loop

**Phase 2b: Make Bot Handler Defensive** (~10 lines)
- [ ] Update `_handle_game_reminder_due()` in bot
- [ ] Check if `game.scheduled_at < now()` before processing
- [ ] Skip notification if game already started
- [ ] Log skipped stale notifications for monitoring

**Phase 3: Configure Daemon Wrappers** (~5 lines)
- [ ] Enable `process_dlq=True` for **both** status_transition_daemon_wrapper.py and notification_daemon_wrapper.py
- [ ] Set `dlq_check_interval=300` (5 minutes) for both daemons

**Phase 4: Per-Message TTL** (~50 lines)
- [ ] Add `expiration_ms` parameter to sync_publisher.py
- [ ] Update event_builders to return (Event, expiration_ms) tuple
- [ ] Calculate TTL as milliseconds until game starts
- [ ] Update daemon to handle tuple and pass TTL

**Phase 5: Schema Enhancement** (~30 lines)
- [ ] Create migration to add `game_scheduled_at` to notification_schedule
- [ ] Update NotificationSchedule model
- [ ] Update populate_schedule() service method
- [ ] Update build_game_reminder_event() to use denormalized field
**Total implementation**: ~150 lines across 5 components
**Total implementation**: ~185 lines across 5 components

### Final Recommendation: Daemon-Based DLQ Processing

**ARCHITECTURAL DECISION: Daemons process DLQ, not bot**

This preserves clean separation of concerns:
- **Daemons**: Query database, publish events, republish from DLQ
- **Bot**: Consume events, process handlers, NACK failures to DLQ

**Implementation approach**:
1. Fix bot consumer to use manual NACK (sends failures to DLQ)
2. Add DLQ processing to generic_scheduler_daemon.py
3. Enable DLQ processing for **both** notification and status transition daemons
4. Process DLQ on daemon startup + every 5 minutes

**Benefits**:
- ✅ **Architectural purity** - Bot stays purely event-driven
- ✅ **Works during bot downtime** - Daemon can republish when bot returns
- ✅ **Uses RabbitMQ's 24hr buffering** - Full window for recovery
- ✅ **No new infrastructure** - Just enhance existing daemon
- ✅ **Event-type-specific retry** - 3 for notifications, 20 for transitions

**User insight**: "The existing service periodically wakes to make sure it didn't miss a message from the DB. On at least some of those wakes it could also just resend the DLQ messages"

## Critical Analysis: Are Daemons Redundant?

## Per-Message TTL for Game Notifications

### User Requirement

**Request**: "Game notification message should actually have a TTL that expires when the game starts, since they are no longer interesting and have lost their usefulness"

**Current behavior**: All messages in `bot_events` queue have 24-hour TTL (queue-level setting)

**Desired behavior**: Notification messages should expire when game starts (dynamic, per-message TTL)

### RabbitMQ Per-Message TTL

**Good news**: RabbitMQ supports per-message TTL via `expiration` property.

**How it works**:
- Publisher sets `expiration` property on individual messages
- Value must be string representation of milliseconds
- Overrides queue-level TTL (`x-message-ttl`)
- **Critical behavior**: Message expiration happens **in the primary queue**
  - Message expires while waiting in `bot_events` queue
  - **With `x-dead-letter-exchange` set**: Expired message dead-lettered to DLQ
  - **Without `x-dead-letter-exchange`**: Expired message discarded (removed entirely)

**Key insight for our use case**:
- Notifications expire in primary queue when game starts
- Bot consumer NACKs failed messages to DLQ immediately (before expiration)
- Therefore: Only **rejected (failed)** notifications reach DLQ, not expired ones
- Any notification in DLQ was rejected before its TTL expired (game hasn't started yet)
- Result: DLQ only contains messages worth retrying (no expired messages to filter)

**Example**:
```python
# In sync_publisher.py
properties = pika.BasicProperties(
    delivery_mode=pika.DeliveryMode.Persistent,
    expiration='3600000',  # Expire in 1 hour (milliseconds as string)
)
channel.basic_publish(exchange, routing_key, body, properties)
```

### Implementation Approach

**Step 1: Enhance sync_publisher.py** (~10 lines)

```python
def publish(self, event: Event, expiration_ms: int | None = None) -> None:
    """Publish event with optional per-message TTL."""
    properties = pika.BasicProperties(
        delivery_mode=pika.DeliveryMode.Persistent,
        content_type="application/json",
    )
    
    # Add expiration if specified
    if expiration_ms is not None:
        properties.expiration = str(expiration_ms)
    
    # ... rest of publish logic
```

**Step 2: Update event builders to calculate TTL** (~20 lines per builder)

```python
# services/scheduler/event_builders.py

def build_game_reminder_event(
    notification: NotificationSchedule
) -> tuple[Event, int | None]:
    """
    Build GAME_REMINDER_DUE event with per-message TTL.
    
    Returns:
        (Event, expiration_ms) tuple
    """
    event_data = GameReminderDueEvent(
        game_id=UUID(notification.game_id),
        reminder_minutes=notification.reminder_minutes,
    )
    
    event = Event(
        event_type=EventType.GAME_REMINDER_DUE,
        data=event_data.model_dump(),
    )
    
    # Calculate TTL: expire when game starts
    expiration_ms = None
    if notification.game_scheduled_at:  # Using denormalized field
        time_until_game = (notification.game_scheduled_at - utc_now()).total_seconds()
        
        if time_until_game > 0:
            expiration_ms = int(time_until_game * 1000)
            logger.debug(
                f"Notification TTL: {time_until_game:.0f}s until game starts"
            )
        else:
            # Game already started - expire immediately
            expiration_ms = 1
            logger.warning("Game already started, notification will expire immediately")
    
    return event, expiration_ms


def build_status_transition_event(
    schedule: GameStatusSchedule
) -> tuple[Event, int | None]:
    """
    Build GAME_STATUS_TRANSITION_DUE event (no TTL - never expires).
    
    Returns:
        (Event, None) - status transitions never expire
    """
    event_data = GameStatusTransitionDueEvent(
        game_id=UUID(schedule.game_id),
        target_status=schedule.target_status,
    )
    
    event = Event(
        event_type=EventType.GAME_STATUS_TRANSITION_DUE,
        data=event_data.model_dump(),
    )
    
    # Status transitions NEVER expire - must eventually succeed
    return event, None
```

**Step 3: Update daemon to handle tuple return** (~10 lines)

```python
# services/scheduler/generic_scheduler_daemon.py

def _process_item(self, item):
    """Process scheduled item."""
    try:
        # Build event (now returns tuple)
        result = self.event_builder(item)
        
        # Handle both tuple and single return for backward compatibility
        if isinstance(result, tuple):
            event, expiration_ms = result
        else:
            event, expiration_ms = result, None
        
        # Publish with optional TTL
        self.publisher.publish(event, expiration_ms=expiration_ms)
        
        # Mark as processed and commit
        # ... existing logic
```

### Dependencies: Schema Denormalization

**Problem**: Need `game.scheduled_at` to calculate TTL, but accessing `notification.game.scheduled_at` requires:
- Loading the relationship (N+1 queries)
- JOIN in daemon query (slower)

**Solution**: Add `game_scheduled_at` to `notification_schedule` table (see Schema Enhancement section below)

**Benefit**: Event builder has direct access without JOIN or relationship loading

### Current Daemon Sleep Interval

**User question**: "I think current sleep interval is 900 seconds - there is no reason to make it shorter"

**Verification from generic_scheduler_daemon.py**:
```python
def run(self, shutdown_requested, max_timeout: int = 900):
```

**Confirmed**: Default sleep interval is 900 seconds (15 minutes) - no change needed.

**Why this is appropriate**:
- Daemon wakes on PostgreSQL NOTIFY (instant for new items)
- 900s timeout is fallback for missed notifications
- Notifications are not time-critical to the second
- Status transitions use same mechanism

## Per-Message TTL Expiration: Discard vs Dead-Letter

### The Problem

When implementing per-message TTL for notifications (expire when game starts), we face a choice:

**Option 1: Expired messages go to DLQ** (current configuration)
- Queue has `x-dead-letter-exchange` configured
- Expired notifications sent to DLQ
- DLQ processing must check expiration and skip expired messages
- Adds complexity to daemon DLQ processing

**Option 2: Expired messages are discarded** (remove DLX for TTL expiration)
- RabbitMQ discards expired messages automatically
- DLQ only receives rejected messages (handler failures)
- Simpler DLQ processing - all DLQ messages should be republished
- Cleaner separation: TTL = discard, failure = DLQ

### Current Configuration Analysis

From `rabbitmq/definitions.json`:
```json
{
  "name": "bot_events",
  "arguments": {
    "x-dead-letter-exchange": "game_scheduler.dlx",
    "x-message-ttl": 86400000
  }
}
```

**Current behavior**:
- Queue-level TTL: 24 hours
- All expired messages → DLQ
- Per-message TTL would also send to DLQ

### Option 1: DLQ Processing Checks Expiration

**Implementation**: Daemon DLQ processing inspects message properties and skips expired messages.

```python
def _should_retry_dlq_message(self, message) -> bool:
    """Check if message should be republished from DLQ."""
    # Check if message has expired
    if 'expiration' in message.properties:
        expiration_ms = int(message.properties['expiration'])
        # If expiration time has passed, discard (don't republish)
        # This is tricky - we don't know when message was published
        # RabbitMQ already checked expiration before sending to DLQ
        pass
    
    # Check event type
    event = Event.model_validate_json(message.body)
    
    # Notifications already expired if in DLQ (via per-message TTL)
    if event.event_type == EventType.GAME_REMINDER_DUE:
        return False  # Don't republish expired notifications
    
    # Status transitions always republish
    if event.event_type == EventType.GAME_STATUS_TRANSITION_DUE:
        return True
    
    return False
```

**Problems**:
- RabbitMQ **doesn't include original expiration property** in dead-lettered messages
- Can't easily determine if message was expired vs rejected
- Need to inspect `x-death` header to determine dead-letter reason
- `x-death[0]['reason']` can be: `expired`, `rejected`, `maxlen`, `ttl`
- More complex logic in daemon

**Benefits**:
- Single queue configuration
- All message types in same queue
- No RabbitMQ configuration changes needed

### Option 2: Remove DLX, Let RabbitMQ Discard Expired Messages

**Challenge**: We need DLX for **rejected messages** (handler failures), but not for **expired messages** (TTL).

**RabbitMQ limitation**: Queue either has DLX or doesn't - can't differentiate by reason.

**Potential solutions**:

#### Solution 2a: Per-Event-Type Queues
Create separate queues for notifications and status transitions:
```json
{
  "name": "bot_events.notifications",
  "arguments": {
    // NO x-dead-letter-exchange - expired messages discarded
  }
},
{
  "name": "bot_events.transitions",
  "arguments": {
    "x-dead-letter-exchange": "game_scheduler.dlx"  // Keep DLX for failures
  }
}
```

**Benefits**:
- Expired notifications discarded automatically
- Status transition failures go to DLQ
- Daemon DLQ processing only sees messages that should be republished
- Cleaner logic

**Drawbacks**:
- More complex queue configuration
- Need routing changes in publisher
- Need to consume from multiple queues in bot
- Architectural change

#### Solution 2b: Accept Expired Messages in DLQ

Just accept that expired notifications go to DLQ and handle in daemon:

```python
def _should_retry_dlq_message(self, message) -> bool:
    """Check if message should be republished from DLQ."""
    # Inspect x-death header
    if 'x-death' in message.headers:
        death_info = message.headers['x-death'][0]
        reason = death_info.get('reason')
        
        # If expired, check event type
        if reason == 'expired':
            event = Event.model_validate_json(message.body)
            # Expired notifications - don't republish
            if event.event_type == EventType.GAME_REMINDER_DUE:
                return False
            # Expired status transitions shouldn't happen (no TTL set)
            # But if they do, republish anyway
            return True
        
        # If rejected (handler failure), check event type
        if reason == 'rejected':
            event = Event.model_validate_json(message.body)
            # Always republish status transitions
            if event.event_type == EventType.GAME_STATUS_TRANSITION_DUE:
                return True
            # Could republish notifications, but probably already stale
            return False
    
    # No x-death header - shouldn't happen
    return False
```

**Benefits**:
- No RabbitMQ configuration changes
- Single queue for all event types
- Logic handles both expiration and rejection

**Drawbacks**:
- DLQ accumulates expired notifications
- Daemon must parse and inspect all DLQ messages
- More complex logic

### Recommendation

**Use Option 2b: Accept expired messages in DLQ with event-type-aware logic**.

**Rationale**:
1. **Simplicity**: No RabbitMQ configuration changes needed
2. **Flexibility**: Logic can differentiate between expiration and rejection
3. **Observability**: Can monitor how many notifications expire vs fail
4. **Correctness**: Handles all cases (expired notifications, failed notifications, failed transitions)
5. **Low overhead**: Expired notifications should be rare (sent minutes before game starts)

**Implementation**:
- **Simplified approach: Bot handles staleness defensively**
- **Two ways messages reach DLQ**:
  1. **Expired** (TTL expiration): `x-death[0]['reason'] = 'expired'`
     - Message sat in primary queue until TTL elapsed (unconsumed)
     - With `x-dead-letter-exchange`: dead-lettered to DLQ
     - Without `x-dead-letter-exchange`: discarded (not sent to DLQ)
  2. **Rejected** (handler failure): `x-death[0]['reason'] = 'rejected'`
     - Bot consumer NACKed after handler failed
     - Could be stale if game started while in DLQ
     - **Should republish** - bot handler checks staleness

**Key insight: Per-message TTL is relative to publish time**:
- `expiration='600000'` means "10 minutes from NOW"
- When daemon republishes, TTL resets (new 10-minute window)
- Stale notification (game started at 8:00, republished at 8:02) gets delivered
- **Bot handler must check game status** and skip if already started

**Daemon logic**:
- Can republish all DLQ messages without checking x-death
- Remove TTL when republishing (let bot decide staleness)
- Bot handler is defensive: check game.scheduled_at before processing

**Simplified daemon logic**:
```python
def _process_dlq_messages(self):
    """Consume from DLQ and republish all messages.
    
    Simple approach: Republish everything without TTL.
    - Expired messages: Sat unconsumed until TTL elapsed (rare)
    - Rejected messages: Handler failed (common)
    
    Per-message TTL resets on republish (relative to publish time).
    Bot handler checks game status before processing (defensive).
    """
    # Connect to DLQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.rabbitmq_host))
    channel = connection.channel()
    
    # Get queue depth first
    queue_state = channel.queue_declare(queue='dead_letter_queue', passive=True)
    message_count = queue_state.method.message_count
    
    if message_count == 0:
        logger.debug("DLQ is empty, nothing to process")
        connection.close()
        return
    
    logger.info(f"Processing {message_count} messages from DLQ")
    
    processed = 0
    republished = 0
    discarded = 0
    
    # Consume messages one at a time
    for method, properties, body in channel.consume('dead_letter_queue', auto_ack=False):
        try:
            # Parse event and republish (no x-death checking needed)
            event = Event.model_validate_json(body)
            
            # Republish without TTL (bot handler checks staleness defensively)
            self.publisher.publish(event, expiration_ms=None)
            republished += 1
            
            # ACK the DLQ message
            channel.basic_ack(method.delivery_tag)
            processed += 1
            
            # Break if we've processed all messages
            if processed >= message_count:
                break
                
        except Exception as e:
            logger.error(f"Error processing DLQ message: {e}")
            # NACK without requeue - don't want to get stuck
            channel.basic_nack(method.delivery_tag, requeue=False)
    
    channel.cancel()
    connection.close()
    
    logger.info(f"DLQ processing: {republished} messages republished")
```

**Why this works**:
- Per-message TTL is relative to publish time (resets on republish)
- Stale notifications get delivered to bot after republish
- Bot handler checks `game.scheduled_at < now()` and skips stale notifications
- Defensive programming in bot is simpler than complex DLQ logic
- Works for both expired (rare) and rejected (common) messages

This approach is simpler and doesn't require x-death header inspection.


## Comprehensive Solution Summary

### Final Architecture

**Three complementary mechanisms for reliability**:
1. **Manual ACK/NACK in Bot Consumer** (~5 lines)
   - Fix: Replace `message.process()` with manual acknowledgment
   - Success → ACK, failure → NACK to DLQ (no requeue)
   - Simple: all failures go to DLQ for daemon processing
   - Eliminates message loss from auto-ACK bug

2. **Daemon-Based DLQ Processing** (~40 lines)
   - Add to `generic_scheduler_daemon.py`
   - Process DLQ on startup + every 5 minutes
   - Simple logic: republish all messages without TTL
   - Bot handler checks game status defensively (skip if started)
   - Enable for **both** notification and status transition daemons
   - Preserves architectural purity (daemon publishes, bot consumes)

3. **Per-Message TTL for Notifications** (~50 lines)
   - Add `expiration_ms` parameter to publisher
   - Calculate TTL = milliseconds until game starts
   - Notifications expire when game starts (no longer useful)
   - Requires `game_scheduled_at` denormalization

### Schema Enhancement

**Add `game_scheduled_at` to `notification_schedule` table** (~30 lines):
- Migration to add column with backfill
- Update model, service, event builder
- Eliminates JOIN overhead for TTL calculation
- Full replacement pattern makes consistency trivial

### Key Design Decisions

1. **Daemon DLQ processing over bot recovery**
   - Preserves separation of concerns
   - Works during bot downtime
   - Uses RabbitMQ's 24hr buffering window
   - User insight: "The daemons should run the DLQ as part of startup"
2. **Natural staleness control via defensive bot handler**
   - Notifications: Per-message TTL expires in primary queue (unconsumed)
   - Rejected messages may become stale while in DLQ
   - Daemon republishes everything (TTL resets - relative to publish time)
   - Bot handler checks `game.scheduled_at < now()` before processing
   - Status transitions: Never expire, always process

3. **Database remains source of truth**
   - Daemon polls for `executed=False`
   - DLQ processing is safety net
   - Both paths query same authoritative source

4. **RabbitMQ durability guarantees**
   - Durable queues + persistent delivery = no message loss in transit
   - TTL expiration sends to DLQ (not lost)
   - User clarification: Messages don't disappear, they move to DLQ

5. **Denormalization justified**
   - User insight: "We already have to modify the notification entry when game changes"
   - Full replacement pattern (delete all + recreate) maintains consistency
   - Zero additional complexity for updates
   - Negligible storage cost (160KB-400KB for 10K games)

### Implementation Order

**Recommended sequence**:

1. **Schema migration** (game_scheduled_at) - enables TTL calculation
2. **Per-message TTL** - depends on schema change
3. **Bot consumer fix** - prerequisite for DLQ processing
4. **Daemon DLQ processing** - depends on consumer fix
   - Must check message expiration and skip expired notifications

**Alternative: Let RabbitMQ discard expired messages**:
- Remove `x-dead-letter-exchange` from queue configuration
- Expired notifications discarded automatically (not sent to DLQ)
- Rejected messages (handler failures) still need DLQ
- Would require per-event-type queues or more sophisticated routing

**Total effort**: ~135 lines across 6 components (simpler DLQ logic + defensive bot handler)

### Success Criteria
- ✅ Messages only ACKed after successful handler execution
- ✅ Failed messages go to DLQ without instant retry loops
- ✅ DLQ accumulates all failures for daemon processing and monitoring
- ✅ DLQ accumulates repeatedly failed messages for monitoring
- ✅ Daemon republishes from DLQ on startup and periodically
- ✅ Notifications expire when game starts (no stale reminders)
- ✅ Status transitions eventually succeed (data consistency guaranteed)
- ✅ Bot remains purely event-driven consumer
- ✅ No new services/containers required
- ✅ Architectural purity preserved

### User Requirements Captured

- ✅ "Verify that the daemon does not update the database until the message has been successfully sent to rabbitmq" (confirmed correct: publish → mark → commit)
- ✅ "The daemons should run the DLQ as part of startup"
- ✅ "On at least some of those wakes it could also just resend the DLQ messages"
- ✅ "Game notification message should actually have a TTL that expires when the game starts"
- ✅ "Current sleep interval is 900 seconds - there is no reason to make it shorter" (verified, no change needed)
- ✅ "Can we expand the notification table schema to include scheduled_at instead of loading the game?" (yes, with full replacement pattern)
- ✅ "We already have to modify the notification entry when game changes, right?" (yes, confirmed update_schedule uses delete all + recreate)
