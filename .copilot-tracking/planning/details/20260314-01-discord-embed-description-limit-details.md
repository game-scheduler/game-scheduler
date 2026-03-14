<!-- markdownlint-disable-file -->

# Task Details: Discord Embed Description Length Fix

## Research Reference

**Source Research**: #file:../research/20260314-01-discord-embed-description-limit-research.md

## Phase 1: Update Shared Constants

### Task 1.1: Add new constants to `shared/utils/limits.py`

Replace `MAX_STRING_DISPLAY_LENGTH = 100` with four focused constants that clearly express their individual purposes.

- **Files**:
  - `shared/utils/limits.py` — add `DISCORD_EMBED_TOTAL_LIMIT = 6000`, `DISCORD_EMBED_TOTAL_SAFE_LIMIT = 5900`, `MAX_DESCRIPTION_LENGTH = 2000`, `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH = 100`; remove `MAX_STRING_DISPLAY_LENGTH`
- **Success**:
  - All four constants are present; `MAX_STRING_DISPLAY_LENGTH` is removed
  - All existing references to `MAX_STRING_DISPLAY_LENGTH` updated to the appropriate new constant
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 63-92) — inconsistent limits table and recommended constants
- **Dependencies**:
  - None

## Phase 2: Bot Formatter Dynamic Truncation (TDD)

### Task 2.1: Create stub in `services/bot/formatters/game_message.py`

Remove the `_prepare_description_and_urls` 97-char truncation. Add a private stub `_trim_embed_if_needed(embed)` that raises `NotImplementedError`. Import `DISCORD_EMBED_TOTAL_SAFE_LIMIT` from `shared.utils.limits`.

- **Files**:
  - `services/bot/formatters/game_message.py` — remove hardcoded 97-char truncation; add `_trim_embed_if_needed` stub raising `NotImplementedError`; import `DISCORD_EMBED_TOTAL_SAFE_LIMIT` from `shared.utils.limits`
- **Success**:
  - `_trim_embed_if_needed` exists and raises `NotImplementedError`
  - Old truncation logic removed
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 94-103) — recommended restructuring of `create_game_embed`
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Write failing (xfail) tests for dynamic truncation

Write tests with real assertions marked `@pytest.mark.xfail(strict=True)` in `tests/services/bot/formatters/test_game_message.py`:

- Short description (< 2,000 chars): embed description unchanged after embed construction
- Description exactly 4,096 chars with total embed under 5,900: description preserved in full
- Total embed length exceeding 5,900 chars: description trimmed to fit, ending with `"..."`

- **Files**:
  - `tests/services/bot/formatters/test_game_message.py` — add three `@pytest.mark.xfail(strict=True)` test cases
- **Success**:
  - Tests run and are marked as expected failures (xfail)
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 115-127) — success criteria and test cases
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Implement dynamic truncation and remove xfail markers

Implement `_trim_embed_if_needed(embed)` to trim `embed.description` when `len(embed) > DISCORD_EMBED_TOTAL_SAFE_LIMIT`. Remove `@pytest.mark.xfail` markers from the tests written in Task 2.2. Do NOT modify test assertions.

- **Files**:
  - `services/bot/formatters/game_message.py` — implement `_trim_embed_if_needed`; call it at the end of `create_game_embed`
  - `tests/services/bot/formatters/test_game_message.py` — remove `@pytest.mark.xfail` decorators only
- **Success**:
  - All three new tests pass (not xfail)
  - All pre-existing formatter tests still pass
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 97-103) — dynamic trim algorithm
- **Dependencies**:
  - Task 2.2 complete

### Task 2.4: Refactor and add edge-case tests

Add remaining edge-case tests: `None`/empty `description`, and a description exactly at 2,000 chars passing through untruncated in a normal game scenario.

- **Files**:
  - `tests/services/bot/formatters/test_game_message.py` — add edge-case tests
- **Success**:
  - All tests pass with no xfail markers remaining
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 56-62) — participant character budget confirming 2,000-char descriptions are safe
- **Dependencies**:
  - Task 2.3 complete

## Phase 3: game_embeds.py Snippet Constant

### Task 3.1: Replace hardcoded `[:100]` with `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH`

In `shared/discord/game_embeds.py`, replace `game.description[:100]` with `game.description[:GAME_LIST_DESCRIPTION_SNIPPET_LENGTH]`, importing the constant from `shared.utils.limits`.

- **Files**:
  - `shared/discord/game_embeds.py` — import `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH`; replace hardcoded `[:100]`
- **Success**:
  - No magic number `100` for description snippets in `game_embeds.py`
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 16-18) — hardcoded `[:100]` in `build_game_list_embed`
- **Dependencies**:
  - Phase 1 complete

## Phase 4: API Schema Limits

### Task 4.1: Update description `max_length` to 2,000 in API schemas

Change `max_length=4000` to `max_length=2000` on `description` fields in `GameCreateRequest`, `GameUpdateRequest`, `TemplateCreateRequest`, and `TemplateUpdateRequest`.

- **Files**:
  - `shared/schemas/game.py` — update `max_length` on `GameCreateRequest.description` and `GameUpdateRequest.description`
  - `shared/schemas/template.py` — update `max_length` on `TemplateCreateRequest.description` and `TemplateUpdateRequest.description`
- **Success**:
  - API returns 422 for descriptions over 2,000 chars
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 19-24) — current schema `max_length` values
- **Dependencies**:
  - Phase 1 complete

### Task 4.2: Write tests verifying the 2,000-char schema limit

Add tests confirming that a 2,001-character description is rejected (422) and a 2,000-character description is accepted.

- **Files**:
  - `tests/shared/schemas/` — add schema validation tests for game and template description limits
- **Success**:
  - 2,001-char descriptions are rejected; 2,000-char descriptions are accepted
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 122-127) — success criteria
- **Dependencies**:
  - Task 4.1 complete

## Phase 5: Frontend Constant Alignment

### Task 5.1: Update `MAX_DESCRIPTION_LENGTH` in `frontend/src/constants/ui.ts`

Change `MAX_DESCRIPTION_LENGTH: 4000` to `2000` in `frontend/src/constants/ui.ts`.

- **Files**:
  - `frontend/src/constants/ui.ts` — update `MAX_DESCRIPTION_LENGTH` from `4000` to `2000`
- **Success**:
  - `UI.MAX_DESCRIPTION_LENGTH === 2000` at runtime
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 29-30) — `MAX_DESCRIPTION_LENGTH: 4000` in `ui.ts`
- **Dependencies**:
  - None

### Task 5.2: Remove duplicated local constant in `GameForm.tsx`

Replace the local `MAX_DESCRIPTION_LENGTH = 2000` constant in `frontend/src/components/GameForm.tsx` with `UI.MAX_DESCRIPTION_LENGTH`, matching the pattern already used by `TemplateForm.tsx`.

- **Files**:
  - `frontend/src/components/GameForm.tsx` — remove local constant; import and use `UI.MAX_DESCRIPTION_LENGTH`
- **Success**:
  - `GameForm.tsx` has no local `MAX_DESCRIPTION_LENGTH`
  - Both form components derive the limit from the same source
- **Research References**:
  - #file:../research/20260314-01-discord-embed-description-limit-research.md (Lines 25-30) — frontend form constant analysis
- **Dependencies**:
  - Task 5.1 complete

## Dependencies

- discord.py (already installed)
- pytest (already installed)

## Success Criteria

- All existing tests pass
- New formatter tests cover the dynamic trim path
- API rejects descriptions over 2,000 chars
- Frontend forms cap input at 2,000 chars consistently
- `len(embed)` never exceeds 6,000 in any constructed embed
