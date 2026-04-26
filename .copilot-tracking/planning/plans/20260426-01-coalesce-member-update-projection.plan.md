---
applyTo: '.copilot-tracking/changes/20260426-01-coalesce-member-update-projection-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: coalesce-member-update-projection

## Overview

Replace the direct `repopulate_all` calls in the three member-event handlers with an
`asyncio.Event`-based coalescing worker that caps rebuilds at one per 60 seconds.

## Objectives

- Eliminate redundant full projection rebuilds when Discord fires batched `member_update`
  events on reconnect/resume
- Preserve accurate per-event-type trigger counts in the existing "Repopulation Rate by
  Reason" dashboard panel
- Simplify the duration and member-count histogram panels to a single unlabelled series

## Research Summary

### Project Files

- `services/bot/bot.py` — `GameSchedulerBot` with `on_member_add/update/remove`, `on_ready`, `setup_hook`, and `_projection_heartbeat` (canonical background-task pattern)
- `services/bot/guild_projection.py` — `repopulate_all` function with `reason` param and all three OTEL metrics
- `tests/unit/bot/test_guild_projection.py` — existing `TestRepopulateAll` test class with 8 call sites passing `reason=`

### External References

- #file:../research/20260426-01-coalesce-member-update-projection-research.md — verified findings, recommended design, and implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/unit-tests.instructions.md — unit test quality

## Implementation Checklist

### [ ] Phase 1: TDD RED — write xfail tests for new worker and updated signatures

- [ ] Task 1.1: Create `tests/unit/bot/test_bot_member_event_worker.py` with xfail tests for worker coalescing, cooldown, and on_ready path
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 11–35)

- [ ] Task 1.2: Add xfail tests to `TestRepopulateAll` in `test_guild_projection.py` for the signature-without-reason and no-counter-inside-function behaviors
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 36–56)

### [ ] Phase 2: Update `repopulate_all` signature and all callers

- [ ] Task 2.1: Remove `reason` param, counter call, and `{"reason": reason}` labels from `repopulate_all` in `guild_projection.py`
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 60–82)

- [ ] Task 2.2: Update `on_ready` to emit the started counter before calling `repopulate_all`; drop `reason=` from all four call sites in `bot.py`
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 83–103)

- [ ] Task 2.3: Remove `reason=` from all 8 call sites in `test_guild_projection.py`, update the metrics test, and remove xfail from Phase 1 guild_projection tests
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 105–122)

### [ ] Phase 3: Add `_member_event_worker` and replace member event handlers

- [ ] Task 3.1: Initialize `self._member_event = asyncio.Event()` in `GameSchedulerBot.__init__`
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 126–142)

- [ ] Task 3.2: Add `_member_event_worker` async method to `GameSchedulerBot`
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 143–169)

- [ ] Task 3.3: Start worker task in `setup_hook` with `hasattr` guard
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 171–188)

- [ ] Task 3.4: Replace `on_member_add`, `on_member_update`, `on_member_remove` to emit counter + `self._member_event.set()`
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 190–218)

- [ ] Task 3.5: Remove xfail markers from worker tests and confirm full suite passes
  - Details: .copilot-tracking/planning/details/20260426-01-coalesce-member-update-projection-details.md (Lines 220–233)

## Dependencies

- Python `asyncio` stdlib — no new third-party packages
- `pytest-asyncio` — already present in the test suite

## Success Criteria

- A burst of N `on_member_update` calls produces exactly N counter increments and exactly 1 `repopulate_all` call
- `on_ready` still triggers an immediate `repopulate_all` with the counter emitted before it
- `repopulate_all` accepts only `bot` and `redis`; duration and member-count histograms carry no labels
- Full unit test suite passes at every phase boundary
