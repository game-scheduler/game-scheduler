<!-- markdownlint-disable-file -->

# Task Details: E2E Test Strategy - Discord Message Validation

## Research Reference

**Source Research**: #file:../research/20251222-e2e-test-strategy-research.md

## Phase 1: Discord Test Helper Module

### Task 1.1: Create DiscordTestHelper class structure

Create a new helper module for Discord API interactions in E2E tests.

- **Files**:
  - tests/e2e/helpers/__init__.py - Empty module initializer
  - tests/e2e/helpers/discord.py - DiscordTestHelper class implementation
- **Success**:
  - Class initializes with bot token parameter
  - Implements async context manager (__aenter__, __aexit__)
  - Has connect() and disconnect() methods
  - Tracks connection state to avoid duplicate logins
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 315-355) - Helper module pattern recommendation
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 470-550) - Discord message reading implementation example
- **Dependencies**:
  - discord.py library (already installed)
  - pytest-asyncio for async test support

### Task 1.2: Implement message fetching methods

Add methods to retrieve Discord messages from channels.

- **Files**:
  - tests/e2e/helpers/discord.py - Add get_message(), get_recent_messages(), find_message_by_embed_title()
- **Success**:
  - get_message(channel_id, message_id) returns discord.Message object
  - get_recent_messages(channel_id, limit) returns list of recent messages
  - find_message_by_embed_title(channel_id, title, limit) finds message by embed title
  - All methods handle channel and message fetching via discord.py client
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 470-550) - Message fetching implementation
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 115-142) - discord.py bot usage patterns
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 144-170) - Discord Message API reference
- **Dependencies**:
  - Task 1.1 completion (DiscordTestHelper class exists)

### Task 1.3: Implement DM verification methods

Add methods to retrieve and verify direct messages sent to users.

- **Files**:
  - tests/e2e/helpers/discord.py - Add get_user_recent_dms(), find_game_reminder_dm()
- **Success**:
  - get_user_recent_dms(user_id, limit) returns list of DMs sent to user by bot
  - find_game_reminder_dm(user_id, game_title) finds specific game reminder DM
  - Methods filter for bot's messages only (msg.author.id == bot user id)
  - Searches embed content for game title
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 470-550) - DM verification implementation
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 197-210) - DM verification capabilities
- **Dependencies**:
  - Task 1.1 completion (DiscordTestHelper class exists)

### Task 1.4: Implement embed verification utilities

Add helper methods to extract and verify Discord embed content.

- **Files**:
  - tests/e2e/helpers/discord.py - Add extract_embed_field_value(), verify_game_embed()
- **Success**:
  - extract_embed_field_value(embed, field_name) returns field value or None
  - verify_game_embed(embed, expected_title, expected_host_id, expected_max_players) validates embed structure
  - verify_game_embed checks: title, host field with mention, players field with count
  - Uses assertions for clear test failure messages
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 470-550) - Embed verification implementation
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 144-170) - Discord embed structure
- **Dependencies**:
  - Task 1.1 completion (DiscordTestHelper class exists)

## Phase 2: First E2E Test - Game Announcement

### Task 2.1: Create test environment fixtures

Create pytest fixtures for E2E test setup and teardown.

- **Files**:
  - tests/e2e/test_game_announcement.py - New test file with fixtures
- **Success**:
  - discord_helper fixture creates DiscordTestHelper, connects, yields, disconnects
  - test_guild_config fixture creates database guild configuration
  - test_channel_config fixture creates database channel configuration
  - test_host_user fixture creates database user record
  - Fixtures use environment variables from env/env.e2e (TEST_DISCORD_TOKEN, TEST_GUILD_ID, etc.)
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 357-407) - Fixture-based and helper module patterns
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 552-573) - Test execution considerations (environment requirements)
- **Dependencies**:
  - Phase 1 completion (DiscordTestHelper module exists)
  - env/env.e2e configured with Discord test credentials

### Task 2.2: Implement game creation announcement test

Write test that creates game via API and verifies Discord announcement.

- **Files**:
  - tests/e2e/test_game_announcement.py - Add test_game_creation_posts_announcement_to_discord()
- **Success**:
  - Test creates game via API POST /api/games
  - Waits for bot to process game.created event (asyncio.sleep with timeout)
  - Fetches game from database to get message_id
  - Uses discord_helper to fetch Discord message by message_id
  - Asserts message exists and has one embed
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 247-313) - Recommended first test structure
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 234-245) - Why this test first
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 552-596) - Test execution considerations (timing, isolation)
- **Dependencies**:
  - Task 2.1 completion (fixtures exist)
  - Running full stack via compose.e2e.yaml

### Task 2.3: Validate message content and embed structure

Extend game creation test to verify Discord message content details.

- **Files**:
  - tests/e2e/test_game_announcement.py - Enhance test_game_creation_posts_announcement_to_discord()
- **Success**:
  - Uses discord_helper.verify_game_embed() to check embed structure
  - Validates embed title matches game title
  - Verifies host field contains user mention (<@discord_id>)
  - Confirms players field shows correct count (0/max_players)
  - All assertions provide clear failure messages
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 247-313) - Test implementation example
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 315-324) - Success criteria for first test
- **Dependencies**:
  - Task 2.2 completion (basic test exists)
  - Task 1.4 completion (verify_game_embed implemented)

## Phase 3: Additional E2E Test Scenarios

### Task 3.1: Implement game update message refresh test

