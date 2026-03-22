---
applyTo: '.copilot-tracking/changes/20260322-01-archive-reward-player-mentions-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Archive Player @mentions for Reward Games

## Overview

When a game with rewards is archived to an archive channel, @mention the confirmed players
(not waitlisted, not roles) in the archive post content.

## Objectives

- Discard role-mention content from archive posts entirely
- Build player @mentions from confirmed real user IDs when `game.rewards` is set
- Send `content=None` when rewards are not set or no confirmed players exist
- All existing and new tests pass with no overrides

## Research Summary

### Project Files

- `services/bot/events/handlers.py` — `_archive_game_announcement` (~line 1256) is the production target
- `services/bot/formatters/game_message.py` — `format_game_announcement` builds existing role-mention content
- `shared/utils/participant_sorting.py` — `partition_participants` returns `.confirmed_real_user_ids`
- `tests/unit/bot/events/test_handlers_misc.py` — unit test target for new tests (lines 410–460 for existing error paths)
- `tests/unit/services/bot/events/test_handlers.py` — existing archive test to update (lines 616–751)
- `tests/e2e/test_game_rewards.py` — e2e target: `test_save_and_archive_archives_game_within_seconds` (line 108)

### External References

- #file:../research/20260322-01-archive-reward-player-mentions-research.md — full analysis, code examples, test patterns

### Standards References

- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/python.instructions.md — Python conventions

## Implementation Checklist

### [x] Phase 1: Write Failing Tests (TDD RED Phase)

- [x] Task 1.1: Add four xfail unit tests to `test_handlers_misc.py`
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 11–37)

- [x] Task 1.2: Mark existing archive test as xfail in `test_handlers.py`
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 38–59)

- [x] Task 1.3: Modify e2e test to add player mention assertion (xfail)
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 60–87)

- [x] Task 1.4: Run unit tests to confirm RED / xfail state
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 88–100)

### [ ] Phase 2: Implement Production Code (TDD GREEN Phase)

- [ ] Task 2.1: Implement player @mention logic in `_archive_game_announcement`
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 104–142)

### [ ] Phase 3: Clean Up and Verify (TDD REFACTOR Phase)

- [ ] Task 3.1: Remove xfail markers and fix existing test assertion
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 146–172)

- [ ] Task 3.2: Run full unit test suite and confirm all pass
  - Details: .copilot-tracking/planning/details/20260322-01-archive-reward-player-mentions-details.md (Lines 173–182)

## Dependencies

- `partition_participants` (already imported in `handlers.py`)
- Discord `message.content` — surfaces raw mention strings `<@user_id>` via discord.py

## Success Criteria

- Archive post `content` = space-separated `<@uid>` for confirmed players when rewards are set
- No role mentions in archive post under any condition
- Waitlist and placeholder participants are NOT mentioned
- `content=None` when rewards not set or no confirmed players
- All existing and new tests pass without overrides
