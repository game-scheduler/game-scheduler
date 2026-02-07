<!-- markdownlint-disable-file -->

# Release Changes: Game Creation Form Validation

**Related Plan**: 20260207-01-game-form-validation-plan.instructions.md
**Implementation Date**: 2026-02-07

## Summary

Implementing comprehensive frontend validation for game creation forms with reusable DurationSelector component and shared validation utilities, following TDD methodology.

**Phase 0 Complete**: Created reusable DurationSelector component with preset options (2h, 4h) and custom hours/minutes input, following strict TDD Red-Green-Refactor cycle.

**Phase 1 Complete**: Created comprehensive field validation utilities with 100% test coverage, following strict TDD Red-Green-Refactor cycle. All validators handle optional fields, range validation, and user-friendly error messages.

**Phase 2 Tasks 2.1-2.3 Complete**: Integrated validation into GameForm with comprehensive test coverage (16 tests, 100% pass rate). Following TDD RED-GREEN cycle, created validation state management, failing tests, and implemented validation handlers using fieldValidation utilities. Form submission blocks when errors exist. Fixed test performance issues by using `user.paste()` for long text inputs and `user.keyboard()` for shorter inputs instead of `user.type()` which was causing timeouts.

**Phase 2 Complete**: Successfully integrated all validation into GameForm with DurationSelector component, date validation, and character counters:

- Tasks 2.1-2.3: Validation state management and handlers (16 tests, 100% pass)
- Task 2.4: Replaced text-based duration with DurationSelector component
- Task 2.5: Added disablePast prop to DateTimePicker for past date prevention
- Task 2.6: Added dynamic character counters to location, description, and signup_instructions fields

## Changes

### Added

- frontend/src/components/DurationSelector.tsx - Reusable duration selector with preset options and custom mode for hours/minutes input
- frontend/src/components/**tests**/DurationSelector.test.tsx - Comprehensive test suite with 15 tests covering presets, custom mode, v- frontend/src/components/**tests**/GameForm.validation.test.tsx - Comprehensive GameForm validation test suite with 16 tests (Task 2.2)- frontend/src/utils/fieldValidation.ts - Reusable validation utilities with ValidationResult interface and 5 validator functions (100% coverage)
- frontend/src/utils/**tests**/fieldValidation.test.ts - Comprehensive test suite with 33 tests covering all validators with edge cases

### Modified

- frontend/src/components/GameForm.tsx - Added validation error state variables and validation handler stubs for TDD (Task 2.1)
- frontend/src/components/GameForm.tsx - Imported DurationSelector component (Task 2.4)
- frontend/src/components/GameForm.tsx - Changed expectedDurationMinutes field type from string to number|null (Task 2.4)
- frontend/src/components/GameForm.tsx - Replaced duration TextField with DurationSelector component (Task 2.4)
- frontend/src/components/GameForm.tsx - Added handleDurationChange handler accepting number|null (Task 2.4)
- frontend/src/components/GameForm.tsx - Removed parseDurationString call from validateDurationField (Task 2.4)
- frontend/src/components/GameForm.tsx - Removed parseDuration variable from handleSubmit (Task 2.4)
- frontend/src/components/GameForm.tsx - Added disablePast prop to DateTimePicker (Task 2.5)
- frontend/src/components/GameForm.tsx - Added getLocationHelperText(), getDescriptionHelperText(), getSignupInstructionsHelperText() functions (Task 2.6)
- frontend/src/components/GameForm.tsx - Updated location field helperText to show character count (Task 2.6)
- frontend/src/components/GameForm.tsx - Updated description field helperText to show character count (Task 2.6)
- frontend/src/components/GameForm.tsx - Updated signupInstructions field helperText to show character count (Task 2.6)

- frontend/src/components/GameForm.tsx - Imported fieldValidation utilities and implemented validation handlers for all fields (Task 2.3)
- frontend/src/components/GameForm.tsx - Added onBlur handlers to TextField components to trigger validation
- frontend/src/components/GameForm.tsx - Added error/helperText display to all validated fields
- frontend/src/components/GameForm.tsx - Added form submission blocking when validation errors exist
- frontend/src/components/GameForm.tsx - Extracted magic number 500 to MAX_LOCATION_LENGTH constant for ESLint compliance
- frontend/src/components/**tests**/GameForm.validation.test.tsx - Adjusted test expectations to match actual validation messages (Task 2.3)
- frontend/src/components/**tests**/GameForm.validation.test.tsx - Fixed test performance by using user.paste() for long text (480+ chars) and user.keyboard() for shorter inputs
- frontend/src/contexts/AuthContext.tsx - Exported AuthContextType interface for test mocking- .pre-commit-config.yaml - Added per-test timeout to pytest (30s) and vitest (10s) to prevent indefinite test hangs
- pyproject.toml - Added pytest-timeout dependency for pytest --timeout support

### Removed
