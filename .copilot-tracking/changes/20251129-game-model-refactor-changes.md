<!-- markdownlint-disable-file -->

# Release Changes: Game Model Refactor (Remove min_players, Add where field)

**Related Plan**: 20251129-game-model-refactor-plan.instructions.md
**Implementation Date**: 2025-11-30

## Summary

Refactoring the game data model to remove the unused `min_players` field and add a `where` field for game location information. This change improves the user experience by simplifying participant count displays and adding location tracking capabilities.

## Changes

### Phase 1: Add where Field to Database ✓

### Added

- alembic/versions/014_add_where_field.py - Migration to add where column to game_sessions table

### Modified

- shared/models/game.py - Added where field to GameSession model as nullable Text field
  - Positioned after scheduled_at for logical grouping (when/where)
  - Implemented as `Mapped[str | None] = mapped_column(Text, nullable=True)`

### Database Changes

- game_sessions table now includes `where` column (TEXT, nullable)
- Migration 014_add_where_field executed successfully
- All existing game records preserved with NULL values for where field

### Removed

### Phase 2: Add where Field to API Layer ✓

### Modified

- shared/schemas/game.py - Added where field to all Pydantic schemas
  - GameCreateRequest: where field as optional with max_length=500
  - GameUpdateRequest: where field as optional with max_length=500
  - GameResponse: where field as nullable with description
- services/api/services/games.py - Added where field handling in create_game and update_game methods
  - create_game: where field stored from game_data.where
  - update_game: where field updated from update_data.where
- tests/services/api/services/test_games.py - Added tests for where field
  - test_create_game_with_where_field: Verifies where field is stored on game creation
  - test_update_game_where_field: Verifies where field can be updated

### Test Results

All backend tests pass successfully:

- `tests/services/api/services/test_games.py`: 18 tests passed (including 2 new where field tests)
- `tests/services/api/routes/test_games_timezone.py`: 4 tests passed
- `tests/services/api/services/test_games_promotion.py`: 3 tests passed

### Code Quality

- All modified Python files pass ruff linting
- Code follows Python 3.11+ conventions with modern type hints
- Self-documenting code with appropriate docstrings
- All Docker containers build successfully (API, test)

## Release Summary

_Will be completed after all phases are implemented_
