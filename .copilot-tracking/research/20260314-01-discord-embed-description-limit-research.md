<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Embed Description Length Fix

## Research Executed

### File Analysis

- `shared/utils/limits.py`
  - `MAX_STRING_DISPLAY_LENGTH = 100` — used as the truncation limit for embed description
  - Also used as the snippet length in game list embed field values
- `services/bot/formatters/game_message.py`
  - `_prepare_description_and_urls` truncates description to `MAX_STRING_DISPLAY_LENGTH` before embed is built
  - `create_game_embed` assembles: title, description, author, thumbnail, image, game time fields, participant fields, footer
  - `discord.Embed.__len__` returns total char count across all text fields
- `shared/discord/game_embeds.py`
  - `build_game_list_embed` uses hardcoded `game.description[:100]` for snippet in field values
  - Called by `/list-games` slash command
- `shared/schemas/game.py`
  - `GameCreateRequest.description`: `max_length=4000`
  - `GameUpdateRequest.description`: `max_length=4000`
- `shared/schemas/template.py`
  - `TemplateCreateRequest.description`: `max_length=4000`
  - `TemplateUpdateRequest.description`: `max_length=4000`
- `frontend/src/components/GameForm.tsx`
  - Local constant `MAX_DESCRIPTION_LENGTH = 2000` (soft validation only, no HTML `maxLength` attribute on textarea)
- `frontend/src/components/TemplateForm.tsx`
  - Uses `UI.MAX_DESCRIPTION_LENGTH` from constants
- `frontend/src/constants/ui.ts`
  - `MAX_DESCRIPTION_LENGTH: 4000`

### External Research

- #fetch:https://docs.discord.com/developers/resources/message#embed-object-embed-limits
  - `description`: max **4,096 characters**
  - `title`: max 256 characters
  - `field.value`: max 1,024 characters
  - `footer.text`: max 2,048 characters
  - `author.name`: max 256 characters
  - **Total across all embeds in a message: 6,000 characters**
  - Limits measured against raw strings (not rendered). Mention `<@123456789012345678>` is ~21 chars.
  - Violating limits returns `400 Bad Request`

### Project Conventions

- Standards referenced: `shared/utils/limits.py` for shared numeric constants
- `discord.Embed.__len__` is available in discord.py and counts all text fields

## Key Discoveries

### Current Truncation Flow

Description is truncated to 97 chars in `_prepare_description_and_urls` before the embed is built.
This is far below the 4,096 per-field and 6,000 total Discord limits.

### Participant Character Budget

- Max players capped at 100 (`le=100` in schema)
- Each mention: `<@XXXXXXXXXXXXXXXXXX>` ≈ 21 chars
- 100 participants × 21 chars ≈ 2,100 chars in participant fields
- At max participants + 2,000 char description + other fields ≈ ~4,500 chars total — well under 6,000

### Inconsistent Description Limits Across the Stack

| Layer                         | Current limit                           |
| ----------------------------- | --------------------------------------- |
| Database (`sa.Text()`)        | Unlimited                               |
| API schema (`max_length=`)    | 4,000                                   |
| `GameForm.tsx` validation     | 2,000                                   |
| `TemplateForm.tsx` validation | 4,000 (via `UI.MAX_DESCRIPTION_LENGTH`) |
| Discord embed display         | ~97 chars                               |

## Recommended Approach

**Dynamic truncation with 2,000-character API/form limit alignment.**

Build the embed fully (description capped at 4,096 per Discord's field limit), then trim the description only if `len(embed) > 5900` (6,000 − 100 fudge factor for hidden characters). Simultaneously align the API schemas and frontend forms to a consistent 2,000-character maximum so the vast majority of descriptions are displayed in full.

## Implementation Guidance

- **Objectives**:
  - Show full description on Discord for typical games
  - Never send an embed exceeding Discord's 6,000-char total limit
  - Consistent 2,000-char limit across API, web forms, and effective Discord display

- **Key Tasks**:
  1. **`shared/utils/limits.py`** — Replace `MAX_STRING_DISPLAY_LENGTH = 100` with two constants:
     - `DISCORD_EMBED_TOTAL_LIMIT = 6000`
     - `DISCORD_EMBED_TOTAL_SAFE_LIMIT = 5900` (fudge factor of 100)
     - `MAX_DESCRIPTION_LENGTH = 2000` (shared by API schemas and frontend)
     - `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH = 100` (keep list snippets short)

  2. **`services/bot/formatters/game_message.py`** — Restructure `create_game_embed`:
     - Remove truncation from `_prepare_description_and_urls` (or remove the method entirely if URLs are the only other thing it does)
     - Cap description at 4,096 before setting on embed (Discord per-field limit)
     - After all fields are added, apply dynamic trim:
       ```python
       excess = len(embed) - DISCORD_EMBED_TOTAL_SAFE_LIMIT
       if excess > 0 and embed.description:
           trim_to = len(embed.description) - excess - 3
           embed.description = embed.description[:trim_to] + "..."
       ```

  3. **`shared/discord/game_embeds.py`** — Replace hardcoded `[:100]` with `[:GAME_LIST_DESCRIPTION_SNIPPET_LENGTH]`

  4. **`shared/schemas/game.py`** — Change `max_length=4000` → `max_length=2000` on `GameCreateRequest.description` and `GameUpdateRequest.description`

  5. **`shared/schemas/template.py`** — Change `max_length=4000` → `max_length=2000` on `TemplateCreateRequest.description` and `TemplateUpdateRequest.description`

  6. **`frontend/src/constants/ui.ts`** — Change `MAX_DESCRIPTION_LENGTH: 4000` → `2000`

  7. **`frontend/src/components/GameForm.tsx`** — Replace local `MAX_DESCRIPTION_LENGTH = 2000` constant with `UI.MAX_DESCRIPTION_LENGTH` (removes duplication, consistent with template form)

  8. **`tests/services/bot/formatters/test_game_message.py`** — Add tests:
     - Short description passes through unchanged
     - Description exactly at 4,096 chars is not trimmed when total embed is under 5,900
     - Embed exceeding 5,900 total chars has description trimmed to fit, ending with `"..."`

- **Dependencies**: None — all changes are self-contained within the listed files

- **Success Criteria**:
  - All existing formatter tests pass
  - New tests cover the dynamic trim path
  - API rejects descriptions over 2,000 chars
  - Frontend forms cap input at 2,000 chars consistently
  - `len(embed)` never exceeds 6,000 in any constructed embed
