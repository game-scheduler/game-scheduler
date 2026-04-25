<!-- markdownlint-disable-file -->

# Task Research Notes: Game List Pagination

## Research Executed

### File Analysis

- `frontend/src/pages/MyGames.tsx`
  - Single `GET /api/v1/games` call with `status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']` — no `limit`, `offset`, or `role` params sent
  - Splits result client-side: `hosted = allGames.filter(game.host.user_id === user.user_uuid)`
  - No pagination UI — all games rendered in one pass
  - Two tabs: "Hosting" and "Joined" — both derived from one flat response

- `frontend/src/pages/BrowseGames.tsx`
  - Single `GET /api/v1/games` call; `guild_id`, `channel_id`, `status` filters applied
  - Client-side channel filtering: fetches all games, then filters by `channel_id` in JS
  - No `limit`, `offset` sent; no pagination UI

- `frontend/src/types/index.ts`
  - `GameListResponse`: `{ games: GameSession[], total: number }` — `total` returned but never used

- `services/api/routes/games.py` (list_games route, line 413)
  - `limit`: default 50, max 100
  - `offset`: default 0
  - `status`: `list[str] | None` with `.in_()` — multi-status already implemented
  - No `role` parameter exists
  - Returns `total=len(authorized_games)` — this is the count for the current page only, not the full dataset total; unusable for pagination controls

- `services/api/services/games.py` (list_games method, line 1016)
  - Accepts `guild_id`, `channel_id`, `status: list[str] | None`, `limit`, `offset`
  - DB count query runs before pagination slice; that `_total` value is discarded at the route layer
  - No `role` parameter exists
  - Returns `(games, total)` tuple

- `shared/schemas/game.py` (GameListResponse, line 232)
  - `games: list[GameResponse]`, `total: int` — no `limit` or `offset` fields

- `shared/models/game.py`
  - `GameSession.host_id` is a FK to `users.id`
  - `GameSession.participants` relationship to `GameParticipant`

- `shared/models/participant.py`
  - `GameParticipant.user_id` is nullable FK to `users.id`
  - `GameParticipant.game_session_id` FK to `game_sessions.id`

- `shared/models/user.py`
  - `User.id` is the DB UUID primary key
  - `User.discord_id` is the Discord snowflake string

### Code Search Results

- `GameListResponse` usages
  - `shared/schemas/game.py`: definition
  - `services/api/routes/games.py`: constructed and returned
  - `tests/unit/services/api/routes/test_games_routes.py`: patched in 5 test classes; all call `list_games()` with `guild_id`, `channel_id`, `status`, `limit`, `offset` as positional/keyword args — no `role` arg present

- `list_games` service test coverage
  - `tests/unit/services/api/services/test_games_service.py`: `test_list_games_no_filters` and `test_list_games_with_filters` — neither passes a `role` argument

- MUI component availability
  - Project uses `@mui/material` throughout; `Pagination` component is available in MUI v5/v6 and fits the existing import pattern

### Project Conventions

- Standards referenced: `python.instructions.md`, `typescript-5-es2022.instructions.md`, `unit-tests.instructions.md`, `test-driven-development.instructions.md`
- Backend pagination: offset/limit pattern already in place; no cursor-based pagination in use
- Frontend state: `useState` + `useEffect` pattern used in both pages; no global state manager

## Key Discoveries

### The `total` Problem

The route currently does:

```python
games, _total = await game_service.list_games(...)  # _total is DB pre-auth count
# ... authorization loop ...
return GameListResponse(games=..., total=len(authorized_games))  # page-count, not full total
```

`len(authorized_games)` is the count of games on the _current page_ that the user is authorized to see — not the total across all pages. Pagination controls (`totalPages = ceil(total / limit)`) require the full dataset total.

The fix is to pass the DB pre-auth count (`_total`) through to the response. It may be very slightly larger than the true authorized total (if some games on later pages are auth-blocked), but that is an acceptable approximation — a pagination control showing one extra page that renders empty is a minor UX issue far preferable to the current unbounded load.

