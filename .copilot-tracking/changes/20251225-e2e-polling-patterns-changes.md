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
- tests/e2e/test_player_removal.py - Replaced 10s sleep with wait_for_recent_dm for removal DM polling
- tests/e2e/test_player_removal.py - Replaced 3s sleep with wait_for_message for message creation polling
- tests/e2e/test_player_removal.py - Removed asyncio import (no longer needed)
- tests/e2e/test_waitlist_promotion.py - Replaced 6s sleep with wait_for_recent_dm for promotion DM polling
- tests/e2e/test_waitlist_promotion.py - Replaced 2s sleep with wait_for_message for message creation polling
- tests/e2e/test_waitlist_promotion.py - Simplified DM verification (removed redundant polling loop)
- tests/e2e/test_waitlist_promotion.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_update.py - Replaced first 3s sleep with wait_for_message for message creation polling
- tests/e2e/test_game_update.py - Replaced second 3s sleep with wait_for_message_update to poll for title change
- tests/e2e/test_game_update.py - Removed asyncio import (no longer needed)
- tests/e2e/test_user_join.py - Replaced first 3s sleep with wait_for_message for message creation polling
- tests/e2e/test_user_join.py - Replaced second 3s sleep with wait_for_message_update to poll for participant count (1/4)
- tests/e2e/test_user_join.py - Added verification code after join to check participant count update (test was incomplete)
- tests/e2e/test_user_join.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_cancellation.py - Replaced 2s sleep with wait_for_message for initial message creation polling
- tests/e2e/test_game_cancellation.py - Replaced 3s sleep with wait_for_message_update to poll for cancellation footer
- tests/e2e/test_game_cancellation.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_status_transitions.py - Replaced 3s sleep with wait_for_message for message creation polling (asyncio still used by status polling loops)
- tests/e2e/test_join_notification.py - Replaced first 2s sleep with wait_for_message for game message creation
- tests/e2e/test_join_notification.py - Replaced second 2s sleep with wait_for_message for game message creation
- tests/e2e/test_game_reminder.py - Replaced 3s sleep with wait_for_message for game message creation polling
- tests/e2e/test_game_announcement.py - Replaced custom database polling loop (10 attempts x 0.5s) with wait_for_db_condition
- tests/e2e/test_game_announcement.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_announcement.py - Added import for wait_for_db_condition from conftest
- tests/e2e/test_game_reminder.py - Replaced custom database polling loop (5 attempts x 1s) with wait_for_db_condition
- tests/e2e/test_game_reminder.py - Replaced custom DM polling loop (150s timeout, 5s interval) with wait_for_recent_dm
- tests/e2e/test_game_reminder.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_reminder.py - Added import for wait_for_db_condition from conftest
- tests/e2e/test_join_notification.py - Replaced first custom DM polling loop (90s timeout, 5s interval) with wait_for_recent_dm
- tests/e2e/test_join_notification.py - Replaced second custom DM polling loop (90s timeout, 5s interval) with wait_for_recent_dm
- tests/e2e/test_join_notification.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_status_transitions.py - Replaced custom IN_PROGRESS status polling loop (150s timeout, 5s interval) with wait_for_db_condition
- tests/e2e/test_game_status_transitions.py - Replaced custom COMPLETED status polling loop (180s timeout, 5s interval) with wait_for_db_condition
- tests/e2e/test_game_status_transitions.py - Removed asyncio import (no longer needed)
- tests/e2e/test_game_status_transitions.py - Added import for wait_for_db_condition from conftest
- tests/e2e/conftest.py - Added TimeoutType StrEnum for type-safe timeout operation keys
- tests/e2e/conftest.py - Added e2e_timeouts fixture with TimeoutType enum keys and standard timeout values
- tests/e2e/test_game_status_transitions.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_game_status_transitions.py - Replaced hardcoded timeout=10 with e2e_timeouts[TimeoutType.MESSAGE_CREATE]
- tests/e2e/test_game_status_transitions.py - Replaced hardcoded timeout=150/180 with e2e_timeouts[TimeoutType.STATUS_TRANSITION]
- tests/e2e/test_waitlist_promotion.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_waitlist_promotion.py - Replaced hardcoded timeout=10 with e2e_timeouts[TimeoutType.MESSAGE_CREATE]
- tests/e2e/test_waitlist_promotion.py - Replaced hardcoded timeout=10 (DM) with e2e_timeouts[TimeoutType.DM_IMMEDIATE]
- tests/e2e/test_game_update.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_game_update.py - Replaced hardcoded timeout=10 with e2e_timeouts[TimeoutType.MESSAGE_CREATE/MESSAGE_UPDATE]
- tests/e2e/test_player_removal.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_player_removal.py - Replaced hardcoded timeout=10/15 with e2e_timeouts[TimeoutType.MESSAGE_CREATE/DM_IMMEDIATE]
- tests/e2e/test_game_reminder.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_game_reminder.py - Replaced hardcoded timeout values with appropriate TimeoutType enum values
- tests/e2e/test_user_join.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_user_join.py - Replaced hardcoded timeout=10 with e2e_timeouts[TimeoutType.MESSAGE_CREATE/MESSAGE_UPDATE]
- tests/e2e/test_join_notification.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_join_notification.py - Replaced hardcoded timeout=10/90 with e2e_timeouts[TimeoutType.MESSAGE_CREATE/DM_SCHEDULED]
- tests/e2e/test_game_announcement.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_game_announcement.py - Replaced hardcoded timeout=5 with e2e_timeouts[TimeoutType.DB_WRITE]
- tests/e2e/test_game_cancellation.py - Added import for TimeoutType and e2e_timeouts fixture parameter
- tests/e2e/test_game_cancellation.py - Replaced hardcoded timeout=10 with e2e_timeouts[TimeoutType.MESSAGE_CREATE/MESSAGE_UPDATE]
- tests/e2e/test_game_reminder.py - Fixed undefined helper variable name to main_bot_helper
- tests/e2e/test_join_notification.py - Fixed undefined helper variable names to main_bot_helper
- tests/e2e/test_join_notification.py - Fixed line too long by breaking signup_instructions into multi-line string
- tests/e2e/test_player_removal.py - Fixed undefined channel_id to discord_channel_id
- tests/e2e/test_player_removal.py - Fixed undefined recent_dms reference in assertion
- tests/e2e/test_player_removal.py - Removed leftover polling code lines from incomplete refactoring
- tests/e2e/test_game_update.py - Added clean_test_data fixture to fix missing fixture error
- tests/e2e/test_player_removal.py - Added clean_test_data fixture to fix missing fixture error
- tests/e2e/test_user_join.py - Added clean_test_data fixture to fix missing fixture error
- tests/e2e/test_user_join.py - Fixed missing await on db_session.commit()
- tests/e2e/test_game_update.py - Added wait_for_db_condition import
- tests/e2e/test_game_update.py - Replaced immediate database query with wait_for_db_condition to poll for message_id population (async via RabbitMQ)
- tests/e2e/conftest.py - Added wait_for_game_message_id helper function to centralize common pattern of waiting for message_id after game creation
- tests/e2e/test_game_update.py - Replaced wait_for_db_condition call with new wait_for_game_message_id helper
- tests/e2e/test_game_cancellation.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_player_removal.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_user_join.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_waitlist_promotion.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_game_reminder.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_join_notification.py - Added wait_for_game_message_id import and replaced immediate query with helper call (2 locations)
- tests/e2e/test_game_status_transitions.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_game_announcement.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_game_reminder.py - Fixed missing await on wait_for_db_condition call
- tests/e2e/test_game_status_transitions.py - Fixed 2 missing awaits on wait_for_db_condition calls
- tests/e2e/test_player_removal.py - Fixed DMType import scope (moved from fixture function to module-level import)
- tests/e2e/test_waitlist_promotion.py - Fixed DMType import scope (moved from fixture function to module-level import)
- tests/e2e/test_game_reminder.py - Fixed DMType import scope (moved from fixture function to module-level import)
- tests/e2e/test_join_notification.py - Fixed DMType import scope (moved from fixture function to module-level import)
- shared/message_formats.py - Created centralized module for Discord message format strings and predicates
- shared/message_formats.py - Added DMFormats class with static methods for promotion, removal, join (with/without instructions), and reminder (host/participant) DMs
- shared/message_formats.py - Added DMPredicates class with static methods returning predicate functions for matching each DM type
- shared/message_formats.py - Added DiscordMessage Protocol for type hints in predicates
- tests/e2e/helpers/discord.py - Added import for DMPredicates from shared.message_formats
- tests/e2e/helpers/discord.py - Replaced inline lambda predicates in wait_for_recent_dm with DMPredicates.* calls
- tests/e2e/helpers/discord.py - Updated wait_for_recent_dm docstring to mention centralized predicates from shared.message_formats
- tests/e2e/helpers/test_discord.py - Fixed test_promotion_dm_type to use actual promotion message format ("A spot opened up", "moved from the waitlist")

