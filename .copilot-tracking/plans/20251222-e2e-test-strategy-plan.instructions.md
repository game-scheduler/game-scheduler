---
applyTo: ".copilot-tracking/changes/20251222-e2e-test-strategy-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: E2E Test Strategy - Discord Message Validation

## Overview

Implement true end-to-end testing that validates Discord bot behavior and message content, addressing the gap in current database-focused tests.

## Objectives

- Verify game announcements appear in Discord channels with correct content
- Validate Discord message embeds, fields, and user mentions
- Test DM reminder delivery to participants
- Establish reusable patterns for Discord message validation
- Create helper utilities for Discord API interactions

## Research Summary

### Project Files

- tests/e2e/test_game_notification_api_flow.py - Database-focused tests without Discord validation
- tests/e2e/test_guild_template_api.py - Integration tests with mocked Discord responses
- services/bot/events/handlers.py - Discord event handlers and message posting logic
- services/bot/formatters/game_message.py - Game announcement embed formatting
- TESTING_E2E.md - E2E test environment documentation

### External References

- #file:../research/20251222-e2e-test-strategy-research.md - Comprehensive E2E strategy analysis
- #fetch:https://discord.com/developers/docs/resources/message - Discord Message API documentation
- discord.py library - Message reading capabilities (fetch_message, embeds, content)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Testing standards

## Implementation Checklist

### [ ] Phase 1: Discord Test Helper Module

- [ ] Task 1.1: Create DiscordTestHelper class structure
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 15-43)

- [ ] Task 1.2: Implement message fetching methods
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 45-73)

- [ ] Task 1.3: Implement DM verification methods
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 75-103)

- [ ] Task 1.4: Implement embed verification utilities
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 105-133)

### [ ] Phase 2: First E2E Test - Game Announcement

- [ ] Task 2.1: Create test environment fixtures
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 135-163)

- [ ] Task 2.2: Implement game creation announcement test
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 165-193)

- [ ] Task 2.3: Validate message content and embed structure
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 195-223)

### [ ] Phase 3: Additional E2E Test Scenarios

- [ ] Task 3.1: Implement game update message refresh test
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 225-253)

- [ ] Task 3.2: Implement user join participant list test
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 255-283)

- [ ] Task 3.3: Implement DM reminder delivery test
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 285-313)

- [ ] Task 3.4: Implement game deletion message removal test
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 315-343)

### [ ] Phase 4: Documentation and CI/CD Integration

- [ ] Task 4.1: Update TESTING_E2E.md with new test execution instructions
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 345-373)

- [ ] Task 4.2: Document Discord test environment requirements
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 375-403)

- [ ] Task 4.3: Configure CI/CD for E2E test execution
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 405-433)

## Dependencies

- pytest-asyncio for async test support
- discord.py library (already installed)
- Test Discord guild, channel, bot token, and test user
- Running full stack via compose.e2e.yaml profile
- RabbitMQ for event messaging
- PostgreSQL for game session storage

## Success Criteria

- DiscordTestHelper module provides clean API for Discord operations
- test_game_creation_posts_announcement passes with message validation
- All five priority E2E scenarios have passing tests
- Documentation updated with test execution instructions
- Pattern established for future E2E test development
- Clear path forward for implementing advanced test scenarios
