<!-- markdownlint-disable-file -->

# Release Changes: Discord Calendar Download Feature

**Related Plan**: 20251218-discord-calendar-download-plan.instructions.md
**Implementation Date**: 2025-12-19

## Summary

Enable Discord users to download game calendars via clickable embed title that opens a frontend download page with authentication.

## Changes

### Added

- frontend/src/pages/DownloadCalendar.tsx - New page component for authenticated calendar downloads with loading states and error handling
- frontend/src/pages/__tests__/DownloadCalendar.test.tsx - Comprehensive unit tests with 97.67% statement coverage (8 test cases covering authentication, download flow, error handling, navigation)

### Modified

- frontend/src/App.tsx - Added route for /download-calendar/:gameId with ProtectedRoute wrapper using Outlet pattern and DownloadCalendar import
- frontend/package.json - Added @vitest/coverage-v8 dev dependency for test coverage reporting
- services/bot/config.py - Added frontend_url configuration field (defaults to http://localhost:5173 for development)
- services/bot/formatters/game_message.py - Updated create_game_embed to accept game_id parameter and generate clickable title URL linking to frontend download page
- tests/services/bot/formatters/test_game_message.py - Added 2 unit tests for URL functionality (with and without game_id)
- services/api/routes/export.py - Added generate_calendar_filename() helper function and updated export_game() endpoint to use descriptive filename with game title and date
- tests/services/api/routes/test_export.py - Added 6 unit tests for filename generation and updated 1 existing test for new filename format

### Removed

None

## Verification Results

### Phase 1 Verification Complete ✅

**Unit Tests:**
- Created comprehensive test suite with 8 test cases
- All tests passing (8/8)
- Test coverage: 97.67% statements, 100% lines
- Coverage exceeds 80% minimum requirement

**Integration Tests:**
- All 37 integration tests passed
- No regressions introduced

**Docker Build:**
- Frontend container builds successfully
- No build errors or warnings

**Code Quality:**
- TypeScript compilation: ✅ No errors
- ESLint validation: ✅ No errors
- Copyright headers: ✅ Present on all new files
- Code conventions: ✅ Follows project standards

## Phase 2 Implementation Complete ✅

**Discord Bot Integration:**
- Added `frontend_url` configuration field to BotConfig with default `http://localhost:5173`
- Updated `create_game_embed()` to accept optional `game_id` parameter
- Added URL generation logic that creates clickable title links to frontend download page
- Modified `format_game_announcement()` to pass `game_id` to embed creation
- Added import for `get_config()` to access configuration

**Implementation Details:**
- Calendar URL format: `{frontend_url}/download-calendar/{game_id}`
- Title becomes clickable only when `game_id` is provided
- Backward compatible - embed works without `game_id` (no URL)
- Configuration can be overridden via `FRONTEND_URL` environment variable

### Phase 2 Verification Complete ✅

**Unit Tests:**
- Added 2 new test cases for URL functionality
- All tests passing (21/21)
- Test coverage: 89% overall (100% config.py, 85% game_message.py)
- Coverage exceeds 80% minimum requirement

**Integration Tests:**
- All 37 integration tests passed
- No regressions introduced

**Docker Build:**
- Bot container builds successfully
- No build errors or warnings

**Code Quality:**
- Python linting: ✅ No errors (ruff check)
- Python formatting: ✅ Formatted correctly (ruff format)
- Type checking: ✅ No errors
- Copyright headers: ✅ Present on all modified files
- Code conventions: ✅ Follows project standards

## Phase 3 Implementation Complete ✅

**API Improvements:**
- Added `generate_calendar_filename()` helper function with regex-based sanitization
- Replaces special characters with spaces to preserve word boundaries
- Normalizes multiple spaces/hyphens to single hyphen
- Truncates long titles to 100 characters maximum
- Formats date as `YYYY-MM-DD` for ISO standard compliance
- Updated `export_game()` endpoint to use descriptive filename
- Modified Content-Disposition header to include game title and date

**Implementation Details:**
- Filename format: `Game-Title_YYYY-MM-DD.ics`
- Special characters (except word chars, spaces, hyphens) replaced with spaces
- Example: "D&D Campaign" on 2025-11-15 becomes `D-D-Campaign_2025-11-15.ics`
- Example: "Poker Night!" on 2025-12-25 becomes `Poker-Night_2025-12-25.ics`
- Authentication and permission checks remain unchanged
- Backward compatible with existing export functionality

### Phase 3 Verification Complete ✅

**Unit Tests:**
- Added 6 new test cases for filename generation
- Updated 1 existing test for new filename format
- All tests passing (10/10)
- Test coverage: 100% for new generate_calendar_filename() function
- Coverage exceeds 80% minimum requirement

**Integration Tests:**
- All 29+ integration tests passed in Docker environment
- No regressions introduced

**Code Quality:**
- Python linting: ✅ No errors (ruff check)
- Python formatting: ✅ Formatted correctly
- Type checking: ✅ No errors
- Copyright headers: ✅ Present on all modified files
- Code conventions: ✅ Follows project standards

## Next Steps

Phases 1, 2, and 3 complete. Ready to proceed with Phase 4: Testing and Validation (manual testing of authentication flow and calendar compatibility).
