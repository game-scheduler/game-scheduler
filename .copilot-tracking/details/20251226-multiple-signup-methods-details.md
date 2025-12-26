<!-- markdownlint-disable-file -->

# Task Details: Multiple Signup Methods

## Research Reference

**Source Research**: #file:../research/20251226-multiple-signup-methods-research.md

## Phase 1: Backend Schema and Model

### Task 1.1: Create SignupMethod enum

Create new enum for signup method types following existing GameStatus pattern.

- **Files**:
  - shared/models/signup_method.py - New enum definition
  - shared/models/__init__.py - Export SignupMethod
- **Success**:
  - SignupMethod enum uses `class SignupMethod(str, Enum)` pattern
  - Has SELF_SIGNUP and HOST_SELECTED values
  - Includes display_name and description properties
  - Follows GameStatus enum pattern exactly
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 127-156) - SignupMethod enum specification
  - shared/models/game.py (Lines 38-56) - GameStatus enum pattern to follow
- **Dependencies**:
  - None

### Task 1.2: Update GameTemplate model with signup method fields

Add signup method configuration fields to GameTemplate model.

- **Files**:
  - shared/models/template.py - Add allowed_signup_methods and default_signup_method fields
- **Success**:
  - `allowed_signup_methods: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)` added
  - `default_signup_method: Mapped[str | None] = mapped_column(String(50), nullable=True)` added
  - Fields positioned with other pre-populated fields (after locked fields section)
  - Comments explain: null/empty list = all methods, default must be in allowed list
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 158-183) - Configuration storage design
  - shared/models/template.py (Lines 46-145) - Existing template structure
- **Dependencies**:
  - Task 1.1 completion (enum available for import)

### Task 1.3: Update GameSession model with signup_method field

Add signup_method field to GameSession model to store selected method.

- **Files**:
  - shared/models/game.py - Add signup_method field
- **Success**:
  - `signup_method: Mapped[str] = mapped_column(String(50), default=SignupMethod.SELF_SIGNUP.value, nullable=False)` added
  - Field positioned with other core game fields (after status)
  - Import SignupMethod from .signup_method
  - Default value uses SignupMethod.SELF_SIGNUP.value
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 158-183) - GameSession field requirements
  - shared/models/game.py (Lines 58-110) - GameSession model structure
- **Dependencies**:
  - Task 1.1 completion (enum available for import)

### Task 1.4: Create database migration

Create Alembic migration to add signup method fields with data backfill.

- **Files**:
  - alembic/versions/YYYYMMDD_add_signup_methods.py - New migration file
- **Success**:
  - Migration adds allowed_signup_methods (JSON, nullable) to game_templates
  - Migration adds default_signup_method (String(50), nullable) to game_templates
  - Migration adds signup_method (String(50), nullable) to game_sessions
  - Backfill: `UPDATE game_sessions SET signup_method = 'SELF_SIGNUP'`
  - After backfill: `ALTER COLUMN signup_method SET NOT NULL`
  - Downgrade reverses all changes
  - Migration runs successfully
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 210-230) - Migration pattern
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 103-118) - Database migration patterns
  - alembic/versions/ - Recent migration examples
- **Dependencies**:
  - Task 1.1, 1.2, 1.3 completion (models updated)

## Phase 2: API Schema and Service

### Task 2.1: Update GameCreateRequest schema

Add optional signup_method field to GameCreateRequest schema.

- **Files**:
  - shared/schemas/game.py - Update GameCreateRequest
- **Success**:
  - `signup_method: str | None` field added with Field() descriptor
  - Description: "Signup method override (uses template default if None)"
  - Positioned with other optional overrides (after initial_participants)
  - No validation here (validated in service layer)
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 240-247) - Schema updates
  - shared/schemas/game.py (Lines 34-83) - GameCreateRequest structure
- **Dependencies**:
  - Phase 1 completion (database schema exists)

### Task 2.2: Update GameResponse schema

Add signup_method field to GameResponse schema.

- **Files**:
  - shared/schemas/game.py - Update GameResponse
- **Success**:
  - `signup_method: str` field added (required, not optional)
  - Description: "Signup method for this game"
  - Positioned with other game configuration fields (after status)
  - Field included in all game responses
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 240-247) - Schema updates
  - shared/schemas/game.py (Lines 136-173) - GameResponse structure