### Role Filter SQL

For `role=host`:

```python
query = query.where(game_model.GameSession.host_id == user_db_id)
count_query = count_query.where(game_model.GameSession.host_id == user_db_id)
```

For `role=participant` (non-host participant — user appears in `game_participants` but is not the host):

```python
participant_subquery = (
    select(participant_model.GameParticipant.game_session_id)
    .where(participant_model.GameParticipant.user_id == user_db_id)
)
query = query.where(game_model.GameSession.id.in_(participant_subquery))
query = query.where(game_model.GameSession.host_id != user_db_id)
count_query = count_query.where(game_model.GameSession.id.in_(participant_subquery))
count_query = count_query.where(game_model.GameSession.host_id != user_db_id)
```

`user_db_id` is `current_user.user.id` (the `users.id` UUID), available in the route.

### MUI Pagination Component

```typescript
import { Pagination } from '@mui/material';

<Pagination
  count={Math.ceil(total / limit)}
  page={page}
  onChange={(_event, value) => setPage(value)}
  sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}
/>
```

`count` is total number of pages. Component is zero-config beyond `count`, `page`, and `onChange`.

## Recommended Approach

### Backend Changes

**1. `shared/schemas/game.py` — add `limit` and `offset` to `GameListResponse`**

```python
class GameListResponse(BaseModel):
    games: list[GameResponse] = Field(..., description="List of games")
    total: int = Field(..., description="Total number of matching games (pre-authorization approximation)")
    limit: int = Field(..., description="Page size used for this request")
    offset: int = Field(..., description="Offset used for this request")
```

**2. `services/api/services/games.py` — add `role` and `user_id` parameters to `list_games`**

```python
async def list_games(
    self,
    guild_id: str | None = None,
    channel_id: str | None = None,
    status: list[str] | None = None,
    role: str | None = None,
    user_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[game_model.GameSession], int]:
```

Role filter additions (after existing guild/channel/status filters):

```python
if role == "host" and user_id:
    query = query.where(game_model.GameSession.host_id == user_id)
    count_query = count_query.where(game_model.GameSession.host_id == user_id)
elif role == "participant" and user_id:
    participant_subquery = (
        select(participant_model.GameParticipant.game_session_id)
        .where(participant_model.GameParticipant.user_id == user_id)
    )
    query = query.where(game_model.GameSession.id.in_(participant_subquery))
    query = query.where(game_model.GameSession.host_id != user_id)
    count_query = count_query.where(game_model.GameSession.id.in_(participant_subquery))
    count_query = count_query.where(game_model.GameSession.host_id != user_id)
```

**3. `services/api/routes/games.py` — add `role` param; fix `total`; pass `limit`/`offset` to response**

```python
@router.get("", response_model=game_schemas.GameListResponse)
async def list_games(
    guild_id: Annotated[str | None, Query()] = None,
    channel_id: Annotated[str | None, Query()] = None,
    status: Annotated[list[str] | None, Query()] = None,
    role: Annotated[str | None, Query(description="'host' or 'participant'")] = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    ...
```

Pass `role` and `user_id` to service; use DB total in response:

```python
games, total = await game_service.list_games(
    guild_id=guild_id,
    channel_id=channel_id,
    status=status,
    role=role,
    user_id=current_user.user.id,
    limit=limit,
    offset=offset,
)
# ... authorization loop (authorized_games) ...
return game_schemas.GameListResponse(
    games=list(game_responses),
    total=total,       # DB pre-auth count, not len(authorized_games)
    limit=limit,
    offset=offset,
)
```

### Frontend Changes

**`frontend/src/types/index.ts`**

```typescript
export interface GameListResponse {
  games: GameSession[];
  total: number;
  limit: number;
  offset: number;
}
```

