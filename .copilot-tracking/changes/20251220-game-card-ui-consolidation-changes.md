# Implementation Changes: Game Card UI Consolidation - Web and Discord

**Date:** December 20, 2025
**Plan:** [20251220-game-card-ui-consolidation-plan.instructions.md](../plans/20251220-game-card-ui-consolidation-plan.instructions.md)
**Details:** [20251220-game-card-ui-consolidation-details.md](../details/20251220-game-card-ui-consolidation-details.md)

## Implementation Progress

### Added Files

### Modified Files

- frontend/src/pages/GameDetails.tsx - Restructured layout with host+avatar at top, consolidated When+calendar link, added location context with server and channel, consolidated participant count format (X/N), removed ExportButton import, made signup instructions host-only visible
- frontend/src/components/ParticipantList.tsx - Removed redundant "X/Y players" count display (now only in Participants heading)
- frontend/src/types/index.ts - Added guild_name field to GameSession interface
- shared/schemas/game.py - Added guild_name field to GameResponse schema
- services/api/routes/games.py - Added guild_name fetching from Discord API and included in GameResponse
- services/bot/formatters/game_message.py - Reorganized and consolidated Discord embed fields for compact display: removed "When" label (timestamp displays directly), combined Duration and Where into main field with timestamp and calendar link, changed calendar link text from "Download Calendar" to "Download", removed separate Players field (count now in Participants heading as "Participants (X/N)"), removed Signup Instructions field, removed embed timestamp to show only status in footer. All information now in single main field with clean line breaks.
- tests/services/bot/formatters/test_game_message.py - Updated test to check for timestamp format instead of "When" label, and verify participant count in Participants heading

### Removed Files

### Notes

**Phase 1 Completed:** All web layout restructuring tasks completed and verified working
- Moved signup instructions to appear just before Participants section
- Added guild name + # prefix to channel name in Location field (fetched from Discord API)
- Moved Duration field directly below When field
- Combined Duration and Reminders on one line with proper spacing
- Removed separate Players count display (now only in Participants heading)
- Removed redundant "1/8 players" count from ParticipantList component
- All changes verified to display correctly in browser

**Phase 2 Completed:** All frontend tests pass (71 tests), no linting errors, responsive design maintained through MUI components

**API Enhancement:** Added guild_name field to GameResponse schema and fetching from Discord API with caching

**Phase 3 Completed:** Discord bot card field reorganization completed
- Verified host author field with avatar already implemented correctly (lines 118-123)
- Reorganized embed fields to match web layout order:
  1. When field includes calendar link inline (no separate Calendar field)
  2. Duration field with inline=True (label and value on same line)
  3. Where field with inline=True (label and value on same line)
  4. Voice Channel follows Where
  5. Participants heading includes count as "Participants (X/N)" - removed separate Players field
  6. Host field only shown when no display name provided (backward compatibility)
  7. Participants list shows "No participants yet" when empty
  8. Waitlist maintained with clear "(N)" count indicator
  9. Signup Instructions field removed to reduce clutter
- Vertical space optimized: Duration and Where use inline=True for compact display (2 lines instead of 4)

**Phase 4 Completed:** All tests passing (27 tests in test_game_message.py), field order verified