- **Dependencies**:
  - Phase 1 completion (database schema exists)

### Task 2.3: Update GameService.create_game() with signup method resolution

Add signup method validation and resolution logic to game creation.

- **Files**:
  - services/api/services/games.py - Update create_game method
- **Success**:
  - Resolve signup_method: request value → template default → SELF_SIGNUP fallback
  - Validate against template.allowed_signup_methods if list is not empty
  - Raise ValueError if signup_method not in allowed list
  - Store resolved signup_method in GameSession
  - Import SignupMethod enum for validation
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 249-260) - Service layer logic
  - services/api/services/games.py (Lines 132-330) - create_game method structure
- **Dependencies**:
  - Task 2.1, 2.2 completion (schemas updated)

### Task 2.4: Update template schemas for signup method fields

Add signup method fields to template response schemas.

- **Files**:
  - shared/schemas/template.py - Update template schemas
- **Success**:
  - TemplateResponse includes allowed_signup_methods (list[str] | None)
  - TemplateResponse includes default_signup_method (str | None)
  - CreateTemplateRequest includes optional signup method fields
  - UpdateTemplateRequest includes optional signup method fields
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 262-273) - Template API updates
- **Dependencies**:
  - Phase 1 completion (database schema exists)

## Phase 3: Discord Bot Button Control

### Task 3.1: Update GameView with signup_method parameter

Add signup_method parameter to GameView and use it to control join button state.

- **Files**:
  - services/bot/views/game_view.py - Update GameView class
- **Success**:
  - Add `signup_method: str` parameter to __init__
  - Store as instance variable
  - Update join_button.disabled logic: `disabled=is_started or (signup_method == SignupMethod.HOST_SELECTED.value)`
  - Import SignupMethod enum
  - Docstring updated with signup_method parameter
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 275-284) - GameView updates
  - services/bot/views/game_view.py (Lines 29-121) - GameView implementation
- **Dependencies**:
  - Phase 1 completion (SignupMethod enum exists)

### Task 3.2: Update format_game_announcement() to pass signup_method

Add signup_method parameter to message formatter and pass to GameView.

- **Files**:
  - services/bot/formatters/game_message.py - Update format_game_announcement function
- **Success**:
  - Add `signup_method: str` parameter to function signature
  - Pass signup_method to GameView constructor
  - Update docstring with new parameter
  - Update all callers to provide signup_method
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 286-295) - Message formatter updates
  - services/bot/formatters/game_message.py (Lines 223-330) - format_game_announcement implementation
- **Dependencies**:
  - Task 3.1 completion (GameView accepts signup_method)

### Task 3.3: Update event handlers to pass signup_method to GameView

Update all event handlers that create game messages to pass signup_method.

