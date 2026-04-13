<!-- markdownlint-disable-file -->

# Task Details: Discord Member Fetch Performance

## Research Reference

**Source Research**: #file:../research/20260413-01-discord-member-fetch-performance-research.md

## Phase 1: Add Rate Limit Constants

### Task 1.1 (Tests): Write tests for rate limit constants

Write a test file `tests/unit/shared/cache/test_rate_limit_constants.py` that imports `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE` from `shared.cache.ttl` and asserts their values are `25` and `45` respectively. These tests will fail with `ImportError` until the constants are added.

- **Files**:
  - `tests/unit/shared/cache/test_rate_limit_constants.py` - new test file asserting constant values
- **Success**:
  - Tests exist and fail with `ImportError` or `AttributeError`
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 117-139) - Fix 2 constant names and rationale
- **Dependencies**:
  - None

### Task 1.2 (Implement): Add constants to shared/cache/ttl.py

Add `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND = 25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE = 45` as module-level integer constants in `shared/cache/ttl.py`. Background (25) matches the existing hardcoded Lua value; interactive (45) allows user-facing requests to claim more of the 50 req/s Discord global budget.

- **Files**:
  - `shared/cache/ttl.py` - add two integer constants at module level
- **Success**:
  - Tests from Task 1.1 pass
  - Constants are importable from `shared.cache.ttl`
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 117-139) - Fix 2 constant values and rationale
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Parameterize global_max in Rate Limit Infrastructure

### Task 2.1 (Tests): Write failing tests for global_max parameter in claim functions

Add tests to `tests/unit/shared/cache/test_claim_global_and_channel_slot.py` for `claim_global_and_channel_slot(channel_id, global_max=45)` and to a matching section for `claim_global_slot(global_max=45)` that verify the supplied value overrides the default 25 — e.g., that the Lua ARGV[3] receives the correct value. Add a test in `tests/unit/shared/discord/test_discord_api_client.py` inside `TestMakeAPIRequestRateLimit` verifying `_make_api_request` accepts and forwards `global_max`. Mark new tests `xfail(strict=True)`.

- **Files**:
  - `tests/unit/shared/cache/test_claim_global_and_channel_slot.py` - add tests for non-default `global_max` values
  - `tests/unit/shared/discord/test_discord_api_client.py` - add test that `_make_api_request` accepts `global_max`
- **Success**:
  - New tests exist and are marked `xfail(strict=True)`
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 43-56) - existing test file locations and test counts
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 117-139) - Fix 2 parameter threading specification
- **Dependencies**:
  - Task 1.2 completion (constants available for use in tests)

### Task 2.2 (Implement): Parameterize Lua script and cache client functions

- In `_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA` (`shared/cache/client.py` line 106): change `local global_max = 25` to `local global_max = tonumber(ARGV[3] or '25')`.
- Update `claim_global_and_channel_slot(channel_id, global_max: int = 25)` (line 414): pass `str(global_max)` as ARGV[3].
- Update `claim_global_slot(global_max: int = 25)` (line 460): pass `str(global_max)` as ARGV[3].

All existing callers pass no `global_max`, so default behaviour is unchanged.

- **Files**:
  - `shared/cache/client.py` - Lua script (line 106), `claim_global_and_channel_slot` (line 414), `claim_global_slot` (line 460)
- **Success**:
  - Tests from Task 2.1 pass (remove `xfail` markers)
  - All 17 existing tests in `test_claim_global_and_channel_slot.py` still pass
  - Default `global_max=25` behaviour unchanged for all existing callers
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 117-139) - Fix 2 Lua and function changes
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Thread global_max and Parallelize Discord Client

### Task 3.1 (Tests): Write failing tests for global_max threading and asyncio.gather in Discord client

Add tests to `tests/unit/shared/discord/test_discord_api_client.py` verifying:

- `_make_api_request` passes `global_max` to `claim_global_slot` / `claim_global_and_channel_slot`
- `get_guild_member` accepts `global_max` and passes it to `_make_api_request`
- `get_guild_members_batch` dispatches all user fetches concurrently (no serial loop) and passes `global_max` to each
- A 404 for one user in the batch is silently dropped; other exceptions propagate from `gather`

