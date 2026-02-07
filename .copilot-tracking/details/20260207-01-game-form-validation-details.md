<!-- markdownlint-disable-file -->

# Task Details: Game Creation Form Validation

## Research Reference

**Source Research**: #file:../research/20260207-01-game-form-validation-research.md

## Phase 0: DurationSelector Component with TDD

### Task 0.1: Create DurationSelector component stub

Create new TypeScript component file with stub implementation that throws error for TDD red phase.

- **Files**:
  - frontend/src/components/DurationSelector.tsx - New component file with interface and stub
- **Success**:
  - Component exports with TypeScript interface defined
  - Stub throws `Error('not yet implemented')` when rendered
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 195-204) - Component requirements
- **Dependencies**:
  - None (first task in project)

### Task 0.2: Write failing tests for DurationSelector

Write comprehensive test suite that expects error to be thrown for all interactions.

- **Files**:
  - frontend/src/components/**tests**/DurationSelector.test.tsx - New test file
- **Success**:
  - Tests for preset selection (2h, 4h) expecting error
  - Tests for custom mode activation expecting error
  - Tests for custom hours/minutes input expecting error
  - Tests for value conversion (120 min → "2 hours" preset) expecting error
  - All tests fail with "not yet implemented" error message
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 206-215) - Test requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 456-462) - TDD methodology
- **Dependencies**:
  - Task 0.1 completion (stub must exist)

### Task 0.3: Implement minimal DurationSelector

Replace error-throwing stub with basic preset dropdown functionality to pass initial tests.

- **Files**:
  - frontend/src/components/DurationSelector.tsx - Implement preset selection
- **Success**:
  - Basic preset dropdown renders with values (120, 240, 'custom')
  - onChange handler calls parent with selected preset value
  - Initial preset tests pass
  - Custom mode tests still fail (not yet implemented)
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 217-226) - Minimal implementation
- **Dependencies**:
  - Task 0.2 completion (tests must exist)

### Task 0.4: Update tests and add custom mode

Update passing tests to verify actual behavior and implement custom hours/minutes input.

- **Files**:
  - frontend/src/components/DurationSelector.tsx - Add custom mode UI
  - frontend/src/components/**tests**/DurationSelector.test.tsx - Update tests
- **Success**:
  - Custom mode appears when 'Custom...' selected
  - Hours and minutes TextFields render
  - Custom value calculation works (hours \* 60 + minutes)
  - All tests pass including custom mode tests
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 228-237) - Custom mode requirements
- **Dependencies**:
  - Task 0.3 completion

### Task 0.5: Refactor and add edge case tests

Add validation for custom inputs and comprehensive edge case test coverage.

- **Files**:
  - frontend/src/components/DurationSelector.tsx - Add input validation
  - frontend/src/components/**tests**/DurationSelector.test.tsx - Add edge case tests
- **Success**:
  - Hours validated (0-24 range)
  - Minutes validated (0-59 range)
  - Tests for null values, out-of-range numbers
  - Tests for error prop display
  - Full test suite passes with 100% coverage
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 239-250) - Edge case requirements
- **Dependencies**:
  - Task 0.4 completion

## Phase 1: Shared Validation Utilities with TDD

### Task 1.1: Create validation utilities stub

Create new utilities file with TypeScript interfaces and stub functions throwing errors.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - New utilities file
- **Success**:
  - ValidationResult interface defined
  - Stubs for validateDuration, validateReminderMinutes, validateMaxPlayers, validateCharacterLimit, validateFutureDate
  - Each stub throws `Error('not yet implemented')`
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 252-264) - Validation utilities structure
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 34-83) - Current validation gaps
- **Dependencies**:
  - None (independent from Phase 0)

### Task 1.2: Write failing tests for all validators

Write comprehensive test suite for all validation functions expecting errors.

- **Files**:
  - frontend/src/utils/**tests**/fieldValidation.test.ts - New test file
