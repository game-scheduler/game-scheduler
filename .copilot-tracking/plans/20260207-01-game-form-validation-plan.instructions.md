---
applyTo: '.copilot-tracking/changes/20260207-01-game-form-validation-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Creation Form Validation

## Overview

Implement comprehensive frontend validation for game creation forms with reusable DurationSelector component and shared validation utilities, following TDD methodology.

## Objectives

- Create reusable DurationSelector component to replace error-prone text parsing
- Build shared validation utility library for form field validation
- Apply validation to GameForm with immediate user feedback on blur
- Apply identical validation to TemplateForm for consistency
- Ensure backend schemas align with frontend validation constraints
- Achieve 100% test coverage for all validation logic

## Research Summary

### Project Files

- frontend/src/components/GameForm.tsx - Main form component with minimal validation
- frontend/src/pages/CreateGame.tsx - Orchestrates submission, handles backend errors
- shared/schemas/game.py - Backend Pydantic validation schemas
- services/api/routes/games.py - API endpoint with image validation

### External References

- #file:../research/20260207-01-game-form-validation-research.md - Complete validation requirements analysis
- #fetch:https://mui.com/x/react-date-pickers/validation/ - MUI DateTimePicker validation patterns
- #fetch:https://react-hook-form.com/get-started - React form validation library reference

### Standards References

- #file:../../.github/instructions/reactjs.instructions.md - React development standards
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript guidelines
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology

## Implementation Checklist

### [x] Phase 0: DurationSelector Component with TDD

- [x] Task 0.1: Create DurationSelector component stub
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 11-24)

- [x] Task 0.2: Write failing tests for DurationSelector
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 25-42)

- [x] Task 0.3: Implement minimal DurationSelector
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 43-59)

- [x] Task 0.4: Add custom mode and pass remaining tests
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 60-75)

- [x] Task 0.5: Refactor and add edge case tests
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 76-95)

### [x] Phase 1: Shared Validation Utilities with TDD

- [x] Task 1.1: Create validation utilities stub
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 96-111)

- [x] Task 1.2: Write failing tests for all validators
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 112-131)

- [x] Task 1.3: Implement validateDuration
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 132-149)

- [x] Task 1.4: Implement validateReminderMinutes
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 150-167)

- [x] Task 1.5: Implement validateMaxPlayers
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 168-185)

- [x] Task 1.6: Implement validateCharacterLimit
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 186-204)

- [x] Task 1.7: Implement validateFutureDate
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 205-223)

- [x] Task 1.8: Refactor and verify full coverage
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 224-243)

### [x] Phase 2: GameForm Validation Integration with TDD

- [x] Task 2.1: Add validation state to GameForm
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 244-259)

- [x] Task 2.2: Write failing GameForm validation tests
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 260-277)

- [x] Task 2.3: Implement GameForm validation handlers
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 278-296)

- [x] Task 2.4: Replace duration TextField with DurationSelector
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 297-315)

- [x] Task 2.5: Add date validation to DateTimePicker
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 316-333)

- [x] Task 2.6: Add character counters to text fields
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 334-352)

### [x] Phase 3: TemplateForm Validation Integration with TDD

- [x] Task 3.1: Add on-blur validation to TemplateForm
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 353-367)

- [x] Task 3.2: Write failing TemplateForm validation tests
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 368-384)

- [x] Task 3.3: Implement TemplateForm validation
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 385-401)

- [x] Task 3.4: Replace duration TextField with DurationSelector
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 402-417)

- [x] Task 3.5: Add character counters
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 418-435)

### [ ] Phase 4: Backend Schema Alignment with TDD

- [ ] Task 4.1: Update template schema constraints
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 436-450)

- [ ] Task 4.2: Write/update API tests for schema validation
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 451-468)

- [ ] Task 4.3: Verify API tests pass
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 469-486)

### [ ] Phase 5: Cleanup and Final Verification with TDD

- [ ] Task 5.1: Remove deprecated parsing functions
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 487-503)

- [ ] Task 5.2: Write integration tests for error handling
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 504-521)

- [ ] Task 5.3: Run full test suite
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 522-538)

- [ ] Task 5.4: Manual QA testing
  - Details: .copilot-tracking/details/20260207-01-game-form-validation-details.md (Lines 539-577)

## Dependencies

- MUI X DatePickers (already installed)
- vitest and @testing-library/react (already configured)
- TypeScript 5.x with ES2022 target
- Existing Pydantic schemas for validation constraint reference

## Success Criteria

- DurationSelector component replaces text parsing with dropdown + custom input
- All validation logic centralized in fieldValidation.ts with 100% test coverage
- GameForm provides immediate validation feedback on blur for all fields
- TemplateForm has identical validation behavior to GameForm
- Backend schemas aligned with frontend constraints
- All tests pass (unit, integration, API)
- Character counters display on all limited-length fields
- No silent validation failures possible
- Mobile users get appropriate input types for numeric fields
