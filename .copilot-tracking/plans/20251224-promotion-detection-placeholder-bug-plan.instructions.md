---
title: "Fix Promotion Detection Bug with Placeholder Participants"
description: "Fix waitlist promotion detection failing when placeholders occupy confirmed slots, with phased approach from immediate fix to architectural refactoring"
applyTo: ".copilot-tracking/changes/20251224-promotion-detection-placeholder-bug-changes.md"
priority: "high"
status: "planned"
created: "2025-12-24"
---

# Plan: Fix Promotion Detection Bug with Placeholder Participants

## Problem Statement

The waitlist promotion detection in `services/api/services/games.py::_detect_and_notify_promotions()` fails to correctly identify promoted users when placeholder participants occupy confirmed slots. This causes users who are promoted from overflow to confirmed status to not receive DM notifications, despite the Discord message correctly updating.

### Root Cause

The promotion detection filters participants to only "real" users (with `user_id`) but then compares against `max_players` which is designed to apply to ALL participants including placeholders:

```python
# Current buggy code (lines 810-816)
old_all_participants = [p for p in game.participants if p.user_id and p.user]  # ❌ Filters out placeholders
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]  # ❌ Wrong threshold
    if p.user is not None
}
```

### Impact

- **Severity:** High - Users miss critical notifications about their promotion
- **Frequency:** Occurs whenever placeholders are used (common feature)
- **Affected Scenarios:**
  - Real user promoted when placeholder removed
  - Real user promoted when max_players increased with placeholders present
  - Any game with mixed placeholder and real participants

## Solution Approach

### Phase 1: Immediate Bug Fix (Critical)
Fix the promotion detection logic to account for all participants including placeholders.

### Phase 2: Architectural Refactoring (Enhancement)
Create centralized participant partitioning utility to prevent future bugs and simplify maintenance.

## Implementation Plan

### Phase 1: Immediate Bug Fix

#### 1.1 Fix Promotion Detection Logic
**File:** `services/api/services/games.py`
**Function:** `update_game()` (lines 810-816)

**Change:**
```python
# Before: Only includes real users, causing incorrect overflow detection
old_all_participants = [p for p in game.participants if p.user_id and p.user]
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]
    if p.user is not None
}

# After: Include ALL participants, filter at the end
old_all_participants = game.participants  # Include placeholders
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]
    if p.user is not None and p.user.discord_id  # Filter HERE
}
```

**Also update the "new" state calculation** (around lines ~1180-1190 in the same function):
```python
# Similar fix for new_overflow_ids calculation
new_all_participants = updated_game.participants  # Include placeholders
new_sorted_participants = participant_sorting.sort_participants(new_all_participants)
new_overflow_ids = {
    p.user.discord_id
    for p in new_sorted_participants[updated_game.max_players:]
    if p.user is not None and p.user.discord_id
}
```

**Rationale:** This matches the bot formatter logic which correctly handles all participants.

