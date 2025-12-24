---
applyTo: ".copilot-tracking/changes/20251222-e2e-test-strategy-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: E2E Test Strategy - Discord Message Validation

## Overview

Implement true end-to-end testing that validates Discord bot behavior and message content, addressing the gap in current database-focused tests. **Prerequisite refactoring (Discord client token unification) is now COMPLETE and this work can proceed.**

## Objectives

- Verify game announcements appear in Discord channels with correct content
- Validate Discord message embeds, fields, and user mentions
- Test DM reminder delivery to participants
- Establish reusable patterns for Discord message validation
- Create helper utilities for Discord API interactions

## Status

**REFACTORING PREREQUISITE: ✅ COMPLETE**
- Discord client token unification refactored and committed (commit: 0d70d93)
- Automatic token type detection now available in `DiscordAPIClient._get_auth_header()`
- Unified `get_guilds()` method works with both bot and OAuth tokens
- All 791 unit tests passing, code quality verified
- **E2E work can now proceed without blocking issues**

## Research Summary

### Project Files

- tests/e2e/test_game_notification_api_flow.py - Database-focused tests without Discord validation
- tests/e2e/test_guild_template_api.py - Integration tests with mocked Discord responses
- services/bot/events/handlers.py - Discord event handlers and message posting logic
- services/bot/formatters/game_message.py - Game announcement embed formatting
- TESTING_E2E.md - E2E test environment documentation
- shared/discord/client.py - Unified Discord client with automatic token type detection (**REFACTORED**)

### External References

- #file:../research/20251222-e2e-test-strategy-research.md - Comprehensive E2E strategy analysis (updated with microservice communication path analysis)
- #file:../research/20251224-microservice-communication-architecture.md - Mermaid diagrams showing all service communication paths and test coverage gaps
- #file:../research/20251222-discord-client-token-unification-research.md - Token unification refactor details
- #fetch:https://discord.com/developers/docs/resources/message - Discord Message API documentation
- discord.py library - Message reading capabilities (fetch_message, embeds, content)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Testing standards

## Implementation Checklist

### [x] Phase 1: E2E Infrastructure Setup

- [x] Task 1.1: Create DiscordTestHelper module
  - Create tests/e2e/helpers/discord.py with DiscordTestHelper class
  - Implement connect/disconnect lifecycle for discord.py bot client
  - Implement get_channel_message(channel_id, message_id) method
  - Implement get_user_recent_dms(user_id, limit=10) method
  - Implement verify_game_announcement(message, game_title, host_id) validation method
  - Add proper error handling and logging
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 11-25)

- [x] Task 1.2: Set up E2E fixtures in conftest.py
  - Create environment variable fixtures (discord_token, guild_id, channel_id, test_user_id)
  - Create database fixtures (db_engine, db_session) with proper connection pooling
  - Create http_client fixture (httpx.AsyncClient with base URL)
  - Create discord_helper fixture with automatic connect/disconnect
  - Set appropriate fixture scopes (session for db, function for http_client)
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 26-42)

- [x] Task 1.3: Verify E2E test environment
  - Validate env/env.e2e has required Discord credentials
  - Verify compose.e2e.yaml includes all required services
  - Test that fixtures connect successfully without errors
  - Document any additional setup steps needed
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 43-61)

### [x] Phase 2: Core Authentication

- [x] Task 2.1: Extract bot Discord ID from token
  - Extract Discord user ID from `DISCORD_ADMIN_BOT_TOKEN` by base64 decoding first segment
  - Implement utility function to parse bot token format with proper padding
  - Moved extraction logic to shared/utils/discord_tokens.py for reuse
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 62-74)

- [x] Task 2.2: Create authenticated_admin_client fixture
  - Create fixture in tests/e2e/conftest.py with function scope
  - Manually create Redis session using bot Discord ID and admin bot token
  - Set session_token cookie in HTTP client
  - Yield authenticated client for test use
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 75-87)

- [x] Task 2.3: Add synced_guild fixture
  - Create function-scoped fixture that verifies pre-seeded guild exists
  - Guild/channel already created by init service, no sync needed
  - Returns guild configuration info for use in game creation tests
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 88-102)
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 88-102)

### [x] Phase 3: Complete First Test - Game Announcement

- [x] Task 3.1: Update test to use authenticated client
  - Modify test_game_announcement.py to use authenticated_admin_client fixture
  - Replace plain http_client with authenticated_admin_client
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 103-115)

- [x] Task 3.2: Include template_id in game creation request
  - Add template_id field to game creation request body
  - Use test_template_id from synced_guild fixture
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 116-128)

- [x] Task 3.3: Verify Discord announcement message posted
  - Create game via API
  - Fetch message_id from database (game_sessions.message_id)
  - Use DiscordTestHelper to retrieve message from Discord channel
  - Verify message exists
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 129-142)

- [x] Task 3.4: Complete embed content validation
  - Validate embed title matches game title
  - Validate embed contains host mention
  - Validate embed contains player count (0/max_players)
  - Validate embed structure and fields
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 143-157)

