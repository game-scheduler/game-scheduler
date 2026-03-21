<!-- markdownlint-disable-file -->

# Task Research Notes: Rewards Feature

## Research Executed

### File Analysis

- `shared/models/game.py` — `GameSession` model; has `description`, `signup_instructions`, `where` as `Text, nullable=True`; has `archive_channel_id`, `archive_delay_seconds`; no `rewards` or `remind_host_rewards` fields
- `shared/models/template.py` — `GameTemplate` model; has pre-populated host-editable fields section; no `remind_host_rewards`
- `shared/schemas/game.py` — `GameUpdateRequest`, `GameCreateRequest`, `GameResponse`; no `rewards` or `remind_host_rewards`
- `shared/schemas/template.py` — `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, `TemplateListItem`; no `remind_host_rewards`
- `services/api/services/games.py` — `_update_simple_text_fields()`, `_build_game_session()`, `clone_game()`, `_update_remaining_fields()`
- `services/bot/formatters/game_message.py` — `create_game_embed()`, `format_game_announcement()`, `_trim_embed_if_needed()`; imports `get_config()` for `frontend_url`
- `services/bot/events/handlers.py` — `_handle_post_transition_actions()`, `_send_dm()`; imports `DMFormats` from `shared.message_formats`; does NOT currently import `get_config` (available via `services.bot.config`)
- `shared/message_formats.py` — `DMFormats` class; has `promotion`, `removal`, `join_*`, `reminder_host`, `reminder_participant`, `clone_confirmation` static methods
- `frontend/src/types/index.ts` — `GameSession` interface
- `frontend/src/components/GameForm.tsx` — `GameFormData` interface; renders all game fields; no status-conditional rendering
- `frontend/src/pages/EditGame.tsx` — single `handleSubmit`; PUT to `/api/v1/games/${gameId}`
- `frontend/src/pages/GameDetails.tsx` — read-only game display
- `shared/utils/limits.py` — `DISCORD_EMBED_TOTAL_SAFE_LIMIT = 5900`
- `alembic/versions/` — latest migration: `20260311_add_archive_fields.py`

### Code Search Results

- `_trim_embed_if_needed` in `game_message.py`
  - Trims description when `len(embed) > DISCORD_EMBED_TOTAL_SAFE_LIMIT`
  - Only trims description, not embed fields
- `_handle_post_transition_actions` in `handlers.py`
  - Currently only fires archival logic on ARCHIVED; needs COMPLETED branch for DM
- `get_config()` in `services/bot/config.py`
  - Provides `frontend_url` (e.g. `http://localhost:5173`)
- `archive_delay_seconds` in `GameUpdateRequest`
  - NOT currently in schema — must be added for Save and Archive flow
- Status schedule bug fix (see research doc 01)
  - Prerequisite: after bug fix, updating a COMPLETED game with `archive_delay_seconds` in the API update payload causes `_update_status_schedules` to upsert an ARCHIVED schedule via `_ensure_archived_schedule_if_configured`

### Project Conventions

- Standards referenced: Python models use `Mapped[str | None] = mapped_column(Text, nullable=True)` pattern; bool columns use `server_default=text('false')`
- Instructions followed: `fastapi-transaction-patterns.instructions.md`, TDD, `python.instructions.md`, `reactjs.instructions.md`

## Key Discoveries

### Feature Requirements Summary

1. `rewards` text field on `GameSession` (nullable)
2. `remind_host_rewards` boolean on `GameTemplate` and `GameSession` (default False), in the pre-populated/host-editable section
3. Edit page: rewards textarea visible only when `status ∈ {IN_PROGRESS, COMPLETED, ARCHIVED}`; `remind_host_rewards` checkbox always visible
4. Edit page: "Save and Archive" button visible when `rewards` non-empty AND `archive_channel_id` non-empty
5. "Save and Archive" uses existing status schedule infrastructure (depends on bug fix in doc 01): sets `archive_delay_seconds = 1` in payload, which causes `_ensure_archived_schedule_if_configured` to create a 1-second ARCHIVED schedule
6. Discord embed: rewards shown as `||rewards text||` spoiler field; description truncated to fit if needed
7. Web display (`GameDetails.tsx`, `GameCard.tsx`): rewards shown as click-to-reveal spoiler
8. Bot COMPLETED handler: when `remind_host_rewards = True` AND `game.rewards` is empty/None, send DM to host with link to edit page

