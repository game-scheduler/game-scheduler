---
applyTo: ".copilot-tracking/changes/20251218-discord-calendar-download-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Calendar Download Feature

## Overview

Enable Discord users to download game calendars via clickable embed title that opens a frontend download page with authentication.

## Objectives

- Provide one-click calendar download from Discord game cards
- Require authentication via frontend protected route
- Maintain existing permission checks (host, participant, admin, or bot manager)
- Generate descriptive filenames for downloaded calendar files
- Handle errors gracefully with clear user feedback

## Research Summary

### Project Files

- [frontend/src/components/ExportButton.tsx](frontend/src/components/ExportButton.tsx) - Existing calendar export component with blob download logic
- [services/api/routes/export.py](services/api/routes/export.py) - Current export endpoint with authentication and permission checks
- [services/api/services/calendar_export.py](services/api/services/calendar_export.py) - CalendarExportService generates iCal format data
- [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Creates Discord embeds for game announcements
- [services/bot/config.py](services/bot/config.py) - Bot configuration settings

### External References

- #file:../research/20251218-discord-calendar-download-research.md - Complete research with authentication analysis, implementation approaches, and code examples
- #githubRepo:"Rapptz/discord.py embed title url" - Discord.py embed URL patterns for clickable titles
- #fetch:"https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition" - HTTP Content-Disposition header for file downloads

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript best practices
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Code commenting standards

## Implementation Checklist

### [ ] Phase 1: Frontend Download Page

- [ ] Task 1.1: Create DownloadCalendar page component
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-download-details.md) (Lines 14-45)

- [ ] Task 1.2: Add route with ProtectedRoute wrapper
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-download-details.md) (Lines 47-61)

### [ ] Phase 2: Discord Bot Integration

- [ ] Task 2.1: Add FRONTEND_URL configuration to bot
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-download-details.md) (Lines 63-75)

- [ ] Task 2.2: Update Discord embed with clickable title URL
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-download-details.md) (Lines 77-94)

### [ ] Phase 3: API Improvements

- [ ] Task 3.1: Add descriptive filename generation to export endpoint
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-download-details.md) (Lines 96-121)

### [ ] Phase 4: Testing and Validation

- [ ] Task 4.1: Test authentication and redirect flow
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-download-details.md) (Lines 123-141)

- [ ] Task 4.2: Verify calendar compatibility
  - Details: [.copilot-tracking/details/20251218-discord-calendar-download-details.md](../.copilot-tracking/details/20251218-discord-calendar-details.md) (Lines 143-157)

## Dependencies

- Existing `useAuth` hook (frontend authentication)
- Existing `ProtectedRoute` component (route protection)
- Existing OAuth2 redirect flow (post-login redirect handling)
- Existing CalendarExportService (iCal generation)
- Existing permission checking system
- `FRONTEND_URL` environment variable for bot service

## Success Criteria

- Discord game card title is clickable on all announcements
- Unauthenticated users are redirected to login page
- After login, users return to download page automatically
- Calendar downloads with descriptive filename format: `Game-Title_YYYY-MM-DD.ics`
- Permission checks function correctly (403 for unauthorized users)
- Error messages display for permission denied and game not found scenarios
- Downloaded calendar files import successfully into Google Calendar, Outlook, and Apple Calendar
- Loading states display during authentication and download process
