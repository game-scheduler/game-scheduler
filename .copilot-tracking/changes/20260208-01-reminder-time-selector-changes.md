<!-- markdownlint-disable-file -->

# Release Changes: Reminder Time Selector Component

**Related Plan**: 20260208-01-reminder-time-selector-plan.instructions.md
**Implementation Date**: 2026-02-08

## Summary

Implementation of ReminderSelector component to replace text-based comma-separated reminder input with intuitive Select + Chip multi-selector matching DurationSelector interaction pattern.

## Changes

### Added

- frontend/src/components/ReminderSelector.tsx - Created component stub with TypeScript interface and error throw
- frontend/src/components/**tests**/ReminderSelector.test.tsx - Created comprehensive test suite with 20 test cases covering all expected behaviors

### Modified

- frontend/src/components/ReminderSelector.tsx - Implemented preset selection with dropdown showing 5min, 30min, 1hr, 2hr, 1day options
- frontend/src/components/ReminderSelector.tsx - Added Chip display for selected values with delete functionality
- frontend/src/components/ReminderSelector.tsx - Implemented custom minute input mode with validation (1-10080 range, integers only, no duplicates)
- frontend/src/components/**tests**/ReminderSelector.test.tsx - Fixed test assertions to use within() helper for disambiguation and corrected empty dropdown expectation
- frontend/src/components/GameForm.tsx - Added reminderMinutesArray field to FormData interface and initialized from initialData.reminder_minutes
- frontend/src/components/**tests**/GameForm.test.tsx - Added ReminderSelector integration tests for rendering, empty state, and existing data initialization
- frontend/src/components/GameForm.tsx - Imported ReminderSelector component and added handleReminderChange handler to sync array and string state
- frontend/src/components/GameForm.tsx - Replaced TextField with ReminderSelector for reminder time input with array-based state management
- frontend/src/components/ReminderSelector.tsx - Added safeValue defensive check to handle undefined/null value prop gracefully
- frontend/src/components/GameForm.tsx - Updated validateReminderField to validate reminderMinutesArray directly instead of parsing string
- frontend/src/components/**tests**/GameForm.error-handling.test.tsx - Updated test to reflect ReminderSelector's internal validation
- frontend/src/pages/**tests**/EditGame.test.tsx - Updated reminder time assertions to check for ReminderSelector presence instead of TextField value
- frontend/src/components/TemplateForm.tsx - Added reminderMinutesArray state field and initialized from template.reminder_minutes
- frontend/src/components/TemplateForm.tsx - Imported ReminderSelector component and replaced TextField with ReminderSelector for reminder time input
- frontend/src/components/TemplateForm.tsx - Added handleReminderChange handler to sync reminderMinutesArray and reminderMinutes string state
- frontend/src/components/TemplateForm.tsx - Updated validation logic to use reminderMinutesArray with range checking (1-10080 minutes)
- frontend/src/components/TemplateForm.tsx - Updated handleSubmit to use reminderMinutesArray directly instead of parsing string
- frontend/src/components/TemplateForm.tsx - Removed unused reminderMinutes string state and reminderError state
- frontend/src/components/TemplateForm.tsx - Simplified handleReminderChange to only update reminderMinutesArray
- frontend/src/components/TemplateForm.tsx - Removed unused handleReminderBlur handler and validateReminderMinutes import
- frontend/src/components/**tests**/TemplateForm.test.tsx - Added comprehensive ReminderSelector integration tests (preset selection, chip deletion, custom value addition, form submission)

### Removed

- frontend/src/components/**tests**/GameForm.validation.test.tsx - Removed 3 obsolete TextField-based reminder validation tests (functionality now tested in ReminderSelector.test.tsx)
- frontend/src/components/**tests**/TemplateForm.validation.test.tsx - Removed obsolete TextField-based reminder validation test
- frontend/src/components/TemplateForm.tsx - Removed string-based comma-parsing validation logic