Mark new tests `xfail(strict=True)`.

- **Files**:
  - `tests/unit/shared/discord/test_discord_api_client.py` - tests for `global_max` threading, gather concurrency, and 404 drop / exception propagation
- **Success**:
  - New tests exist and are marked `xfail(strict=True)`
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 90-116) - Fix 1 gather implementation with error handling code
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 43-56) - existing `TestMakeAPIRequestRateLimit` test class location
- **Dependencies**:
  - Phase 2 completion

### Task 3.2 (Implement): Thread global_max and replace serial loop with asyncio.gather

- Add `global_max: int = DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND` to `_make_api_request` (line 198 of `shared/discord/client.py`); pass to the appropriate `claim_global_slot` / `claim_global_and_channel_slot` call.
- Add `global_max: int = DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND` to `get_guild_member` (line 764); thread to `_make_api_request`.
- In `get_guild_members_batch` (line 790): add `global_max: int = DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND` parameter; replace the serial `for` loop with the `asyncio.gather` pattern from the research (handling 404 drops and exception propagation).

- **Files**:
  - `shared/discord/client.py` - `_make_api_request` (line 198), `get_guild_member` (line 764), `get_guild_members_batch` (line 790)
- **Success**:
  - Tests from Task 3.1 pass (remove `xfail` markers)
  - All existing `TestMakeAPIRequestRateLimit` tests still pass
  - Default `global_max=DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND` preserves existing behaviour
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 90-116) - Fix 1 complete implementation with `asyncio.gather` and error handling
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Skip Participant Resolution in list_games and Use Interactive Budget in get_game

### Task 4.1 (Tests): Write failing tests for resolve_participants flag and interactive budget

Add tests to `tests/unit/services/api/routes/test_games_helpers.py` verifying:

- `_build_game_response(game, resolve_participants=False)` does not call `_resolve_display_data` for participants (host still resolved)
- `_build_game_response(game)` default still resolves all participants

Add tests to `tests/unit/services/api/routes/test_games_routes.py` verifying:

- `list_games` calls `_build_game_response` with `resolve_participants=False`
- `get_game` calls the display names stack with `global_max=DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE`

Add tests to `tests/unit/services/api/services/test_display_names.py` verifying:

- `resolve_display_names_and_avatars` accepts and threads `global_max` to `_fetch_and_cache_display_names` and then to `get_guild_members_batch`

Mark new tests `xfail(strict=True)`.

- **Files**:
  - `tests/unit/services/api/routes/test_games_helpers.py` - tests for `resolve_participants` flag behaviour
  - `tests/unit/services/api/routes/test_games_routes.py` - tests for correct call-site arguments in `list_games` and `get_game`
  - `tests/unit/services/api/services/test_display_names.py` - tests for `global_max` threading through display names service
- **Success**:
  - New tests exist and are marked `xfail(strict=True)`
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 140-160) - Fix 3 flag specification and call sites
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 162-200) - success criteria and interactive budget threading
- **Dependencies**:
  - None (can be written in parallel with Phase 3)

### Task 4.2 (Implement): Add resolve_participants flag and wire interactive budget

- Add `resolve_participants: bool = True` to `_build_game_response` (line 897 of `services/api/routes/games.py`); pass flag to `_resolve_display_data`.
- In `_resolve_display_data`: when `resolve_participants=False`, skip participant resolution entirely (host still resolved).
- In `list_games` route (line 403): call `_build_game_response(game, resolve_participants=False)`.
- Thread `global_max` through `resolve_display_names_and_avatars` (line ~280 of `services/api/services/display_names.py`) → `_fetch_and_cache_display_names` (line 102) → `get_guild_members_batch`. Default stays `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND`.
- In the `get_game` route (line 456): call display name resolution with `global_max=DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE`.

- **Files**:
  - `services/api/routes/games.py` - `_build_game_response` (line 897), `_resolve_display_data`, `list_games` call (line 403), `get_game` call (line 456)
  - `services/api/services/display_names.py` - `resolve_display_names_and_avatars` (line ~280), `_fetch_and_cache_display_names` (line 102)
