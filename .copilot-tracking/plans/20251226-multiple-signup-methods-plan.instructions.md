---
applyTo: ".copilot-tracking/changes/20251226-multiple-signup-methods-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Multiple Signup Methods

## Overview

Add support for multiple signup methods (Self Signup and Host Selected) with template-level configuration controlling which methods are available and the default selection.

## Objectives

- Create SignupMethod enum with SELF_SIGNUP and HOST_SELECTED values
- Add signup method configuration fields to GameTemplate (allowed methods list and default)
- Store selected signup method in GameSession
- Control Discord join button enabled/disabled state based on signup method
- Provide dropdown selector in game creation form with template-driven defaults and restrictions
- Migrate existing games to SELF_SIGNUP method

## Research Summary

### Project Files

- shared/models/game.py - GameSession model and GameStatus enum pattern
- shared/models/template.py - GameTemplate model with locked and pre-populated fields
- shared/schemas/game.py - GameCreateRequest and GameResponse schemas
- services/bot/views/game_view.py - GameView with join/leave buttons
- frontend/src/pages/CreateGame.tsx - Game creation form with template selection
- frontend/src/components/GameForm.tsx - Shared form component

### External References

- #file:../research/20251226-multiple-signup-methods-research.md - Complete research findings
- #file:../../.github/instructions/python.instructions.md - Python coding standards
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript standards

### Standards References

- str, Enum pattern from GameStatus (shared/models/game.py lines 38-56)
- Template configuration pattern (locked vs pre-populated fields)
- Database migration patterns from recent migrations
- Frontend template-driven form initialization

## Implementation Checklist

### [ ] Phase 1: Backend Schema and Model

- [ ] Task 1.1: Create SignupMethod enum
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 15-45)

- [ ] Task 1.2: Update GameTemplate model with signup method fields
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 47-75)

- [ ] Task 1.3: Update GameSession model with signup_method field
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 77-100)

- [ ] Task 1.4: Create database migration
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 102-145)

### [ ] Phase 2: API Schema and Service

- [ ] Task 2.1: Update GameCreateRequest schema
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 147-170)

- [ ] Task 2.2: Update GameResponse schema
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 172-190)

- [ ] Task 2.3: Update GameService.create_game() with signup method resolution
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 192-235)

- [ ] Task 2.4: Update template schemas for signup method fields
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 237-260)

### [ ] Phase 3: Discord Bot Button Control

- [ ] Task 3.1: Update GameView with signup_method parameter
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 262-290)

- [ ] Task 3.2: Update format_game_announcement() to pass signup_method
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 292-320)

- [ ] Task 3.3: Update event handlers to pass signup_method to GameView
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 322-355)

### [ ] Phase 4: Frontend UI

- [ ] Task 4.1: Update TypeScript types and interfaces
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 357-385)

- [ ] Task 4.2: Add signup method selector to GameForm
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 387-430)

- [ ] Task 4.3: Update CreateGame page with signup method handling
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 432-465)

- [ ] Task 4.4: Display signup method in GameDetails page
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 467-495)

### [ ] Phase 5: Testing and Validation

- [ ] Task 5.1: Add unit tests for SignupMethod enum
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 497-520)

- [ ] Task 5.2: Add integration tests for game creation with signup methods
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 522-555)

- [ ] Task 5.3: Add E2E tests for Discord button behavior
  - Details: .copilot-tracking/details/20251226-multiple-signup-methods-details.md (Lines 557-585)

## Dependencies

- Python 3.11+ (str, Enum support already in use)
- Existing template system
- GameSession and GameTemplate models
- Discord button view system
- Frontend form infrastructure

## Success Criteria

- SignupMethod enum with SELF_SIGNUP and HOST_SELECTED values exists
- GameTemplate has allowed_signup_methods (JSON array, nullable) and default_signup_method (string, nullable)
- GameSession has signup_method (string, non-nullable, defaults to SELF_SIGNUP)
- Empty/null allowed_signup_methods means all methods available
- Game creation form dropdown shows only allowed methods with default selected
- Discord join button disabled when signup_method is HOST_SELECTED
- All existing games migrated to SELF_SIGNUP
- API validates signup_method against template's allowed list
- Frontend displays selected signup method in game details
- All tests pass
