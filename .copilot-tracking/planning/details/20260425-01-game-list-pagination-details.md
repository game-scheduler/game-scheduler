<!-- markdownlint-disable-file -->

# Task Details: Game List Pagination

## Research Reference

**Source Research**: #file:../research/20260425-01-game-list-pagination-research.md

---

## Phase 1: RED — failing Python tests for service role filter

### Task 1.1: Add xfail tests for `role=host` filter in service tests

Add two `@pytest.mark.xfail(strict=True)` tests to `tests/unit/services/api/services/test_games_service.py` that assert the `role=host` filter passes `host_id == user_id` SQL to the query.

- **Files**:
  - `tests/unit/services/api/services/test_games_service.py` — add xfail tests after existing `test_list_games_with_filters`
- **Success**:
  - `uv run pytest tests/unit/services/api/services/test_games_service.py -v` shows new tests as `xfailed`
  - No other tests affected
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 86-107) — Role Filter SQL: exact WHERE clauses for `role=host`
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 125-175) — Recommended service signature and params
- **Dependencies**:
  - None (existing test file)

### Task 1.2: Add xfail tests for `role=participant` filter in service tests

Add two `@pytest.mark.xfail(strict=True)` tests asserting the `role=participant` filter uses a `game_session_id IN (subquery)` + `host_id != user_id` WHERE clause.

- **Files**:
  - `tests/unit/services/api/services/test_games_service.py` — add after role=host xfail tests
- **Success**:
  - Both new participant tests show as `xfailed`
  - Existing tests still pass
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 86-107) — Role Filter SQL: exact WHERE clauses for `role=participant`
- **Dependencies**:
  - Task 1.1 completion (use same test structure)

### Task 1.3: Verify xfail tests fail as expected

Run the service test file in isolation and confirm output shows `xfailed`, not `passed` or `failed`.

- **Files**: none — verification only
- **Success**:
  - `uv run pytest tests/unit/services/api/services/test_games_service.py -v` output includes `XFAIL` for each new test
- **Research References**: none
- **Dependencies**:
  - Tasks 1.1 and 1.2 complete

---

## Phase 2: GREEN — backend implementation

### Task 2.1: Add `limit` and `offset` to `GameListResponse` schema

Update `shared/schemas/game.py` to add `limit: int` and `offset: int` as required fields to `GameListResponse`.

- **Files**:
  - `shared/schemas/game.py` (line 232) — `GameListResponse` class; add two `Field(...)` entries
- **Success**:
  - `GameListResponse` has `limit: int` and `offset: int` fields
  - `uv run python -c "from shared.schemas.game import GameListResponse"` succeeds
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 125-140) — Exact Pydantic field definitions with descriptions
- **Dependencies**:
  - None

### Task 2.2: Add `role`/`user_id` params and role-filter SQL to service; lower default limit

Update `services/api/services/games.py` `list_games` method (line 1016):

1. Add `role: str | None = None` and `user_id: str | None = None` parameters
2. Lower the `limit` default from 50 to 25
3. After existing guild/channel/status filters, add the role filter block:
   - `role == "host"`: add `game_model.GameSession.host_id == user_id` WHERE to both `query` and `count_query`
   - `role == "participant"`: build a subquery on `GameParticipant.game_session_id` WHERE `user_id == user_id`; add `id.in_(subquery)` and `host_id != user_id` to both `query` and `count_query`

- **Files**:
  - `services/api/services/games.py` (line 1016) — `list_games` method signature and filter block
- **Success**:
  - Service signature includes `role` and `user_id`
  - Unit tests still import cleanly (`uv run python -c "from services.api.services.games import GameService"`)
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 86-107) — Role Filter SQL
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 141-175) — Full recommended service signature and role block
- **Dependencies**:
  - Task 2.1 (schema must accept `limit`/`offset`)

### Task 2.3: Add `role` query param to route; lower limit; fix `total`; pass `limit`/`offset`

Update `services/api/routes/games.py` `list_games` route (line 413):

1. Add `role: Annotated[str | None, Query(description="'host' or 'participant'")] = None`
2. Lower `limit` default to 25 and max to 25 (`ge=1, le=25`)
3. Pass `role=role, user_id=current_user.user.id` to `game_service.list_games()`
4. Capture `games, total = await game_service.list_games(...)` (assign `total` instead of `_total`)
5. Pass `total=total, limit=limit, offset=offset` into `GameListResponse(...)`

- **Files**:
  - `services/api/routes/games.py` (line 413) — `list_games` route function
