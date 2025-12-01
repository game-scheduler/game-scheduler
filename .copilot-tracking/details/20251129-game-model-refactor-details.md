<!-- markdownlint-disable-file -->

# Task Details: Game Model Refactor (Remove min_players, Add where field)

## Research Reference

**Source Research**: #file:../research/20251129-game-model-refactor-research.md

## Phase 1: Add where Field to Database (Safe - Optional Column)

### Task 1.1: Create migration to add where column

Create Alembic migration to add where column as nullable field.

- **Files**:
  - `alembic/versions/014_add_where_field.py` - New migration file
- **Success**:
  - Migration file created with proper upgrade/downgrade functions
  - upgrade() adds where column as nullable TEXT
  - downgrade() drops where column
  - Migration follows existing naming convention (014\_\*)
  - System remains fully functional after migration
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 222-240) - Migration strategy
  - alembic/versions/005_add_description_signup_instructions.py - Pattern for adding nullable fields
- **Dependencies**:
  - Alembic configured and working

### Task 1.2: Add where field to GameSession model

Add the where field to the SQLAlchemy model.

- **Files**:
  - `shared/models/game.py` - GameSession class
- **Success**:
  - where field added as `Mapped[str | None] = mapped_column(Text, nullable=True)`
  - where field positioned after scheduled_at field for logical grouping
  - Model imports remain correct
  - Model works with existing database schema
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 242-253) - Field specifications
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Run migration to add where column

Execute the migration against the database.

- **Files**:
  - Database schema updated
- **Success**:
  - Migration runs successfully with `alembic upgrade head`
  - where column added to game_sessions table as nullable
  - Existing game records preserve all data
  - System continues to work without code changes
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 222-240) - Migration strategy
- **Dependencies**:
  - Task 1.1 and 1.2 completion

## Phase 2: Add where Field to API Layer (with tests)

### Task 2.1: Add where field to API schemas

Add where field to all Pydantic schemas.

- **Files**:
  - `shared/schemas/game.py` - GameCreateRequest, GameUpdateRequest, GameResponse
- **Success**:
  - where field added to GameCreateRequest as optional with max_length=500
  - where field added to GameUpdateRequest as optional
  - where field added to GameResponse as nullable
  - All fields have proper Field descriptions
  - min_players remains unchanged (still working)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 242-253) - Field specifications
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update service layer to handle where field

Add where field handling to game service methods.

- **Files**:
  - `services/api/services/games.py` - create_game() and update_game() methods
- **Success**:
  - where field handled in game creation (stored from game_data.where)
  - where field handled in game updates (updated from update_data.where)
  - where field included in response building
  - min_players logic remains unchanged
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 56-62) - where field handling
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update backend tests for where field

Add where field to backend test fixtures.

- **Files**:
  - `tests/services/api/routes/test_games_timezone.py` - Add where field to test data
  - `tests/services/api/services/test_games_promotion.py` - Add where field to test data
  - `tests/services/api/services/test_games_edit_participants.py` - Add where field to test data
  - All other test files with GameSession creation
- **Success**:
  - where field added to test fixtures (can be None or test value)
  - Tests verify where field is stored and retrieved correctly
  - Tests verify where field appears in API responses
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 81-87) - Test file list
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Run backend tests to verify where field

Execute backend tests to ensure where field works.

- **Files**:
  - All backend test files
- **Success**:
  - All backend unit tests pass
  - All backend service tests pass
  - where field properly stored and retrieved
  - No regressions in existing functionality
- **Research References**:
  - Test execution patterns from existing test suite
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: Add where Field to Discord Bot (with tests)

### Task 3.1: Update game message formatter for where field

Add where field display to Discord game embeds.

- **Files**:
  - `services/bot/formatters/game_message.py` - GameMessageFormatter.create_game_embed() and format_game_announcement()
