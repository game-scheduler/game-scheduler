<!-- markdownlint-disable-file -->

# Task Details: E2E Test Polling Pattern Refactoring

## Research Reference

**Source Research**: #file:../research/20251225-e2e-polling-patterns-research.md

## Phase 1: Core Polling Utilities

### Task 1.1: Add `wait_for_condition` generic polling function to discord.py

Add generic async polling utility as standalone function in tests/e2e/helpers/discord.py that can be used by all test helper methods.

- **Files**:
  - tests/e2e/helpers/discord.py - Add wait_for_condition function before DiscordTestHelper class
- **Success**:
  - Function accepts check_func callback returning (bool, T | None)
  - Function supports timeout, interval, description parameters
  - Function logs polling attempts and elapsed time
  - Function raises AssertionError with descriptive message on timeout
  - Function has complete type hints (TypeVar, Generic)
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 125-195) - Core polling utility implementation with logging
- **Dependencies**:
  - None (foundation for all other utilities)

### Task 1.2: Add `wait_for_message` method to DiscordTestHelper

Add method to poll for Discord message existence using channel.fetch_message().

- **Files**:
  - tests/e2e/helpers/discord.py - Add wait_for_message method to DiscordTestHelper class
- **Success**:
  - Method accepts channel_id, message_id, timeout, interval parameters
  - Method uses wait_for_condition internally
  - Method handles discord.NotFound and discord.HTTPException gracefully
  - Method returns discord.Message object on success
  - Method has complete docstring with example
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 199-235) - wait_for_message implementation
- **Dependencies**:
  - Task 1.1 completion (requires wait_for_condition)

### Task 1.3: Add `wait_for_message_update` method to DiscordTestHelper

Add method to poll for Discord message to match predicate function (for embed updates, content changes).

- **Files**:
  - tests/e2e/helpers/discord.py - Add wait_for_message_update method to DiscordTestHelper class
- **Success**:
  - Method accepts channel_id, message_id, check_func, timeout, interval, description parameters
  - Method polls message until check_func returns True
  - Method returns updated discord.Message object
  - Method handles message fetch errors gracefully
  - Docstring includes usage example for embed checking
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 237-278) - wait_for_message_update implementation
- **Dependencies**:
  - Task 1.1 completion (requires wait_for_condition)

### Task 1.4: Add `wait_for_dm_matching` method to DiscordTestHelper

Add method to poll user DM channel until message matching predicate found.

- **Files**:
  - tests/e2e/helpers/discord.py - Add wait_for_dm_matching method to DiscordTestHelper class
- **Success**:
  - Method accepts user_id, predicate, timeout, interval, description parameters
  - Method uses longer default timeout (150s) for daemon-triggered DMs
  - Method polls get_user_recent_dms with limit=15
  - Method returns matching discord.Message object
  - Docstring includes game reminder example
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 280-320) - wait_for_dm_matching implementation
- **Dependencies**:
  - Task 1.1 completion (requires wait_for_condition)
  - Existing get_user_recent_dms method in DiscordTestHelper

### Task 1.5: Add `wait_for_recent_dm` convenience method to DiscordTestHelper

Add convenience wrapper for common game-related DM types (reminder, join, removal, promotion).

- **Files**:
  - tests/e2e/helpers/discord.py - Add wait_for_recent_dm method to DiscordTestHelper class
- **Success**:
  - Method accepts user_id, game_title, dm_type, timeout, interval parameters
  - Method supports dm_type values: "reminder", "join", "removal", "promotion"
  - Method builds appropriate predicate based on dm_type
  - Method delegates to wait_for_dm_matching
  - Method raises ValueError for unknown dm_type
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 322-364) - wait_for_recent_dm implementation
- **Dependencies**:
  - Task 1.4 completion (uses wait_for_dm_matching)

### Task 1.6: Add `wait_for_db_condition` database polling utility

Add standalone async function for polling database queries until predicate satisfied.

- **Files**:
  - tests/e2e/conftest.py - Add wait_for_db_condition function (or create tests/e2e/helpers/database.py if preferred)
- **Success**:
  - Function accepts db_session, query, params, predicate, timeout, interval, description
  - Function executes SQLAlchemy text query with parameters
  - Function checks result with predicate function
  - Function returns query result when predicate satisfied
  - Docstring includes message_id population example
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 368-411) - wait_for_db_condition implementation
- **Dependencies**:
  - Task 1.1 completion (requires wait_for_condition pattern)
  - SQLAlchemy async session (already available in fixtures)

## Phase 2: High Priority Test Refactoring

### Task 2.1: Refactor test_player_removal.py (10s sleep → poll for removal DM)

Replace fixed 10-second sleep with polling for PLAYER_REMOVED DM at line 234.

- **Files**:
  - tests/e2e/test_player_removal.py - Replace asyncio.sleep(10) with wait_for_recent_dm call
