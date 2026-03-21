<!-- markdownlint-disable-file -->

# Task Details: Rewards Feature

## Research Reference

**Source Research**: #file:../research/20260321-02-rewards-feature-research.md

---

## Phase 1: Database Migration

### Task 1.1: Create Alembic migration for rewards fields

Add three new columns: `rewards TEXT NULL` on `game_sessions`, and `remind_host_rewards BOOLEAN NOT NULL DEFAULT FALSE` on both `game_sessions` and `game_templates`.

- **Files**:
  - `alembic/versions/20260321_add_rewards_fields.py` — new migration file
- **Success**:
  - Migration upgrades cleanly from current head (`20260311_add_archive_fields.py`)
  - Downgrade restores prior state
  - Columns present with correct types and defaults after `alembic upgrade head`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 143-170) — Implementation Guidance: migration details
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 7-22) — File Analysis: existing model patterns for nullable text and bool columns
- **Dependencies**:
  - Bug fix from research doc `20260321-01-*` must be implemented first (Save and Archive depends on it)

---

## Phase 2: Backend Models & Schemas

### Task 2.1: Update shared models

Add `rewards` and `remind_host_rewards` to `GameSession`; add `remind_host_rewards` to `GameTemplate` in the pre-populated/host-editable section.

- **Files**:
  - `shared/models/game.py` — add two mapped columns
  - `shared/models/template.py` — add one mapped column in the host-editable section
- **Success**:
  - `GameSession.rewards` is `Mapped[str | None]`, nullable Text column
  - `GameSession.remind_host_rewards` is `Mapped[bool]`, non-nullable, `server_default=text('false')`
  - `GameTemplate.remind_host_rewards` is `Mapped[bool]`, non-nullable, `server_default=text('false')`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 143-170) — Implementation Guidance: exact field definitions
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 38-41) — Project Conventions: model column patterns
- **Dependencies**:
  - Task 1.1 migration must exist before testing against a real database

### Task 2.2: Update shared schemas

Add `rewards` and `remind_host_rewards` to game schemas; add `archive_delay_seconds` to `GameUpdateRequest` (currently absent); add `remind_host_rewards` to template schemas.

