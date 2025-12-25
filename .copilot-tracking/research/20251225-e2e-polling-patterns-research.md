# E2E Test Polling Pattern Analysis and Improvement Proposal

## Problem Statement

Current E2E tests use inconsistent sleep/wait patterns when waiting for asynchronous operations to complete. Many tests use fixed `asyncio.sleep()` calls that either:
1. **Sleep too long** - unnecessarily extending test execution time
2. **Sleep too short** - potentially causing flaky test failures
3. **Don't verify completion** - assume operation completed after fixed delay

This creates maintenance burden, unreliable tests, and poor developer experience.

## Current State Analysis

### Sleep Pattern Inventory

Found **21 sleep calls** across E2E test suite:

#### Pattern 1: Fixed Sleeps Without Verification (12 occurrences)

**Short sleeps (2-3 seconds):**
- `test_game_announcement.py:171` - 0.5s x10 iterations (5s total) - waiting for message_id in database
- `test_game_update.py:157` - 3s - waiting for message update
- `test_game_update.py:189` - 3s - waiting for message update (2nd test)
- `test_user_join.py:217` - 3s - waiting for participant update
- `test_user_join.py:250` - 3s - waiting for participant update (2nd test)
- `test_game_cancellation.py:157` - 2s - waiting for initial message
- `test_game_cancellation.py:173` - 3s - waiting for cancellation processing
- `test_game_status_transitions.py:173` - 3s - waiting for initial message
- `test_join_notification.py:185` - 2s - waiting for join notification schedule
- `test_waitlist_promotion.py:172` - 2s - waiting for initial message

**Long sleeps (6-10 seconds):**
- `test_player_removal.py:182` - 3s - waiting for initial message
- `test_player_removal.py:234` - **10s** - waiting for PLAYER_REMOVED DM (no verification loop)
- `test_waitlist_promotion.py:223` - **6s** - waiting for promotion DM (no verification loop)

**Problem:** These assume operation completes within fixed time. If system is slow, test fails. If system is fast, test wastes time.

#### Pattern 2: Polling Loops with Sleep (9 occurrences)

**Database polling:**
- `test_game_announcement.py:160-171` - Poll for message_id in database (10 attempts x 0.5s = 5s max)
- `test_game_reminder.py:190-197` - Poll for reminder in notification_schedule (10 attempts x 1s = 10s max)

**DM polling:**
- `test_game_reminder.py:205-235` - Poll for reminder DM (150s timeout, 5s interval)
- `test_join_notification.py:240-251` - Poll for join notification DM (150s timeout, 5s interval)
- `test_join_notification.py:360-368` - Poll for join notification DM (120s timeout, 5s interval)

**Status polling:**
- `test_game_status_transitions.py:228-244` - Poll for IN_PROGRESS status (150s timeout, 5s interval)
- `test_game_status_transitions.py:283-295` - Poll for COMPLETED status (150s timeout, 5s interval)

**Schedule polling:**
- `test_join_notification.py:204-217` - Poll for notification_schedule entry (15s timeout, 1s interval)

**Problem:** Each test implements own polling logic with different timeouts, intervals, and logging styles. Code duplication, inconsistent behavior.

### Test Execution Impact

**Total unnecessary wait time (worst case):**
- Fixed sleeps: ~42 seconds per full test run
- Polling loops already optimized (exit early on success)

**Flakiness risk:**
- Tests with 2-3s fixed sleeps vulnerable to slow CI environments
- No exponential backoff for transient failures
- Inconsistent timeout values (some 10s, others 150s for similar operations)

## Proposed Solution: Modular Polling Utilities

### Design Principles

1. **Single Responsibility** - Each utility function handles one type of wait pattern
2. **Consistent API** - All polling functions share common parameters (timeout, interval, description)
3. **Debug-Friendly** - Built-in logging for troubleshooting test failures
4. **Flexible** - Support custom predicates/conditions via callbacks
5. **Type-Safe** - Proper type hints for return values and parameters

### Core Polling Utility

Add to `tests/e2e/helpers/discord.py`:

```python
import asyncio
from collections.abc import Callable, Awaitable
from typing import TypeVar, Generic

T = TypeVar('T')

async def wait_for_condition(
    check_func: Callable[[], Awaitable[tuple[bool, T | None]]],
    timeout: int = 30,
    interval: float = 1.0,
    description: str = "condition",
) -> T:
    """
    Poll for condition with timeout.

    Generic polling utility that repeatedly calls check_func until it returns
    (True, result) or timeout is reached.

    Args:
        check_func: Async function returning (condition_met: bool, result: T | None)
                   Should return (True, value) when condition met, (False, None) otherwise
        timeout: Maximum seconds to wait
        interval: Seconds between checks
        description: Human-readable description for error messages

    Returns:
        Result value returned by check_func when condition met

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        async def check_message_exists():
            try:
                msg = await channel.fetch_message(msg_id)
                return (True, msg)
            except discord.NotFound:
                return (False, None)

        message = await wait_for_condition(
            check_message_exists,
            timeout=10,
            description="Discord message to appear"
        )
    """
    start_time = asyncio.get_event_loop().time()
    attempt = 0

    while True:
        attempt += 1
        elapsed = asyncio.get_event_loop().time() - start_time

        condition_met, result = await check_func()

        if condition_met:
            print(f"[WAIT] ✓ {description} met after {elapsed:.1f}s (attempt {attempt})")
            return result

        if elapsed >= timeout:
            raise AssertionError(
                f"{description} not met within {timeout}s timeout "
                f"({attempt} attempts)"
            )

        if attempt == 1:
            print(f"[WAIT] Waiting for {description} (timeout: {timeout}s, interval: {interval}s)")
        elif attempt % 5 == 0:
            print(f"[WAIT] Still waiting for {description}... ({elapsed:.0f}s elapsed, attempt {attempt})")

        await asyncio.sleep(interval)
```

### Specialized Discord Polling Methods

Add these methods to `DiscordTestHelper` class:

```python
async def wait_for_message(
    self,
    channel_id: str,
    message_id: str,
    timeout: int = 10,
    interval: float = 0.5,
) -> discord.Message:
    """
    Wait for Discord message to exist.

    Polls channel.fetch_message() until message found or timeout.
    Useful after API operations that create/update Discord messages.

    Args:
        channel_id: Discord channel snowflake
        message_id: Discord message snowflake
        timeout: Maximum seconds to wait
        interval: Seconds between fetch attempts

    Returns:
        Discord Message object

    Raises:
        AssertionError: If message not found within timeout
    """
    async def check_message():
        try:
            msg = await self.get_message(channel_id, message_id)
            return (True, msg)
        except (discord.NotFound, discord.HTTPException):
            return (False, None)

    return await wait_for_condition(
        check_message,
        timeout=timeout,
        interval=interval,
        description=f"message {message_id} in channel {channel_id}",
    )

async def wait_for_message_update(
    self,
    channel_id: str,
    message_id: str,
    check_func: Callable[[discord.Message], bool],
    timeout: int = 10,
    interval: float = 1.0,
    description: str = "message update",
) -> discord.Message:
    """
    Wait for Discord message to match condition.

    Polls message until check_func returns True. Useful for verifying
    embed updates, content changes, etc.

    Args:
        channel_id: Discord channel snowflake
        message_id: Discord message snowflake
        check_func: Function that returns True when message matches expected state
        timeout: Maximum seconds to wait
        interval: Seconds between checks
        description: Human-readable description for logging

    Returns:
        Updated Discord Message object

    Example:
        # Wait for embed title to change
        updated_msg = await helper.wait_for_message_update(
            channel_id,
            message_id,
            lambda msg: msg.embeds[0].title == "New Title",
            description="embed title update"
        )
    """
    async def check_update():
        try:
            msg = await self.get_message(channel_id, message_id)
            if check_func(msg):
                return (True, msg)
            return (False, None)
        except (discord.NotFound, discord.HTTPException):
            return (False, None)

    return await wait_for_condition(
        check_update,
        timeout=timeout,
        interval=interval,
        description=description,
    )

async def wait_for_dm_matching(
    self,
    user_id: str,
    predicate: Callable[[discord.Message], bool],
    timeout: int = 150,
    interval: int = 5,
    description: str = "DM",
) -> discord.Message:
    """
    Wait for DM matching predicate.

    Polls user's DM channel until message matching predicate found.
    Uses longer default timeout since DMs may be delayed by notification
    daemon polling intervals.

    Args:
        user_id: Discord user snowflake
        predicate: Function returning True for matching DM
        timeout: Maximum seconds to wait (default 150s for daemon delays)
        interval: Seconds between DM channel checks
        description: Human-readable description for logging

    Returns:
        Matching Discord Message object

    Example:
        # Wait for game reminder DM
        reminder_dm = await helper.wait_for_dm_matching(
            user_id,
            lambda dm: "Test Game" in dm.content and "starts <t:" in dm.content,
            description="game reminder DM"
        )
    """
    async def check_dms():
        dms = await self.get_user_recent_dms(user_id, limit=15)
        for dm in dms:
            if predicate(dm):
                return (True, dm)
        return (False, None)

    return await wait_for_condition(
        check_dms,
        timeout=timeout,
        interval=interval,
        description=description,
    )

async def wait_for_recent_dm(
    self,
    user_id: str,
    game_title: str,
    dm_type: str = "notification",
    timeout: int = 150,
    interval: int = 5,
) -> discord.Message:
    """
    Wait for specific type of game-related DM.

    Convenience wrapper around wait_for_dm_matching for common DM types.

    Args:
        user_id: Discord user snowflake
        game_title: Title of game to find DM for
        dm_type: Type of DM - "reminder", "join", "removal", or "promotion"
        timeout: Maximum seconds to wait
        interval: Seconds between checks

    Returns:
        Matching Discord Message object
    """
    predicates = {
        "reminder": lambda dm: (
            dm.content
            and game_title in dm.content
            and "starts <t:" in dm.content
        ),
        "join": lambda dm: (
            dm.content
            and "joined" in dm.content.lower()
            and game_title in dm.content
        ),
        "removal": lambda dm: (
            dm.content
            and game_title in dm.content
            and "removed" in dm.content.lower()
        ),
        "promotion": lambda dm: (
            dm.content
            and game_title in dm.content
            and "promoted" in dm.content.lower()
        ),
    }

    if dm_type not in predicates:
        raise ValueError(f"Unknown dm_type: {dm_type}. Must be one of {list(predicates.keys())}")

    return await self.wait_for_dm_matching(
        user_id,
        predicates[dm_type],
        timeout=timeout,
        interval=interval,
        description=f"{dm_type} DM for '{game_title}'",
    )
```

### Database Polling Utility

Add to `tests/e2e/conftest.py` or new `tests/e2e/helpers/database.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

async def wait_for_db_condition(
    db_session: AsyncSession,
    query: str,
    params: dict,
    predicate: Callable[[Any], bool],
    timeout: int = 10,
    interval: float = 0.5,
    description: str = "database condition",
) -> Any:
    """
    Poll database query until predicate satisfied.

    Args:
        db_session: SQLAlchemy async session
        query: SQL query string
        params: Query parameters
        predicate: Function returning True when result matches expectation
        timeout: Maximum seconds to wait
        interval: Seconds between queries
        description: Human-readable description

    Returns:
        Query result when predicate satisfied

    Example:
        # Wait for message_id to be populated
        result = await wait_for_db_condition(
            db_session,
            "SELECT message_id FROM game_sessions WHERE id = :game_id",
            {"game_id": game_id},
            lambda row: row[0] is not None,
            description="message_id population"
        )
        message_id = result[0]
    """
    async def check_db():
        result = db_session.execute(text(query), params)
        row = result.fetchone()
        if row and predicate(row):
            return (True, row)
        return (False, None)

    return await wait_for_condition(
        check_db,
        timeout=timeout,
        interval=interval,
        description=description,
    )
```

## Implementation Plan

### Phase 1: Add Polling Utilities