### Save and Archive API Flow (depends on bug fix)

The frontend sends a normal PUT update with two additional fields:

- `archive_delay_seconds = 1`
- (rewards field already included)

The API service processes this as a normal update. Because of the bug fix, when `game.status == COMPLETED`, `_update_status_schedules` calls `_ensure_archived_schedule_if_configured` which creates/updates an ARCHIVED schedule at `now + 1s`. The pg_notify trigger wakes the scheduler daemon immediately and archival proceeds through existing code.

For IN_PROGRESS games: the same works — the bug fix makes `_update_status_schedules` update (not delete) the COMPLETED schedule. Setting `archive_delay_seconds = 1` also stores the value on the game session so when COMPLETED fires, the bot's `_schedule_archive_transition_if_needed` creates the 1-second ARCHIVED schedule.

**`archive_delay_seconds` must be added to `GameUpdateRequest`** (currently absent from schema).

### Discord Embed Spoiler

Discord spoiler syntax: `||text||`. The rewards field should be added as an embed field (not appended to description), positioned after the main content fields.

`_trim_embed_if_needed` only trims `embed.description`. Since rewards is an embed field, the trimming logic must account for the rewards field size when computing how much to trim the description:

```python
@staticmethod
def _trim_embed_if_needed(embed: discord.Embed) -> discord.Embed:
    excess = len(embed) - DISCORD_EMBED_TOTAL_SAFE_LIMIT
    if excess > 0 and embed.description:
        trim_to = len(embed.description) - excess - 3
        embed.description = embed.description[:max(0, trim_to)] + "..."
    return embed
```

This existing logic already handles the rewards field being present in the embed — `len(embed)` includes all fields. No change needed to `_trim_embed_if_needed` itself; rewards just gets added as a field before `_trim_embed_if_needed` is called.

### Web Spoiler Implementation

MUI does not have a built-in spoiler component. Use a simple CSS approach:

```tsx
// Revealed state toggled by onClick
<Box
  onClick={() => setRevealed(true)}
  sx={!revealed ? { filter: 'blur(4px)', cursor: 'pointer', userSelect: 'none' } : {}}
>
  {game.rewards}
</Box>
```

Show a label "🏆 Rewards (click to reveal)" when not yet revealed.

### DM Rewards Reminder

`_handle_post_transition_actions` in `handlers.py`:

```python
async def _handle_post_transition_actions(self, game, target_status):
    if target_status == GameStatus.COMPLETED.value:
        if game.remind_host_rewards and not game.rewards:
            config = get_config()
            edit_url = f"{config.frontend_url}/games/{game.id}/edit"
            message = DMFormats.rewards_reminder(game.title, str(game.id), edit_url)
            await self._send_dm(game.host_discord_id, message)

    if target_status != GameStatus.ARCHIVED.value:
        return
    await self._archive_game_announcement(game)
```

`game.host_discord_id` — need to verify field name. The game has a `host_id` FK to users. Looking at handlers.py existing code: `game.host.discord_id` via relationship load, or `host_discord_id` as a direct field. Need to confirm at implementation time.

`DMFormats.rewards_reminder` new static method:

```python
@staticmethod
def rewards_reminder(game_title: str, game_id: str, edit_url: str) -> str:
    return (
        f"🏆 **{game_title}** has completed! "
        f"Don't forget to add rewards for your players.\n\n"
        f"[Edit game to add rewards]({edit_url})"
    )
```

## Recommended Approach

Implement in dependency order:

