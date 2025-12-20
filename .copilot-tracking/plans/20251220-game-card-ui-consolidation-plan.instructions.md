---
applyTo: ".copilot-tracking/changes/20251220-game-card-ui-consolidation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Card UI Consolidation

## Overview

Consolidate the UI layout between web GameDetails page and Discord bot game card to present a unified, consistent user experience with standardized field order and layout structure.

## Objectives

- Create visual consistency between web and Discord card layouts
- Improve information hierarchy by moving host to top of both displays
- Remove redundant UI elements (export button, separate max players display)
- Consolidate related information on single lines (When + Calendar, Location context)
- Ensure both interfaces follow identical field order

## Research Summary

### Project Files

- [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Web game details page with current layout structure
- [frontend/src/components/GameCard.tsx](frontend/src/components/GameCard.tsx) - Summary card component with host avatar already displayed
- [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Discord embed formatter with author field and calendar link
- [frontend/src/components/ExportButton.tsx](frontend/src/components/ExportButton.tsx) - Calendar export button to be replaced with link

### External References

- #file:../research/20251220-game-card-ui-consolidation-research.md - Comprehensive analysis of current layouts and target structure
- [frontend/src/types/index.ts](frontend/src/types/index.ts) - GameSession and Participant interfaces with avatar_url field

### Standards References

- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript development conventions
- #file:../../.github/instructions/python.instructions.md - Python coding standards for bot formatter

## Implementation Checklist

### [ ] Phase 1: Web GameDetails Page Restructuring

- [ ] Task 1.1: Move host section to top with avatar display
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 15-32)

- [ ] Task 1.2: Consolidate When field with calendar link
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 34-50)

- [ ] Task 1.3: Add location context display (server + channel)
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 52-67)

- [ ] Task 1.4: Remove separate max players display
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 69-82)

- [ ] Task 1.5: Update Participants component to show count format
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 84-100)

- [ ] Task 1.6: Remove ExportButton component usage
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 102-115)

### [ ] Phase 2: Discord Bot Card Field Reorganization

- [ ] Task 2.1: Verify and maintain author field with host avatar
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 119-135)

- [ ] Task 2.2: Reorganize embed fields to match web layout order
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 137-163)

- [ ] Task 2.3: Consolidate location display with guild context
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 165-180)

- [ ] Task 2.4: Update participants field format to match web display
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 182-196)

### [ ] Phase 3: Validation and Testing

- [ ] Task 3.1: Visual consistency verification
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 200-215)

- [ ] Task 3.2: Update frontend tests
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 217-230)

- [ ] Task 3.3: Update bot formatter tests
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 232-245)

## Dependencies

- Material-UI components (Avatar, Chip, Typography, Box) already in use
- React Router for navigation
- ExportButton API endpoint `/api/v1/export/game/{gameId}` already functional
- Discord.py embed formatting
- ParticipantList component

## Success Criteria

- Web and Discord displays follow identical field order
- Host with avatar displays at top in both interfaces
- Calendar link appears inline with When timestamp on web page
- Max players consolidated into participant count display (X/N format)
- ExportButton component removed from GameDetails page
- Location shows server_name and channel_name together in both interfaces
- All existing functionality preserved (join, leave, edit, cancel, export calendar)
- Tests pass for both web and bot components
