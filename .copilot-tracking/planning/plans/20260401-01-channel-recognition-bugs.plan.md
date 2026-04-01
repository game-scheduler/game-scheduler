---
applyTo: '.copilot-tracking/changes/20260401-01-channel-recognition-bugs-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Channel Recognition Bug Fixes

## Overview

Fix three bugs in channel name recognition and display: emoji/Unicode in channel
names is rejected by the regex, `<#snowflake>` input is not handled, and clicking
a suggestion chip does not update the Location field; also add `where_display` so
the web UI renders human-readable channel names instead of raw `<#id>` tokens.

## Objectives

- Accept emoji and Unicode in channel names entered as `#channel-name`
- Silently accept `<#id>` tokens when the ID is valid in the guild
- Clicking a suggestion chip populates the Location field with the channel name
- `GameCard`, `GameDetails`, and the edit form show human-readable channel names
- Edit path calls the channel resolver the same way create does

## Research Summary

### Project Files

- `services/api/services/channel_resolver.py` - Core resolver with regex bugs
- `services/api/services/games.py` - `create_game` (resolver called) vs `update_game` (resolver absent)
- `services/api/routes/games.py` - `_build_game_response` for schema and display
- `shared/schemas/game.py` - `GameResponse` to add `where_display` field
- `shared/discord/client.py` - `get_guild_channels` and `fetch_channel_name_safe` helpers
- `frontend/src/types/index.ts` - `GameSession` type
- `frontend/src/components/GameCard.tsx` - Renders `game.where` as raw text (line 186)
- `frontend/src/pages/GameDetails.tsx` - Renders `game.where` as raw text (line 313)
- `frontend/src/components/GameForm.tsx` - Pre-populates and handles suggestion clicks
- `frontend/src/pages/CreateGame.tsx` - Reference for 422 channel error handling pattern
- `frontend/src/pages/EditGame.tsx` - Missing channel error handling

### External References

- #file:../research/20260401-01-channel-recognition-bugs-research.md - Comprehensive bug analysis and fix specifications

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/reactjs.instructions.md - React conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD workflow (xfail for bug fixes)

## Implementation Checklist

### [x] Phase 1: Channel Resolver Unit Tests and Fixes (TDD)

- [x] Task 1.1: Write xfail regression tests for all resolver changes
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 11-30)

- [x] Task 1.2: Fix hashtag regex to accept emoji/Unicode (Bug 1 GREEN)
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 31-46)

- [x] Task 1.3: Add `<#snowflake>` input handling (Bug 2 GREEN)
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 47-62)

- [x] Task 1.4: Add `render_where_display` function (GREEN)
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 63-85)

### [x] Phase 2: Backend Schema and API Response (TDD)

- [x] Task 2.1: Write xfail test for `where_display` in `_build_game_response`
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 88-102)

- [x] Task 2.2: Add `where_display` field to `GameResponse`
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 103-119)

- [x] Task 2.3: Populate `where_display` in `_build_game_response` (GREEN)
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 120-142)

### [ ] Phase 3: Backend — Edit Path (TDD)

- [ ] Task 3.1: Write xfail test for `update_game` channel resolution
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 145-161)

- [ ] Task 3.2: Add resolver to `update_game` (GREEN)
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 162-179)

### [ ] Phase 4: Frontend — Types and Display

- [ ] Task 4.1: Add `where_display` to `GameSession` type
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 182-195)

- [ ] Task 4.2: Render `where_display` in `GameCard` and `GameDetails`
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 196-213)

- [ ] Task 4.3: Update `GameForm` pre-populate and suggestion click handler (Bug 3 GREEN)
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 214-237)

### [ ] Phase 5: Frontend — EditGame 422 Handling

- [ ] Task 5.1: Add `channelValidationErrors` state to `EditGame`
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 240-255)

- [ ] Task 5.2: Parse channel errors from 422 response in `EditGame`
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 256-272)

- [ ] Task 5.3: Pass channel validation props to `GameForm` in `EditGame`
  - Details: .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md (Lines 273-303)

## Dependencies

- Python 3.12+, FastAPI, pytest
- React 18+, TypeScript 5, Vitest

## Success Criteria

- `#🍻tavern-generalchat` in Location resolves correctly at both create and edit time
- `<#406497579061215235>` in Location is silently accepted when the channel ID is valid in the guild
- Clicking a suggestion chip populates the Location field with the channel name
- `GameCard` and `GameDetails` render human-readable channel names, not `<#id>` tokens
- Edit form pre-populates Location with the human-readable channel name
- All unit tests pass with `xfail` markers removed after each fix