**`frontend/src/pages/BrowseGames.tsx`**

- Add `const [page, setPage] = useState(1);`
- Add `const PAGE_SIZE = 25;` constant
- Include `limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE` in every fetch
- Store `total` from response in state
- Reset `page` to 1 on status or channel filter change (channel filter remains client-side post-fetch since it filters within the returned page)
- Add below the game list:
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

**`frontend/src/pages/MyGames.tsx`**

- Replace single fetch with two parallel fetches:
  ```typescript
  const [hostedPage, setHostedPage] = useState(1);
  const [joinedPage, setJoinedPage] = useState(1);
  const [hostedTotal, setHostedTotal] = useState(0);
  const [joinedTotal, setJoinedTotal] = useState(0);
  const PAGE_SIZE = 25;
  ```
- Fetch on `[user, hostedPage, joinedPage]`:
  ```typescript
  const [hostedResponse, joinedResponse] = await Promise.all([
    apiClient.get<GameListResponse>('/api/v1/games', {
      params: {
        role: 'host',
        status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
        limit: PAGE_SIZE,
        offset: (hostedPage - 1) * PAGE_SIZE,
      },
    }),
    apiClient.get<GameListResponse>('/api/v1/games', {
      params: {
        role: 'participant',
        status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
        limit: PAGE_SIZE,
        offset: (joinedPage - 1) * PAGE_SIZE,
      },
    }),
  ]);
  setHostedGames(hostedResponse.data.games);
  setHostedTotal(hostedResponse.data.total);
  setJoinedGames(joinedResponse.data.games);
  setJoinedTotal(joinedResponse.data.total);
  ```
- Remove client-side hosted/joined split (no longer needed)
- Add `<Pagination>` inside each `<TabPanel>` driven by the respective total

## Implementation Guidance

- **Objectives**: bound page load time to 25 games per request; give users page navigation controls on BrowseGames and both MyGames tabs
- **Key Tasks**:
  1. `shared/schemas/game.py`: add `limit` and `offset` fields to `GameListResponse`
  2. `services/api/services/games.py`: add `role` and `user_id` params; add role filter SQL; lower `limit` default to 25
  3. `services/api/routes/games.py`: add `role` query param; lower `limit` default/max to 25; pass `_total` (DB count) and `limit`/`offset` into `GameListResponse`
  4. `tests/unit/services/api/services/test_games_service.py`: add tests for `role=host` and `role=participant` filters
  5. `tests/unit/services/api/routes/test_games_routes.py`: update existing call sites to include `role=None`; add tests for role param passthrough and `total`/`limit`/`offset` in response
  6. `frontend/src/types/index.ts`: add `limit` and `offset` to `GameListResponse`
  7. `frontend/src/pages/BrowseGames.tsx`: add page state; send `limit`/`offset`; add `<Pagination>` control
  8. `frontend/src/pages/MyGames.tsx`: split into two parallel role-filtered fetches; add per-tab page state and `<Pagination>` controls
- **Dependencies**: no new packages; MUI `Pagination` is already available via `@mui/material`
- **Files touched**: `shared/schemas/game.py`, `services/api/services/games.py`, `services/api/routes/games.py`, `tests/unit/services/api/routes/test_games_routes.py`, `tests/unit/services/api/services/test_games_service.py`, `frontend/src/types/index.ts`, `frontend/src/pages/BrowseGames.tsx`, `frontend/src/pages/MyGames.tsx`
- **Success Criteria**:
  - Default page load fetches ≤25 games per request
  - BrowseGames shows page controls when `total > 25`; channel filter continues to work within the fetched page
  - MyGames "Hosting" tab fetches only `role=host` games, paginated independently
  - MyGames "Joined" tab fetches only `role=participant` games, paginated independently
  - `total` in the response reflects the DB pre-authorization count (usable for page count calculation)
  - All existing route and service unit tests pass; new tests cover role filter and updated response shape
