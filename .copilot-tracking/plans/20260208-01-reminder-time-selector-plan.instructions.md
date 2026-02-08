---
applyTo: '.copilot-tracking/changes/20260208-01-reminder-time-selector-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Reminder Time Selector Component

## Overview

Replace text-based comma-separated reminder input with intuitive Select + Chip multi-selector component matching DurationSelector interaction pattern.

## Objectives

- Create ReminderSelector component supporting multiple value selection
- Provide preset options (5min, 30min, 1hr, 2hr, 1day) plus custom input
- Display selected reminders as deletable chips for clear visual feedback
- Maintain consistency with DurationSelector UX patterns
- Preserve existing validation rules (1-10080 minute range)

## Research Summary

### Project Files

- frontend/src/components/DurationSelector.tsx - Single-value selector pattern to adapt
- frontend/src/components/GameForm.tsx (lines 615-640) - Current TextField to replace
- frontend/src/utils/fieldValidation.ts (lines 50-80) - Existing validation logic

### External References

- #file:../research/20260208-01-reminder-time-selector-research.md - Complete analysis of approaches and implementation patterns
- #fetch:https://mui.com/material-ui/react-chip/ - Chip component for multi-value display
- #fetch:https://mui.com/material-ui/react-autocomplete/ - Alternative multi-select patterns

### Standards References

- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript standards
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology

## Implementation Checklist

### [x] Phase 0: ReminderSelector Component with TDD

- [x] Task 0.1: Create ReminderSelector component stub
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 15-27)

- [x] Task 0.2: Write failing tests for ReminderSelector
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 29-44)

- [x] Task 0.3: Implement preset selection with dropdown
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 46-60)

- [x] Task 0.4: Add chip display with delete functionality
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 62-75)

- [x] Task 0.5: Add custom minute input mode
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 77-90)

- [x] Task 0.6: Refactor and add edge case tests
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 92-105)

### [x] Phase 1: GameForm Integration with TDD

- [x] Task 1.1: Update GameForm state for array-based reminders
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 109-121)

- [x] Task 1.2: Write failing GameForm integration tests
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 123-136)

- [x] Task 1.3: Replace TextField with ReminderSelector
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 138-151)

- [x] Task 1.4: Update validation for array-based input
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 153-165)

- [x] Task 1.5: Test backward compatibility with existing data
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 167-179)

### [x] Phase 2: TemplateForm Integration with TDD

- [x] Task 2.1: Add ReminderSelector to TemplateForm
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 183-196)

- [x] Task 2.2: Write TemplateForm integration tests
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 198-210)

- [x] Task 2.3: Update TemplateForm validation handlers
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 212-224)

### [ ] Phase 3: Cleanup and Final Verification

- [ ] Task 3.1: Update EditGame page
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 228-239)

- [ ] Task 3.2: Remove deprecated comma-parsing logic
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 241-252)

- [ ] Task 3.3: Run full test suite and verify coverage
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 254-265)

- [ ] Task 3.4: Manual QA testing
  - Details: .copilot-tracking/details/20260208-01-reminder-time-selector-details.md (Lines 267-279)

## Dependencies

- MUI components (already installed): Select, MenuItem, Chip, TextField, Button, FormControl, FormHelperText, Box
- vitest and @testing-library/react (already configured)
- No new external dependencies required

## Success Criteria

- ReminderSelector component displays preset options with clear labels
- Multiple reminder times can be selected from presets
- Selected reminders appear as deletable chips
- Custom minute values can be added with validation
- Duplicate values cannot be added (disabled or prevented)
- Values automatically sort in ascending order
- Component rejects values outside 1-10080 minute range
- All tests pass with 100% coverage for new code
- Existing games with comma-separated data load correctly
- Interaction pattern feels consistent with DurationSelector