- **Success**:
  - create_game_embed() accepts where parameter (optional)
  - format_game_announcement() accepts where parameter (optional)
  - where field displayed immediately after "When" field
  - Format: `embed.add_field(name="Where", value=where, inline=False)` (only if where is not None)
  - Field order: When → Where → Players → Host → other fields
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 175-191) - Display positioning
  - services/bot/formatters/game_message.py (Lines 76-84) - Current embed structure
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Update event handlers to pass where field

Pass where field from GameSession to message formatter.

- **Files**:
  - `services/bot/events/handlers.py` - \_create_game_announcement() method
- **Success**:
  - format_game_announcement() call includes where=game.where parameter
  - where field retrieved from GameSession model
  - All game announcement calls include where field
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 64-69) - Event handler updates
  - services/bot/events/handlers.py (Lines 547-577) - Current implementation
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Run bot tests to verify where field

Execute bot tests to ensure where field displays correctly.

- **Files**:
  - Bot formatter tests
  - Bot event handler tests
- **Success**:
  - Bot tests pass
  - where field appears in Discord embeds when populated
  - Embed formatting correct
  - No errors in bot message generation
- **Research References**:
  - Existing bot test patterns
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Add where Field to Frontend (with tests)

### Task 4.1: Add where field to TypeScript interfaces

Add where field to GameSession interface.

- **Files**:
  - `frontend/src/types/index.ts` - GameSession interface
- **Success**:
  - where field added as `where: string | null`
  - Field positioned after scheduled_at for logical grouping
  - TypeScript compilation succeeds
  - min_players remains in interface (still functional)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 50-62) - Frontend types
- **Dependencies**:
  - Phase 2 completion (API returns where field)

### Task 4.2: Add where input to CreateGame and EditGame pages

Add where input field to game forms.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Game creation form
  - `frontend/src/pages/EditGame.tsx` - Game editing form
- **Success**:
  - Where input field added to both forms (positioned after scheduled time)
  - Where field uses TextField with multiline (up to 3 rows) for longer locations
  - Form state includes where field
  - API calls include where field in payload
  - Min Players field remains unchanged (still functional)
  - Field order: Title → Scheduled Time → Where → Description → Min/Max Players
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 71-79) - Frontend forms
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Display where field in GameDetails page

Display where field below "When:" field.

- **Files**:
  - `frontend/src/pages/GameDetails.tsx` - Game details display
- **Success**:
  - where field displayed immediately after "When:" field (after Line 209)
  - Format: `<Typography><strong>Where:</strong> {game.where}</Typography>`
  - Only displayed if game.where is not null/empty
  - Consistent styling with other fields
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 193-207) - Display positioning
  - frontend/src/pages/GameDetails.tsx (Line 209) - Current structure
- **Dependencies**:
  - Task 4.1 completion

### Task 4.4: Display where field in GameCard component

Display where field in game list cards.

- **Files**:
  - `frontend/src/components/GameCard.tsx` - Game card component
- **Success**:
  - where field displayed below "When:" field (after Line 81)
  - Format matches GameDetails styling
  - Only show where if populated
  - Participant count still shows min-max format (unchanged)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 193-207) - Display positioning
  - frontend/src/components/GameCard.tsx (Line 81) - Current structure
- **Dependencies**:
  - Task 4.1 completion

### Task 4.5: Update frontend tests for where field

Add where field to frontend test mocks.

- **Files**:
  - `frontend/src/pages/__tests__/EditGame.test.tsx` - Update mock GameSession
  - All other frontend test files with GameSession mocks
- **Success**:
  - where field added to all mock GameSession objects
  - Tests verify where field renders correctly
  - Form tests verify where input works
  - min_players remains in mocks (still functional)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 89-91) - Frontend tests
- **Dependencies**:
  - Task 4.4 completion

### Task 4.6: Run frontend tests to verify where field

Execute frontend tests to ensure where field works.

- **Files**:
  - All frontend test files
