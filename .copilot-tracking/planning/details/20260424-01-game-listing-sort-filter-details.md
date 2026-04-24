<!-- markdownlint-disable-file -->

# Task Details: Game Listing Sort and Filter

## Research Reference

**Source Research**: #file:../research/20260424-01-game-listing-sort-filter-research.md

## Phase 1: TDD RED — Backend Service Tests

### Task 1.1: Write xfail unit tests for multi-status list param filtering

Add new test methods to `TestListGames` in `tests/unit/api/services/test_games.py` that assert
the service correctly accepts a list of status strings. Mark each with
`@pytest.mark.xfail(strict=True, reason="list_games does not yet accept list[str] status")`.
Run to confirm they show as `xfail`.

Test cases to add:

- `test_list_games_multi_status_filter`: call with `status=["SCHEDULED", "COMPLETED"]`, assert
  only those two statuses are returned
- `test_list_games_single_status_as_list`: call with `status=["SCHEDULED"]`, assert only
  SCHEDULED games returned

- **Files**:
  - `tests/unit/api/services/test_games.py` — add xfail test methods to `TestListGames`
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py::TestListGames::test_list_games_multi_status_filter` shows `XFAIL`
  - `uv run pytest tests/unit/api/services/test_games.py::TestListGames::test_list_games_single_status_as_list` shows `XFAIL`
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 83-105) — multi-status API change spec with exact code
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 160-168) — integration test update notes
- **Dependencies**:
  - None

### Task 1.2: Write xfail unit test for Python-side sort order

Add a sort-order test to `TestListGames`. Create games with statuses COMPLETED, SCHEDULED,
CANCELLED, IN_PROGRESS and varied `scheduled_at` timestamps. Assert the returned list is
ordered: SCHEDULED (soonest first) → IN_PROGRESS → COMPLETED (most recently ended first,
descending `scheduled_at`) → CANCELLED. Mark
`@pytest.mark.xfail(strict=True, reason="list_games does not yet apply Python-side sort")`.

- **Files**:
  - `tests/unit/api/services/test_games.py` — add `test_list_games_sort_order` to `TestListGames`
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py::TestListGames::test_list_games_sort_order` shows `XFAIL`
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 133-157) — `_STATUS_ORDER` dict and `_game_sort_key` design
- **Dependencies**:
  - None

### Task 1.3: Confirm all new tests show as `xfail`

Run the full `TestListGames` suite to confirm only the newly added tests are `xfail` and that
all existing tests still pass.

- **Files**: none (verification only)
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py -v` — new tests show `XFAIL`, existing tests show `PASSED`
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md — TDD RED phase verification requirement
- **Dependencies**:
  - Tasks 1.1 and 1.2

## Phase 2: Backend Service Implementation (GREEN)

### Task 2.1: Change `status` param to `list[str] | None` and use `.in_()` filter

In `services/api/services/games.py`, change the `list_games` method signature from
`status: str | None = None` to `status: list[str] | None = None`. Replace the equality filter
`game_model.GameSession.status == status` with `game_model.GameSession.status.in_(status)`
for both the main query and the count query.

- **Files**:
  - `services/api/services/games.py` — `list_games` method (lines 999–1057 per research)
- **Success**:
  - `test_list_games_multi_status_filter` shows `PASSED`
  - `test_list_games_single_status_as_list` shows `PASSED`
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 83-105) — exact signature and `.in_()` usage
- **Dependencies**:
  - Phase 1 completed

### Task 2.2: Add `_STATUS_ORDER`, `_game_sort_key`, and apply Python sort

Add a module-level `_STATUS_ORDER` dict mapping `GameStatus` enum values to integer ranks.
Add a module-level `_game_sort_key` function returning `(rank, ts)` where `ts` is negated for
COMPLETED and CANCELLED. After the DB fetch in `list_games`, wrap the scalar result in
`sorted(..., key=_game_sort_key)`.

Sort specification:

- SCHEDULED → rank 0, ascending `scheduled_at` (soonest first)
- IN_PROGRESS → rank 1, ascending `scheduled_at`
- COMPLETED → rank 2, descending `scheduled_at` (negate `ts`)
- CANCELLED → rank 3, descending `scheduled_at` (negate `ts`)
- ARCHIVED → rank 4

- **Files**:
  - `services/api/services/games.py` — add `_STATUS_ORDER` and `_game_sort_key` at module level; update `list_games` return
- **Success**:
  - `test_list_games_sort_order` shows `PASSED`
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 133-157) — `_STATUS_ORDER` and `_game_sort_key` implementation
- **Dependencies**:
  - Task 2.1

### Task 2.3: Remove SQL `ORDER BY scheduled_at ASC` clause

Remove the `.order_by(game_model.GameSession.scheduled_at.asc())` call from the query in
`list_games`. The Python sort supersedes it; retaining it is misleading and wasteful.

- **Files**:
  - `services/api/services/games.py` — remove `order_by` clause from `list_games` query
- **Success**:
  - All unit tests still pass after removal
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 133-160) — rationale: Python sort supersedes DB ordering
- **Dependencies**:
  - Task 2.2

### Task 2.4: Remove xfail markers; verify all service tests pass

Remove the `@pytest.mark.xfail` decorators from all test methods added in Phase 1. Run the
full unit test suite to confirm no regressions.

- **Files**:
  - `tests/unit/api/services/test_games.py` — remove xfail markers from Phase 1 tests
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py -v` — all tests show `PASSED`
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md — GREEN phase: remove xfail markers
- **Dependencies**:
  - Tasks 2.1, 2.2, 2.3

## Phase 3: Backend Route Update