- **Success**:
  - Tests for validateDuration: null, 0, 1, 120, 1440, 1441, -5
  - Tests for validateReminderMinutes: "", "60", "60,15", "abc", "60,abc,15", "-60", "10081"
  - Tests for validateMaxPlayers: "", "1", "50", "100", "0", "101", "abc", "-5"
  - Tests for validateCharacterLimit: within limit, at 95%, exceeds limit
  - Tests for validateFutureDate: null, past date, future date, minHours parameter
  - All tests expect "not yet implemented" errors
  - All tests fail correctly
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 266-284) - Test case specifications
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 85-101) - Backend validation constraints
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Implement validateDuration

Replace NotImplementedError with duration validation logic.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Implement validateDuration function
- **Success**:
  - Handles null/0 as valid (optional field)
  - Validates range 1-1440 minutes (1 day max)
  - Returns appropriate error messages
  - Duration tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 286-293) - Duration validation logic
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 38-42) - Current duration parsing issues
- **Dependencies**:
  - Task 1.2 completion

### Task 1.4: Implement validateReminderMinutes

Implement comma-separated value parsing and validation.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Implement validateReminderMinutes function
- **Success**:
  - Parses comma-separated string
  - Validates each value is number in range 1-10080 (1 week max)
  - Returns array of numbers in ValidationResult.value
  - Reminder tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 295-302) - Reminder validation logic
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 44-48) - Current reminder validation gaps
- **Dependencies**:
  - Task 1.2 completion

### Task 1.5: Implement validateMaxPlayers

Implement integer parsing and range validation.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Implement validateMaxPlayers function
- **Success**:
  - Parses integer from string
  - Validates range 1-100
  - Handles empty string as valid (optional field)
  - Max players tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 304-311) - Max players validation logic
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 50-54) - Current max players validation gaps
- **Dependencies**:
  - Task 1.2 completion

### Task 1.6: Implement validateCharacterLimit

Implement character counting with warning threshold at 95%.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Implement validateCharacterLimit function
- **Success**:
  - Counts string length
  - Returns error if exceeds max
  - Returns warning at 95% threshold
  - Includes character count in messages
  - Character limit tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 313-321) - Character limit validation logic
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 56-59) - Current character limit gaps
- **Dependencies**:
  - Task 1.2 completion

### Task 1.7: Implement validateFutureDate

Implement date comparison with configurable future offset.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Implement validateFutureDate function
- **Success**:
  - Checks for null date
  - Compares against current time
  - Applies minHoursInFuture offset (default 0)
  - Returns user-friendly error messages
  - Date validation tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 323-331) - Date validation logic
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 61-65) - Current date validation gaps
- **Dependencies**:
  - Task 1.2 completion

### Task 1.8: Refactor and verify full coverage

Refactor validation code and ensure 100% test coverage.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Code refactoring
  - frontend/src/utils/**tests**/fieldValidation.test.ts - Additional edge case tests
- **Success**:
  - Code clarity improved
  - All edge cases tested
  - 100% test coverage verified
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 333-341) - Coverage requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 448-454) - Quality standards
- **Dependencies**:
  - Tasks 1.3-1.7 completion

## Phase 2: GameForm Validation Integration with TDD

### Task 2.1: Add validation state to GameForm

Add error state management and validation handler stubs to GameForm.

- **Files**:
  - frontend/src/components/GameForm.tsx - Add state and handler stubs
- **Success**:
  - Error state variables for each validated field
  - Validation handler functions (stubs throwing errors)
  - Blur event handlers calling validators
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 343-351) - GameForm integration requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 17-21) - Current GameForm structure
- **Dependencies**:
  - Phase 1 completion (validators must exist)

### Task 2.2: Write failing GameForm validation tests

Write integration tests for GameForm validation behavior.

- **Files**:
  - frontend/src/components/**tests**/GameForm.validation.test.tsx - New test file
