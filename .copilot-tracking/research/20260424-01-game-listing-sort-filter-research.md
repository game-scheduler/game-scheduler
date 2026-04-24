<!-- markdownlint-disable-file -->

# Task Research Notes: Game Listing Sort and Filter

## Research Executed

### File Analysis

- `frontend/src/pages/MyGames.tsx`
  - Root route (`/`) — the first page users see after login
  - Fetches `/api/v1/games` with no status filter — receives all statuses including ARCHIVED
  - No sorting applied — renders games in API return order

- `frontend/src/pages/BrowseGames.tsx`
  - Reachable via `/guilds/:guildId/games`
  - `selectedStatus` defaults to `'SCHEDULED'` — first load already filters to scheduled only
  - Status dropdown: ALL, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED — no ARCHIVED option
  - When `selectedStatus === 'ALL'`: passes no status param; backend returns everything including ARCHIVED

- `frontend/src/api/client.ts`
  - axios client with no `paramsSerializer` configured
  - Default axios serializes arrays as bracket notation: `status[]=SCHEDULED&status[]=COMPLETED`
  - FastAPI expects repeated params: `?status=SCHEDULED&status=COMPLETED`
  - Must add `paramsSerializer` using `URLSearchParams` (no `qs` library present)

- `frontend/src/types/index.ts` line 104
  - `status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'` — `'ARCHIVED'` missing from the union type

- `services/api/services/games.py` lines 999–1057 (`list_games`)
  - `status: str | None = None` — single string, uses `== status` filter
  - Ordering: `game_model.GameSession.scheduled_at.asc()` only

- `services/api/routes/games.py` lines 414–428 (`list_games` route)
  - `status: Annotated[str | None, Query(...)] = None` — single value only
  - Passes directly to service

### Code Search Results

- `list_games` callers: one route caller (`games.py:435`), multiple integration tests in `test_games_route_guild_isolation.py`
- Integration tests pass `status="SCHEDULED"` as a string — all need updating to list form
- No existing caller passes `status=None` relying on ARCHIVED being returned
- App routing: root route `/` maps to `MyGames`

### Project Conventions

- Standards: Python TDD per `python.instructions.md`, `test-driven-development.instructions.md`
- FastAPI multi-value query param pattern: `list[str]` type with `Query()` accepts repeated `?status=X&status=Y`
- SQLAlchemy: `.in_(list)` clause for multi-value filter

## Key Discoveries

### Root Cause

`list_games` accepts only a single `status` string. The frontend has no way to request "all except ARCHIVED" — it can only pass one status value or nothing. When nothing is passed, ARCHIVED games are returned.

### The Three Problems

1. **ARCHIVED games visible**: `MyGames` passes no status → backend returns all including ARCHIVED
2. **No status-group ordering**: Backend sorts by `scheduled_at ASC` only; desired order is SCHEDULED first (soonest), then COMPLETED (most recently ended first)
3. **Missing `'ARCHIVED'` in TypeScript type**: `GameSession.status` union omits `'ARCHIVED'`

### API Change: Single Status → List of Statuses

**Backend service** (`services/api/services/games.py`):

```python
async def list_games(
    self,
    guild_id: str | None = None,
    channel_id: str | None = None,
    status: list[str] | None = None,   # was: str | None
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[game_model.GameSession], int]:
    ...
    if status:
        query = query.where(game_model.GameSession.status.in_(status))
    ...
    if status:
        count_query = count_query.where(game_model.GameSession.status.in_(status))
```

**Backend route** (`services/api/routes/games.py`):

```python
status: Annotated[list[str] | None, Query(description="Filter by status")] = None,
```

FastAPI natively handles this as repeated query params: `?status=SCHEDULED&status=COMPLETED`

**Frontend `paramsSerializer`** (`frontend/src/api/client.ts`):

```typescript
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
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
});
```

**Frontend `MyGames.tsx`**: Pass explicit list (all non-archived statuses) instead of no param:

```typescript
const params: Record<string, unknown> = {
  status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
};
```

