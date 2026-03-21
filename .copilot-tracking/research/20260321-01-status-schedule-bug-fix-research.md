<!-- markdownlint-disable-file -->

# Task Research Notes: Status Schedule Not Updated for IN_PROGRESS and COMPLETED Games

## Research Executed

### File Analysis

- `services/api/services/games.py`
  - `_update_status_schedules()` at line ~1403: only handles `SCHEDULED` (upsert IN_PROGRESS + COMPLETED schedules) and everything else (delete all schedules). No handling for IN_PROGRESS or COMPLETED game states.
  - `_update_remaining_fields()` at line ~1117: sets `status_schedule_needs_update = True` when `status` changes, but does NOT set it when `expected_duration_minutes` changes
  - `_update_game_fields()` at line ~1148: `scheduled_at_updated` sets both `schedule_needs_update` and `status_schedule_needs_update`, but duration change does not

- `services/bot/events/handlers.py`
  - `_schedule_archive_transition_if_needed()` at line 1211: creates ARCHIVED `GameStatusSchedule` row after COMPLETED transition — only runs in bot event handler, not in API update path
  - `_handle_post_transition_actions()` at line 1234: only acts on ARCHIVED status

- `alembic/versions/c2135ff3d5cd_initial_schema.py`
  - PostgreSQL trigger `notify_game_status_schedule_changed` fires `pg_notify('game_status_schedule_changed', ...)` on any INSERT or UPDATE where `executed = FALSE` — daemon wakes immediately without polling delay

### Code Search Results

- `_update_status_schedules` called from
  - `_process_game_update_schedules()` line 1594 — only when `status_schedule_needs_update = True`
- `status_schedule_needs_update = True` set in
  - `_update_remaining_fields()` — only on `status` field change (line 1141-1142)
  - `_update_game_fields()` — also when `scheduled_at` changes (line 1178)
  - NOT when `expected_duration_minutes` changes

### Project Conventions

- Standards referenced: `services/api/services/games.py` patterns, `shared/models/game_status_schedule.py`
- Instructions followed: `fastapi-transaction-patterns.instructions.md`, TDD

## Key Discoveries

### The Bug

When a host edits an IN_PROGRESS game and changes `expected_duration_minutes`, the COMPLETED `GameStatusSchedule` row is NOT updated to reflect the new duration. The existing code:

```python
async def _update_status_schedules(self, game):
    status_schedules = ...  # fetch all existing rows

    if game.status == GameStatus.SCHEDULED.value:
        await self._ensure_in_progress_schedule(game, status_schedules)
        await self._ensure_completed_schedule(game, status_schedules)
    else:
        # Delete ALL schedules — wrong for IN_PROGRESS and COMPLETED
        for schedule in status_schedules:
            await self.db.delete(schedule)
```

The `else` branch deletes ALL schedules for any non-SCHEDULED game, which means:

1. Editing an IN_PROGRESS game deletes the pending COMPLETED schedule entirely (game never auto-completes)
2. Editing a COMPLETED game deletes any pending ARCHIVED schedule (game never auto-archives)
3. Changing `expected_duration_minutes` on an IN_PROGRESS or SCHEDULED game does not update the COMPLETED schedule time

Additionally, `status_schedule_needs_update` is never triggered by a `expected_duration_minutes` change, so `_update_status_schedules` is never even called in that scenario for SCHEDULED games either.

### Current Correct Behaviors to Preserve

- SCHEDULED → host edits `scheduled_at` or `expected_duration_minutes`: `_update_status_schedules` IS called (via `scheduled_at_updated`) and correctly upserts both schedules
- ARCHIVED/CANCELLED: deleting all schedules is correct

### Fix

Two changes to `services/api/services/games.py`:

**1. Trigger `status_schedule_needs_update` when `expected_duration_minutes` changes in `_update_remaining_fields()`:**

```python
if update_data.expected_duration_minutes is not None:
    game.expected_duration_minutes = update_data.expected_duration_minutes
    status_schedule_needs_update = True  # ADD THIS
```

**2. Expand `_update_status_schedules()` to handle IN_PROGRESS and COMPLETED states:**

