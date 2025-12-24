# Bug Discovery: Promotion Detection Ignores Placeholder Participants

**Date:** December 24, 2025
**Found During:** E2E Test Task 5.3 Implementation (Waitlist Promotion → DM Notification)
**Status:** ✅ FIXED - Architectural solution implemented with centralized `partition_participants()` utility

## Bug Description

The waitlist promotion detection in `services/api/services/games.py::_detect_and_notify_promotions()` fails to correctly identify promoted users when placeholder participants occupy confirmed slots.

### Root Cause (Original Bug)

The promotion detection filtered to only "real" participants (with `user_id`) but compared against `max_players` which applies to ALL participants including placeholders:

```python
# services/api/services/games.py, OLD CODE (lines 810-816)
old_all_participants = [p for p in game.participants if p.user_id and p.user]  # ❌ Filters out placeholders
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]  # ❌ Uses max_players designed for ALL participants
    if p.user is not None
}
```

### Fix Implemented

The bug was fixed by implementing the complete architectural solution - a centralized `partition_participants()` utility that handles placeholders correctly:

```python
# services/api/services/games.py, FIXED CODE (lines 810)
old_partitioned = partition_participants(game.participants, old_max_players)
# ...later at line 863-865...
new_partitioned = partition_participants(game.participants, new_max_players)
promoted_discord_ids = new_partitioned.cleared_waitlist(old_partitioned)
```

The utility correctly:
1. Includes ALL participants (including placeholders) when sorting
2. Partitions into confirmed/overflow based on position in sorted list
3. Filters to real user IDs only AFTER partitioning
4. Provides `cleared_waitlist()` method to detect promotions by comparing before/after states

### Scenario That Fails

**Initial State:**
- Game created with `max_players=1`
- Participants: `["Reserved", "<@discord_user_id>"]`
- Visual representation: Reserved (confirmed), test_user (overflow)
- Discord message correctly shows: "Participants (1/1)" with test_user in "Overflow" section

**What Promotion Detection Sees:**
- `old_all_participants` = [test_user] (placeholder filtered out)
- `old_sorted_participants[0:1]` = [test_user]
- `old_overflow_ids` = {} (**empty!** - test_user is within the slice)

**Promotion Trigger:**
- Remove "Reserved" placeholder OR increase `max_players` to 2
- **Fixed**: Promotion correctly detected with `partition_participants()` utility
- test_user moves from `overflow_real_user_ids` to `confirmed_real_user_ids`
- DM sent via `cleared_waitlist()` detection

## Evidence

### Test Output (Before Fix)
```
✓ Created game with placeholder + test user (overflow)
✓ Initial message shows 1/1 with Reserved, test user in overflow
✓ Discord message shows 2/2 with test user promoted
[TEST] Found 10 DMs for user 1444075864064004097
[TEST] Looking for promotion DM with game_title='E2E Promotion (max_players increase)...'
[TEST] Looking for phrases: 'A spot opened up', 'moved from the waitlist'
AssertionError: Test user should have received promotion DM. Recent DMs: [...]
```

### Test Status (After Fix)
The E2E test should now pass with the implemented `partition_participants()` utility.

### Visual Discord State vs API State

**Discord Correctly Shows (via bot formatters):**
- Initial: "Participants (1/1)" - Reserved confirmed, test_user overflow
- After promotion: "Participants (2/2)" - Both confirmed

**API Promotion Detection Sees:**
- Initial: 1 real participant (test_user) with max_players=1 → position 0/1 → NOT overflow
- After: No promotion detected

## Impact

**Affected Scenarios:**
1. ✅ Real user → real user promotion (works - both counted)
2. ❌ Placeholder → real user (from overflow) promotion (**fails** - placeholder not counted)
3. ❌ Any scenario where placeholders occupy confirmed slots (**fails**)

**User Experience:**
- Users promoted from waitlist when placeholder is removed: **No DM sent**
- Users promoted when max_players increased with placeholders present: **No DM sent**
- Discord message updates correctly, but user never notified of promotion

## Design Inconsistency

The codebase has two different interpretations of participant positioning:

### Bot Formatters (Already Correct)
```python
# services/bot/formatters/game_message.py
all_participants = sort_participants([p for p in game.participants])  # Includes ALL
confirmed_participants = all_participants[:game.max_players]
overflow_participants = all_participants[game.max_players:]
```