- **Success**:
  - Fixed sleep removed
  - Uses main_bot_helper.wait_for_recent_dm with dm_type="removal"
  - Timeout set to 15 seconds (50% more than old fixed sleep)
  - Test still verifies DM content and game details
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 450-467) - Refactoring example for player removal
- **Dependencies**:
  - Task 1.5 completion (requires wait_for_recent_dm)

### Task 2.2: Refactor test_waitlist_promotion.py (6s sleep → poll for promotion DM)

Replace fixed 6-second sleep with polling for promotion DM at line 223.

- **Files**:
  - tests/e2e/test_waitlist_promotion.py - Replace asyncio.sleep(6) with wait_for_recent_dm call
- **Success**:
  - Fixed sleep removed
  - Uses wait_for_recent_dm with dm_type="promotion"
  - Timeout set to 10 seconds
  - Test still verifies promotion DM content
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 469-486) - Refactoring example for waitlist promotion
- **Dependencies**:
  - Task 1.5 completion (requires wait_for_recent_dm)

### Task 2.3: Refactor test_game_update.py (2 × 3s sleeps → poll for message updates)

Replace two fixed 3-second sleeps at lines 157 and 189 with message update polling.

- **Files**:
  - tests/e2e/test_game_update.py - Replace both asyncio.sleep(3) calls with wait_for_message_update
- **Success**:
  - Both fixed sleeps removed
  - First update polls for changed embed title
  - Second update polls for changed embed description
  - Timeout set to 10 seconds for each
  - Lambda predicates check specific embed fields
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 488-507) - Refactoring example for game updates
- **Dependencies**:
  - Task 1.3 completion (requires wait_for_message_update)

### Task 2.4: Refactor test_user_join.py (2 × 3s sleeps → poll for participant updates)

Replace two fixed 3-second sleeps at lines 217 and 250 with participant count polling.

- **Files**:
  - tests/e2e/test_user_join.py - Replace both asyncio.sleep(3) calls with wait_for_message_update
- **Success**:
  - Both fixed sleeps removed
  - First update polls for "1/4" participant count in embed field
  - Second update polls for participant count in second test
  - Timeout set to 10 seconds for each
  - Lambda predicates check embed field name/value
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 509-529) - Refactoring example for user join
- **Dependencies**:
  - Task 1.3 completion (requires wait_for_message_update)

### Task 2.5: Refactor test_game_cancellation.py (2s + 3s sleeps → poll for message updates)

Replace fixed sleeps at lines 157 (2s) and 173 (3s) with message existence and update polling.

- **Files**:
  - tests/e2e/test_game_cancellation.py - Replace both asyncio.sleep calls with polling
- **Success**:
  - Line 157: Use wait_for_message for initial message creation
  - Line 173: Use wait_for_message_update for cancellation status change
  - Appropriate timeouts for each operation
  - Lambda predicate checks for cancelled indicator in embed
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 531-532) - Listed in high priority refactoring
- **Dependencies**:
  - Task 1.2 completion (requires wait_for_message)
  - Task 1.3 completion (requires wait_for_message_update)

### Task 2.6: Refactor test_game_status_transitions.py (3s sleep → poll for message)

Replace fixed 3-second sleep at line 173 with message existence polling.

- **Files**:
  - tests/e2e/test_game_status_transitions.py - Replace asyncio.sleep(3) with wait_for_message
- **Success**:
  - Fixed sleep removed
  - Uses wait_for_message to verify initial message creation
  - Timeout set to 10 seconds
  - Test continues with existing status transition polling
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 533-533) - Listed in high priority refactoring
- **Dependencies**:
  - Task 1.2 completion (requires wait_for_message)

### Task 2.7: Refactor test_join_notification.py (2 × 2s sleeps → poll for message/schedule)

Replace two fixed 2-second sleeps at lines 185 and 331 with appropriate polling.

- **Files**:
  - tests/e2e/test_join_notification.py - Replace both asyncio.sleep(2) calls with polling
- **Success**:
  - Line 185: Use wait_for_message for initial game message
  - Line 331: Use wait_for_message for second test's game message
  - Timeout set to 10 seconds for each
  - Tests continue with existing notification schedule polling
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 534-534) - Listed in high priority refactoring
- **Dependencies**:
  - Task 1.2 completion (requires wait_for_message)

### Task 2.8: Refactor test_game_reminder.py (3s sleep → poll for message)

Replace fixed 3-second sleep at line 180 with message existence polling.

- **Files**:
  - tests/e2e/test_game_reminder.py - Replace asyncio.sleep(3) with wait_for_message
- **Success**:
  - Fixed sleep removed
  - Uses wait_for_message to verify game message creation
  - Timeout set to 10 seconds
  - Test continues with existing reminder polling
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 535-536) - Listed in high priority refactoring
- **Dependencies**:
  - Task 1.2 completion (requires wait_for_message)

## Phase 3: Medium Priority Test Consolidation