### Removed

None
- tests/e2e/test_user_join.py - Added wait_for_game_message_id import and replaced immediate query with helper call (2 locations)
- tests/e2e/test_waitlist_promotion.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_game_reminder.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_join_notification.py - Added wait_for_game_message_id import and replaced immediate queries with helper call (2 locations)
- tests/e2e/test_game_status_transitions.py - Added wait_for_game_message_id import and replaced immediate query with helper call
- tests/e2e/test_game_announcement.py - Replaced wait_for_db_condition with wait_for_game_message_id helper and removed obsolete channel_id reference
- tests/e2e/test_game_reminder.py - Fixed missing await on wait_for_db_condition call
- tests/e2e/test_game_reminder.py - Added DMType import and changed dm_type parameter from string to DMType.REMINDER enum
- tests/e2e/test_player_removal.py - Added DMType import and changed dm_type parameter from string to DMType.REMOVAL enum
- tests/e2e/test_join_notification.py - Added DMType import and changed dm_type parameter from string to DMType.JOIN enum (2 locations)
- tests/e2e/test_waitlist_promotion.py - Added DMType import and changed dm_type parameter from string to DMType.PROMOTION enum
- tests/e2e/test_player_removal.py - Moved DMType import from fixture to module level to fix NameError
- tests/e2e/test_game_reminder.py - Moved DMType import from fixture to module level to fix NameError
- tests/e2e/test_join_notification.py - Moved DMType import from fixture to module level to fix NameError
- tests/e2e/test_waitlist_promotion.py - Moved DMType import from fixture to module level to fix NameError
- tests/e2e/test_game_status_transitions.py - Added missing await to two wait_for_db_condition calls for status transitions

### Removed