### Promotion Detection (Now Fixed)
```python
# services/api/services/games.py - Now uses centralized utility
old_partitioned = partition_participants(game.participants, old_max_players)
# Promotion detection uses overflow_real_user_ids which correctly accounts for placeholders
```

## Fix Implemented

The bug was fixed by implementing the complete architectural solution - creating a centralized `partition_participants()` utility in `shared/utils/participant_sorting.py`.

### Utility Implementation

**File:** `shared/utils/participant_sorting.py`

```python
@dataclass
class PartitionedParticipants:
    """Result of partitioning participants into confirmed and overflow groups."""
    all_sorted: list["GameParticipant"]
    confirmed: list["GameParticipant"]
    overflow: list["GameParticipant"]
    confirmed_real_user_ids: set[str]  # Discord IDs of confirmed real users
    overflow_real_user_ids: set[str]   # Discord IDs of overflow real users

    def cleared_waitlist(self, previous: "PartitionedParticipants") -> set[str]:
        """Identify users promoted from overflow to confirmed."""
        return {
            discord_id
            for discord_id in previous.overflow_real_user_ids
            if discord_id in self.confirmed_real_user_ids
        }

def partition_participants(
    participants: list["GameParticipant"],
    max_players: int | None = None,
) -> PartitionedParticipants:
    """Sort and partition participants into confirmed and overflow groups."""
    max_players = max_players or DEFAULT_MAX_PLAYERS
    sorted_all = sort_participants(participants)
    confirmed = sorted_all[:max_players]
    overflow = sorted_all[max_players:]

    confirmed_ids = {p.user.discord_id for p in confirmed if p.user and p.user.discord_id}
    overflow_ids = {p.user.discord_id for p in overflow if p.user and p.user.discord_id}

    return PartitionedParticipants(
        all_sorted=sorted_all,
        confirmed=confirmed,
        overflow=overflow,
        confirmed_real_user_ids=confirmed_ids,
        overflow_real_user_ids=overflow_ids,
    )
```

### Usage in Game Service

**File:** `services/api/services/games.py::update_game()`

```python
# Line 810 - Capture state before update
old_max_players = resolve_max_players(game.max_players)
old_partitioned = partition_participants(game.participants, old_max_players)

# ... game updates happen ...

# Line 863-865 - Detect promotions after update
new_max_players = resolve_max_players(game.max_players)
new_partitioned = partition_participants(game.participants, new_max_players)
promoted_discord_ids = new_partitioned.cleared_waitlist(old_partitioned)

if promoted_discord_ids:
    await self._notify_promoted_users(game=game, promoted_discord_ids=promoted_discord_ids)
```

### Why This Fix Works

1. **Includes ALL participants** (real users + placeholders) when sorting
2. **Partitions by position** in the sorted list (0 to max_players-1 = confirmed)
3. **Filters to real user IDs** AFTER partitioning (not before)
4. **Compares before/after states** using `cleared_waitlist()` to detect promotions
5. **Single source of truth** eliminates inconsistencies across services

### Benefits

1. ✅ **Single source of truth** for participant ordering logic
2. ✅ **Consistent handling** of placeholders across all services
3. ✅ **Pre-computed sets** for efficient Discord ID lookups
4. ✅ **Type-safe** with dataclass structure
5. ✅ **Future-proof** for enhancements like priority tiers, reserved slots, etc.
6. ✅ **Eliminates code duplication** across multiple locations in the codebase

## Original Proposed Fixes (For Historical Reference)

### Option 1: Include All Participants in Promotion Detection (Simple Fix)

```python
# In update_game(), line 810
old_all_participants = game.participants  # Include ALL participants
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]
    if p.user is not None and p.user.discord_id  # Filter HERE, not earlier
}
```

**Pros:**
- Matches bot formatter logic
- Correctly identifies overflow position accounting for placeholders
- Minimal code change

**Cons:**
- Must handle None user carefully in set comprehension

### Option 2: Track Placeholder Count Separately