### Task 3.1: Consolidate test_game_announcement.py database polling

Replace custom polling loop at lines 160-171 with wait_for_db_condition utility.

- **Files**:
  - tests/e2e/test_game_announcement.py - Replace for loop with wait_for_db_condition call
- **Success**:
  - Custom polling loop removed
  - Uses wait_for_db_condition with query for message_id
  - Predicate checks row[0] is not None
  - Timeout and interval match original (5s total, 0.5s interval)
  - Result extraction simplified
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 540-541) - Listed for consolidation
- **Dependencies**:
  - Task 1.6 completion (requires wait_for_db_condition)

### Task 3.2: Consolidate test_game_reminder.py database and DM polling

Replace custom polling loops at lines 190-197 (database) and 205-235 (DM).

- **Files**:
  - tests/e2e/test_game_reminder.py - Replace both custom polling loops
- **Success**:
  - Database polling replaced with wait_for_db_condition
  - DM polling replaced with wait_for_recent_dm
  - Timeouts and intervals match original behavior
  - Custom logging removed (utility provides logging)
  - Test assertions unchanged
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 542-542) - Listed for consolidation
- **Dependencies**:
  - Task 1.5 completion (requires wait_for_recent_dm)
  - Task 1.6 completion (requires wait_for_db_condition)

### Task 3.3: Consolidate test_join_notification.py database and DM polling

Replace custom polling loops at lines 204-217 (database), 240-251 (DM), and 360-368 (DM).

- **Files**:
  - tests/e2e/test_join_notification.py - Replace all three custom polling loops
- **Success**:
  - Database polling replaced with wait_for_db_condition
  - Both DM polling loops replaced with wait_for_recent_dm
  - Timeouts and intervals preserved (15s, 120s, 150s)
  - Custom logging and print statements removed
  - Test logic unchanged
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 543-543) - Listed for consolidation
- **Dependencies**:
  - Task 1.5 completion (requires wait_for_recent_dm)
  - Task 1.6 completion (requires wait_for_db_condition)

### Task 3.4: Consolidate test_game_status_transitions.py status polling

Replace custom polling loops at lines 228-244 (IN_PROGRESS) and 283-295 (COMPLETED).

- **Files**:
  - tests/e2e/test_game_status_transitions.py - Replace both status polling loops
- **Success**:
  - IN_PROGRESS polling replaced with wait_for_message_update
  - COMPLETED polling replaced with wait_for_message_update
  - Lambda predicates check game status in embed
  - Timeouts preserved (150s for daemon operations)
  - Custom logging removed
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 544-544) - Listed for consolidation
- **Dependencies**:
  - Task 1.3 completion (requires wait_for_message_update)

## Phase 4: Configuration and Testing

### Task 4.1: Add e2e_timeouts fixture to conftest.py

Create pytest fixture providing standard timeout values for different operation types.

- **Files**:
  - tests/e2e/conftest.py - Add e2e_timeouts fixture
- **Success**:
  - Fixture returns dict with timeout values
  - Keys: message_create, message_update, dm_immediate, dm_scheduled, status_transition, db_write
  - Values match recommended timeouts from research
  - Fixture documented with docstring
  - Can be easily adjusted for CI environments
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 549-561) - Configuration section
- **Dependencies**:
  - None (configuration only)

### Task 4.2: Run full E2E test suite and verify improvements

Execute complete E2E test suite to validate refactoring.

- **Files**:
  - All tests/e2e/test_*.py files executed
- **Success**:
  - All E2E tests pass with 100% success rate
  - No test failures due to timeout issues
  - No test failures due to missing imports
  - All polling utilities work correctly
  - Tests complete faster than baseline
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 563-586) - Expected benefits section
- **Dependencies**:
  - All Phase 1, 2, and 3 tasks completed

### Task 4.3: Measure and document test execution time improvements

Collect metrics comparing before/after test execution times.

- **Files**:
  - Create .copilot-tracking/results/20251225-e2e-polling-patterns-metrics.md (or similar)
- **Success**:
  - Baseline execution time measured (before refactoring)
  - Post-refactoring execution time measured
  - Percentage improvement calculated
  - Per-test timing breakdown documented
  - Worst-case scenarios verified (timeouts still work)
- **Research References**:
  - #file:../research/20251225-e2e-polling-patterns-research.md (Lines 588-602) - Metrics section
- **Dependencies**:
  - Task 4.2 completion (requires working test suite)

## Dependencies

- pytest-asyncio (already installed)
- discord.py (already installed)
- SQLAlchemy async session support (already installed)

## Success Criteria

- All 21 sleep/polling patterns replaced with new utilities
- E2E test suite passes with 100% success rate
- Average test execution time reduced by 20-40%
- Zero fixed sleep calls remaining (except truly unavoidable waits)
- All polling uses consistent timeout/interval/logging patterns
- New utilities have proper type hints and docstrings
