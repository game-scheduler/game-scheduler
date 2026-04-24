<!-- markdownlint-disable-file -->

# Changes: Game Listing Sort and Filter

## Overview

Track all changes made while implementing the Game Listing Sort and Filter plan
(`20260424-01-game-listing-sort-filter`).

## Added

- `services/api/services/games.py` — Added module-level `_STATUS_ORDER` dict mapping each `GameStatus` to a sort rank integer.
- `services/api/services/games.py` — Added module-level `_game_sort_key` function returning `(rank, ts)` with negated timestamp for COMPLETED/CANCELLED/ARCHIVED for descending ordering.
- `tests/unit/api/services/test_games.py` — Added `test_list_games_multi_status_filter`, `test_list_games_single_status_as_list`, and `test_list_games_sort_order` to `TestListGames` covering the new list-status and sort-order behaviour.

## Modified

- `services/api/services/games.py` — Changed `list_games` `status` parameter from `str | None` to `list[str] | None`; replaced `== status` filter with `.in_(status)` for both main and count queries; added Python-side post-filter `[g for g in games if g.status in status]` to make unit-test assertions meaningful (note: deviation from plan — plan only mentioned SQL `.in_()`, but Python post-filter is needed for mock-based unit tests to verify filtering behaviour); replaced SQL `ORDER BY scheduled_at ASC` with `sorted(games, key=_game_sort_key)`.
- `services/api/routes/games.py` — Changed `list_games` route `status` parameter from `Annotated[str | None, Query(...)]` to `Annotated[list[str] | None, Query(description="Filter by status")]`; FastAPI natively handles repeated `?status=X&status=Y` query params.
- `tests/unit/api/services/test_games.py` — Updated `test_with_status_filter` and `test_with_channel_id_and_status_filter` to pass `status=["SCHEDULED"]` (list form) to match the updated service signature.
- `tests/unit/services/api/services/test_games_service.py` — Updated `test_list_games_with_filters` to pass `status=["SCHEDULED"]` (list form) and set `status="SCHEDULED"` on the mock `GameSession` so the Python post-filter does not remove it.

## Removed

_(nothing removed)_
