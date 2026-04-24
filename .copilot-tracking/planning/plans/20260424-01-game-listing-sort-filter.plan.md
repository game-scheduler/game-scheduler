---
applyTo: '.copilot-tracking/changes/20260424-01-game-listing-sort-filter-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Listing Sort and Filter

## Overview

Add multi-status filtering and status-group sort order to the game listing API and frontend
views, hiding ARCHIVED games from normal views.

## Objectives

- Hide ARCHIVED games from `MyGames` and `BrowseGames` "ALL" views
- Sort listed games: SCHEDULED (soonest first) → IN_PROGRESS → COMPLETED (most recently ended
  first) → CANCELLED
- Support `?status=X&status=Y` repeated query params in backend and frontend
- Add `'ARCHIVED'` to the TypeScript `GameSession.status` union type

## Research Summary

### Project Files

- `services/api/services/games.py` — `list_games` service with single-status filter and ASC sort
- `services/api/routes/games.py` — `list_games` route accepting a single `status` string
- `frontend/src/api/client.ts` — axios client missing `paramsSerializer`
- `frontend/src/types/index.ts` — `GameSession.status` union missing `'ARCHIVED'`
- `frontend/src/pages/MyGames.tsx` — passes no status filter; receives ARCHIVED games
- `frontend/src/pages/BrowseGames.tsx` — passes single status string; ALL passes nothing
- `tests/unit/api/services/test_games.py` — unit tests for `list_games` service
- `tests/integration/test_games_route_guild_isolation.py` — integration tests using `status="SCHEDULED"`
- `frontend/src/pages/__tests__/BrowseGames.test.tsx` — frontend tests for BrowseGames

### External References

- #file:../research/20260424-01-game-listing-sort-filter-research.md — complete analysis with
  code examples for all changes

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python TDD, type hints, Ruff conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — RED→GREEN→REFACTOR workflow
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md — FastAPI query param patterns

## Implementation Checklist

### [x] Phase 1: TDD RED — Backend Service Tests

- [x] Task 1.1: Write xfail unit tests for multi-status list param filtering
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 11-34)

- [x] Task 1.2: Write xfail unit test for Python-side sort order
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 35-51)

- [x] Task 1.3: Confirm all new tests show as `xfail`
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 52-63)

### [x] Phase 2: Backend Service Implementation (GREEN)

- [x] Task 2.1: Change `status` param to `list[str] | None` and use `.in_()` filter
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 67-83)

- [x] Task 2.2: Add `_STATUS_ORDER`, `_game_sort_key`, and apply Python sort
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 84-106)

- [x] Task 2.3: Remove SQL `ORDER BY scheduled_at ASC` clause
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 107-120)

- [x] Task 2.4: Remove xfail markers; verify all service tests pass
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 121-133)

### [x] Phase 3: Backend Route Update

- [x] Task 3.1: Change route `status` param to `list[str] | None` with `Query()`
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 137-153)

### [x] Phase 4: TDD RED — Frontend Tests

- [x] Task 4.1: Update `BrowseGames.test.tsx` to expect `status` as array
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 156-175)

### [x] Phase 5: Frontend Implementation (GREEN)

- [x] Task 5.1: Add `paramsSerializer` to `frontend/src/api/client.ts`
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 178-211)

- [x] Task 5.2: Add `'ARCHIVED'` to `GameSession.status` union in `frontend/src/types/index.ts`
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 212-225)

- [x] Task 5.3: Update `MyGames.tsx` to pass explicit non-archived status list
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 226-240)

- [x] Task 5.4: Update `BrowseGames.tsx` to wrap status in list; ALL → non-archived list
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 241-259)

### [x] Phase 6: Integration Test Updates

- [x] Task 6.1: Update `test_games_route_guild_isolation.py` to use list form
  - Details: .copilot-tracking/planning/details/20260424-01-game-listing-sort-filter-details.md (Lines 262-279)

## Dependencies

- No database migration required
- `uv` for Python package management
- `npm` / Vitest for frontend testing

## Success Criteria

- `MyGames` shows no ARCHIVED games; SCHEDULED before COMPLETED; soonest first, most recently ended first
- `BrowseGames` "ALL" shows no ARCHIVED games
- `?status=SCHEDULED&status=COMPLETED` returns only those two statuses
- No status param returns all (including ARCHIVED)
- All unit tests pass: `uv run pytest tests/unit/`
- Integration tests pass for `test_games_route_guild_isolation.py`
- All frontend tests pass: `npm run test`