- **Success**:
  - Tests from Task 4.1 pass (remove `xfail` markers)
  - `GET /api/v1/games` (list) makes no Discord member API calls for participants
  - `GET /api/v1/games/{id}` (detail) resolves all participants in parallel at up to 45 req/s
  - All existing route unit tests pass
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 140-160) - Fix 3 implementation
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 162-200) - success criteria
- **Dependencies**:
  - Phase 3 completion (`get_guild_members_batch` uses `asyncio.gather`)
  - Task 4.1 completion

## Phase 5: Parallel Host Fetch in list_games

### Task 5.1 (Tests): Write failing tests for prefetched_display_data and parallel host gathering

Add tests to `tests/unit/services/api/routes/test_games_helpers.py` verifying:

- `_build_game_response(game, prefetched_display_data={...})` does not call `_resolve_display_data` and uses the provided map instead
- `_build_game_response(game)` default (no `prefetched_display_data`) still calls `_resolve_display_data` as before

Add tests to `tests/unit/services/api/routes/test_games_routes.py` verifying:

- `list_games` makes exactly one `resolve_display_names_and_avatars` call per guild (not one per game)
- `list_games` passes `prefetched_display_data` into each `_build_game_response` call
- A host appearing in multiple games is fetched only once

Mark new tests `xfail(strict=True)`.

- **Files**:
  - `tests/unit/services/api/routes/test_games_helpers.py` - tests for `prefetched_display_data` parameter behaviour
  - `tests/unit/services/api/routes/test_games_routes.py` - tests for batch collection and single-call-per-guild behaviour in `list_games`
- **Success**:
  - New tests exist and are marked `xfail(strict=True)`
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 176-260) - Addendum: problem statement, solution design, call chain, and key properties
- **Dependencies**:
  - Phase 4 completion (`_build_game_response` has `resolve_participants=False` pattern already)

### Task 5.2 (Implement): Pre-batch host IDs and gather responses in list_games

Add `prefetched_display_data: dict[str, dict[str, str | None]] | None = None` to `_build_game_response` (line 897 of `services/api/routes/games.py`); when provided, skip `_resolve_display_data` entirely and use the map to populate host display data. In `list_games` (line 403): collect unique host Discord IDs grouped by guild using `collections.defaultdict`; issue one `asyncio.gather` over `resolve_display_names_and_avatars(guild_id, host_ids)` per guild; merge results into a single `prefetched_display_data` dict; then gather all `_build_game_response(game, resolve_participants=False, prefetched_display_data=prefetched)` calls concurrently. Add `import asyncio` and `from collections import defaultdict` to `services/api/routes/games.py` if not already present. All existing callers (`get_game`, `join_game`, etc.) pass no `prefetched_display_data`, so the `None` default preserves their behavior.

- **Files**:
  - `services/api/routes/games.py` - `_build_game_response` (line 897), `list_games` (line 403)
- **Success**:
  - Tests from Task 5.1 pass (remove `xfail` markers)
  - A host appearing in N games triggers exactly one Discord member fetch
  - All host fetches across the game list are concurrent via a single `asyncio.gather`
  - All existing route unit tests pass
- **Research References**:
  - #file:../research/20260413-01-discord-member-fetch-performance-research.md (Lines 176-260) - Addendum full specification including call chain and key properties
- **Dependencies**:
  - Phase 4 completion
  - Task 5.1 completion

## Dependencies

- `asyncio` is already imported in `shared/discord/client.py`
- `asyncio` and `collections.defaultdict` need to be imported in `services/api/routes/games.py`
- No new packages required

## Success Criteria

- `GET /api/v1/games` cold-cache completes in ~2s (host resolution only, no participant Discord calls)
- `GET /api/v1/games/{id}` cold-cache completes in ~1.5s (parallel gather, 45 req/s budget)
- No 429s from Discord under normal load
- All existing unit tests pass; new tests cover `global_max` threading and gather error handling
- A host appearing in multiple games in `list_games` is fetched exactly once (deduplication)
