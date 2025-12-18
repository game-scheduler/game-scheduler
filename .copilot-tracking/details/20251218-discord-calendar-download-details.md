<!-- markdownlint-disable-file -->

# Task Details: Discord Calendar Download Feature

## Research Reference

**Source Research**: #file:../research/20251218-discord-calendar-download-research.md

## Phase 1: Frontend Download Page

### Task 1.1: Create DownloadCalendar page component

Create a new React component at [frontend/src/pages/DownloadCalendar.tsx](frontend/src/pages/DownloadCalendar.tsx) that handles authentication and triggers calendar download.

- **Files**:
  - `frontend/src/pages/DownloadCalendar.tsx` - New page component
- **Success**:
  - Component extracts gameId from URL parameters
  - Uses `useAuth` hook to check authentication status
  - Shows loading spinner during authentication check
  - Automatically downloads calendar when authenticated
  - Displays error alerts for permission denied (403) or not found (404)
  - Redirects to `/my-games` after successful download
  - Works with `ProtectedRoute` for automatic login redirect
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 281-370) - Complete DownloadCalendar component implementation
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 240-279) - Authentication analysis and flow
- **Dependencies**:
  - Existing `useAuth` hook from `frontend/src/hooks/useAuth.ts`
  - React Router's `useParams` and `useNavigate`
  - Material-UI components: `Box`, `CircularProgress`, `Typography`, `Alert`

### Task 1.2: Add route with ProtectedRoute wrapper

Add new route to [frontend/src/App.tsx](frontend/src/App.tsx) that wraps DownloadCalendar component with ProtectedRoute.

- **Files**:
  - `frontend/src/App.tsx` - Add new route
- **Success**:
  - Route pattern: `/download-calendar/:gameId`
  - Wrapped with `ProtectedRoute` component
  - Import statement added for `DownloadCalendar`
  - Unauthenticated users redirected to `/login` automatically
  - OAuth callback redirects back to download page after authentication
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 372-393) - Route configuration example
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 240-279) - Authentication flow explanation
- **Dependencies**:
  - Task 1.1 completion (DownloadCalendar component exists)
  - Existing `ProtectedRoute` component

## Phase 2: Discord Bot Integration

### Task 2.1: Add FRONTEND_URL configuration to bot

Add `FRONTEND_URL` configuration setting to bot service configuration.

- **Files**:
  - `services/bot/config.py` - Add frontend_url field
- **Success**:
  - `frontend_url` field added to `BotConfig` class
  - Reads from `FRONTEND_URL` environment variable
  - Defaults to `http://localhost:5173` for development
  - Used to construct calendar download URLs
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 448-451) - Configuration example
- **Dependencies**:
  - None (new configuration field)

### Task 2.2: Update Discord embed with clickable title URL

Modify [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) to add URL parameter to Discord embed, making title clickable.

- **Files**:
  - `services/bot/formatters/game_message.py` - Update `create_game_embed()` function
- **Success**:
  - Embed title becomes clickable link
  - URL points to frontend download page: `{FRONTEND_URL}/download-calendar/{game_id}`
  - Uses `get_bot_config()` to retrieve frontend URL
  - Works with new and existing game announcements
  - URL opens in user's default browser when clicked
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 395-413) - Discord embed update example
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 16-20) - Current game message formatter analysis
- **Dependencies**:
  - Task 2.1 completion (FRONTEND_URL configuration exists)

## Phase 3: API Improvements

### Task 3.1: Add descriptive filename generation to export endpoint

Update [services/api/routes/export.py](services/api/routes/export.py) to generate descriptive filenames for downloaded calendar files.

- **Files**:
  - `services/api/routes/export.py` - Add filename generation helper and update export_game endpoint
- **Success**:
  - Helper function `generate_calendar_filename()` created
  - Filename format: `Game-Title_YYYY-MM-DD.ics`
  - Special characters removed from game title
  - Spaces and hyphens normalized
  - Title truncated to 100 characters if needed
  - Date formatted as `YYYY-MM-DD`
  - Content-Disposition header includes descriptive filename
  - Authentication and permission checks remain unchanged
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 415-446) - API endpoint update with filename generation
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 788-823) - Filename generation pattern and examples
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 11-15) - Current CalendarExportService implementation
- **Dependencies**:
  - Python `re` module for regex pattern matching
  - Existing `export_game()` endpoint function

## Phase 4: Testing and Validation

### Task 4.1: Test authentication and redirect flow

Verify complete authentication and redirect workflow functions correctly.

- **Files**:
  - Manual testing across authentication scenarios
- **Success**:
  - Unauthenticated user clicks Discord title → redirected to `/login`
  - After Discord OAuth → redirected back to `/download-calendar/{game_id}`
  - Authenticated user clicks Discord title → calendar downloads immediately
  - Permission denied (403) shows clear error message
  - Game not found (404) shows clear error message
  - Loading states display during authentication check
  - Post-download redirect to `/my-games` works correctly
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 454-467) - User flow documentation
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 240-279) - Authentication system analysis
- **Dependencies**:
  - All Phase 1, 2, and 3 tasks completed

### Task 4.2: Verify calendar compatibility

Test downloaded calendar files import correctly into various calendar applications.

- **Files**:
  - Manual testing with calendar applications
- **Success**:
  - Calendar imports successfully into Google Calendar
  - Calendar imports successfully into Outlook
  - Calendar imports successfully into Apple Calendar
  - Event details display correctly (title, time, description, location)
  - Participant information preserved
  - Reminders/alarms function as expected
  - Timezone handling correct
  - Filenames are descriptive and readable
- **Research References**:
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 11-15) - CalendarExportService iCal format implementation
  - #file:../research/20251218-discord-calendar-download-research.md (Lines 788-823) - Filename generation examples
- **Dependencies**:
  - Task 4.1 completion (can download calendars)
  - Access to Google Calendar, Outlook, and Apple Calendar for testing

## Dependencies

- React 18+ with TypeScript
- React Router v6 for routing
- Material-UI v5 for UI components
- Discord.py for bot embed functionality
- Existing authentication infrastructure
- Python icalendar library (already in use)
- `FRONTEND_URL` environment variable

## Success Criteria

- All phases completed and tasks checked off
- Frontend download page works with authentication
- Discord embed titles are clickable and open browser
- Calendar downloads with descriptive filenames
- Permission checks function correctly
- Error handling works for all edge cases
- Calendar files import successfully into major calendar applications
- User experience is smooth with clear feedback
- No regressions in existing calendar export functionality