- **Success**:
  - All frontend unit tests pass
  - All component rendering tests pass
  - where field displays correctly
  - No regressions in existing functionality
- **Research References**:
  - Existing frontend test patterns
- **Dependencies**:
  - Task 4.5 completion

## Phase 5: Remove min_players from API Layer (with tests)

### Task 5.1: Remove min_players from API schemas

Remove min_players field from all Pydantic schemas.

- **Files**:
  - `shared/schemas/game.py` - GameCreateRequest, GameUpdateRequest, GameResponse
- **Success**:
  - min_players removed from GameCreateRequest (currently Line 24)
  - min_players removed from GameUpdateRequest (currently Line 66)
  - min_players removed from GameResponse (currently Line 116)
  - All other fields remain functional
  - Database still has min_players column (safe)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 38-48) - Current schema structure
- **Dependencies**:
  - Phase 4 completion (frontend no longer uses min_players)

### Task 5.2: Remove min_players validation from routes

Remove min_players validation from API route handlers.

- **Files**:
  - `services/api/routes/games.py` - create_game and update_game endpoints
- **Success**:
  - Min/max players validation removed from create_game (Lines 64-68)
  - Related validation comments updated or removed
  - No validation logic references min_players
  - Routes continue to work correctly
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 50-54) - Route validation
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Remove min_players validation from service layer

Remove min_players validation from game service methods.

- **Files**:
  - `services/api/services/games.py` - create_game() and update_game() methods
- **Success**:
  - Min/max validation removed from create_game() (Lines 129-133)
  - Min/max validation removed from update_game() (Lines 483-493)
  - No code references min_players field
  - Service methods work correctly
  - Database column still exists (safe)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 50-54) - Service validation
- **Dependencies**:
  - Task 5.2 completion

### Task 5.4: Update backend tests to remove min_players

Remove min_players from backend test fixtures and assertions.

- **Files**:
  - `tests/services/api/routes/test_games_timezone.py` - Remove min_players (Lines 40, 96, 151, 222)
  - `tests/services/api/services/test_games_promotion.py` - Remove min_players (Line 94)
  - `tests/services/api/services/test_games_edit_participants.py` - Remove min_players (Lines 127, 218)
  - `tests/services/api/routes/test_games_participant_count.py` - Remove min_players (Lines 53, 116, 194, 277)
  - All other test files with GameSession creation
- **Success**:
  - All min_players references removed from test data
  - Tests no longer assert on min_players
  - Test fixtures valid without min_players
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 81-87) - Test file list
- **Dependencies**:
  - Task 5.3 completion

### Task 5.5: Run backend tests to verify min_players removal

Execute backend tests to ensure min_players removal works.

- **Files**:
  - All backend test files
- **Success**:
  - All backend unit tests pass
  - All backend service tests pass
  - No min_players validation errors
  - API works correctly without min_players
- **Research References**:
  - Test execution patterns
- **Dependencies**:
  - Task 5.4 completion

## Phase 6: Remove min_players from Frontend (with tests)

### Task 6.1: Remove min_players from TypeScript interfaces

Remove min_players field from GameSession interface.

- **Files**:
  - `frontend/src/types/index.ts` - GameSession interface
- **Success**:
  - min_players removed from GameSession (currently Line 40)
  - TypeScript compilation succeeds
  - No component references min_players
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 50-62) - Frontend types
- **Dependencies**:
  - Phase 5 completion (API no longer returns min_players)

### Task 6.2: Remove min_players from CreateGame and EditGame pages

Remove min_players input field from game forms.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Game creation form
  - `frontend/src/pages/EditGame.tsx` - Game editing form
- **Success**:
  - Min Players input field removed from both forms
  - Form state no longer includes min_players
  - Form validation no longer checks min <= max
  - API calls do not include min_players in payload
  - Field order: Title → Scheduled Time → Where → Description → Max Players
  - Forms work correctly
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 71-79) - Frontend forms
- **Dependencies**:
  - Task 6.1 completion

