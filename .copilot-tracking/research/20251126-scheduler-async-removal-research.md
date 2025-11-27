<!-- markdownlint-disable-file -->
# Task Research Notes: Remove Async Operations from Scheduler Service

## Research Executed

### File Analysis
- `services/scheduler/tasks/check_notifications.py`
  - Celery task wraps async function with `asyncio.run_until_complete()`
  - Uses AsyncSession for database queries
  - Uses async RabbitMQ publisher (aio_pika) for Celery task scheduling
  - Sequential operations in loops (no concurrent I/O)
  
- `services/scheduler/tasks/update_game_status.py`
  - Celery task wraps async function with event loop management
  - Uses AsyncSession for database queries
  - Uses async EventPublisher for RabbitMQ messaging
  - Sequential status updates (no parallelism)
  
- `services/scheduler/tasks/send_notification.py`
  - Celery task wraps async function with event loop management
  - Uses AsyncSession for single database lookups
  - Uses async NotificationService for RabbitMQ publishing
  - Simple sequential flow with retry logic

- `services/scheduler/services/notification_service.py`
  - Async send_game_reminder() method
  - Creates/connects/closes EventPublisher for each call
  - Single RabbitMQ publish operation per invocation

- `shared/database.py`
  - Uses SQLAlchemy AsyncEngine with asyncpg driver
  - Provides AsyncSession via async_sessionmaker
  - Two patterns: FastAPI dependency injection and context manager

- `shared/messaging/publisher.py`
  - Uses aio_pika for async RabbitMQ operations
  - Async connect/publish methods
  - Manages connection lifecycle

### Code Search Results
- Async patterns in scheduler:
  - 3 Celery task entry points: all use event loop wrapper pattern
  - ~15 async helper functions: database queries, RabbitMQ publishing
  - Event loop management boilerplate repeated in each task entry point

### Anti-Pattern Identified
```python
# Current pattern in ALL scheduler tasks
@app.task
def task_name():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_task_name_async())
```

This pattern:
- Blocks the worker on async operations (no concurrency benefit)
- Adds event loop lifecycle complexity
- Creates defect opportunities (loop state, context management)
- Provides zero performance benefit in sequential code

### Project Conventions
- Standards referenced: Python best practices, Celery task patterns
- Current async usage is library-driven (SQLAlchemy, aio_pika) not architecture-driven
- No concurrent I/O operations anywhere in scheduler code

## Key Discoveries

### Current Async Usage Analysis

**Database Operations (AsyncSession)**
- All queries are sequential (await one, then await next)
- No use of `asyncio.gather()` or concurrent queries
- Example pattern:
  ```python
  games = await _get_upcoming_games(db, start, end)
  for game in games:
      notifications = await _schedule_game_notifications(db, game)
      await db.commit()
  ```
- Blocking on each operation eliminates async benefits

**RabbitMQ Operations (aio_pika)**
- Single publish per operation
- Connection/channel created, used once, closed
- Example pattern:
  ```python
  await event_publisher.connect()
  await event_publisher.publish(event)
  await event_publisher.close()
  ```
- No concurrent publishing, no connection pooling benefits

**Celery Concurrency Model**
- Worker-level concurrency (multiple worker processes)
- Task-level execution is single-threaded per worker
- No benefit from async within a task unless doing concurrent I/O
- Current code does sequential I/O, defeating async purpose

### Value Assessment

**What Async Currently Provides:**
1. ❌ **No concurrency** - All operations are sequential
2. ❌ **No performance gain** - Blocking on each operation
3. ✅ **Library compatibility** - Required by asyncpg and aio_pika
4. ❌ **No I/O multiplexing** - Not using gather/create_task

**What Async Currently Costs:**
1. ❌ **Complexity overhead** - Event loop management in every task
2. ❌ **Defect surface** - More ways for things to go wrong
3. ❌ **Cognitive load** - Async/await everywhere for sequential code
4. ❌ **Debugging difficulty** - Stack traces through event loops
5. ❌ **Maintenance burden** - Understanding async patterns for simple sequential code

