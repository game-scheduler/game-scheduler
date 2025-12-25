---
applyTo: ".copilot-tracking/changes/20251225-e2e-polling-patterns-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: E2E Test Polling Pattern Refactoring

## Overview

Replace inconsistent sleep patterns in E2E tests with modular polling utilities to eliminate flakiness, reduce test execution time, and improve maintainability.

## Objectives

- Create reusable polling utilities for Discord message, DM, and database operations
- Eliminate 12 fixed sleep calls that waste time and risk flakiness
- Consolidate 9 duplicate polling loops into shared implementations
- Reduce test execution time by 20-40% through early exit on success
- Provide consistent timeout/interval/logging behavior across all E2E tests

## Research Summary

### Project Files

- tests/e2e/helpers/discord.py - Base helper class for Discord operations
- tests/e2e/conftest.py - Test fixtures and configuration
- tests/e2e/test_*.py - 11 test files with 21 sleep/polling patterns

### External References

- #file:../research/20251225-e2e-polling-patterns-research.md - Complete analysis of current state and proposed solution
- #githubRepo:"pytest-dev/pytest-asyncio asyncio polling" - Async polling patterns for pytest
- #githubRepo:"Rapptz/discord.py message polling" - Discord.py message fetch patterns

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Core Polling Utilities

- [x] Task 1.1: Add `wait_for_condition` generic polling function to discord.py
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 12-48)

- [x] Task 1.2: Add `wait_for_message` method to DiscordTestHelper
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 50-78)

- [x] Task 1.3: Add `wait_for_message_update` method to DiscordTestHelper
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 80-115)

- [x] Task 1.4: Add `wait_for_dm_matching` method to DiscordTestHelper
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 117-151)

- [x] Task 1.5: Add `wait_for_recent_dm` convenience method to DiscordTestHelper
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 153-185)

- [x] Task 1.6: Add `wait_for_db_condition` database polling utility
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 187-225)

### [x] Phase 2: High Priority Test Refactoring

- [x] Task 2.1: Refactor test_player_removal.py (10s sleep → poll for removal DM)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 227-247)

- [x] Task 2.2: Refactor test_waitlist_promotion.py (6s sleep → poll for promotion DM)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 249-268)

- [x] Task 2.3: Refactor test_game_update.py (2 × 3s sleeps → poll for message updates)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 270-293)

- [x] Task 2.4: Refactor test_user_join.py (2 × 3s sleeps → poll for participant updates)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 295-318)

- [x] Task 2.5: Refactor test_game_cancellation.py (2s + 3s sleeps → poll for message updates)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 320-341)

- [x] Task 2.6: Refactor test_game_status_transitions.py (3s sleep → poll for message)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 343-361)

- [x] Task 2.7: Refactor test_join_notification.py (2 × 2s sleeps → poll for message/schedule)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 363-384)

- [x] Task 2.8: Refactor test_game_reminder.py (3s sleep → poll for message)
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 386-404)

### [x] Phase 3: Medium Priority Test Consolidation

- [x] Task 3.1: Consolidate test_game_announcement.py database polling
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 406-427)

- [x] Task 3.2: Consolidate test_game_reminder.py database and DM polling
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 429-454)

- [x] Task 3.3: Consolidate test_join_notification.py database and DM polling
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 456-481)

- [x] Task 3.4: Consolidate test_game_status_transitions.py status polling
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 483-508)

### [x] Phase 4: Configuration and Testing

- [x] Task 4.1: Add e2e_timeouts fixture to conftest.py
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 510-535)

- [x] Task 4.2: Run full E2E test suite and verify improvements
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 537-561)

- [x] Task 4.3: Measure and document test execution time improvements
  - Details: .copilot-tracking/details/20251225-e2e-polling-patterns-details.md (Lines 563-586)

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