### Task 6.3: Update ParticipantList to show X/max format

Update participant count display format.

- **Files**:
  - `frontend/src/components/ParticipantList.tsx` - Participant list component
- **Success**:
  - Participant count format changed from "X/min-max" to "X/max"
  - Remove any min_players props or references
  - Display logic simplified
  - Component works correctly
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 255-260) - Participant count format
- **Dependencies**:
  - Task 6.1 completion

### Task 6.4: Update GameCard participant count display

Update participant count in game cards.

- **Files**:
  - `frontend/src/components/GameCard.tsx` - Game card component
- **Success**:
  - Participant count updated from "X/min-max" to "X/max" format
  - No references to min_players
  - Cards display correctly
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 255-260) - Participant count format
  - frontend/src/components/GameCard.tsx (Line 81) - Current structure
- **Dependencies**:
  - Task 6.1 completion

### Task 6.5: Update frontend tests to remove min_players

Remove min_players from frontend test mocks.

- **Files**:
  - `frontend/src/pages/__tests__/EditGame.test.tsx` - Update mock GameSession
  - All other frontend test files with GameSession mocks
- **Success**:
  - min_players removed from all mock GameSession objects
  - Tests verify participant count format is "X/max"
  - All test assertions updated
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 89-91) - Frontend tests
- **Dependencies**:
  - Task 6.4 completion

### Task 6.6: Run frontend tests to verify min_players removal

Execute frontend tests to ensure min_players removal works.

- **Files**:
  - All frontend test files
- **Success**:
  - All frontend unit tests pass
  - All component rendering tests pass
  - Participant count displays correctly
  - No regressions in functionality
- **Research References**:
  - Existing frontend test patterns
- **Dependencies**:
  - Task 6.5 completion

## Phase 7: Remove min_players from Database (with tests)

### Task 7.1: Remove min_players from GameSession model

Remove the min_players field from the SQLAlchemy model.

- **Files**:
  - `shared/models/game.py` - GameSession class
- **Success**:
  - min_players field removed from model (currently Line 42)
  - Model imports remain correct
  - Model works correctly (column still in DB is safe)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 14-36) - Current model structure
- **Dependencies**:
  - Phase 5 and 6 completion (no code references min_players)

### Task 7.2: Create migration to drop min_players column

Create Alembic migration to remove min_players column from database.

- **Files**:
  - `alembic/versions/015_remove_min_players_field.py` - New migration file
- **Success**:
  - Migration file created with proper upgrade/downgrade functions
  - upgrade() drops min_players column
  - downgrade() restores min_players column with default value
  - Migration follows existing naming convention (015\_\*)
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 222-240) - Migration strategy
  - alembic/versions/004_add_min_players_field.py - Reverse of this migration
- **Dependencies**:
  - Task 7.1 completion

### Task 7.3: Run migration to drop min_players column

Execute the migration against the database.

- **Files**:
  - Database schema updated
- **Success**:
  - Migration runs successfully with `alembic upgrade head`
  - min_players column removed from game_sessions table
  - Existing game records preserve all other data
  - System works correctly without the column
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 222-240) - Migration strategy
- **Dependencies**:
  - Task 7.2 completion

### Task 7.4: Run integration tests to verify database changes

Execute integration tests to verify database schema changes.

- **Files**:
  - Integration test suite
- **Success**:
  - All integration tests pass
  - Database operations work correctly
  - No errors related to missing min_players column
  - where field properly stored and retrieved
- **Research References**:
  - Existing integration test patterns
- **Dependencies**:
  - Task 7.3 completion

## Phase 8: Final Verification

### Task 8.1: Run full test suite

Execute complete test suite to verify all changes.

- **Files**:
  - All test files (backend, frontend, integration, e2e)
