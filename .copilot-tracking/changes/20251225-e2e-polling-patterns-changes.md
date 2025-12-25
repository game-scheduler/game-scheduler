<!-- markdownlint-disable-file -->

# Release Changes: E2E Test Polling Pattern Refactoring

**Related Plan**: 20251225-e2e-polling-patterns-plan.instructions.md
**Implementation Date**: 2025-12-25

## Summary

Refactoring E2E tests to replace inconsistent sleep patterns with modular polling utilities, eliminating flakiness and reducing test execution time.

## Changes

### Added

- tests/e2e/helpers/test_discord.py - Unit tests for wait_for_condition and all DiscordTestHelper polling methods
- tests/e2e/test_conftest.py - Unit tests for wait_for_db_condition database polling utility

### Modified

- tests/e2e/helpers/discord.py - Added wait_for_condition generic polling utility with logging and timeout support
- tests/e2e/helpers/discord.py - Added wait_for_message method to poll for Discord message existence
- tests/e2e/helpers/discord.py - Added wait_for_message_update method to poll for message content/embed changes
- tests/e2e/helpers/discord.py - Added wait_for_dm_matching method to poll for DMs matching predicates
- tests/e2e/helpers/discord.py - Added wait_for_recent_dm convenience method with DMType StrEnum for type safety
- tests/e2e/helpers/discord.py - Added DMType StrEnum (REMINDER, JOIN, REMOVAL, PROMOTION)
- tests/e2e/conftest.py - Added wait_for_db_condition function for database polling with predicates

### Removed
