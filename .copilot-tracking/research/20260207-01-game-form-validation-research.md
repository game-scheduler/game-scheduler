<!-- markdownlint-disable-file -->

# Task Research Notes: Game Creation Form Validation

## Research Executed

### File Analysis

- `/home/mckee/src/github.com/bretmckee/game-scheduler/frontend/src/components/GameForm.tsx`
  - Main form component with field definitions and minimal frontend validation
  - Contains time parsing logic that silently fails for invalid input
- `/home/mckee/src/github.com/bretmckee/game-scheduler/frontend/src/pages/CreateGame.tsx`
  - Orchestrates form submission, handles backend validation errors for mentions only
- `/home/mckee/src/github.com/bretmckee/game-scheduler/shared/schemas/game.py`
  - Backend Pydantic schemas with field-level validation constraints
  - Validates after data reaches server, not before submission
- `/home/mckee/src/github.com/bretmckee/game-scheduler/services/api/routes/games.py`
  - API endpoint handles form data, validates images

### Code Search Results

- `parseDurationString` function in GameForm.tsx
  - Returns `null` for invalid input with no error notification
  - Valid formats: "2h", "90m", "1h 30m", "1:30", plain numbers
- Form submission only validates: `!guildId || !formData.channelId || !formData.scheduledAt`
  - No validation of reminder_minutes, expected_duration_minutes, max_players, or location length

### External Research

- #fetch:https://mui.com/x/react-date-pickers/validation/
  - MUI DateTimePicker provides built-in validation props: `minDate`, `maxDate`, `disablePast`, `shouldDisableDate`
  - Can show error states with `slotProps.textField.error` and `helperText`
- #fetch:https://react-hook-form.com/get-started
  - Industry standard for React form validation with TypeScript support
  - Provides `register`, `formState.errors`, custom validators, and `yup`/`zod` integration

### Project Conventions

- Standards referenced: `.github/instructions/reactjs.instructions.md`, `.github/instructions/typescript-5-es2022.instructions.md`, `.github/instructions/test-driven-development.instructions.md`
- Instructions followed: Self-explanatory code, minimize comments, proper error handling, TDD methodology

## Key Discoveries

### Project Structure

The game creation workflow follows a three-tier validation pattern:

1. **Frontend form (GameForm.tsx)**: User input collection with minimal validation
2. **API endpoint (games.py)**: Form data parsing and image validation
3. **Pydantic schemas (game.py)**: Backend data validation before database persistence

### Current Validation State

#### Fields WITH Backend Validation (Pydantic)

```python
# shared/schemas/game.py
class GameCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)
    max_players: int | None = Field(None, ge=1, le=100)
    expected_duration_minutes: int | None = Field(None, ge=1)
    where: str | None = Field(None, max_length=500)
    signup_instructions: str | None = Field(None, max_length=1000)
    signup_method: str | None = Field(None, max_length=50)
```

#### Fields WITHOUT Frontend Validation

1. **Expected Duration** (`expectedDurationMinutes`)
   - No error shown when user types invalid input like "Twenty nine hours"
   - `parseDurationString()` returns `null` silently
   - Sent to backend as empty/null, no user feedback

2. **Reminder Minutes** (`reminderMinutes`)
   - Accepts any text input (e.g., "abc", "1,2,invalid")
   - No validation for comma-separated format
   - No range checks (negative numbers, unreasonable values)

3. **Max Players** (`maxPlayers`)
   - HTML input type="number" allows negative numbers and decimals
   - No min/max constraints in frontend
   - Can submit values outside 1-100 range

4. **Location** (`where`)
   - `maxLength={500}` in HTML but no visual feedback when exceeded
   - No character counter shown to user

5. **Scheduled Time** (`scheduledAt`)
   - No validation for past dates
   - No minimum future time requirement
   - Can schedule games in the past

#### Fields WITH Validation

- **Title**: Required field (HTML `required` attribute)
- **Description**: Required field
- **Channel**: Required field
- **Images**: Size (<5MB) and type validation with `alert()` feedback
- **Participants**: Backend validation with rich error feedback and suggestions