- **Success**:
  - All backend unit tests pass
  - All backend integration tests pass
  - All backend e2e tests pass
  - All frontend unit tests pass
  - All frontend component tests pass
  - No regressions in existing functionality
  - Both migrations (add where, remove min_players) can be rolled back
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 285-299) - Success criteria
- **Dependencies**:
  - Phase 7 completion

### Task 8.2: Add where field to game display pages

Display the where field on both game summary and details pages, labeled as "Where" and positioned right under the "When" line.

- **Files**:
  - `frontend/src/components/GameCard.tsx` - Game summary card component
  - `frontend/src/pages/GameDetails.tsx` - Game details page
- **Success**:
  - Where field displays on GameCard (My Games page) under the When line
  - Where field displays on GameDetails page under the When line
  - Label is "Where:"
  - Field only displays when where value exists
  - Styling is consistent with When field
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 214-226) - GameCard structure
  - #file:../research/20251129-game-model-refactor-research.md (Lines 200-212) - GameDetails structure
- **Dependencies**:
  - Phase 4 completion (where field in TypeScript interfaces)

### Task 8.3: Add where field to Discord bot embed message

Display the where field in the Discord bot's game announcement embed message, positioned under the When line.

- **Files**:
  - `services/bot/formatters/game_message.py` - Game message formatter
- **Success**:
  - Where field displays in Discord embed under When field
  - Label is "Where:"
  - Field only displays when where value exists
  - Formatting matches existing When field style
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 124-140) - Bot formatter structure
- **Dependencies**:
  - Phase 3 completion (where field in bot handlers)

### Task 8.4: Reorder where field on create game page

Move the where input field to be positioned directly below the Game Title field on the create/edit game forms.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Game creation form
  - `frontend/src/pages/EditGame.tsx` - Game editing form (if separate)
- **Success**:
  - Where field appears immediately after Game Title field
  - Form flow is: Game Title → Where → When → other fields
  - Field validation and behavior unchanged
- **Research References**:
  - #file:../research/20251129-game-model-refactor-research.md (Lines 181-198) - CreateGame structure
- **Dependencies**:
  - Phase 4 completion (where field added to forms)

### Task 8.5: Display Max Players and Notify Roles on same line

Adjust the game creation form layout to display Max Players and Notify Roles fields on the same horizontal line.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Game creation form
  - `frontend/src/pages/EditGame.tsx` - Game editing form (if separate)
- **Success**:
  - Max Players and Notify Roles fields appear on same row
  - Fields are appropriately sized for horizontal layout
  - Form remains responsive on smaller screens
  - Field functionality unchanged
- **Research References**:
  - Material-UI Grid layout patterns for side-by-side fields
  - #file:../research/20251129-game-model-refactor-research.md (Lines 181-198) - CreateGame structure
- **Dependencies**:
  - Phase 4 completion

### Task 8.6: Verify system functionality end-to-end

Manual verification of complete system behavior.

- **Files**:
  - System running in test/dev environment
- **Success**:
  - Can create games with where field via web UI
  - Can create games with where field via Discord bot
  - Games display where field in Discord messages (under When line)
  - Games display where field in web UI (GameCard and GameDetails, under When line)
  - Where field positioned below Game Title on create/edit forms
  - Max Players and Notify Roles on same line in forms
  - Participant counts show "X/max" format everywhere
  - No min_players references in UI
  - System stable and performant
- **Research References**:
  - User acceptance criteria from requirements
- **Dependencies**:
  - Tasks 8.1-8.5 completion

## Dependencies

- PostgreSQL database
- Alembic migration tool
- Python 3.11+ with SQLAlchemy and Pydantic
- Node.js with TypeScript
- React and Material-UI

## Success Criteria

- Database schema updated (min_players removed, where added)
- All API schemas and routes updated
- Discord bot displays where field in announcements
- Frontend forms and displays updated
- Participant counts show "X/max" format
- All tests pass
- Migration is reversible
