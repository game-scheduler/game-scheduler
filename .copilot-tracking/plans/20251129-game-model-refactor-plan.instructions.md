---
applyTo: ".copilot-tracking/changes/20251129-game-model-refactor-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Model Refactor (Remove min_players, Add where field)

## Overview

Refactor the game data model to remove the unused min_players field and add a where field for game location information.

## Objectives

- Remove min_players field from all layers (database, API, frontend, Discord bot)
- Add where field to all layers for location information
- Update display formats to show "X/max" instead of "X/min-max" for participant counts
- Display where field below "When" field in all interfaces
- Ensure all tests pass with updated model

## Research Summary

### Project Files

- shared/models/game.py - GameSession model with min_players field to remove
- shared/schemas/game.py - API schemas with min_players in request/response objects
- services/bot/formatters/game_message.py - Discord embed formatting for game announcements
- frontend/src/types/index.ts - TypeScript interfaces for GameSession
- frontend/src/pages/GameDetails.tsx - Game details display page
- frontend/src/components/GameCard.tsx - Game card component

### External References

- #file:../research/20251129-game-model-refactor-research.md - Complete impact analysis and field specifications

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices

## Implementation Checklist

### [x] Phase 1: Add where Field to Database (Safe - Optional Column)

- [x] Task 1.1: Create migration to add where column

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 18-34)

- [x] Task 1.2: Add where field to GameSession model

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 36-49)

- [x] Task 1.3: Run migration to add where column
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 51-61)

### [x] Phase 2: Add where Field to API Layer (with tests)

- [x] Task 2.1: Add where field to API schemas

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 63-78)

- [x] Task 2.2: Update service layer to handle where field

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 80-94)

- [x] Task 2.3: Update backend tests for where field

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 96-110)

- [x] Task 2.4: Run backend tests to verify where field
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 112-122)
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 112-122)

### [x] Phase 3: Add where Field to Discord Bot (with tests)

- [x] Task 3.1: Update game message formatter for where field

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 124-140)

- [x] Task 3.2: Update event handlers to pass where field

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 142-154)

- [x] Task 3.3: Run bot tests to verify where field
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 156-165)

### [x] Phase 4: Add where Field to Frontend (with tests)

- [x] Task 4.1: Add where field to TypeScript interfaces

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 167-179)

- [x] Task 4.2: Add where input to CreateGame and EditGame pages

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 181-198)

- [x] Task 4.3: Display where field in GameDetails page

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 200-212)

- [x] Task 4.4: Display where field in GameCard component

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 214-226)

- [x] Task 4.5: Update frontend tests for where field

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 228-240)

- [x] Task 4.6: Run frontend tests to verify where field
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 242-251)

### [x] Phase 5: Remove min_players from API Layer (with tests)

- [x] Task 5.1: Remove min_players from API schemas

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 253-267)

- [x] Task 5.2: Remove min_players validation from routes

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 269-281)

- [x] Task 5.3: Remove min_players validation from service layer

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 283-296)

- [x] Task 5.4: Update backend tests to remove min_players

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 298-314)

- [x] Task 5.5: Run backend tests to verify min_players removal
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 316-325)

### [x] Phase 6: Remove min_players from Frontend (with tests)

- [x] Task 6.1: Remove min_players from TypeScript interfaces

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 327-338)

- [x] Task 6.2: Remove min_players from CreateGame and EditGame pages

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 340-355)

- [x] Task 6.3: Update ParticipantList to show X/max format

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 357-369)

- [x] Task 6.4: Update GameCard participant count display

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 371-383)

- [x] Task 6.5: Update frontend tests to remove min_players

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 385-397)

- [x] Task 6.6: Run frontend tests to verify min_players removal
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 399-408)

### [ ] Phase 7: Remove min_players from Database (with tests)

- [ ] Task 7.1: Remove min_players from GameSession model

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 410-422)

- [ ] Task 7.2: Create migration to drop min_players column

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 424-439)

- [ ] Task 7.3: Run migration to drop min_players column

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 441-451)

- [ ] Task 7.4: Run integration tests to verify database changes
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 453-463)

### [ ] Phase 8: Final Verification

- [ ] Task 8.1: Run full test suite

  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 465-477)

- [ ] Task 8.2: Verify system functionality end-to-end
  - Details: .copilot-tracking/details/20251129-game-model-refactor-details.md (Lines 479-490)

## Dependencies

- PostgreSQL database
- Alembic migration tool
- Python 3.11+ with SQLAlchemy
- Node.js with TypeScript
- React and Material-UI
- Discord.py library

## Success Criteria

- Database migration successfully adds where column, then removes min_players column (two separate migrations)
- All API endpoints accept and return where field, no longer reference min_players
- Discord bot displays where field in game announcements (when populated)
- Frontend forms include where input field, no min_players field
- Frontend displays show where below "When:" field
- Participant counts display as "X/max" format
- **Tests pass continuously** - after each phase completion:
  - Phase 2: Backend tests pass with where field
  - Phase 3: Bot tests pass with where field
  - Phase 4: Frontend tests pass with where field
  - Phase 5: Backend tests pass without min_players
  - Phase 6: Frontend tests pass without min_players
  - Phase 7: Integration tests pass with database changes
  - Phase 8: Full test suite passes
- No breaking changes during implementation (system functional at every step)
- Both migrations are reversible