- **Success**:
  - Tests for error display on blur for each field
  - Tests for error clearing when field corrected
  - Tests for form submission blocked with errors
  - Tests for successful submission with valid fields
  - Tests fail (handlers not implemented)
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 353-366) - GameForm test requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 126-138) - TextField validation patterns
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Implement GameForm validation handlers

Implement blur handlers and wire to validation utilities.

- **Files**:
  - frontend/src/components/GameForm.tsx - Implement validation handlers
- **Success**:
  - Import validators from fieldValidation
  - Blur handlers call validators and update error state
  - TextField components display error/helperText props
  - Form submission blocked if any errors exist
  - GameForm tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 368-379) - Handler implementation
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 140-152) - API documentation
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Replace duration TextField with DurationSelector

Swap text-based duration input with new DurationSelector component.

- **Files**:
  - frontend/src/components/GameForm.tsx - Replace TextField with DurationSelector
  - frontend/src/components/**tests**/GameForm.validation.test.tsx - Update tests
- **Success**:
  - DurationSelector component imported
  - Duration TextField replaced in JSX
  - Duration change handler updated
  - parseDurationString usage removed
  - Tests updated for new component
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 381-390) - DurationSelector integration
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 103-109) - parseDurationString problems
- **Dependencies**:
  - Phase 0 completion (DurationSelector must exist)
  - Task 2.3 completion

### Task 2.5: Add date validation to DateTimePicker

Add validation props to MUI DateTimePicker component.

- **Files**:
  - frontend/src/components/GameForm.tsx - Update DateTimePicker
- **Success**:
  - disablePast prop added
  - Validation on date change using validateFutureDate
  - Error display via slotProps.textField
  - Tests for past date rejection
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 392-402) - DateTimePicker validation
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 111-124) - MUI DateTimePicker patterns
- **Dependencies**:
  - Task 2.3 completion

### Task 2.6: Add character counters to text fields

Display character counts with warnings at 95% threshold.

- **Files**:
  - frontend/src/components/GameForm.tsx - Add character counters
- **Success**:
  - validateCharacterLimit applied to location, description, signup_instructions
  - Character count displayed in helperText
  - Tests for counter display and warnings
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 404-413) - Character counter requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 56-59) - Current location field issues
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: TemplateForm Validation Integration with TDD

### Task 3.1: Add on-blur validation to TemplateForm

Add validation state and blur handlers to TemplateForm.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Add validation state and handlers
- **Success**:
  - Error state for each field
  - Validation handlers (stubs throwing errors)
  - Blur event handlers added
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 415-423) - TemplateForm validation requirements
- **Dependencies**:
  - Phase 1 completion

### Task 3.2: Write failing TemplateForm validation tests

Write integration tests matching GameForm validation patterns.

- **Files**:
  - frontend/src/components/**tests**/TemplateForm.validation.test.tsx - New test file
- **Success**:
  - Tests for on-blur validation behavior
  - Tests for character counters
  - Tests for submit-time validation still works
  - Tests fail correctly
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 425-437) - TemplateForm test requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 448-454) - Consistency requirements
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Implement TemplateForm validation

Implement blur handlers and update TextField components.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Implement validation handlers
- **Success**:
  - Import shared validators
  - Implement blur handlers
  - Update TextField components with error props
  - Tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 439-449) - Implementation details
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Replace duration TextField with DurationSelector

Swap duration input to match GameForm pattern.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Replace TextField
- **Success**:
  - DurationSelector imported
  - Duration TextField replaced
  - Tests updated
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 451-459) - DurationSelector integration
- **Dependencies**:
  - Phase 0 completion
  - Task 3.3 completion

### Task 3.5: Add character counters

Add character counters matching GameForm behavior.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Add character counters
- **Success**:
  - Character validation applied to text fields
  - Counters displayed in helperText
  - Tests for counters pass
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 461-471) - Character counter requirements
- **Dependencies**:
  - Task 3.3 completion

## Phase 4: Backend Schema Alignment with TDD

### Task 4.1: Update template schema constraints

Ensure backend template schema matches game schema validation constraints.