- **Files**:
  - `shared/schemas/game.py` — update `GameUpdateRequest`, `GameCreateRequest`, `GameResponse`
  - `shared/schemas/template.py` — update `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, `TemplateListItem`
- **Success**:
  - `GameUpdateRequest` has `rewards: str | None = Field(None, max_length=2000)`, `remind_host_rewards: bool | None = None`, `archive_delay_seconds: int | None = Field(None, ge=0)`
  - `GameResponse` has `rewards: str | None`, `remind_host_rewards: bool`, `archive_channel_id: str | None`
  - All template schemas carry `remind_host_rewards` appropriately
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 143-200) — Implementation Guidance: schema field specifications
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 56-67) — Save and Archive API flow requiring `archive_delay_seconds`
- **Dependencies**:
  - Task 2.1 models completed

---

## Phase 3: API Service & Routes

### Task 3.1: Update game service layer

Wire the new fields through the service functions that create, update, and clone game sessions.

- **Files**:
  - `services/api/services/games.py` — update `_update_simple_text_fields`, `_update_remaining_fields`, `_build_game_session`, `clone_game`
- **Success**:
  - `_update_simple_text_fields()` handles `rewards`
  - `_update_remaining_fields()` handles `remind_host_rewards`
  - `_build_game_session()` copies `remind_host_rewards` from template
  - `clone_game()` copies `remind_host_rewards` and sets `rewards = None`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 143-220) — Implementation Guidance: service function changes
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 24-37) — Code Search Results: existing service structure
- **Dependencies**:
  - Tasks 2.1 and 2.2 completed

### Task 3.2: Update game API routes

Add form parameters and response fields to the game routes.

- **Files**:
  - `services/api/routes/games.py` — update `update_game` endpoint and `_build_game_response`
- **Success**:
  - `update_game` accepts `rewards`, `remind_host_rewards`, and `archive_delay_seconds` as form fields
  - `_build_game_response()` includes `rewards`, `remind_host_rewards`, `archive_channel_id` in the response
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 195-220) — Implementation Guidance: route changes
- **Dependencies**:
  - Tasks 2.2 and 3.1 completed

---

## Phase 4: Bot Formatters & Handlers

### Task 4.1: Update Discord embed formatter

Add the rewards spoiler field to the game announcement embed.

- **Files**:
  - `services/bot/formatters/game_message.py` — update `create_game_embed`, `format_game_announcement`, and all callers
- **Success**:
  - `create_game_embed(rewards=game.rewards)` adds `name="🏆 Rewards", value=f"||{rewards}||", inline=False` when `rewards` is non-empty
  - `_trim_embed_if_needed` continues to work correctly — `len(embed)` already accounts for all fields
  - All callers in `handlers.py` pass `rewards=game.rewards`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 68-101) — Discord Embed Spoiler: formatter changes and trim logic
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 195-215) — Implementation Guidance: formatter function signatures
- **Dependencies**:
  - Tasks 2.1 and 2.2 completed

### Task 4.2: Add DM rewards reminder

Add `DMFormats.rewards_reminder` and wire the COMPLETED transition handler to send it.

- **Files**:
  - `shared/message_formats.py` — add `rewards_reminder` static method to `DMFormats`
  - `services/bot/events/handlers.py` — import `get_config`, add COMPLETED branch in `_handle_post_transition_actions`
- **Success**:
  - `DMFormats.rewards_reminder(game_title, game_id, edit_url)` returns expected markdown string
  - When a game transitions to COMPLETED with `remind_host_rewards=True` and `rewards` empty/None, host receives a DM
  - No DM sent when `rewards` is non-empty
  - No DM sent when `remind_host_rewards=False`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 102-133) — DM Rewards Reminder: message format and handler logic
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 195-215) — Implementation Guidance: handler changes
- **Dependencies**:
  - Task 4.1 completed; `get_config` already available in `services.bot.config`

---

## Phase 5: Frontend

### Task 5.1: Update TypeScript types

Add rewards and remind_host_rewards fields to frontend type definitions.

- **Files**:
  - `frontend/src/types/index.ts` — update `GameSession` and `GameTemplate` interfaces
- **Success**:
  - `GameSession` has `rewards?: string | null`, `remind_host_rewards?: boolean`, `archive_channel_id?: string | null`
  - `GameTemplate` has `remind_host_rewards?: boolean`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 195-215) — Implementation Guidance: type definitions
- **Dependencies**:
  - No backend dependency for types, but implement after Phase 3 for full integration

### Task 5.2: Update GameForm component

Add rewards textarea (edit-only, status-gated) and remindHostRewards checkbox, plus "Save and Archive" button.

- **Files**:
  - `frontend/src/components/GameForm.tsx` — update `GameFormData`, add rewards field, checkbox, and Save and Archive button
- **Success**:
  - `rewards` textarea only rendered when `mode === 'edit'` and `initialData?.status` is not `'SCHEDULED'`
  - `remindHostRewards` checkbox always visible in create and edit modes
  - "Save and Archive" button only rendered when `onSaveAndArchive` prop provided AND `formData.rewards` non-empty AND `initialData?.archive_channel_id` non-empty
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 45-55) — Feature Requirements: UI visibility rules
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 195-215) — Implementation Guidance: GameForm changes
- **Dependencies**:
  - Task 5.1 types completed

### Task 5.3: Update EditGame page

Wire the new fields into the edit submission and add Save and Archive handler.

- **Files**:
  - `frontend/src/pages/EditGame.tsx` — update `handleSubmit`, add `handleSaveAndArchive`
- **Success**:
  - `handleSubmit` includes `rewards` and `remind_host_rewards` in PUT payload
  - `handleSaveAndArchive` includes same fields plus `archive_delay_seconds: 1`
  - `onSaveAndArchive={handleSaveAndArchive}` passed to `GameForm`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 56-67) — Save and Archive API Flow
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 195-215) — Implementation Guidance: EditGame changes
- **Dependencies**:
  - Tasks 5.1 and 5.2 completed

### Task 5.4: Update GameDetails and GameCard components

Add spoiler display for rewards on the game detail and card views.

- **Files**:
  - `frontend/src/pages/GameDetails.tsx` — add click-to-reveal blur spoiler for rewards
  - `frontend/src/components/GameCard.tsx` — add spoiler indicator when rewards present
- **Success**:
  - `GameDetails` renders rewards as a blurred box with "🏆 Rewards (click to reveal)" label; click removes blur
  - `GameCard` shows a "🏆 Rewards available" indicator when `game.rewards` is set
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 86-101) — Web Spoiler Implementation: CSS approach
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 45-55) — Feature Requirements: web display rules
- **Dependencies**:
  - Task 5.1 types completed

---

## Phase 6: Tests (TDD)

### Task 6.1: Integration tests

Create integration tests covering the new fields and Save and Archive flow. Write tests first (they will xfail), then implement until all pass.

- **Files**:
  - `tests/integration/test_rewards_fields.py` — new integration test file
- **Success**:
  - All integration tests listed in research pass
  - `test_rewards_field_persists_through_game_update`
  - `test_remind_host_rewards_propagates_from_template_to_game`
  - `test_clone_game_does_not_copy_rewards`
  - `test_clone_game_copies_remind_host_rewards`
  - `test_save_and_archive_creates_archived_schedule`
  - `test_save_and_archive_updates_existing_archived_schedule`
  - `test_archive_delay_seconds_not_in_game_update_for_non_archive_case`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 225-236) — Integration Tests: full test specifications
- **Dependencies**:
  - Phases 1-3 must be complete for integration tests to pass

### Task 6.2: E2E tests

Create E2E tests for end-to-end flows. Write tests first (they will xfail), then implement until all pass.

- **Files**:
  - `tests/e2e/test_game_rewards.py` — new E2E test file
- **Success**:
  - All E2E tests listed in research pass
  - `test_save_and_archive_archives_game_within_seconds`
  - `test_rewards_reminder_dm_sent_on_completion_when_empty`
  - `test_discord_embed_shows_rewards_spoiler`
- **Research References**:
  - #file:../research/20260321-02-rewards-feature-research.md (Lines 237-243) — E2E Tests: full test specifications
- **Dependencies**:
  - All prior phases must be complete for E2E tests to pass

---

## Dependencies

- Bug fix from `20260321-01-*` research/plan (Save and Archive prereq)
- Python/SQLAlchemy/Alembic (existing)
- Discord.py (existing)
- FastAPI + MUI (existing)

## Success Criteria

- All rewards fields persist correctly through API
- Save and Archive triggers archival within ~1 second
- Discord embed shows `||rewards||` spoiler field when rewards set
- Bot sends host DM at COMPLETED when `remind_host_rewards=True` and `rewards` is empty
- Web display shows blur spoiler for rewards
- All integration and E2E tests pass