### Complete Examples

#### MUI DateTimePicker with Validation

```typescript
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';

<DateTimePicker
  label="Scheduled Time *"
  value={formData.scheduledAt}
  onChange={handleDateChange}
  disablePast
  minDate={new Date()}
  slotProps={{
    textField: {
      error: !!dateError,
      helperText: dateError || 'Game start time',
    },
  }}
/>
```

#### TextField with Validation State

```typescript
<TextField
  label="Expected Duration"
  value={formData.expectedDurationMinutes}
  onChange={handleChange}
  error={!!durationError}
  helperText={durationError || 'e.g., 2h, 90m, 1h 30m'}
  placeholder="2h 30m"
/>
```

### API and Schema Documentation

#### Pydantic Field Validators

Pydantic provides:

- `Field(min_length=N, max_length=M)` for string length
- `Field(ge=N, le=M)` for numeric ranges
- `@field_validator` decorator for custom validation logic
- Automatic error responses with field-level detail

#### Error Response Format

```json
{
  "detail": [
    {
      "loc": ["body", "max_players"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### Technical Requirements

1. **Frontend validation** should mirror backend Pydantic constraints
2. **Error messages** must be user-friendly and actionable
3. **Validation timing**: Show errors on blur or submit, not on every keystroke
4. **Visual feedback**: Use MUI `error` prop and `helperText` for inline errors
5. **Accessibility**: Ensure error messages are announced to screen readers
6. **TDD Requirement**: All new code must follow Red-Green-Refactor cycle with tests written before implementation

## Recommended Approach

### Phase 0: DurationSelector Component with TDD

**Objective**: Replace text-based duration parsing with dropdown + custom input pattern

- [ ] Task 0.1: Create DurationSelector component stub
  - Create `frontend/src/components/DurationSelector.tsx` with stub implementation throwing `Error('not yet implemented')`
  - Define TypeScript interface for props
  - Export component with NotImplemented error
  - Details: Component receives `value` (minutes), `onChange`, `error`, `helperText` props

- [ ] Task 0.2: Write failing tests for DurationSelector
  - Create `frontend/src/components/__tests__/DurationSelector.test.tsx`
  - Test preset selection (2h, 4h) - expect error thrown
  - Test custom mode activation - expect error thrown
  - Test custom hours/minutes input - expect error thrown
  - Test value conversion (120 minutes → "2 hours" preset) - expect error thrown
  - Verify tests fail with "not yet implemented" error
  - Details: Use vitest and @testing-library/react

- [ ] Task 0.3: Implement minimal DurationSelector
  - Replace error with basic preset dropdown functionality
  - Add Select component with preset values (120, 240, 'custom')
  - Implement onChange handler for preset selection
  - Run tests - basic preset tests should pass
  - Details: Use MUI Select, FormControl components

- [ ] Task 0.4: Update tests and add custom mode
  - Update passing tests to verify actual behavior
  - Add custom mode UI (hours/minutes TextFields)
  - Implement custom value calculation
  - Run tests - all tests should pass
  - Details: Custom inputs appear when 'Custom...' selected

- [ ] Task 0.5: Refactor and add edge case tests
  - Add validation for hours (0-24) and minutes (0-59)
  - Add tests for invalid custom input
  - Add tests for value initialization (custom value shows custom mode)
  - Add tests for error prop display
  - Full test suite passes
  - Details: Handle edge cases like null values, out-of-range numbers

### Phase 1: Shared Validation Utilities with TDD

**Objective**: Create reusable validation functions tested comprehensively

- [ ] Task 1.1: Create validation utilities stub
  - Create `frontend/src/utils/fieldValidation.ts`
  - Define `ValidationResult` interface
  - Create stubs for all validators throwing errors:
    - `validateDuration()`
    - `validateReminderMinutes()`
    - `validateMaxPlayers()`
    - `validateCharacterLimit()`
    - `validateFutureDate()`
  - Details: Each function returns `ValidationResult` type

- [ ] Task 1.2: Write failing tests for all validators
  - Create `frontend/src/utils/__tests__/fieldValidation.test.ts`
  - Write comprehensive test cases for each validator:
    - `validateDuration`: null, 0, 1, 120, 1440, 1441, -5
    - `validateReminderMinutes`: "", "60", "60,15", "abc", "60,abc,15", "-60", "10081"
    - `validateMaxPlayers`: "", "1", "50", "100", "0", "101", "abc", "-5"
    - `validateCharacterLimit`: within limit, at 95%, exceeds limit
    - `validateFutureDate`: null, past date, future date, minHours parameter
  - All tests expect "not yet implemented" errors
  - Verify tests fail correctly
  - Details: Achieve 100% branch coverage target

- [ ] Task 1.3: Implement validateDuration
  - Replace NotImplementedError with duration validation logic
  - Handle null/0 as valid (optional field)
  - Validate range 1-1440 minutes
  - Run duration tests - should pass
  - Details: Return appropriate error messages

- [ ] Task 1.4: Implement validateReminderMinutes
  - Implement comma-separated parsing
  - Validate each value is number in range 1-10080
  - Run reminder tests - should pass
  - Details: Return array of numbers in ValidationResult.value

- [ ] Task 1.5: Implement validateMaxPlayers
  - Parse integer from string
  - Validate range 1-100
  - Run max players tests - should pass
  - Details: Handle empty string as valid (optional)

- [ ] Task 1.6: Implement validateCharacterLimit
  - Count string length
  - Return error if exceeds max
  - Return warning at 95%
  - Run character limit tests - should pass
  - Details: Include character count in messages

- [ ] Task 1.7: Implement validateFutureDate
  - Check for null
  - Compare against current time
  - Apply minHoursInFuture offset
  - Run date validation tests - should pass
  - Details: Return user-friendly error messages

- [ ] Task 1.8: Refactor and verify full coverage
  - Refactor for code clarity
  - Add edge case tests if needed
  - Verify 100% test coverage
  - All tests pass
  - Details: Run coverage report, ensure no untested paths

### Phase 2: GameForm Validation Integration with TDD

**Objective**: Apply shared validators to GameForm with complete test coverage

- [ ] Task 2.1: Add validation state to GameForm
  - Add error state variables for each validated field
  - Create validation handler functions (stubs throwing errors)
  - Add blur event handlers calling validators
  - Details: Use useState for error messages per field

- [ ] Task 2.2: Write failing GameForm validation tests
  - Create `frontend/src/components/__tests__/GameForm.validation.test.tsx`
  - Test error display on blur for each field
  - Test error clearing when field corrected
  - Test form submission blocked with errors
  - Test successful submission with valid fields
  - Verify tests fail (handlers not implemented)
  - Details: Use @testing-library/user-event for interactions

- [ ] Task 2.3: Implement GameForm validation handlers
  - Import validators from fieldValidation
  - Implement blur handlers calling validators
  - Update TextField components with error/helperText props
  - Run GameForm tests - should pass
  - Details: Block form submission if any errors exist

- [ ] Task 2.4: Replace duration TextField with DurationSelector
  - Import DurationSelector component
  - Replace duration TextField in JSX
  - Update duration change handler
  - Update tests for new component
  - All tests pass
  - Details: Remove parseDurationString usage

- [ ] Task 2.5: Add date validation to DateTimePicker
  - Add `disablePast` prop
  - Add validation on date change
  - Add error display via slotProps
  - Add tests for past date rejection
  - All tests pass
  - Details: Use validateFutureDate utility

- [ ] Task 2.6: Add character counters to text fields
  - Apply validateCharacterLimit to location, description, signup_instructions
  - Display character count in helperText
  - Add tests for counter display and warnings
  - All tests pass
  - Details: Show counters at 95% threshold

### Phase 3: TemplateForm Validation Integration with TDD

**Objective**: Apply same validation pattern to TemplateForm for consistency

- [ ] Task 3.1: Add on-blur validation to TemplateForm
  - Add error state for each field
  - Create validation handlers (stubs)
  - Add blur event handlers
  - Details: Currently only validates on submit

- [ ] Task 3.2: Write failing TemplateForm validation tests
  - Create `frontend/src/components/__tests__/TemplateForm.validation.test.tsx`
  - Test on-blur validation behavior
  - Test character counters
  - Test submit-time validation still works
  - Verify tests fail correctly
  - Details: Ensure consistency with GameForm patterns

- [ ] Task 3.3: Implement TemplateForm validation
  - Import shared validators
  - Implement blur handlers
  - Update TextField components with error props
  - Run tests - should pass
  - Details: Replace inline validation in validate() method

- [ ] Task 3.4: Replace duration TextField with DurationSelector
  - Import DurationSelector
  - Replace duration TextField
  - Update tests
  - All tests pass
  - Details: Same pattern as GameForm

- [ ] Task 3.5: Add character counters
  - Apply character validation to text fields
  - Display counters in helperText
  - Add tests for counters
  - All tests pass
  - Details: Match GameForm behavior

### Phase 4: Backend Schema Alignment with TDD

**Objective**: Ensure backend validation matches frontend constraints

- [ ] Task 4.1: Update template schema constraints
  - Add missing max_length to description, where, signup_instructions
  - Details: Match GameCreateRequest constraints

- [ ] Task 4.2: Write/update API tests for schema validation
  - Test max_length enforcement
  - Test field range validation
  - Verify Pydantic error responses
  - Details: Ensure frontend/backend validation parity

- [ ] Task 4.3: Verify API tests pass
  - Run API test suite
  - Fix any validation mismatches
  - All tests pass
  - Details: Backend validation should match frontend

### Phase 5: Cleanup and Final Verification with TDD

**Objective**: Remove deprecated code and verify complete integration

- [ ] Task 5.1: Remove deprecated parsing functions
  - Delete `parseDurationString` from GameForm.tsx
  - Delete `formatDurationForDisplay` if unused
  - Search for other usages and remove
  - Details: No longer needed with DurationSelector

- [ ] Task 5.2: Write integration tests for error handling
  - Test backend error display still works (mentions)
  - Test ValidationErrors component integration
  - Test image upload validation preserved
  - Test error clearing on successful submission
  - Details: Ensure existing error patterns unaffected

- [ ] Task 5.3: Run full test suite
  - Run all frontend tests
  - Run all backend tests
  - Verify 100% coverage for new code
  - All tests pass
  - Details: Full regression validation

- [ ] Task 5.4: Manual QA testing
  - Test GameForm with valid/invalid inputs
  - Test TemplateForm with valid/invalid inputs
  - Test on mobile (numeric keyboards for custom duration)
  - Test accessibility (screen reader announcements)
  - Details: End-to-end user experience validation

## Implementation Guidance

- **Objectives**:
  1. **Test-First Development**: Write tests before implementation for all new code
  2. **DRY Principle**: Single source of truth for validation logic in `fieldValidation.ts`
  3. **Immediate Feedback**: Catch validation errors before backend submission
  4. **Consistency**: Identical validation UX across GameForm and TemplateForm
  5. **100% Coverage**: Complete test coverage for all validation logic

- **Key TDD Requirements**:
  1. Create stubs with `throw new Error('not yet implemented')` BEFORE writing tests
  2. Write tests expecting errors to be thrown (RED phase)
  3. Run tests to verify they fail correctly
  4. Implement minimal solution to make tests pass (GREEN phase)
  5. Refactor with passing tests (REFACTOR phase)
  6. Never skip steps or write implementation before tests

- **Dependencies**:
  - MUI components (already imported)
  - vitest, @testing-library/react (already configured)
  - No new libraries required
  - Existing Pydantic schemas for validation constraints

- **Success Criteria**:
  1. DurationSelector component tested and reusable
  2. All validators in `fieldValidation.ts` have 100% test coverage
  3. GameForm validation prevents all invalid submissions
  4. TemplateForm validation matches GameForm behavior
  5. Backend schemas aligned with frontend constraints
  6. All tests pass (unit, integration, API)
  7. No text parsing errors possible
  8. Character counters display on all limited-length fields
  9. Mobile users get appropriate input types
  10. Existing error handling patterns preserved