### Task 3.1: Change route `status` param to `list[str] | None` with `Query()`

In `services/api/routes/games.py`, change the `list_games` route parameter from
`status: Annotated[str | None, Query(...)] = None` to
`status: Annotated[list[str] | None, Query(description="Filter by status")] = None`.
FastAPI natively handles repeated query params (`?status=SCHEDULED&status=COMPLETED`) with
`list[str]`.

- **Files**:
  - `services/api/routes/games.py` — `list_games` route handler (lines 414–428 per research)
- **Success**:
  - `?status=SCHEDULED&status=COMPLETED` accepted and forwarded to service as `["SCHEDULED", "COMPLETED"]`
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 106-115) — route param change
- **Dependencies**:
  - Phase 2 completed

## Phase 4: TDD RED — Frontend Tests

### Task 4.1: Update `BrowseGames.test.tsx` to expect `status` as array

In `frontend/src/pages/__tests__/BrowseGames.test.tsx`, update mock expectations for the
`status` param from a string to an array:

- For a specific status selected (e.g. `'SCHEDULED'`): expect `status: ['SCHEDULED']`
- For "ALL" selected: expect `status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']`

TypeScript/Vitest tests do not use `xfail` markers. Update expectations first so tests fail
(RED), then implement `BrowseGames.tsx` in Phase 5 to make them pass (GREEN).

- **Files**:
  - `frontend/src/pages/__tests__/BrowseGames.test.tsx` — update `status` mock expectations to array form
- **Success**:
  - `npm run test -- BrowseGames` shows test failures (RED phase confirmed)
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 118-130) — expected array form for BrowseGames
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 156-168) — BrowseGames frontend changes summary
- **Dependencies**:
  - None (can proceed in parallel with Phase 3)

## Phase 5: Frontend Implementation (GREEN)

### Task 5.1: Add `paramsSerializer` to `frontend/src/api/client.ts`

Add a `paramsSerializer` config to the `axios.create()` call. Iterate params entries and
append array values individually to a `URLSearchParams` instance, producing repeated
`?key=val1&key=val2` syntax instead of bracket notation. No external library needed.

Implementation from research:

```typescript
paramsSerializer: {
  serialize: (params) => {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (Array.isArray(value)) {
        for (const v of value) {
          searchParams.append(key, String(v));
        }
      } else if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    }
    return searchParams.toString();
  },
},
```

- **Files**:
  - `frontend/src/api/client.ts` — add `paramsSerializer` to `axios.create()`
- **Success**:
  - Arrays serialize as `status=SCHEDULED&status=COMPLETED` not `status[]=SCHEDULED&status[]=COMPLETED`
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 100-116) — `paramsSerializer` implementation
- **Dependencies**:
  - None

### Task 5.2: Add `'ARCHIVED'` to `GameSession.status` union in `frontend/src/types/index.ts`

At line 104 of `frontend/src/types/index.ts`, extend the `status` field union from
`'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'` to include `| 'ARCHIVED'`.

- **Files**:
  - `frontend/src/types/index.ts` — line 104, add `| 'ARCHIVED'` to status union
- **Success**:
  - TypeScript compilation passes; no TS errors for ARCHIVED status handling
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 22-24) — missing `'ARCHIVED'` in type union
- **Dependencies**:
  - None

### Task 5.3: Update `MyGames.tsx` to pass explicit non-archived status list

In `frontend/src/pages/MyGames.tsx`, where the API call constructs its params object, pass
`status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']` explicitly instead of
omitting the status param entirely.

- **Files**:
  - `frontend/src/pages/MyGames.tsx` — add explicit `status` array to API call params
- **Success**:
  - ARCHIVED games no longer appear in the `MyGames` view
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 116-118) — MyGames explicit status list
- **Dependencies**:
  - Task 5.1 (paramsSerializer must be in place to serialize the array correctly)

### Task 5.4: Update `BrowseGames.tsx` to wrap status in list; ALL → non-archived list

In `frontend/src/pages/BrowseGames.tsx`, update the params construction in the API call:

- Specific status selected: pass `status: [selectedStatus]`
- "ALL" selected: pass `status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']`

Do not add ARCHIVED to the dropdown; the UI options (ALL, SCHEDULED, IN_PROGRESS, COMPLETED,
CANCELLED) remain unchanged. ARCHIVED is intentionally excluded from the filter UI.

- **Files**:
  - `frontend/src/pages/BrowseGames.tsx` — update `params` construction in the games API call
- **Success**:
  - Phase 4 `BrowseGames.test.tsx` tests now pass (GREEN)
  - `BrowseGames` "ALL" view shows no ARCHIVED games
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 118-130) — BrowseGames status list changes
- **Dependencies**:
  - Task 5.1, Task 4.1

## Phase 6: Integration Test Updates

### Task 6.1: Update `test_games_route_guild_isolation.py` to use list form

In `tests/integration/test_games_route_guild_isolation.py`, update all calls that pass
`status="SCHEDULED"` (string) to `status=["SCHEDULED"]` (list). The test HTTP client
forwards this as a repeated query param matching the updated route signature.

- **Files**:
  - `tests/integration/test_games_route_guild_isolation.py` — all `status="SCHEDULED"` → `status=["SCHEDULED"]`
- **Success**:
  - `scripts/run-integration-tests.sh tests/integration/test_games_route_guild_isolation.py` passes
- **Research References**:
  - #file:../research/20260424-01-game-listing-sort-filter-research.md (Lines 58-62) — code search confirming `status="SCHEDULED"` callers
- **Dependencies**:
  - Phase 3 completed (route must accept list form)

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