- **Files**:
  - shared/schemas/game.py - Update TemplateCreateRequest/TemplateUpdateRequest
- **Success**:
  - max_length added to description, where, signup_instructions fields
  - Constraints match GameCreateRequest
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 473-480) - Schema alignment requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 85-101) - Current schema constraints
- **Dependencies**:
  - None (independent backend task)

### Task 4.2: Write/update API tests for schema validation

Ensure API tests validate schema constraints comprehensively.

- **Files**:
  - tests/integration/test_games.py - Update/add validation tests
  - tests/integration/test_templates.py - Update/add validation tests
- **Success**:
  - Tests for max_length enforcement
  - Tests for field range validation
  - Tests verify Pydantic error responses
  - Tests fail for any missing constraints
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 482-491) - API test requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 154-168) - Pydantic validation patterns
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Verify API tests pass

Run API test suite and fix any validation mismatches.

- **Files**:
  - shared/schemas/game.py - Fix any schema mismatches
  - services/api/routes/games.py - Fix any endpoint issues
- **Success**:
  - API test suite passes
  - Backend validation matches frontend constraints
  - All integration tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 493-501) - Verification requirements
- **Dependencies**:
  - Task 4.2 completion

## Phase 5: Cleanup and Final Verification with TDD

### Task 5.1: Remove deprecated parsing functions

Delete obsolete duration parsing code no longer needed.

- **Files**:
  - frontend/src/components/GameForm.tsx - Remove parseDurationString function
  - frontend/src/components/TemplateForm.tsx - Search for any duration parsing code
- **Success**:
  - parseDurationString function deleted
  - formatDurationForDisplay deleted if unused
  - No remaining usages found in codebase
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 503-511) - Cleanup requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 103-109) - parseDurationString issues
- **Dependencies**:
  - Phases 2 and 3 completion (DurationSelector must be in use)

### Task 5.2: Write integration tests for error handling

Verify existing error handling patterns still work correctly.

- **Files**:
  - frontend/src/components/**tests**/GameForm.integration.test.tsx - New test file
- **Success**:
  - Tests for backend error display (mentions validation)
  - Tests for ValidationErrors component integration
  - Tests for image upload validation preserved
  - Tests for error clearing on successful submission
  - All tests pass
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 513-526) - Integration test requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 23-25) - Current error handling
- **Dependencies**:
  - All previous phases complete

### Task 5.3: Run full test suite

Execute complete test suite and verify coverage targets.

- **Files**:
  - All test files across frontend and backend
- **Success**:
  - All frontend tests pass
  - All backend tests pass
  - 100% coverage for new validation code
  - No regressions in existing tests
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 528-538) - Test suite requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 456-462) - Coverage objectives
- **Dependencies**:
  - All implementation tasks complete

### Task 5.4: Manual QA testing

Perform end-to-end manual testing across devices.

- **Files**:
  - N/A (manual testing)
- **Success**:
  - GameForm validates correctly with valid/invalid inputs
  - TemplateForm validates correctly with valid/invalid inputs
  - Mobile numeric keyboards appear for custom duration inputs
  - Screen readers announce errors correctly
  - Character counters display at 95% threshold
  - All validation messages are user-friendly
- **Research References**:
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 540-551) - Manual QA requirements
  - #file:../research/20260207-01-game-form-validation-research.md (Lines 170-178) - Technical requirements
- **Dependencies**:
  - Task 5.3 completion

## Dependencies

- MUI X DatePickers
- vitest
- @testing-library/react
- @testing-library/user-event
- TypeScript 5.x
- React 18+

## Success Criteria

- All validation logic centralized in fieldValidation.ts
- DurationSelector component fully tested and reusable
- GameForm and TemplateForm have identical validation UX
- Backend schemas aligned with frontend constraints
- 100% test coverage for all validation code
- All tests pass (unit, integration, API)
- No silent validation failures possible
- Character counters visible at 95% threshold
- Mobile users get appropriate input types