### [ ] Phase 4: Remaining Test Scenarios

- [x] Task 4.1: Game update → message refresh test
  - Create game and retrieve message_id
  - Update game (title/description) via API
  - Verify message_id unchanged
  - Fetch message from Discord and validate updated content
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 158-170)
  - Status: ✅ COMPLETE - test_game_update_refreshes_message passing

- [x] Task 4.2: User joins → participant list update test
  - Create game, retrieve message_id
  - Simulate join via API (add participant)
  - Fetch message and verify participant count updated
  - Validate player count incremented
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 171-183)
  - Status: ✅ COMPLETE - test_user_join_updates_participant_count passing

- [x] Task 4.3: Game reminder → DM verification test
  - Create game with reminder_minutes=[1] (1 minute timeout instead of 5)
  - Schedule game 2 minutes in future
  - Wait for notification daemon to process
  - Use DiscordTestHelper.get_user_recent_dms() to fetch DMs
  - Verify test user receives DM with game details
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 184-198)
  - Status: ✅ COMPLETE - test_game_reminder_dm_delivery implemented with 1 minute timeout and 2 minute schedule

- [ ] Task 4.4: Game status transitions → message update test
  - Create game scheduled 1 minute in future with 2 minute duration
  - Wait for status transition daemon to process SCHEDULED→IN_PROGRESS
  - Verify Discord message updated and game status changed to IN_PROGRESS
  - Wait for IN_PROGRESS→COMPLETED transition
  - Verify Discord message updated and game status changed to COMPLETED
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 199-220)
  - Status: ❌ NOT STARTED - Critical gap: validates status_transition_daemon → RabbitMQ → Bot path

### [ ] Phase 5: Additional Communication Path Tests

- [ ] Task 5.1: Game cancellation → message update test
  - Create game, retrieve message_id
  - Cancel game via API (DELETE /games/{id})
  - Verify GAME_CANCELLED event published
  - Verify Discord message updated or deleted
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 221-239)
  - Status: ❌ NOT STARTED - Critical gap identified in microservice analysis

- [ ] Task 5.2: Player removal → DM notification test
  - Create game with multiple participants
  - Remove participant via API
  - Verify PLAYER_REMOVED event published
  - Verify removed user receives DM notification
  - Verify Discord message updated with new participant count
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 240-258)
  - Status: ❌ NOT STARTED - Critical gap identified in microservice analysis

- [ ] Task 5.3: Waitlist promotion → DM notification test
  - Create game at max capacity with waitlist
  - Remove active participant to trigger promotion
  - Verify NOTIFICATION_SEND_DM event published
  - Verify promoted user receives DM
  - Verify Discord message updated
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 259-277)
  - Status: ❌ NOT STARTED - Critical gap identified in microservice analysis

- [ ] Task 5.4: Join notification → delayed DM test
  - Create game with signup instructions
  - Join game as participant
  - Verify notification_schedule entry created (type=join_notification)
  - Wait for notification daemon to process
  - Verify NOTIFICATION_DUE event published with type=join_notification
  - Verify participant receives signup instructions DM
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 278-300)
  - Status: ❌ NOT STARTED - Critical gap: validates second notification_type path

### [ ] Phase 6: Documentation and CI/CD Integration

- [ ] Task 6.1: Update TESTING_E2E.md
  - Document new E2E test execution pattern
  - Include DiscordTestHelper usage examples
  - Include authentication fixture usage examples
  - Document guild sync requirement
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 301-318)

- [ ] Task 6.2: Document Discord test environment requirements
  - Admin bot token requirement
  - Test guild and channel setup
  - Test user creation steps
  - DiscordTestHelper configuration
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 319-336)

- [ ] Task 6.3: Configure CI/CD for E2E test execution
  - Document E2E test execution (likely manual-only)
  - Add conditional execution logic based on environment
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 337-355)

## Dependencies

- pytest-asyncio for async test support
- discord.py library (already installed)
- Test Discord guild, channel, bot token, and test user
- Running full stack via compose.e2e.yaml profile
- RabbitMQ for event messaging
- ✅ Discord client token unification (COMPLETE) - enables bot token use with all Discord API endpoints
- ✅ Automatic token type detection - simplifies authentication pattern for tests
- PostgreSQL for game session storage

## Success Criteria

- DiscordTestHelper module provides clean API for Discord operations
- test_game_creation_posts_announcement passes with message validation
- All priority E2E scenarios have passing tests
- Documentation updated with test execution instructions
- Pattern established for future E2E test development
- Clear path forward for implementing advanced test scenarios
- **Comprehensive microservice communication path coverage achieved**:
  - Pattern 1 (Immediate API Events): 5/5 tested (100%)
  - Pattern 2 (Scheduled Notification Events): 2/2 tested (100%)
  - Pattern 3 (Scheduled Status Events): 1/1 tested (100%)
  - Overall: 8/8 critical paths tested (100%)
