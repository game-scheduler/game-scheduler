---
applyTo: ".copilot-tracking/changes/20251220-game-card-ui-consolidation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Card UI Consolidation - Web and Discord

## Overview

Consolidate the UI layout between the web game details page and Discord bot game card to present a unified, consistent user experience with standardized field order and layout structure.

## Objectives

- Move host information with avatar to the top of both web and Discord card displays
- Consolidate "When" timestamp with calendar link on the same line
- Add location context showing server name and channel together
- Remove redundant UI elements (export button, separate max players display)
- Update participant count display to unified format (X/N)
- Ensure visual consistency across web and Discord interfaces

## Research Summary

### Project Files

- [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Web game details page with current layout structure
- [frontend/src/components/GameCard.tsx](frontend/src/components/GameCard.tsx) - Web game card component with existing consolidation example
- [frontend/src/components/ExportButton.tsx](frontend/src/components/ExportButton.tsx) - Calendar export button to be replaced
- [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Discord embed formatter for game announcements
- [frontend/src/types/index.ts](frontend/src/types/index.ts) - TypeScript GameSession and Participant interfaces

### External References

- #file:../research/20251220-game-card-ui-consolidation-research.md - Complete UI consolidation research with current state analysis and target layout specifications

### Standards References

- #file:../../.github/instructions/reactjs.instructions.md - React component development guidelines
- #file:../../.github/instructions/python.instructions.md - Python code conventions for Discord formatter
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Self-documenting code practices
- #file:../../.github/instructions/coding-best-practices.instructions.md - Correctness, modularity, and testing standards

## Implementation Checklist

### [x] Phase 1: Web GameDetails Page - Layout Restructuring

- [x] Task 1.1: Move host section to top of game details
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 23-45)

- [x] Task 1.2: Consolidate When + Calendar link on same line
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 47-70)

- [x] Task 1.3: Add location context with server and channel display
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 72-95)

- [x] Task 1.4: Consolidate participant count and remove max players line
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 97-120)

- [x] Task 1.5: Remove ExportButton and replace with calendar link
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 122-140)

- [x] Task 1.6: Update signup instructions display for host-only visibility
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 142-160)

### [x] Phase 2: Web GameDetails Page - Testing and Validation

- [x] Task 2.1: Test GameDetails page layout changes
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 162-180)

- [x] Task 2.2: Verify responsive design across screen sizes
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 182-195)

### [x] Phase 3: Discord Bot Card - Field Reorganization

- [x] Task 3.1: Verify and document host author field with avatar
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 197-220)

- [x] Task 3.2: Reorganize embed fields to match web layout order
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 222-250)

- [x] Task 3.3: Update location/channel field display
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 252-275)

- [x] Task 3.4: Consolidate participant count format
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 277-295)

- [x] Task 3.5: Remove or adjust waitlist display
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 297-315)

### [x] Phase 4: Discord Bot Card - Testing and Validation

- [x] Task 4.1: Test game message formatting
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 317-340)

- [x] Task 4.2: Verify Discord embed rendering
  - Details: .copilot-tracking/details/20251220-game-card-ui-consolidation-details.md (Lines 342-360)

## Dependencies

- React/TypeScript for web frontend changes
- MUI (Material-UI) components library
- Python discord.py library for Discord bot changes
- Existing calendar link generation functionality
- Participant data structure with avatar_url field already present

## Success Criteria

- Web GameDetails page displays fields in unified order matching Discord card
- Host avatar displays at top of both web and Discord card layouts
- Calendar link appears next to When timestamp (web) or in header (Discord)
- Max players consolidated into participant count display as "X/N"
- Export button removed from web interface
- Location displays server name and channel name together
- Signup instructions only shown to host
- All changes maintain visual consistency and responsive design
- Unit tests updated and passing
- No breaking changes to existing API contracts