### Synchronous Alternatives Available

**Database: PostgreSQL + psycopg2**
- Drop-in replacement for asyncpg
- Simpler connection management
- Same connection pooling capabilities
- Example:
  ```python
  # Current async
  async with database.get_db_session() as db:
      result = await db.execute(select(Game))
      games = result.scalars().all()
  
  # Synchronous equivalent
  with database.get_db_session() as db:
      result = db.execute(select(Game))
      games = result.scalars().all()
  ```

**Messaging: RabbitMQ + pika**
- Synchronous RabbitMQ client
- Simpler connection lifecycle
- Blocking publish (fine for sequential tasks)
- Example:
  ```python
  # Current async
  publisher = EventPublisher()
  await publisher.connect()
  await publisher.publish(event)
  await publisher.close()
  
  # Synchronous equivalent
  publisher = EventPublisher()
  publisher.connect()
  publisher.publish(event)
  publisher.close()
  ```

**Celery Task Pattern**
- Remove event loop boilerplate entirely
- Direct task implementation without wrapper
- Example:
  ```python
  # Current pattern
  @app.task
  def check_notifications():
      loop = asyncio.new_event_loop()
      return loop.run_until_complete(_check_async())
  
  async def _check_async():
      async with get_db_session() as db:
          # ... async operations
  
  # Synchronous pattern
  @app.task
  def check_notifications():
      with get_db_session() as db:
          # ... sync operations
  ```

### Impact on Other Services

**Services NOT Affected:**
- `services/api/` - FastAPI is async-native, benefits from async for HTTP concurrency
- `services/bot/` - Discord.py is async-native, required for Discord API
- Both services handle concurrent connections/requests where async provides real value

**Only Scheduler Service Affected:**
- Celery tasks are inherently synchronous execution contexts
- No concurrent connections to handle
- No I/O multiplexing being performed
- Async is pure overhead without benefit

## Recommended Approach

**Complete removal of async from scheduler service** with synchronous replacements.

### Migration Strategy

**Phase 1: Replace Database Layer**
1. Update `shared/database.py` to provide synchronous SQLAlchemy sessions
2. Replace `create_async_engine()` with `create_engine()`
3. Replace `AsyncSession` with `Session`
4. Keep both patterns temporarily during migration (add sync alongside async)

**Phase 2: Replace Messaging Layer**
1. Create synchronous EventPublisher using `pika` library
2. Update `shared/messaging/publisher.py` with sync implementation
3. Update `shared/messaging/consumer.py` if needed (check bot/api usage first)
4. Maintain separate sync/async publishers if other services need async

**Phase 3: Update Scheduler Tasks**
1. Remove event loop management boilerplate from all task entry points
2. Convert async functions to synchronous equivalents
3. Replace `await` with direct calls
4. Replace `async with` with regular `with` context managers
5. Remove all `asyncio` imports

**Phase 4: Update Notification Service**
1. Convert `NotificationService.send_game_reminder()` to sync
2. Use synchronous EventPublisher
3. Simplify connection management

**Phase 5: Testing & Validation**
1. Run full test suite to ensure functionality unchanged
2. Monitor task execution times (should be same or slightly faster)
3. Verify no event loop errors in logs
4. Confirm retry logic still works correctly

### Dependencies to Change

**Remove:**
- `asyncpg` (PostgreSQL async driver)
- `aio_pika` (RabbitMQ async client) - for scheduler only
- `asyncio` usage in scheduler service

**Add:**
- `psycopg2-binary` (PostgreSQL sync driver)
- `pika` (RabbitMQ sync client) - likely already present

**Check Existing:**
- Verify `pika` is already in dependencies (probably used elsewhere)
- Verify `psycopg2` isn't already present (migrate if so)

## Implementation Guidance

### Objectives
- Eliminate async overhead from scheduler service where it provides no benefit
- Reduce defect surface by removing event loop management complexity
- Simplify code maintenance with straightforward synchronous patterns
- Maintain identical functionality and performance characteristics