#### 1.2 Add Unit Tests for Promotion Detection
**File:** `tests/services/api/services/test_games_promotion.py` (create if doesn't exist)

**Test Cases:**
1. `test_promotion_detection_with_placeholder_removed`
   - Setup: Game with max_players=2, participants=["Placeholder1", "User1", "User2"]
   - Action: Remove "Placeholder1"
   - Expected: User2 promoted from overflow to confirmed, notification sent

2. `test_promotion_detection_with_max_players_increase_and_placeholders`
   - Setup: Game with max_players=1, participants=["Placeholder1", "User1"]
   - Action: Increase max_players to 2
   - Expected: User1 promoted from overflow to confirmed, notification sent

3. `test_promotion_detection_multiple_placeholders`
   - Setup: Game with max_players=3, participants=["P1", "P2", "User1", "User2"]
   - Action: Remove both placeholders
   - Expected: User2 promoted, notification sent

4. `test_no_promotion_all_real_users` (existing behavior)
   - Setup: Game with max_players=2, participants=["User1", "User2", "User3"]
   - Action: Remove User1
   - Expected: User3 promoted, notification sent

**Implementation Notes:**
- Mock the `_publish_promotion_notification` method to verify it's called
- Verify promoted user Discord IDs are correct
- Test both old_overflow_ids and new_overflow_ids calculations

#### 1.3 Verify E2E Test Passes
**File:** `tests/e2e/test_waitlist_promotion.py`
**Test:** `test_promotion_via_max_players_increase`

After fixing the bug, this test should pass without modification.

**Verification:**
```bash
uv run pytest tests/e2e/test_waitlist_promotion.py::test_promotion_via_max_players_increase -v
```

### Phase 2: Architectural Refactoring (Post-Fix Enhancement)

#### 2.1 Create Centralized Participant Partitioning Utility
**File:** `shared/utils/participant_sorting.py`

**Add new dataclass and function:**

```python
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.participant import GameParticipant

@dataclass
class PartitionedParticipants:
    """
    Result of partitioning participants into confirmed and overflow groups.

    This provides a single source of truth for participant ordering that accounts
    for placeholders, ensuring consistent behavior across bot formatters, API
    services, and notification logic.
    """
    all_sorted: list["GameParticipant"]
    """All participants sorted by priority (host, cohost, signup time)"""

    confirmed: list["GameParticipant"]
    """Participants in confirmed slots (0 to max_players-1)"""

    overflow: list["GameParticipant"]
    """Participants in overflow/waitlist (max_players onwards)"""

    confirmed_real_user_ids: set[str]
    """Discord IDs of confirmed participants with user accounts"""

    overflow_real_user_ids: set[str]
    """Discord IDs of overflow participants with user accounts"""


def partition_participants(
    participants: list["GameParticipant"],
    max_players: int | None = None,
) -> PartitionedParticipants:
    """
    Sort and partition participants into confirmed and overflow groups.

    This function handles both real users and placeholder participants,
    ensuring consistent ordering logic across the application.

    Args:
        participants: List of all participants (including placeholders)
        max_players: Maximum confirmed participants (defaults to 10 if None)

    Returns:
        PartitionedParticipants with sorted lists and pre-computed ID sets

    Example:
        >>> partitioned = partition_participants(game.participants, game.max_players)
        >>> confirmed_ids = partitioned.confirmed_real_user_ids
        >>> overflow_ids = partitioned.overflow_real_user_ids
    """
    max_players = max_players or 10
    sorted_all = sort_participants(participants)
    confirmed = sorted_all[:max_players]
    overflow = sorted_all[max_players:]

    confirmed_ids = {
        p.user.discord_id
        for p in confirmed
        if p.user and p.user.discord_id
    }
    overflow_ids = {
        p.user.discord_id
        for p in overflow
        if p.user and p.user.discord_id
    }

    return PartitionedParticipants(
        all_sorted=sorted_all,
        confirmed=confirmed,
        overflow=overflow,
        confirmed_real_user_ids=confirmed_ids,
        overflow_real_user_ids=overflow_ids,
    )
```

**Benefits:**
- Single source of truth for participant ordering
- Pre-computed ID sets for efficient lookups
- Type-safe with dataclass structure
- Handles placeholders consistently
- Simplifies future enhancements (priority tiers, reserved slots)

#### 2.2 Update Promotion Detection to Use New Utility
**File:** `services/api/services/games.py`
**Function:** `update_game()`

**Change:**
```python
# Before: Manual sorting and slicing
old_all_participants = game.participants
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]
    if p.user is not None and p.user.discord_id
}

# After: Use centralized utility
from shared.utils.participant_sorting import partition_participants

old_partitioned = partition_participants(game.participants, old_max_players)
old_overflow_ids = old_partitioned.overflow_real_user_ids

# Similar for new state
new_partitioned = partition_participants(updated_game.participants, updated_game.max_players)
new_overflow_ids = new_partitioned.overflow_real_user_ids
```

#### 2.3 Migrate Bot Event Handlers
**File:** `services/bot/events/handlers.py`

**Locations to update:**
1. `_handle_game_reminder()` (lines 393-403)
2. `_handle_join_notification()` (lines 511-513)
3. `_handle_game_cancelled()` (lines 858-862)

**Pattern:**
```python
# Before
sorted_participants = participant_sorting.sort_participants(game.participants)
confirmed = sorted_participants[:game.max_players]
overflow = sorted_participants[game.max_players:]

# After
from shared.utils.participant_sorting import partition_participants

partitioned = partition_participants(game.participants, game.max_players)
confirmed = partitioned.confirmed
overflow = partitioned.overflow
```

#### 2.4 Migrate API Routes
**File:** `services/api/routes/games.py`
**Function:** `download_calendar()` (line 566)

**Change:**
```python
# Before: Manual sort and slice
sorted_participants = participant_sorting.sort_participants(game.participants)
confirmed_participants = sorted_participants[:game.max_players]

# After: Use utility
from shared.utils.participant_sorting import partition_participants

partitioned = partition_participants(game.participants, game.max_players)
confirmed_participants = partitioned.confirmed
```

#### 2.5 Add Comprehensive Tests for New Utility
**File:** `tests/shared/utils/test_participant_partitioning.py` (---
applyTo: ".copilot-tracking/changes/20251224-promotion-detection-placeholder-bug-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Fix Promotion Detection Bug with Placeholder Participants

## Overview

Fix waitlist promotion detection bug where users are not notified when promoted from overflow positions occupied by placeholders, by implementing a centralized participant partitioning utility.

## Objectives

- Create centralized `partition_participants()` utility for consistent participant ordering
- Fix promotion detection in `update_game()` to correctly identify promoted users with placeholders present
- Fix promotion detection in `_detect_and_notify_promotions()` helper method
- Add comprehensive unit tests for the new utility and bug scenarios
- Verify E2E test passes with the fix

## Research Summary

### Project Files

- services/api/services/games.py - Contains buggy promotion detection logic (lines 810-816, 1195-1210)
- shared/utils/participant_sorting.py - Current location for `sort_participants()`, will add new utility
- services/bot/formatters/game_message.py - Demonstrates correct pattern for handling placeholders
- tests/e2e/test_waitlist_promotion.py - E2E test exposing the bug

### External References

- #file:../research/20251224-promotion-detection-bug.md - Complete bug analysis and solution design
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - General best practices

### Standards References

- #file:../../.github/instructions/python.instructions.md - Type hints, dataclasses, and testing standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Code documentation style

## Implementation Checklist

### [ ] Phase 1: Create Centralized Participant Partitioning Utility

- [x] Task 1.1: Add `PartitionedParticipants` dataclass to `shared/utils/participant_sorting.py`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 15-35)

- [x] Task 1.2: Add `partition_participants()` function to `shared/utils/participant_sorting.py`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 37-75)

