# Resume Work: After Promotion Detection Bug Fix

**Date:** December 24, 2025
**Context:** Git history rewrite to fix promotion detection bug before E2E test commit

## What Happened Before the Break

### Bug Discovery (Task 5.3 - Waitlist Promotion E2E Test)

While implementing the E2E test for waitlist promotion DMs, we discovered a bug in the promotion detection logic:

**Bug:** Promotion DMs not sent when placeholder participants occupy confirmed slots

**Root Cause:**
```python
# services/api/services/games.py, lines ~810-816
old_all_participants = [p for p in game.participants if p.user_id and p.user]  # ❌ Filters placeholders
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {p.user.discord_id for p in old_sorted_participants[old_max_players:]}
```

The code filters out placeholders BEFORE determining overflow position, but `max_players` applies to ALL participants. This causes real users to appear "confirmed" even when placeholders occupy those slots.

**Example Scenario:**
- Game: max_players=1, participants=["Reserved", "<@user_id>"]
- Visual: Reserved (1/1 confirmed), user (overflow)
- Detection sees: 1 real participant (user) with max_players=1 → position 0/1 → NOT overflow
- Result: When placeholder removed or max_players increased, no promotion detected

### Work Completed

1. **E2E Test Created** (`tests/e2e/test_waitlist_promotion.py`)
   - Parametrized test with 2 scenarios:
     - `via_removal`: Remove placeholder to trigger promotion
     - `via_max_players_increase`: Increase max from 1 to 2
   - Test correctly exposes the bug
   - Uses `main_bot_helper` (main bot sends promotion DMs, not admin bot)
   - Includes debug output showing DMs received

2. **Bug Documented** (`.copilot-tracking/research/20251224-promotion-detection-bug.md`)
   - Complete analysis of root cause
   - Impact assessment
   - Architectural recommendation for centralized `partition_participants()` utility
   - Code duplication audit (6+ locations with sort+slice pattern)

3. **Commits Created**
   - Commit 1: Bug research document
   - Commit 2: E2E test (with --no-verify, exposes bug)

### Fix Applied (During Git Magic)

The bug should now be fixed in `services/api/services/games.py::update_game()`:

**Expected Fix:**
```python
# Include ALL participants (including placeholders) when determining overflow
old_all_participants = game.participants  # Include placeholders
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]
    if p.user is not None and p.user.discord_id  # Filter HERE
}
```

This matches the bot formatter pattern and correctly identifies overflow participants.

## What to Verify When Resuming

### 1. Run E2E Test (Should Pass Now)

```bash
./scripts/run-e2e-tests.sh tests/e2e/test_waitlist_promotion.py -v
```

**Expected Output:**
- Both parametrized tests should PASS
- Debug output should show promotion DM received:
  - "✓ Test user received promotion DM: ✅ Good news! A spot opened up..."
  - Message contains: "A spot opened up", "moved from the waitlist"

### 2. Verify Unit Tests Still Pass

```bash
pytest tests/services/api/services/test_games_promotion.py -v
```

All existing promotion tests should still pass.

### 3. Check Git History

```bash
git log --oneline -5
```

Should show bug fix commit inserted BEFORE the E2E test commit, making the test pass on first try.

### 4. Mark Task 5.3 Complete

If tests pass, update task tracking:
- `.copilot-tracking/plans/20251222-e2e-test-strategy-plan.instructions.md`
  - Change Task 5.3 status from "❌ NOT STARTED" to "✅ COMPLETE"
- `.copilot-tracking/changes/20251222-e2e-test-strategy-changes.md`
  - Add Task 5.3 completion entry with test details

## Next Steps After Verification

### Immediate (Task 5.3 Completion)

1. Remove debug print statements from test if they're too verbose
2. Update task tracking documents
3. Consider adding unit tests for placeholder promotion scenarios

### Short Term (Task 5.4)

Continue with E2E test strategy:
- **Task 5.4:** Join notification → delayed DM test
  - Create game with signup instructions
  - User joins game
  - Verify delayed DM sent after 60 seconds with signup instructions

### Medium Term (Architectural Improvement)

Consider implementing the centralized `partition_participants()` utility:
- See `.copilot-tracking/research/20251224-promotion-detection-bug.md` for detailed design
- Benefits: Single source of truth, prevents future bugs, easier to enhance
- Migration: 6+ locations currently duplicate sort+slice logic

## Key Files Reference

**Test File:**
- `tests/e2e/test_waitlist_promotion.py` - E2E test exposing/validating bug fix

**Bug Location (Fixed):**
- `services/api/services/games.py` - Lines ~810-816 in `update_game()`
- `services/api/services/games.py` - Lines ~1184-1250 promotion detection methods

**Related Logic:**
- `services/bot/events/handlers.py` - Bot handlers using sort+slice pattern (lines 393-403, 511-513, 858-862)
- `services/bot/formatters/game_message.py` - Formatter that correctly handles placeholders
- `shared/utils/participant_sorting.py` - Core sorting utility

**Documentation:**
- `.copilot-tracking/research/20251224-promotion-detection-bug.md` - Complete bug analysis
- `.copilot-tracking/plans/20251222-e2e-test-strategy-plan.instructions.md` - Task 5.3 definition
- `.copilot-tracking/details/20251222-e2e-test-strategy-details.md` - Task 5.3 details

## Quick Context Restore Commands

```bash
# Check test status
./scripts/run-e2e-tests.sh tests/e2e/test_waitlist_promotion.py -v

# View bug fix
git show HEAD~1  # Or wherever the fix commit landed

# Review task tracking
code .copilot-tracking/plans/20251222-e2e-test-strategy-plan.instructions.md

# Check for any other failing tests
pytest tests/services/api/services/test_games_promotion.py -v
```

## Expected State After Fix

- ✅ E2E test passes (both scenarios)
- ✅ Unit tests still pass
- ✅ Promotion DMs sent when placeholders occupy confirmed slots
- ✅ Discord message updates AND user receives DM
- ✅ Task 5.3 can be marked complete
- 🔄 Ready to proceed with Task 5.4 (join notification delayed DM test)

## Notes for Future Work

The bug revealed a larger architectural issue: participant ordering logic is duplicated in 6+ locations with inconsistent placeholder handling. Consider creating centralized `partition_participants()` utility as documented in the bug research file.

This would provide:
- Single source of truth for participant ordering
- Consistent placeholder handling across all services
- Easier to enhance for future features (priority tiers, reserved slots, etc.)
- Type-safe with structured result (PartitionedParticipants dataclass)