- **Files**:
  - services/bot/events/handlers.py - Update _handle_game_created, _refresh_game_message
  - services/bot/handlers/*.py - Update any other handlers that create game views
- **Success**:
  - All GameView instantiations include signup_method from game.signup_method
  - format_game_announcement calls include signup_method parameter
  - No errors when creating or updating game messages
  - Button state reflects signup method correctly
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 297-310) - Event handler updates
  - services/bot/events/handlers.py - Event handler implementations
- **Dependencies**:
  - Task 3.2 completion (formatter accepts signup_method)

## Phase 4: Frontend UI

### Task 4.1: Update TypeScript types and interfaces

Add signup method fields to TypeScript type definitions.

- **Files**:
  - frontend/src/types/index.ts - Update GameSession, GameTemplate, add SignupMethod enum
- **Success**:
  - SignupMethod enum/type with SELF_SIGNUP and HOST_SELECTED values
  - GameTemplate interface includes allowed_signup_methods (string[] | null) and default_signup_method (string | null)
  - GameSession interface includes signup_method (string)
  - Helper functions for display names and descriptions
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 312-327) - Frontend types
  - frontend/src/types/index.ts - Existing type definitions
- **Dependencies**:
  - Phase 2 completion (API schemas updated)

### Task 4.2: Add signup method selector to GameForm

Add FormControl with Select dropdown for signup method in GameForm component.

- **Files**:
  - frontend/src/components/GameForm.tsx - Add signup method selector
- **Success**:
  - signupMethod field added to GameFormData interface
  - FormControl with Select positioned after max_players field
  - Dropdown populated with available methods from template
  - Helper text shows description of selected method
  - onChange updates formData.signupMethod
  - Dropdown disabled during loading
  - Label: "Signup Method"
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 329-354) - GameForm updates
  - frontend/src/components/GameForm.tsx - Form component structure
- **Dependencies**:
  - Task 4.1 completion (types defined)

### Task 4.3: Update CreateGame page with signup method handling

Update CreateGame page to load template signup methods and pass to GameForm.

- **Files**:
  - frontend/src/pages/CreateGame.tsx - Add signup method logic
- **Success**:
  - Extract allowed_signup_methods from selectedTemplate
  - Calculate available methods (null/empty = all methods)
  - Auto-select default_signup_method from template or first allowed method
  - Pass availableSignupMethods as prop to GameForm
  - Include signup_method in form submission payload
  - Handle case where template has no signup method configuration (use all methods)
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 356-373) - CreateGame updates
  - frontend/src/pages/CreateGame.tsx (Lines 1-400) - Page implementation
- **Dependencies**:
  - Task 4.2 completion (GameForm accepts signup method props)

### Task 4.4: Display signup method in GameDetails page

Show selected signup method in game details view.

- **Files**:
  - frontend/src/pages/GameDetails.tsx - Add signup method display
- **Success**:
  - Signup method displayed with icon (🔓 for Self Signup, 🔒 for Host Selected)
  - Positioned near other game metadata (after max_players or status)
  - Uses Chip or Typography component
  - Shows display name from SignupMethod helper
  - Includes tooltip with description
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 375-385) - GameDetails display
  - frontend/src/pages/GameDetails.tsx - Details page structure
- **Dependencies**:
  - Task 4.1 completion (types and helpers available)

## Phase 5: Testing and Validation

### Task 5.1: Add unit tests for SignupMethod enum

Test enum values, display names, and descriptions.

- **Files**:
  - tests/shared/models/test_signup_method.py - New test file
- **Success**:
  - Test enum values are correct strings
  - Test display_name property returns correct values
  - Test description property returns correct values
  - Test enum members can be used as strings
  - All tests pass
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 387-397) - Testing requirements
- **Dependencies**:
  - Phase 1 completion (enum implemented)

### Task 5.2: Add integration tests for game creation with signup methods

Test game creation with different signup method configurations.

- **Files**:
  - tests/services/api/services/test_games.py - Add signup method tests
- **Success**:
  - Test game creation with SELF_SIGNUP explicit
  - Test game creation with HOST_SELECTED explicit
  - Test game creation uses template default when not specified
  - Test game creation uses SELF_SIGNUP fallback when no template default
  - Test validation error when signup_method not in allowed list
  - Test null/empty allowed list accepts any method
  - All tests pass
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 399-415) - Integration testing
- **Dependencies**:
  - Phase 2 completion (service layer implemented)

### Task 5.3: Add E2E tests for Discord button behavior

Test Discord join button enabled/disabled state based on signup method.

- **Files**:
  - tests/e2e/test_signup_methods.py - New E2E test file
- **Success**:
  - Test SELF_SIGNUP game has enabled join button
  - Test HOST_SELECTED game has disabled join button
  - Test button state persists after bot restart (using game ID)
  - Test clicking disabled button shows appropriate error
  - All tests pass
- **Research References**:
  - #file:../research/20251226-multiple-signup-methods-research.md (Lines 417-428) - E2E testing
- **Dependencies**:
  - Phase 3 completion (bot implementation finished)

## Dependencies

- Python 3.11+ with str, Enum support
- Existing template system
- Discord button view infrastructure
- Frontend MUI component library

## Success Criteria

- All phases completed with checkboxes marked
- Database migration runs without errors
- All unit tests pass
- All integration tests pass
- All E2E tests pass
- Frontend displays signup method selector correctly
- Discord button respects signup method setting
- Existing games migrated to SELF_SIGNUP
- No breaking changes to existing functionality