### Key Tasks
1. Add synchronous database session factory to `shared/database.py`
2. Create synchronous EventPublisher in `shared/messaging/` (or separate module)
3. Convert all scheduler task functions from async to sync
4. Remove event loop wrapper pattern from all Celery task decorators
5. Update imports and type hints throughout scheduler service
6. Update notification service to use sync operations
7. Run integration tests to verify behavior unchanged

### Dependencies
- Add `psycopg2-binary` to pyproject.toml
- Confirm `pika` is available (likely already present)
- Keep `asyncpg` and `aio_pika` for API and Bot services

### Success Criteria
- ✅ No `async`/`await` keywords in `services/scheduler/` directory
- ✅ No `asyncio` imports in scheduler code
- ✅ All scheduler tests pass
- ✅ Task execution completes successfully in production
- ✅ No event loop errors in logs
- ✅ Task execution time unchanged (or improved)
- ✅ Code complexity reduced (fewer lines, simpler patterns)

### Migration Checklist

**Database Layer:**
- [ ] Add `create_engine()` and synchronous session factory to `shared/database.py`
- [ ] Create `get_sync_db_session()` function for scheduler use
- [ ] Keep async versions for API/Bot services

**Messaging Layer:**
- [ ] Implement synchronous EventPublisher using `pika`
- [ ] Update or create `shared/messaging/sync_publisher.py`
- [ ] Ensure routing keys and exchange configuration match async version

**Task Files:**
- [ ] `tasks/check_notifications.py` - Remove async, update to sync
- [ ] `tasks/update_game_status.py` - Remove async, update to sync  
- [ ] `tasks/send_notification.py` - Remove async, update to sync
- [ ] `services/notification_service.py` - Convert to sync

**Helper Functions:**
- [ ] All database query helpers: remove `async def`, remove `await`
- [ ] All event publishing helpers: remove `async def`, remove `await`
- [ ] Update type hints: `Session` instead of `AsyncSession`

**Testing:**
- [ ] Run `pytest tests/services/scheduler/` - verify all pass
- [ ] Run integration tests if available
- [ ] Manual testing: verify notifications sent, statuses updated
- [ ] Log inspection: no event loop warnings/errors

### Code Example: Before/After

**Before (Async):**
```python
@app.task
def check_upcoming_notifications():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_check_upcoming_notifications_async())

async def _check_upcoming_notifications_async():
    async with database.get_db_session() as db:
        upcoming_games = await _get_upcoming_games(db, start, end)
        for game_session in upcoming_games:
            notifications_sent = await _schedule_game_notifications(db, game_session)
            await db.commit()
    return {"games_checked": len(upcoming_games)}

async def _get_upcoming_games(db: AsyncSession, start, end):
    stmt = select(GameSession).where(...)
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

**After (Sync):**
```python
@app.task
def check_upcoming_notifications():
    with database.get_sync_db_session() as db:
        upcoming_games = _get_upcoming_games(db, start, end)
        for game_session in upcoming_games:
            notifications_sent = _schedule_game_notifications(db, game_session)
            db.commit()
    return {"games_checked": len(upcoming_games)}

def _get_upcoming_games(db: Session, start, end):
    stmt = select(GameSession).where(...)
    result = db.execute(stmt)
    return list(result.scalars().all())
```

**Key Changes:**
- ✅ Removed 7 lines of event loop boilerplate
- ✅ Removed `async`/`await` keywords (4 locations)
- ✅ Removed try/except RuntimeError complexity
- ✅ Identical functionality, simpler code
- ✅ Same execution pattern, less overhead

### Risk Assessment

**Low Risk:**
- Functionality remains identical (sequential operations stay sequential)
- No performance degradation (already blocking on operations)
- Reduced defect surface (fewer failure modes)
- Clear rollback path (revert commits)

**Testing Strategy:**
- Unit tests verify task logic unchanged
- Integration tests verify end-to-end flows work
- Monitoring verifies production behavior matches expected

**Rollback Plan:**
- Git revert to previous async implementation
- No database migrations required
- No data model changes
