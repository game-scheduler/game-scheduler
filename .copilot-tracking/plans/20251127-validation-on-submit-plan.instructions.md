---
applyTo: ".copilot-tracking/changes/20251127-validation-on-submit-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Validation on Submit with @ Display Enhancement

## Overview

Move participant mention validation from real-time (as-you-type) to submit-only, eliminating redundant API calls and adding disambiguation UI. Enhance display to prepend @ to validated users for visual consistency.

## Objectives

- Remove real-time validation during form entry (no API calls while typing)
- Move all validation to form submission (single validation point)
- Add disambiguation UI when multiple users match a mention
- Enhance display components to prepend @ to validated participant mentions
- Preserve form data on validation errors for easy correction
- Reduce server load and eliminate rate limiting concerns

## Research Summary

### Project Files

- frontend/src/components/EditableParticipantList.tsx - Current real-time validation implementation
- frontend/src/pages/CreateGame.tsx - Game creation with validation error handling
- frontend/src/pages/EditGame.tsx - Game editing with validation support
- frontend/src/components/ParticipantList.tsx - Display component for participant list
- services/api/routes/games.py - Backend validation on game creation/update

### External References

- #file:../research/20251127-discord-validation-timing-options-research.md (Lines 1-420) - Complete analysis of validation timing options

### Standards References

- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript 5.x standards
- #file:../../.github/instructions/python.instructions.md - Python backend conventions

## Implementation Checklist

### [x] Phase 1: Frontend - Remove Real-time Validation

- [x] Task 1.1: Simplify ParticipantInput interface

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 15-28)

- [x] Task 1.2: Remove validation state and timers from EditableParticipantList

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 30-48)

- [x] Task 1.3: Simplify handleMentionChange to only update mention text

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 50-63)

- [x] Task 1.4: Remove validation visual indicators from TextField
  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 65-78)

### [x] Phase 2: Frontend - Add Disambiguation UI

- [x] Task 2.1: Create DisambiguationChip component

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 80-101)
  - Note: Component already exists as MentionChip.tsx

- [x] Task 2.2: Create ValidationErrors component

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 103-129)
  - Note: Component already exists with full implementation

- [x] Task 2.3: Integrate ValidationErrors in CreateGame

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 131-147)
  - Note: Integration already existed, added handleSuggestionClick to GameForm

- [x] Task 2.4: Integrate ValidationErrors in EditGame
  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 149-165)

### [x] Phase 3: Frontend - Enhance @ Display

- [x] Task 3.1: Add @ prepending logic to ParticipantList display

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 167-185)

- [x] Task 3.2: Ensure @ handling in EditableParticipantList display
  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 187-202)
  - Note: TextField already preserves user input without modification

### [x] Phase 4: Backend - Enhance Validation Response

- [x] Task 4.1: Verify validation error response format

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 204-224)
  - Note: Backend already returns proper format with error, message, invalid_mentions, valid_participants

- [x] Task 4.2: Ensure form_data preservation in error response
  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 226-239)
  - Note: Added ValidationError handling to update_game endpoint with form_data preservation

### [x] Phase 5: Testing and Validation

- [x] Task 5.1: Test single valid mention submission

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 241-252)

- [x] Task 5.2: Test multiple valid mentions submission

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 254-265)

- [x] Task 5.3: Test invalid mention with disambiguation

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 267-281)

- [x] Task 5.4: Test mixed valid/invalid mentions

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 283-296)

- [x] Task 5.5: Verify @ display enhancement

  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 298-309)

- [x] Task 5.6: Verify no API calls during typing
  - Details: .copilot-tracking/details/20251127-validation-on-submit-details.md (Lines 311-320)

## Dependencies

- React 18+
- Material-UI components
- FastAPI backend with validation error handling
- Discord API for user resolution

## Success Criteria

- No validation API calls occur during form entry
- All validation happens only on form submission
- Disambiguation UI displays when multiple matches found
- Users can click suggestions to replace invalid mentions
- Form preserves all data on validation error
- @ symbol prepended to validated participants in display
- Second submit succeeds after corrections
- All tests pass