```python
async def _update_status_schedules(self, game):
    status_schedules = ...

    if game.status == GameStatus.SCHEDULED.value:
        await self._ensure_in_progress_schedule(game, status_schedules)
        await self._ensure_completed_schedule(game, status_schedules)
    elif game.status == GameStatus.IN_PROGRESS.value:
        await self._ensure_completed_schedule(game, status_schedules)
        # Delete IN_PROGRESS schedule if present (already past)
        for s in status_schedules:
            if s.target_status == GameStatus.IN_PROGRESS.value:
                await self.db.delete(s)
    elif game.status == GameStatus.COMPLETED.value:
        await self._ensure_archived_schedule_if_configured(game, status_schedules)
        # Delete COMPLETED schedule if present (already past)
        for s in status_schedules:
            if s.target_status == GameStatus.COMPLETED.value:
                await self.db.delete(s)
    else:
        # ARCHIVED, CANCELLED — no future transitions
        for schedule in status_schedules:
            await self.db.delete(schedule)
```

**New helper `_ensure_archived_schedule_if_configured()`** (mirrors `_schedule_archive_transition_if_needed` in bot):

```python
async def _ensure_archived_schedule_if_configured(
    self,
    game: game_model.GameSession,
    status_schedules: Sequence[GameStatusSchedule],
) -> None:
    if game.archive_delay_seconds is None:
        return
    archived_schedule = next(
        (s for s in status_schedules if s.target_status == GameStatus.ARCHIVED.value),
        None,
    )
    archive_time = utc_now() + timedelta(seconds=game.archive_delay_seconds)
    if archived_schedule:
        archived_schedule.transition_time = archive_time
        archived_schedule.executed = False
    else:
        self.db.add(GameStatusSchedule(
            id=str(uuid.uuid4()),
            game_id=game.id,
            target_status=GameStatus.ARCHIVED.value,
            transition_time=archive_time,
            executed=False,
        ))
```

**Note:** The `_ensure_completed_schedule()` already computes `completion_time = game.scheduled_at + timedelta(minutes=duration_minutes)`, which correctly recomputes for IN_PROGRESS games.

### How pg_notify Enables Immediate Effect

The PostgreSQL trigger on `game_status_schedule` fires `pg_notify('game_status_schedule_changed', ...)` on every INSERT/UPDATE where `executed = FALSE`. The scheduler daemon is blocked on `LISTEN`, so it wakes immediately when the schedule row is inserted or updated. No polling delay.

## Recommended Approach

Apply both changes above to `services/api/services/games.py` only. No schema changes, no new models, no migration needed — this is purely a logic fix.

## Implementation Guidance

- **Objectives**: Fix silent schedule drop bug for IN_PROGRESS and COMPLETED games
- **Key Tasks**:
  1. In `_update_remaining_fields()`: add `status_schedule_needs_update = True` when `expected_duration_minutes` is updated
  2. In `_update_status_schedules()`: add `elif` branches for IN_PROGRESS and COMPLETED
  3. Add `_ensure_archived_schedule_if_configured()` helper method
- **Dependencies**: None — no migration, no frontend changes
- **Success Criteria**:
  - Editing `expected_duration_minutes` on any game always updates the COMPLETED schedule
  - Editing an IN_PROGRESS game does not destroy its COMPLETED schedule
  - Editing a COMPLETED game does not destroy its ARCHIVED schedule
  - ARCHIVED/CANCELLED games still have all schedules cleaned up

### Integration Tests

New file: `tests/integration/test_status_schedule_updates.py`

- `test_expected_duration_change_updates_completed_schedule_for_scheduled_game` — Create SCHEDULED game, update `expected_duration_minutes`, verify COMPLETED schedule row has updated `transition_time`
- `test_expected_duration_change_updates_completed_schedule_for_in_progress_game` — Create game with SCHEDULED status, manually set to IN_PROGRESS in DB, update `expected_duration_minutes` via API, verify COMPLETED schedule row updated (not deleted)
- `test_api_update_in_progress_game_preserves_completed_schedule` — Verify that updating any non-duration field on an IN_PROGRESS game (e.g. description) does NOT delete the COMPLETED schedule
- `test_api_update_completed_game_preserves_archived_schedule` — Set game to COMPLETED with `archive_delay_seconds`, manually insert an ARCHIVED schedule, then update the game via API, verify the ARCHIVED schedule survives
- `test_api_update_completed_game_creates_archived_schedule` — Set game to COMPLETED with `archive_delay_seconds` but no existing ARCHIVED schedule row, update game via API, verify an ARCHIVED schedule row is created