Test that updating game details causes Discord message to be edited.

- **Files**:
  - tests/e2e/test_game_announcement.py - Add test_game_update_refreshes_discord_message()
- **Success**:
  - Creates game via API, verifies initial announcement
  - Updates game title/description via API PATCH /api/games/{id}
  - Waits for bot to process game.updated event
  - Fetches same message_id from Discord
  - Verifies embed reflects updated content
  - Confirms message_id unchanged (edit, not new post)
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 222-232) - Priority E2E test scenarios (scenario 2)
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 172-192) - System architecture for message editing
- **Dependencies**:
  - Phase 2 completion (basic test pattern established)

### Task 3.2: Implement user join participant list test

Test that joining game updates participant list in Discord message.

- **Files**:
  - tests/e2e/test_game_announcement.py - Add test_user_join_updates_participant_list()
- **Success**:
  - Creates game, verifies initial announcement shows 0 players
  - Adds participant via API POST /api/games/{id}/participants
  - Waits for bot to process participant change
  - Fetches Discord message, verifies player count incremented (1/max)
  - Confirms participant appears in embed field
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 222-232) - Priority E2E test scenarios (scenario 3)
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 172-192) - System architecture for participant updates
- **Dependencies**:
  - Phase 2 completion (basic test pattern established)

### Task 3.3: Implement DM reminder delivery test

Test that notification daemon sends DM reminders to participants.

- **Files**:
  - tests/e2e/test_game_announcement.py - Add test_game_reminder_sends_dm_to_participants()
- **Success**:
  - Creates game with reminder_minutes=[5]
  - Sets scheduled_at to trigger reminder (current time + 6 minutes)
  - Adds test user as participant
  - Waits for notification daemon to process (polling interval + buffer)
  - Uses discord_helper.find_game_reminder_dm() to locate DM
  - Verifies DM embed contains game title and scheduled time
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 222-232) - Priority E2E test scenarios (scenario 4)
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 172-192) - System architecture for notification daemon
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 575-588) - Timing considerations for daemon polling
- **Dependencies**:
  - Phase 2 completion (basic test pattern established)
  - Task 1.3 completion (DM verification methods exist)

### Task 3.4: Implement game deletion message removal test

Test that deleting game removes Discord announcement message.

- **Files**:
  - tests/e2e/test_game_announcement.py - Add test_game_deletion_removes_discord_message()
- **Success**:
  - Creates game, verifies announcement exists
  - Deletes game via API DELETE /api/games/{id}
  - Waits for bot to process game.deleted event
  - Attempts to fetch Discord message by message_id
  - Verifies fetch raises NotFound exception (message deleted)
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 222-232) - Priority E2E test scenarios (scenario 5)
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 172-192) - System architecture for message deletion
- **Dependencies**:
  - Phase 2 completion (basic test pattern established)

## Phase 4: Documentation and CI/CD Integration

### Task 4.1: Update TESTING_E2E.md with new test execution instructions

Document how to run new E2E tests with Discord validation.

- **Files**:
  - TESTING_E2E.md - Add section "Discord Message Validation Tests"
- **Success**:
  - Explains difference between database-focused and Discord validation tests
  - Lists required environment variables (TEST_DISCORD_TOKEN, etc.)
  - Provides command to run new E2E tests
  - Documents expected test execution time and timing considerations
  - Includes troubleshooting section for common issues
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 552-573) - Test execution environment requirements
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 575-596) - Timing and isolation considerations
- **Dependencies**:
  - Phase 3 completion (all E2E tests implemented)

### Task 4.2: Document Discord test environment requirements

Create comprehensive guide for setting up Discord test environment.

- **Files**:
  - TESTING_E2E.md - Expand "Discord Test Environment Setup" section
- **Success**:
  - Documents how to create test Discord guild
  - Explains bot permissions required (VIEW_CHANNEL, SEND_MESSAGES, EMBED_LINKS, etc.)
  - Provides instructions for adding bot to test guild
  - Lists steps to get Discord user ID for test accounts
  - Includes env/env.e2e configuration example
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 39-47) - TESTING_E2E.md current content
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 552-573) - Environment requirements
- **Dependencies**:
  - Phase 3 completion (test requirements validated)

### Task 4.3: Configure CI/CD for E2E test execution

Determine strategy for running E2E tests in CI/CD pipeline.

- **Files**:
  - .github/workflows/e2e-tests.yml - New workflow or update existing test workflow
  - README.md - Document CI/CD E2E test strategy
- **Success**:
  - Documents that E2E tests require external Discord resources
  - Recommends manual execution or conditional CI runs
  - If CI execution desired: GitHub secrets configured for TEST_DISCORD_TOKEN, etc.
  - Workflow includes conditional execution based on env var (ENABLE_E2E_TESTS)
  - Alternative: Skip Discord E2E tests in CI, run manually before releases
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 598-606) - CI/CD considerations
- **Dependencies**:
  - Phase 3 completion (E2E tests validated manually)
  - Project maintainer decision on CI/CD E2E strategy

## Dependencies

- pytest-asyncio for async test support
- discord.py library (already installed)
- Test Discord guild, channel, bot token, and test user
- Running full stack via compose.e2e.yaml profile

## Success Criteria

- All E2E tests pass when run against test Discord environment
- DiscordTestHelper module provides reusable API for Discord operations
- Documentation clearly explains test setup and execution
- Pattern established for adding future E2E test scenarios
- CI/CD strategy documented even if automated execution deferred