- [x] Task 1.3: Add comprehensive unit tests for `partition_participants()`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 77-110)

### [x] Phase 2: Fix Promotion Detection in games.py

- [x] Task 2.1: Update `update_game()` to use `partition_participants()` for old state
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 112-140)

- [x] Task 2.2: Update `_detect_and_notify_promotions()` to use `partition_participants()` for current state
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 142-170)

- [x] Task 2.3: Add unit tests for promotion detection with placeholders
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 172-200)

### [ ] Phase 3: Migrate Bot Event Handlers

- [ ] Task 3.1: Update `_handle_game_reminder()` to use `partition_participants()`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 202-230)

- [ ] Task 3.2: Update `_handle_join_notification()` to use `partition_participants()`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 232-260)

- [ ] Task 3.3: Update `_handle_game_cancelled()` to use `partition_participants()`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 262-290)

### [ ] Phase 4: Migrate API Routes

- [ ] Task 4.1: Update `download_calendar()` to use `partition_participants()`
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 292-315)

### [ ] Phase 5: Verification and Testing

- [ ] Task 5.1: Run existing unit tests to verify no regressions
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 317-330)

- [ ] Task 5.2: Run E2E test to verify bug fix
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 332-345)

- [ ] Task 5.3: Verify all new code passes linting
  - Details: .copilot-tracking/details/20251224-promotion-detection-placeholder-bug-details.md (Lines 347-355)

## Dependencies

- Python 3.11+
- SQLAlchemy models (GameParticipant, User)
- Existing `sort_participants()` function
- pytest for unit tests
- Docker environment for E2E tests

## Success Criteria

- `PartitionedParticipants` dataclass and `partition_participants()` function implemented with comprehensive tests
- All 6 locations migrated to use centralized `partition_participants()` utility
- Promotion detection correctly identifies users promoted when placeholders are removed
- Promotion detection correctly identifies users promoted when max_players increased with placeholders present
- Bot event handlers use consistent participant partitioning logic
- API routes use consistent participant partitioning logic
- All existing unit tests pass without modification
- E2E test `test_waitlist_promotion.py` passes
- No linting errors in new or modified code
- Code follows project Python conventions and documentation standards)

**Test Cases:**
1. `test_partition_all_real_users`
2. `test_partition_with_placeholders_in_confirmed`
3. `test_partition_with_placeholders_in_overflow`
4. `test_partition_mixed_placeholders_and_users`
5. `test_partition_empty_list`
6. `test_partition_default_max_players`
7. `test_partition_preserves_sort_order`
8. `test_confirmed_overflow_id_sets_correct`

#### 2.6 Update Bot Formatter (Optional Cleanup)
**File:** `services/bot/formatters/game_message.py`
**Function:** `format_game_participants()`

The bot formatter already uses the correct logic. Consider updating it to use the new utility for consistency, though this is optional since it already works correctly.

## Testing Strategy

### Unit Tests
- **Phase 1:** Test promotion detection with placeholders
- **Phase 2:** Test new `partition_participants()` utility thoroughly

### Integration Tests
- Verify promotion notifications are sent in all scenarios
- Test placeholder + real user combinations

### E2E Tests
- `test_waitlist_promotion.py::test_promotion_via_max_players_increase` should pass
- Consider adding more E2E scenarios for edge cases