1. Bug fix (doc 01) first — prerequisite for Save and Archive
2. Database migration: add `rewards TEXT NULL` to `game_sessions`, add `remind_host_rewards BOOLEAN NOT NULL DEFAULT FALSE` to both `game_sessions` and `game_templates`
3. Backend: models → schemas → API route → service layer
4. Bot: embed formatter → completion handler DM
5. Frontend: types → GameForm → EditGame → GameDetails → GameCard

## Implementation Guidance

- **Objectives**: Add rewards field with spoiler display, Save and Archive shortcut, and host completion reminder DM
- **Key Tasks**:

  **Migration** (`alembic/versions/20260321_add_rewards_fields.py`):
  - `ALTER TABLE game_sessions ADD COLUMN rewards TEXT`
  - `ALTER TABLE game_sessions ADD COLUMN remind_host_rewards BOOLEAN NOT NULL DEFAULT FALSE`
  - `ALTER TABLE game_templates ADD COLUMN remind_host_rewards BOOLEAN NOT NULL DEFAULT FALSE`

  **`shared/models/game.py`**:
  - Add `rewards: Mapped[str | None] = mapped_column(Text, nullable=True)`
  - Add `remind_host_rewards: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), nullable=False)`

  **`shared/models/template.py`**:
  - Add `remind_host_rewards: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), nullable=False)` in the pre-populated fields section

  **`shared/schemas/game.py`**:
  - `GameUpdateRequest`: add `rewards: str | None = Field(None, max_length=2000)`, `remind_host_rewards: bool | None = None`, `archive_delay_seconds: int | None = Field(None, ge=0)` (the last one was missing and is needed for Save and Archive)
  - `GameResponse`: add `rewards: str | None`, `remind_host_rewards: bool`, `archive_channel_id: str | None`
  - `GameCreateRequest`: add `remind_host_rewards: bool | None = None`

  **`shared/schemas/template.py`**:
  - `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, `TemplateListItem`: add `remind_host_rewards: bool` / `bool | None`

  **`services/api/services/games.py`**:
  - `_update_simple_text_fields()`: add `rewards` handling
  - `_update_remaining_fields()`: add `remind_host_rewards` handling
  - `_build_game_session()`: copy `remind_host_rewards` from template
  - `clone_game()`: copy `remind_host_rewards`; set `rewards = None` (new game should not inherit rewards)

  **`services/api/routes/games.py`**:
  - `update_game`: add `rewards: Annotated[str | None, Form()] = None`, `remind_host_rewards: Annotated[bool | None, Form()] = None`, `archive_delay_seconds: Annotated[int | None, Form()] = None`
  - `_build_game_response()`: include `rewards`, `remind_host_rewards`, `archive_channel_id`

  **`services/bot/formatters/game_message.py`**:
  - `create_game_embed()`: add `rewards: str | None = None` param; when non-empty, add embed field `name="🏆 Rewards", value=f"||{rewards}||", inline=False`
  - `format_game_announcement()`: add `rewards: str | None = None` param, pass through to `create_game_embed`
  - All callers of `format_game_announcement` (in `handlers.py`): pass `rewards=game.rewards`

  **`shared/message_formats.py`**:
  - `DMFormats`: add `rewards_reminder(game_title, game_id, edit_url)` static method
  - `DMPredicates`: add matching predicate

  **`services/bot/events/handlers.py`**:
  - Import `get_config` from `services.bot.config`
  - `_handle_post_transition_actions()`: add COMPLETED branch — when `remind_host_rewards` and no `rewards`, send DM using `DMFormats.rewards_reminder`

  **`frontend/src/types/index.ts`**:
  - `GameSession`: add `rewards?: string | null`, `remind_host_rewards?: boolean`, `archive_channel_id?: string | null`
  - `GameTemplate`: add `remind_host_rewards?: boolean`

  **`frontend/src/components/GameForm.tsx`**:
  - `GameFormData`: add `rewards: string`, `remindHostRewards: boolean`
  - Add rewards `TextField` (multiline) — only rendered when `mode === 'edit' && initialData?.status !== 'SCHEDULED'`
  - Add `remindHostRewards` MUI `Checkbox` with label — always visible in both create and edit modes
  - Add `onSaveAndArchive?: (data: GameFormData) => void` prop
  - "Save and Archive" button: only rendered when `onSaveAndArchive` provided AND `formData.rewards` non-empty AND `initialData?.archive_channel_id` non-empty

  **`frontend/src/pages/EditGame.tsx`**:
  - `handleSubmit`: include `rewards` and `remind_host_rewards` in payload
  - `handleSaveAndArchive`: same as `handleSubmit` but also includes `archive_delay_seconds: 1`
  - Pass `onSaveAndArchive={handleSaveAndArchive}` to `GameForm`

  **`frontend/src/pages/GameDetails.tsx`**:
  - After description section: if `game.rewards`, render a spoiler component (blur/click-to-reveal)

  **`frontend/src/components/GameCard.tsx`**:
  - If `game.rewards`, show a small spoiler indicator (e.g. "🏆 Rewards available")

- **Dependencies**: Bug fix from doc 01 must be implemented first
- **Success Criteria**:
  - Rewards field persists and returns from API
  - Rewards textarea hidden on SCHEDULED edit page, visible on IN_PROGRESS/COMPLETED/ARCHIVED
  - `remind_host_rewards` checkbox visible on all edit/create pages
  - Save and Archive button appears when `rewards` non-empty and `archive_channel_id` non-empty
  - Save and Archive triggers archival within ~1 second
  - Discord embed shows `||rewards||` spoiler field when rewards set
  - Discord description is trimmed if embed would exceed limit
  - Web display shows blur spoiler for rewards
  - Bot sends host DM at COMPLETED when `remind_host_rewards = True` and `rewards` is empty

### Integration Tests

New file: `tests/integration/test_rewards_fields.py`

- `test_rewards_field_persists_through_game_update` — Create game via API, update `rewards` field, fetch game, assert `rewards` returned in response
- `test_remind_host_rewards_propagates_from_template_to_game` — Set `remind_host_rewards = True` on template, create game from template, verify game has `remind_host_rewards = True`
- `test_clone_game_does_not_copy_rewards` — Create game with `rewards = "gold coins"`, clone it, verify cloned game has `rewards = None`
- `test_clone_game_copies_remind_host_rewards` — Create game with `remind_host_rewards = True`, clone it, verify cloned game has `remind_host_rewards = True`
- `test_save_and_archive_creates_archived_schedule` — Create game in COMPLETED state with `archive_channel_id` and no existing ARCHIVED schedule, update via API with `archive_delay_seconds = 1`, verify `game_status_schedule` row for ARCHIVED is created with `transition_time ≈ now + 1s`
- `test_save_and_archive_updates_existing_archived_schedule` — Create game in COMPLETED state with an existing ARCHIVED schedule set far in future, update via API with `archive_delay_seconds = 1`, verify schedule `transition_time` is updated to `≈ now + 1s`
- `test_archive_delay_seconds_not_in_game_update_for_non_archive_case` — Verify updating a game without `archive_delay_seconds` does not affect existing ARCHIVED schedule

### E2E Tests

New file: `tests/e2e/test_game_rewards.py`

- `test_save_and_archive_archives_game_within_seconds` — Create game in IN_PROGRESS state (via DB + status schedule manipulation), update via API with `rewards = "magic sword"` and `archive_delay_seconds = 1`, wait for ARCHIVED status in DB (within 15s), verify Discord message was deleted from original channel and (if archive channel configured) reposted to archive channel; verify embed in archive channel contains `||magic sword||`
- `test_rewards_reminder_dm_sent_on_completion_when_empty` — Create game with `remind_host_rewards = True` and `rewards = None`, trigger COMPLETED transition (via status schedule with `transition_time = now`), wait for DM to host Discord user containing the game title and edit link, verify DM not sent if `rewards` is already populated
- `test_discord_embed_shows_rewards_spoiler` — Create game with pre-set `rewards`, trigger game announcement (or refresh), verify Discord message embed contains a field with `||...||` formatted value