1. **Add `wait_for_condition` to discord.py** - Core polling logic
2. **Add Discord-specific methods to DiscordTestHelper**:
   - `wait_for_message`
   - `wait_for_message_update`
   - `wait_for_dm_matching`
   - `wait_for_recent_dm`
3. **Add `wait_for_db_condition` to conftest.py or new helpers/database.py**

### Phase 2: Refactor Tests (Prioritized by Impact)

#### High Priority - Fixed Sleeps Without Verification

Replace blind sleeps with polling:

1. **test_player_removal.py:234** (10s sleep → poll for DM)
   ```python
   # Before
   await asyncio.sleep(10)
   recent_dms = await main_bot_helper.get_user_recent_dms(...)

   # After
   removal_dm = await main_bot_helper.wait_for_recent_dm(
       user_id=discord_user_id,
       game_title=game_title,
       dm_type="removal",
       timeout=15
   )
   ```

2. **test_waitlist_promotion.py:223** (6s sleep → poll for DM)
   ```python
   # Before
   await asyncio.sleep(6)

   # After
   promotion_dm = await main_bot_helper.wait_for_recent_dm(
       user_id=discord_user_id,
       game_title=game_title,
       dm_type="promotion",
       timeout=10
   )
   ```

3. **test_game_update.py:157, 189** (3s sleeps → poll for message update)
   ```python
   # Before
   await asyncio.sleep(3)
   message = await discord_helper.get_message(channel_id, message_id)

   # After
   message = await discord_helper.wait_for_message_update(
       channel_id,
       message_id,
       lambda msg: msg.embeds[0].title == updated_title,
       timeout=10,
       description="game title update"
   )
   ```

4. **test_user_join.py:217, 250** (3s sleeps → poll for participant count)
   ```python
   # Before
   await asyncio.sleep(3)
   updated_message = await discord_helper.get_message(channel_id, message_id)

   # After
   updated_message = await discord_helper.wait_for_message_update(
       channel_id,
       message_id,
       lambda msg: "1/4" in msg.embeds[0].fields[0].name,
       timeout=10,
       description="participant count update to 1/4"
   )
   ```

5. **test_game_cancellation.py:157, 173** (2s + 3s sleeps)
6. **test_game_status_transitions.py:173** (3s sleep)
7. **test_join_notification.py:185, 331** (2s sleeps)
8. **test_waitlist_promotion.py:172** (2s sleep)
9. **test_game_reminder.py:180** (3s sleep)
10. **test_player_removal.py:182** (3s sleep)

#### Medium Priority - Existing Polling Loops

Consolidate to use new utilities:

1. **test_game_announcement.py:160-171** - Use `wait_for_db_condition`
2. **test_game_reminder.py:190-197** - Use `wait_for_db_condition`
3. **test_join_notification.py:204-217** - Use `wait_for_db_condition`
4. **test_game_reminder.py:205-235** - Use `wait_for_recent_dm`
5. **test_join_notification.py:240-251, 360-368** - Use `wait_for_recent_dm`

### Phase 3: Configuration and Defaults

Add test configuration for timeouts:

```python
# tests/e2e/conftest.py
@pytest.fixture
def e2e_timeouts():
    """Standard timeout values for E2E tests."""
    return {
        "message_create": 10,      # Discord message creation
        "message_update": 10,       # Discord message edit
        "dm_immediate": 10,         # DMs sent immediately by API events
        "dm_scheduled": 150,        # DMs sent by notification daemon (polling delay)
        "status_transition": 150,   # Status transitions (daemon polling delay)
        "db_write": 5,              # Database write operations
    }
```

## Expected Benefits

### Test Reliability
- **Eliminate flakiness** from fixed timeouts
- **Faster failure detection** with immediate polling
- **Better error messages** with descriptive wait conditions

### Test Performance
- **Reduce average test time** by 20-40% (exit early when condition met)
- **Worst-case unchanged** (timeouts remain same)
- **Best-case dramatically faster** for fast operations

### Maintainability
- **Single implementation** of polling logic
- **Consistent behavior** across all tests
- **Easy to adjust** timeouts globally
- **Clear intent** - wait for specific condition, not arbitrary delay