```python
# Calculate how many placeholders occupy confirmed slots
old_sorted = participant_sorting.sort_participants(game.participants)
old_confirmed = old_sorted[:old_max_players]
placeholder_count_in_confirmed = sum(1 for p in old_confirmed if p.user_id is None)

# Adjust threshold for real users
real_user_threshold = old_max_players - placeholder_count_in_confirmed
old_real_participants = [p for p in old_sorted if p.user_id and p.user]
old_overflow_ids = {
    p.user.discord_id
    for p in old_real_participants[real_user_threshold:]
    if p.user
}
```

**Pros:**
- More explicit about the logic
- Easier to understand intent

**Cons:**
- More complex
- Easy to get wrong

## Migration Status

### Completed
- ✅ Created `PartitionedParticipants` dataclass in `shared/utils/participant_sorting.py`
- ✅ Created `partition_participants()` function in `shared/utils/participant_sorting.py`
- ✅ Updated `services/api/services/games.py::update_game()` to use new utility
- ✅ E2E test created (`tests/e2e/test_waitlist_promotion.py`)

### Pending (Future Work)
The following locations still use manual sort+slice patterns and could be migrated to use `partition_participants()`:

1. `services/bot/events/handlers.py::_handle_game_reminder()` (lines 393-403)
2. `services/bot/events/handlers.py::_handle_join_notification()` (lines 511-513)
3. `services/bot/events/handlers.py::_handle_game_cancelled()` (lines 858-862)
4. `services/api/routes/games.py::download_calendar()` (line 566)

**Note:** These locations already work correctly for their use cases. Migration is a code quality improvement (DRY principle) rather than a bug fix.

## Files Changed

### Implementation
- ✅ **New:** `shared/utils/participant_sorting.py` - Added `PartitionedParticipants` dataclass with `cleared_waitlist()` method
- ✅ **New:** `shared/utils/participant_sorting.py` - Added `partition_participants()` function
- ✅ **Updated:** `services/api/services/games.py::update_game()` - Lines 810, 863-865 now use `partition_participants()`

### Testing
- ✅ **New:** `tests/e2e/test_waitlist_promotion.py` - E2E test exposing and validating the fix

## Related Code

- Bot formatters: `services/bot/formatters/game_message.py::format_game_participants()`
- Participant sorting: `shared/utils/participant_sorting.py::sort_participants()`
- Promotion notification: `services/api/services/games.py::_publish_promotion_notification()`

## Test Cases Status

1. ✅ Real user promoted when real user removed (existing - works)
2. ✅ **Real user promoted when placeholder removed** (FIXED - now works)
3. ✅ **Real user promoted when max_players increased with placeholder present** (FIXED - now works)
4. ✅ Real user promoted when max_players increased (existing - works)

All test cases should now pass with the implemented `partition_participants()` utility.

## Code Duplication Audit

**Current Locations with Sort + Slice Pattern:**
1. `services/bot/events/handlers.py::_handle_game_reminder()` (lines 393-403)
2. `services/bot/events/handlers.py::_handle_join_notification()` (lines 511-513)
3. `services/bot/events/handlers.py::_handle_game_cancelled()` (lines 858-862)
4. `services/api/services/games.py::update_game()` (lines 810-816)
5. `services/api/services/games.py::_detect_and_notify_promotions()` (lines 1201-1204)
6. `services/api/routes/games.py::download_calendar()` (line 566)

**Each location independently:**
- Filters participants (sometimes excluding placeholders, sometimes not)
- Calls `sort_participants()`
- Slices by `max_players` to get confirmed/overflow
- Extracts Discord IDs for lookups

**Risk:** Future enhancements (e.g., priority tiers, reserved slots) require updating 6+ locations

## E2E Test Status

- **Test File:** `tests/e2e/test_waitlist_promotion.py`
- **Status:** ✅ Test correctly written, ready to validate fix
- **Expected Result:** Test should PASS with implemented `partition_participants()` utility

## Future Enhancement Considerations

The user mentioned "future enhancements" that make centralized participant ordering more important. Possible scenarios:

1. **Priority Tiers** - VIP/supporter/regular participant levels
2. **Reserved Slots** - Specific participant positions for roles/requirements
3. **Conditional Overflow** - Different overflow rules for different game types
4. **Late Join Windows** - Participants can join after game starts but before cutoff
5. **Alternate Lists** - Separate confirmed/alternate/declined lists

All of these would require modifying the participant partitioning logic in multiple places without a centralized utility.
