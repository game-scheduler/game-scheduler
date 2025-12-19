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

## Next Steps

Phase 1 and 2 complete. Ready to proceed with Phase 3: API Improvements (add descriptive filename generation to export endpoint).