### Regression Testing
- Run full test suite to ensure no breaking changes
- Pay special attention to:
  - `tests/services/api/services/test_games.py`
  - `tests/services/bot/events/test_handlers.py`
  - `tests/e2e/test_waitlist_promotion.py`

## Migration Checklist

### Phase 1 (Immediate Fix) - Must Complete
- [ ] Fix `update_game()` old_overflow_ids calculation
- [ ] Fix `update_game()` new_overflow_ids calculation
- [ ] Add unit tests for placeholder promotion scenarios
- [ ] Verify E2E test passes
- [ ] Run full test suite
- [ ] Manual testing with real Discord bot

### Phase 2 (Architectural Refactoring) - Can Be Separate PR
- [ ] Add `PartitionedParticipants` dataclass to `shared/utils/participant_sorting.py`
- [ ] Add `partition_participants()` function
- [ ] Add comprehensive unit tests for new utility
- [ ] Update `services/api/services/games.py::update_game()`
- [ ] Update `services/bot/events/handlers.py::_handle_game_reminder()`
- [ ] Update `services/bot/events/handlers.py::_handle_join_notification()`
- [ ] Update `services/bot/events/handlers.py::_handle_game_cancelled()`
- [ ] Update `services/api/routes/games.py::download_calendar()`
- [ ] Run full test suite
- [ ] Code review focusing on consistency

## Success Criteria

### Phase 1
- ✅ E2E test `test_promotion_via_max_players_increase` passes
- ✅ All new unit tests pass
- ✅ No regression in existing tests
- ✅ Manual testing confirms DMs sent for placeholder promotions

### Phase 2
- ✅ All code locations use centralized utility
- ✅ No duplicated sort-and-slice logic remains
- ✅ All tests pass with refactored code
- ✅ Code is more maintainable and future-proof

## Rollback Plan

### Phase 1
If the fix causes unexpected issues:
1. Revert the changes to `services/api/services/games.py::update_game()`
2. Disable the failing E2E test temporarily
3. Investigate and create more targeted fix

### Phase 2
Since Phase 2 is a refactoring with no behavior change:
1. Each file migration can be reverted independently
2. The old code still works (Phase 1 fix is separate)
3. Can roll back partial migrations without issue

## Future Enhancements Enabled by Phase 2

With centralized participant partitioning, these features become easier:

1. **Priority Tiers** - VIP/supporter/regular participant levels
   - Add `priority_tier` field to partition logic
   - Sort by tier then signup time

2. **Reserved Slots** - Specific positions for roles/requirements
   - Add reserved slot tracking to `PartitionedParticipants`
   - Handle reserved vs open slots

3. **Conditional Overflow** - Different rules per game type
   - Add game type parameter to `partition_participants()`
   - Apply type-specific rules

4. **Late Join Windows** - Join after start but before cutoff
   - Add time-based logic to partitioning
   - Track late-join vs pre-start participants

## Dependencies

- No external dependencies required
- Uses existing `shared/utils/participant_sorting.py::sort_participants()`
- Compatible with current database schema

## Timeline Estimate

### Phase 1 (Critical Priority)
- Fix implementation: 1 hour
- Unit tests: 2 hours
- E2E verification: 1 hour
- Testing and validation: 2 hours
- **Total: ~6 hours (1 day)**

### Phase 2 (Enhancement)
- Utility implementation: 2 hours
- Utility tests: 2 hours
- Migration (6 locations): 3 hours
- Integration testing: 2 hours
- Code review and refinement: 2 hours
- **Total: ~11 hours (1-2 days)**

## Notes

- **Phase 1 should be prioritized** as it fixes a user-facing bug
- **Phase 2 can be done separately** as a code quality improvement
- Consider creating two PRs: one for the immediate fix, one for refactoring
- The research document should be preserved as documentation of the bug discovery

## Related Files

### Phase 1
- `services/api/services/games.py` - Main fix location
- `tests/services/api/services/test_games_promotion.py` - New test file
- `tests/e2e/test_waitlist_promotion.py` - Verification test

### Phase 2
- `shared/utils/participant_sorting.py` - New utility
- `tests/shared/utils/test_participant_partitioning.py` - New test file
- `services/bot/events/handlers.py` - Multiple functions
- `services/api/routes/games.py` - Calendar download
- `services/bot/formatters/game_message.py` - Optional update

## References

- Research document: `.copilot-tracking/research/20251224-promotion-detection-bug.md`
- Existing sort function: `shared/utils/participant_sorting.py::sort_participants()`
- Bot formatter (correct logic): `services/bot/formatters/game_message.py::format_game_participants()`