- **Success**:
  - Route signature includes `role` parameter
  - `total` in response uses the DB pre-auth count, not `len(authorized_games)`
  - `limit` and `offset` echoed back in response
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 72-85) — The `total` Problem explanation
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 176-203) — Recommended route changes with exact code
- **Dependencies**:
  - Tasks 2.1 and 2.2

### Task 2.4: Update route unit tests and remove xfail markers

Update `tests/unit/services/api/routes/test_games_routes.py`:

1. All existing `list_games` mock call-site assertions — add `role=None` to the expected keyword args
2. All `GameListResponse(...)` constructions in test fixtures — add `limit=25, offset=0` (or whatever limit/offset the test uses)
3. Add assertions that the response body contains `limit` and `offset` fields where not already present
4. Remove `@pytest.mark.xfail` from all four service tests added in Phase 1

- **Files**:
  - `tests/unit/services/api/routes/test_games_routes.py` — five test classes
  - `tests/unit/services/api/services/test_games_service.py` — remove xfail markers
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_games_routes.py tests/unit/services/api/services/test_games_service.py -v` — all pass, no xfailed
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 51-63) — Code Search Results: existing test patterns
- **Dependencies**:
  - Tasks 2.1, 2.2, 2.3

### Task 2.5: Run full unit test suite

Confirm no regressions from backend changes.

- **Files**: none — verification only
- **Success**:
  - `uv run pytest tests/unit/ -v` passes with zero failures
- **Research References**: none
- **Dependencies**:
  - Task 2.4 complete

---

## Phase 3: RED — failing TypeScript tests for frontend pagination

### Task 3.1: Add optional `limit?`/`offset?` to TypeScript `GameListResponse` interface

Add `limit?: number;` and `offset?: number;` to the `GameListResponse` interface in `frontend/src/types/index.ts`. Using optional (`?`) prevents breaking existing test mocks that don't include these fields yet.

- **Files**:
  - `frontend/src/types/index.ts` — `GameListResponse` interface
- **Success**:
  - TypeScript compiles (`npm run build` in `frontend/`) with no new errors
  - Existing test mocks `{ games: [], total: 0 }` still satisfy the type
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 204-215) — Recommended TypeScript interface
- **Dependencies**:
  - Phase 2 complete (backend must serve `limit`/`offset`)

### Task 3.2: Add `test.failing` tests to `BrowseGames.test.tsx`

Add to `frontend/src/pages/__tests__/BrowseGames.test.tsx`:

1. A `test.failing` test asserting the API call includes `params.limit === 25` and `params.offset === 0` on initial render
2. A `test.failing` test asserting that when `total > 25` the `<Pagination>` MUI component is rendered
3. A `test.failing` test asserting that changing page increments `offset` by 25 in the next API call

Mock responses for these tests must include `limit: 25, offset: 0, total: 50` (two pages).

- **Files**:
  - `frontend/src/pages/__tests__/BrowseGames.test.tsx`
- **Success**:
  - `cd frontend && npm test` shows new tests as `test.failing` (expected failures)
  - Existing BrowseGames tests still pass
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 216-240) — BrowseGames recommended implementation (page state, params, Pagination JSX)
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 108-122) — MUI Pagination component API
- **Dependencies**:
  - Task 3.1

### Task 3.3: Add `test.failing` tests to `MyGames.test.tsx`

Add to `frontend/src/pages/__tests__/MyGames.test.tsx`:

1. A `test.failing` test asserting that `apiClient.get` is called **twice** on mount — once with `role: 'host'` params and once with `role: 'participant'` params
2. A `test.failing` test asserting that the "Hosting" tab renders a `<Pagination>` control when `hostedTotal > 25`
3. A `test.failing` test asserting that the "Joined" tab renders a `<Pagination>` control when `joinedTotal > 25`

Mock both calls: hosted response returns `{ games: [...], total: 30, limit: 25, offset: 0 }` and joined response similarly.

- **Files**:
  - `frontend/src/pages/__tests__/MyGames.test.tsx`
- **Success**:
  - New tests show as expected failures; existing tests pass
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 241-263) — MyGames two-fetch pattern with `Promise.all`
- **Dependencies**:
  - Task 3.1

### Task 3.4: Verify `test.failing` tests fail as expected

Run the frontend test suite and confirm `test.failing` tests show as expected failures (not unexpected passes).

- **Files**: none — verification only
- **Success**:
  - `cd frontend && npm test -- --reporter=verbose` output shows new tests as expected failures
- **Research References**: none
- **Dependencies**:
  - Tasks 3.2 and 3.3

---

## Phase 4: GREEN — frontend implementation

### Task 4.1: Make `limit` and `offset` required in TypeScript interface

Update `frontend/src/types/index.ts`: change `limit?: number` → `limit: number` and `offset?: number` → `offset: number`.

- **Files**:
  - `frontend/src/types/index.ts`
- **Success**:
  - TypeScript compiles; any test mock missing `limit`/`offset` causes a compile error (those will be fixed in Tasks 4.4)
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 204-215) — Final TypeScript interface
- **Dependencies**:
  - Phase 3 complete

### Task 4.2: Implement BrowseGames page state, params, and Pagination control

In `frontend/src/pages/BrowseGames.tsx`:

1. Add `const PAGE_SIZE = 25;` constant
2. Add `const [page, setPage] = useState(1);` and `const [total, setTotal] = useState(0);` state
3. Reset `page` to `1` when status or channel filter changes (add `page` to the `useEffect` dependency array; add `setPage(1)` in the status/channel change handlers)
4. Include `limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE` in the `apiClient.get` params
5. Store `response.data.total` into `setTotal` after each fetch
6. After the game list, render:
   ```tsx
   {
     total > PAGE_SIZE && (
       <Pagination
         count={Math.ceil(total / PAGE_SIZE)}
         page={page}
         onChange={(_e, v) => setPage(v)}
         sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}
       />
     );
   }
   ```

- **Files**:
  - `frontend/src/pages/BrowseGames.tsx`
- **Success**:
  - Component renders with page controls when total exceeds 25
  - Channel filter continues to work within the fetched page (client-side filter unchanged)
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 216-240) — BrowseGames full recommended implementation
- **Dependencies**:
  - Task 4.1

### Task 4.3: Implement MyGames two-fetch split with per-tab pagination

In `frontend/src/pages/MyGames.tsx`:

1. Replace single `GET /api/v1/games` fetch with two parallel fetches using `Promise.all`:
   - Hosted: `{ role: 'host', status: [...], limit: PAGE_SIZE, offset: (hostedPage - 1) * PAGE_SIZE }`
   - Joined: `{ role: 'participant', status: [...], limit: PAGE_SIZE, offset: (joinedPage - 1) * PAGE_SIZE }`
2. Add state: `hostedPage`, `joinedPage`, `hostedTotal`, `joinedTotal` (all initialized to 1 or 0)
3. Store `hostedResponse.data.games` and `joinedResponse.data.games` directly (no client-side split)
4. Store `hostedResponse.data.total` and `joinedResponse.data.total`
5. Add `<Pagination>` inside each tab panel driven by the respective total
6. Remove the client-side `allGames.filter(game.host.user_id === user.user_uuid)` split logic

- **Files**:
  - `frontend/src/pages/MyGames.tsx`
- **Success**:
  - Two separate API calls made on mount
  - Hosted and Joined tabs each show their own Pagination control when total > 25
  - Client-side split logic removed
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 241-263) — MyGames two-fetch implementation with Promise.all and state structure
- **Dependencies**:
  - Task 4.1

### Task 4.4: Update existing test mocks; remove `test.failing` markers

Update `frontend/src/pages/__tests__/BrowseGames.test.tsx`:

- Add `limit: 25, offset: 0` to every `mockGamesResponse` fixture used in existing tests
- Remove `test.failing` wrappers from the three tests added in Phase 3

Update `frontend/src/pages/__tests__/MyGames.test.tsx`:

- Add `limit: 25, offset: 0` to `mockGamesResponse` and all similar fixtures
- Update `mockImplementation` stubs that return game responses to return `{ games: [...], total: N, limit: 25, offset: 0 }` shaped data
- Remove `test.failing` wrappers from the three tests added in Phase 3

- **Files**:
  - `frontend/src/pages/__tests__/BrowseGames.test.tsx`
  - `frontend/src/pages/__tests__/MyGames.test.tsx`
- **Success**:
  - TypeScript compilation passes — no `limit`/`offset` missing from `GameListResponse` mocks
  - All tests pass (no `test.failing` markers remain)
- **Research References**:
  - #file:../research/20260425-01-game-list-pagination-research.md (Lines 51-63) — existing test patterns
- **Dependencies**:
  - Tasks 4.2 and 4.3

### Task 4.5: Run full frontend test suite

Confirm no regressions.

- **Files**: none — verification only
- **Success**:
  - `cd frontend && npm test` passes with zero failures
- **Research References**: none
- **Dependencies**:
  - Task 4.4 complete

---

## Dependencies

- `@mui/material` (Pagination) — already installed
- SQLAlchemy subquery pattern — already used in codebase
- No new packages

## Success Criteria

- All unit tests (Python + TypeScript) pass
- `GameListResponse` includes `limit`, `offset`, and corrected `total`
- Service accepts `role` and `user_id`; route exposes `role` query param
- BrowseGames and both MyGames tabs have working page controls
