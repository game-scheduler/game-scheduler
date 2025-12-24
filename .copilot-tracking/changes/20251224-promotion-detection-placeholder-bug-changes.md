<!-- markdownlint-disable-file -->

# Release Changes: Fix Promotion Detection Bug with Placeholder Participants

**Related Plan**: 20251224-promotion-detection-placeholder-bug-plan.instructions.md
**Implementation Date**: 2025-12-24

## Summary

Fix waitlist promotion detection bug where users are not notified when promoted from overflow positions when placeholders occupy confirmed slots. Implement centralized participant partitioning utility to ensure consistent handling across all 6 locations in the codebase.

## Changes

### Added

- shared/utils/participant_sorting.py - Added DEFAULT_MAX_PLAYERS constant (value: 10)
- shared/utils/participant_sorting.py - Added PartitionedParticipants dataclass for consistent participant ordering
- shared/utils/participant_sorting.py - Added partition_participants() function to sort and partition participants into confirmed/overflow groups
- tests/shared/utils/test_participant_sorting.py - Added 11 comprehensive tests for partition_participants() covering all edge cases
- tests/services/api/services/test_games_promotion.py - Added create_placeholder() helper function for creating placeholder participants
- tests/services/api/services/test_games_promotion.py - Added test_promotion_when_placeholder_removed() test case
- tests/services/api/services/test_games_promotion.py - Added test_promotion_with_max_players_increase_and_placeholders() test case
- tests/services/api/services/test_games_promotion.py - Added test_promotion_multiple_placeholders_removed() test case
- tests/services/api/services/test_games_promotion.py - Added test_no_promotion_when_placeholder_added_to_overflow() test case

### Modified

- shared/utils/participant_sorting.py - Updated partition_participants() to use DEFAULT_MAX_PLAYERS constant
- tests/shared/utils/test_participant_sorting.py - Updated tests to use DEFAULT_MAX_PLAYERS constant instead of hardcoded 10
- services/api/services/games.py - Updated update_game() to use partition_participants() for old state overflow detection (Task 2.1)
- services/api/services/games.py - Updated _detect_and_notify_promotions() to use partition_participants() for current state promotion detection (Task 2.2)

### Removed