**Frontend `BrowseGames.tsx`**: Single-status dropdown UI stays as-is, but:

- When specific status selected: `status: [selectedStatus]`
- When "ALL" selected: `status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']`

### Sorting After Fetch (Python-side, in service)

Different sort directions per status group require Python-side sort (simpler than SQL CASE with negated epochs):

```python
_STATUS_ORDER = {
    GameStatus.SCHEDULED: 0,
    GameStatus.IN_PROGRESS: 1,
    GameStatus.COMPLETED: 2,
    GameStatus.CANCELLED: 3,
    GameStatus.ARCHIVED: 4,
}

def _game_sort_key(game: game_model.GameSession) -> tuple[int, float]:
    rank = _STATUS_ORDER.get(game.status, 99)
    ts = game.scheduled_at.timestamp() if game.scheduled_at else 0.0
    if game.status in (GameStatus.COMPLETED, GameStatus.CANCELLED):
        ts = -ts
    return (rank, ts)
```

Applied after the DB fetch: `games = sorted(result.scalars().all(), key=_game_sort_key)`

The existing `ORDER BY scheduled_at ASC` in the query can be removed since Python sort supersedes it.

## Complete Files to Change

| File                                                    | Change                                                                       |
| ------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------- |
| `services/api/services/games.py`                        | `status` param → `list[str]                                                  | None`; use `.in\_()`; add Python sort |
| `services/api/routes/games.py`                          | `status` param → `list[str]                                                  | None`with`Query()`                    |
| `tests/unit/api/services/test_games.py`                 | Update TestListGames to pass lists; add test for multi-status and sort order |
| `tests/integration/test_games_route_guild_isolation.py` | Update `status="SCHEDULED"` calls to `status=["SCHEDULED"]`                  |
| `frontend/src/api/client.ts`                            | Add `paramsSerializer` for array params                                      |
| `frontend/src/types/index.ts`                           | Add `'ARCHIVED'` to `GameSession.status` union                               |
| `frontend/src/pages/MyGames.tsx`                        | Pass `status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']`        |
| `frontend/src/pages/BrowseGames.tsx`                    | Pass `status: [selectedStatus]` or full non-archived list for ALL            |
| `frontend/src/pages/__tests__/BrowseGames.test.tsx`     | Update mock param expectations                                               |

## Recommended Approach

Single combined implementation:

1. Change `list_games` service param from `str | None` to `list[str] | None` with `.in_()` filter; add Python-side sort
2. Change route query param to `list[str] | None`
3. Add `paramsSerializer` to axios client
4. Update `MyGames` and `BrowseGames` to pass explicit status lists
5. Add `'ARCHIVED'` to TypeScript type
6. Update all affected tests

No backend default-exclusion of ARCHIVED — callers are explicit about what they want. Passing no status param means "no filter" (returns everything including ARCHIVED), which is a valid admin/future-use case.

## Implementation Guidance

- **Objectives**: Hide ARCHIVED from normal views; sort SCHEDULED first (soonest), then COMPLETED (most recently ended)
- **Key Tasks**:
  1. Backend service: `list[str] | None` param, `.in_()` filter, Python sort
  2. Backend route: `list[str] | None` query param
  3. `client.ts`: `paramsSerializer` for repeated query params
  4. `types/index.ts`: add `'ARCHIVED'` to status union
  5. `MyGames.tsx`: explicit non-archived status list
  6. `BrowseGames.tsx`: wrap single status in list; ALL → non-archived list
  7. Update unit tests (service + route)
  8. Update integration tests (`status="SCHEDULED"` → `status=["SCHEDULED"]`)
- **Dependencies**: No DB migration needed
- **Success Criteria**:
  - `MyGames` shows no ARCHIVED games; SCHEDULED before COMPLETED; soonest next, most recently ended first
  - `BrowseGames` "ALL" shows no ARCHIVED games
  - `?status=SCHEDULED&status=COMPLETED` returns only those two statuses
  - No status param returns all (including ARCHIVED)
  - Existing integration tests pass after list migration
