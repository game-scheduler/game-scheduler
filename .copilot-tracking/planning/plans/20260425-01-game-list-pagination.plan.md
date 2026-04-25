---
applyTo: '.copilot-tracking/changes/20260425-01-game-list-pagination-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game List Pagination

## Overview

Add server-side pagination to the game list API and wire up MUI `Pagination` controls in the BrowseGames and MyGames frontend pages, replacing unbounded full-table fetches with 25-game pages.

## Objectives

- Bound every `/api/v1/games` response to ≤25 games per request
- Expose `limit` and `offset` in `GameListResponse` so the frontend can compute page counts
- Add `role` filter (`host` | `participant`) to the service and route so MyGames can request only the games the user hosts or only the games they have joined
- Fix the `total` field in the response to reflect the DB pre-authorization count (usable for page-count math) instead of `len(authorized_games)` on the current page
- Add page navigation controls to BrowseGames and to both tabs of MyGames

## Research Summary

### Project Files

- `shared/schemas/game.py` (line 232) — `GameListResponse` schema; needs `limit` and `offset` added
- `services/api/services/games.py` (line 1016) — `list_games` method; DB count already computed but discarded; needs `role`/`user_id` params and role-filter SQL
- `services/api/routes/games.py` (line 413) — `list_games` route; limit default/max too high; total wrong; no `role` param
- `tests/unit/services/api/services/test_games_service.py` — service tests; no `role` coverage yet
- `tests/unit/services/api/routes/test_games_routes.py` — route tests; five test classes; all need `role=None` and updated response shape
- `frontend/src/types/index.ts` — `GameListResponse` interface; no `limit`/`offset` yet
- `frontend/src/pages/BrowseGames.tsx` — single unbounded fetch; no pagination UI
- `frontend/src/pages/MyGames.tsx` — single unbounded fetch split client-side; no pagination UI
- `frontend/src/pages/__tests__/BrowseGames.test.tsx` — Vitest page tests
- `frontend/src/pages/__tests__/MyGames.test.tsx` — Vitest page tests

### External References

- #file:../research/20260425-01-game-list-pagination-research.md — full research findings

## Implementation Checklist

### [ ] Phase 1: RED — failing Python tests for service role filter

- [ ] Task 1.1: Add xfail tests for `role=host` filter in service tests
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 13-27)

- [ ] Task 1.2: Add xfail tests for `role=participant` filter in service tests
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 28-41)

- [ ] Task 1.3: Verify xfail tests fail as expected (`uv run pytest ... -v`)
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 42-52)

### [ ] Phase 2: GREEN — backend implementation

- [ ] Task 2.1: Add `limit` and `offset` to `GameListResponse` schema
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 57-70)

- [ ] Task 2.2: Add `role`/`user_id` params and role-filter SQL to `list_games` service method; lower default limit to 25
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 71-91)

- [ ] Task 2.3: Add `role` query param to route; lower limit max to 25; fix `total`; pass `limit`/`offset` to response
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 92-113)

- [ ] Task 2.4: Update route unit tests — add `role=None` to existing call sites; update expected response shapes; remove xfail markers from service tests
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 114-132)

- [ ] Task 2.5: Run full unit test suite; confirm all tests pass
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 133-143)

### [ ] Phase 3: RED — failing TypeScript tests for frontend pagination

- [ ] Task 3.1: Add `limit?`/`offset?` optional fields to `GameListResponse` TypeScript interface
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 148-161)

- [ ] Task 3.2: Add `test.failing` tests to `BrowseGames.test.tsx` for pagination control and limit/offset params
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 162-182)

- [ ] Task 3.3: Add `test.failing` tests to `MyGames.test.tsx` for role-split fetches and per-tab pagination
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 183-201)

- [ ] Task 3.4: Verify `test.failing` tests fail as expected (`npm test` in `frontend/`)
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 202-212)

### [ ] Phase 4: GREEN — frontend implementation

- [ ] Task 4.1: Make `limit` and `offset` required in the TypeScript `GameListResponse` interface
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 217-229)

- [ ] Task 4.2: Implement BrowseGames page state, limit/offset params, and Pagination control
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 230-260)

- [ ] Task 4.3: Implement MyGames two-fetch split with per-tab page state and Pagination controls
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 261-284)

- [ ] Task 4.4: Update existing BrowseGames and MyGames mocks to include `limit`/`offset`; remove `test.failing` markers
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 285-306)

- [ ] Task 4.5: Run full frontend test suite; confirm all tests pass
  - Details: .copilot-tracking/planning/details/20260425-01-game-list-pagination-details.md (Lines 307-317)

## Dependencies

- Python: SQLAlchemy subquery pattern (already used in codebase)
- TypeScript: `@mui/material` `Pagination` component (already available)
- No new packages required

## Success Criteria

- Default page load fetches ≤25 games per request
- BrowseGames shows `<Pagination>` control when `total > 25`; channel filter continues to work within the fetched page
- MyGames "Hosting" tab fetches only `role=host` games, paginated independently
- MyGames "Joined" tab fetches only `role=participant` games, paginated independently
- `total` in the response reflects the DB pre-authorization count (usable for page count calculation)
- All existing route and service unit tests pass; new tests cover role filter and updated response shape
- All existing frontend page tests pass; new tests cover pagination controls and param passing
