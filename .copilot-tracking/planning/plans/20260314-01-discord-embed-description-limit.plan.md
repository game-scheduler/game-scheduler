---
applyTo: '.copilot-tracking/changes/20260314-01-discord-embed-description-limit-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Embed Description Length Fix

## Overview

Align the description character limit consistently across all layers (API, frontend, Discord embed) to 2,000 characters, replacing the current 97-char embed truncation with a dynamic trim that only activates if the total embed exceeds Discord's 6,000-char hard limit.

## Objectives

- Replace `MAX_STRING_DISPLAY_LENGTH` with purpose-named constants in `shared/utils/limits.py`
- Remove the hardcoded 97-char description truncation from the bot formatter
- Add dynamic embed trimming that respects Discord's 6,000-char total limit
- Align API schema `max_length` to 2,000 on all description fields
- Align frontend form validation to 2,000 chars consistently

## Research Summary

### Project Files

- `shared/utils/limits.py` — defines `MAX_STRING_DISPLAY_LENGTH = 100`, the source of the 97-char truncation
- `services/bot/formatters/game_message.py` — `_prepare_description_and_urls` applies the truncation; `create_game_embed` assembles the embed
- `shared/discord/game_embeds.py` — hardcoded `[:100]` in `build_game_list_embed`
- `shared/schemas/game.py` and `shared/schemas/template.py` — `max_length=4000` on description fields
- `frontend/src/constants/ui.ts` — `MAX_DESCRIPTION_LENGTH: 4000`
- `frontend/src/components/GameForm.tsx` — local `MAX_DESCRIPTION_LENGTH = 2000` constant (duplicated)

### External References

- #file:../research/20260314-01-discord-embed-description-limit-research.md — full research with Discord API limits, character budget analysis, and recommended implementation

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/typescript-5-es2022.instructions.md — TypeScript conventions

## Implementation Checklist

### [ ] Phase 1: Update Shared Constants

- [ ] Task 1.1: Replace `MAX_STRING_DISPLAY_LENGTH` with four focused constants in `shared/utils/limits.py`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 11-23)

### [ ] Phase 2: Bot Formatter Dynamic Truncation (TDD)

- [ ] Task 2.1: Create `_trim_embed_if_needed` stub in `services/bot/formatters/game_message.py`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 27-39)

- [ ] Task 2.2: Write xfail tests for dynamic truncation in `tests/services/bot/formatters/test_game_message.py`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 41-56)

- [ ] Task 2.3: Implement `_trim_embed_if_needed` and remove xfail markers
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 58-71)

- [ ] Task 2.4: Refactor and add edge-case tests
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 73-84)

### [ ] Phase 3: game_embeds.py Snippet Constant

- [ ] Task 3.1: Replace hardcoded `[:100]` with `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH` in `shared/discord/game_embeds.py`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 88-99)

### [ ] Phase 4: API Schema Limits

- [ ] Task 4.1: Update description `max_length` to 2,000 in `shared/schemas/game.py` and `shared/schemas/template.py`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 103-115)

- [ ] Task 4.2: Write tests verifying the 2,000-char schema limit
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 117-128)

### [ ] Phase 5: Frontend Constant Alignment

- [ ] Task 5.1: Update `MAX_DESCRIPTION_LENGTH` to `2000` in `frontend/src/constants/ui.ts`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 132-143)

- [ ] Task 5.2: Replace local constant in `GameForm.tsx` with `UI.MAX_DESCRIPTION_LENGTH`
  - Details: .copilot-tracking/planning/details/20260314-01-discord-embed-description-limit-details.md (Lines 145-157)

## Dependencies

- discord.py (already installed)
- pytest (already installed)

## Success Criteria

- All existing tests pass
- New formatter tests cover the dynamic trim path (short description, at-limit, over-limit)
- API rejects descriptions over 2,000 chars with 422
- Frontend forms cap input at 2,000 chars consistently via `UI.MAX_DESCRIPTION_LENGTH`
- `len(embed)` never exceeds 6,000 in any constructed embed
