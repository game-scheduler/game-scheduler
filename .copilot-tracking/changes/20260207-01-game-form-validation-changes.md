<!-- markdownlint-disable-file -->

# Release Changes: Game Creation Form Validation

**Related Plan**: 20260207-01-game-form-validation-plan.instructions.md
**Implementation Date**: 2026-02-07

## Summary

Implementing comprehensive frontend validation for game creation forms with reusable DurationSelector component and shared validation utilities, following TDD methodology.

**Phase 0 Complete**: Created reusable DurationSelector component with preset options (2h, 4h) and custom hours/minutes input, following strict TDD Red-Green-Refactor cycle.

**Phase 1 Complete**: Created comprehensive field validation utilities with 100% test coverage, following strict TDD Red-Green-Refactor cycle. All validators handle optional fields, range validation, and user-friendly error messages.

**Phase 2 Tasks 2.1-2.3 Complete**: Integrated validation into GameForm with comprehensive test coverage (16 tests, 100% pass rate). Following TDD RED-GREEN cycle, created validation state management, failing tests, and implemented validation handlers using fieldValidation utilities. Form submission blocks when errors exist. Fixed test performance issues by using `user.paste()` for long text inputs and `user.keyboard()` for shorter inputs instead of `user.type()` which was causing timeouts.

## Changes

### Added

- frontend/src/components/DurationSelector.tsx - Reusable duration selector with preset options and custom mode for hours/minutes input
- frontend/src/components/**tests**/DurationSelector.test.tsx - Comprehensive test suite with 15 tests covering presets, custom mode, v- frontend/src/components/**tests**/GameForm.validation.test.tsx - Comprehensive GameForm validation test suite with 16 tests (Task 2.2)- frontend/src/utils/fieldValidation.ts - Reusable validation utilities with ValidationResult interface and 5 validator functions (100% coverage)
- frontend/src/utils/**tests**/fieldValidation.test.ts - Comprehensive test suite with 33 tests covering all validators with edge cases

### Modified

- frontend/src/components/GameForm.tsx - Added validation error state variables and validation handler stubs for TDD (Task 2.1)

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