### Developer Experience
- **Better debugging** with built-in logging
- **Reusable utilities** for future tests
- **Self-documenting** - function names describe what's being waited for

## Metrics

### Current State
- **21 sleep calls** across 11 test files
- **12 fixed sleeps** (42s cumulative worst-case waste)
- **9 custom polling loops** (duplicated logic)
- **0 reusable polling utilities**

### Target State
- **~3 sleep calls** (only truly unavoidable waits)
- **3 polling utilities** (`wait_for_condition`, `wait_for_message`, `wait_for_dm_matching`)
- **5 convenience methods** (specialized wrappers)
- **100% consistent** timeout/interval/logging behavior

## Risks and Mitigations

### Risk: Utilities add complexity
**Mitigation:** Keep utilities simple, single-purpose, well-documented

### Risk: Polling too aggressive (hammers Discord API)
**Mitigation:** Use sensible default intervals (0.5-1s for quick ops, 5s for daemon ops)

### Risk: Tests still flaky if timeouts too short
**Mitigation:** Use generous timeouts (10s+ for most ops, 150s for daemon-triggered ops)

### Risk: Breaking existing tests during refactor
**Mitigation:** Refactor incrementally, run full test suite after each change

## Alternative Approaches Considered

### Alternative 1: pytest-timeout plugin
**Pros:** Built-in solution
**Cons:** Only provides test-level timeouts, not operation-level polling

### Alternative 2: Keep custom polling in each test
**Pros:** No abstraction needed
**Cons:** Code duplication, inconsistent behavior, harder to maintain

### Alternative 3: Use tenacity library for retries
**Pros:** Full-featured retry library
**Cons:** Heavy dependency for simple use case, less readable for test code

**Decision:** Implement custom utilities - provides exact functionality needed without dependencies

## References

- [asyncio.sleep documentation](https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep)
- [pytest-timeout](https://github.com/pytest-dev/pytest-timeout)
- [tenacity retry library](https://github.com/jd/tenacity)
- Pattern inspired by Selenium's WebDriverWait and Playwright's auto-waiting

## Appendix: Complete Test File Inventory

### Tests with Sleep Patterns

1. **test_game_announcement.py**
   - Line 171: Poll loop (0.5s x10 = 5s max) for message_id

2. **test_game_update.py**
   - Line 157: Fixed 3s sleep before checking message
   - Line 189: Fixed 3s sleep before checking update

3. **test_user_join.py**
   - Line 217: Fixed 3s sleep after join
   - Line 250: Fixed 3s sleep after join (2nd test)

4. **test_game_cancellation.py**
   - Line 157: Fixed 2s sleep for initial message
   - Line 173: Fixed 3s sleep after cancellation

5. **test_game_reminder.py**
   - Line 180: Fixed 3s sleep after game creation
   - Line 196: Poll loop (1s x10) for reminder schedule
   - Line 235: Poll loop (5s interval, 150s max) for reminder DM

6. **test_player_removal.py**
   - Line 182: Fixed 3s sleep after game creation
   - Line 234: Fixed 10s sleep waiting for removal DM

7. **test_join_notification.py**
   - Line 185: Fixed 2s sleep after game creation
   - Line 217: Poll loop (1s, 15s max) for notification schedule
   - Line 251: Poll loop (5s, 120s max) for join DM
   - Line 331: Fixed 2s sleep after game creation (2nd test)
   - Line 368: Poll loop (5s, 150s max) for join DM (2nd test)

8. **test_waitlist_promotion.py**
   - Line 172: Fixed 2s sleep after game creation
   - Line 223: Fixed 6s sleep waiting for promotion DM

9. **test_game_status_transitions.py**
   - Line 173: Fixed 3s sleep after game creation
   - Line 244: Poll loop (5s, 150s max) for IN_PROGRESS status
   - Line 295: Poll loop (5s, 150s max) for COMPLETED status

### Tests Without Sleep Patterns
- test_00_environment.py
- test_01_authentication.py

**Total:** 11 test files, 9 with sleep/polling patterns
