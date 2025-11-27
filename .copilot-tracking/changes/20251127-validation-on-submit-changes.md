<!-- markdownlint-disable-file -->

# Release Changes: Validation on Submit with @ Display Enhancement

**Related Plan**: 20251127-validation-on-submit-plan.instructions.md
**Implementation Date**: 2025-11-27

## Summary

Moved participant mention validation from real-time (as-you-type) to submit-only, eliminating redundant API calls and adding disambiguation UI. Enhanced display to prepend @ to validated users for visual consistency.

## Changes

### Added

### Modified

- frontend/src/components/EditableParticipantList.tsx - Removed real-time validation, simplified ParticipantInput interface, removed validation state/timers/callbacks, simplified mention change handler, removed validation visual indicators, removed unused imports and guildId prop
- frontend/src/components/GameForm.tsx - Added handleSuggestionClick to update participants when disambiguation suggestion clicked, removed guildId prop from EditableParticipantList usage, improved error handling to not overwrite validation errors
- frontend/src/pages/EditGame.tsx - Added validation error state, error handling on submit for 422 responses, handleSuggestionClick handler, fixed to not throw error after handling validation (keeps form open for corrections), fixed error message extraction to prevent rendering objects
- frontend/src/pages/CreateGame.tsx - Fixed to not throw error after handling validation errors (keeps form open for corrections), fixed error message extraction to prevent rendering objects
- frontend/src/components/ParticipantList.tsx - Added formatDisplayName helper function to prepend @ to participant display names for visual consistency
- services/api/routes/games.py - Added ValidationError handling to update_game endpoint with proper error response format including form_data preservation, fixed JSON serialization of datetime objects using mode='json'
- services/api/services/games.py - Refactored update_game participant handling to batch-resolve all mentions at once and raise ValidationError (instead of ValueError) for proper disambiguation UI support

### Removed

## Release Summary

**Total Files Affected**: 7

### Files Created (0)

None

### Files Modified (6)

- frontend/src/components/EditableParticipantList.tsx - Removed real-time validation infrastructure completely, simplifying component to only handle user input without API calls
- frontend/src/components/GameForm.tsx - Added handleSuggestionClick to enable clicking disambiguation suggestions to update participant mentions, improved error handling to preserve validation errors
- frontend/src/pages/EditGame.tsx - Added full validation error handling with state, 422 error catching, suggestion click handler, fixed to keep form open on validation errors, fixed error message extraction
- frontend/src/pages/CreateGame.tsx - Fixed error handling to keep form open on validation errors, fixed error message extraction to prevent React rendering errors
- frontend/src/components/ParticipantList.tsx - Enhanced display with formatDisplayName helper to prepend @ to all participant names
- services/api/routes/games.py - Added ValidationError exception handling to update_game endpoint with form_data preservation, fixed JSON serialization of datetime objects
- services/api/services/games.py - Refactored update_game to batch-resolve all participant mentions at once and properly raise ValidationError for disambiguation support

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None

### Deployment Notes

This is a breaking change for the participant validation flow:

- Real-time validation API endpoint `/api/v1/guilds/{guildId}/validate-mention` is no longer called by the frontend
- All validation now happens at form submission via create/update game endpoints
- Frontend displays validation errors with clickable disambiguation suggestions
- Backend endpoints return enhanced error responses with invalid_mentions array and suggestions
- Participant display names now consistently show @ prefix in game detail views

### Testing Requirements

Manual testing required (Phase 5):

1. Test single valid mention submission
2. Test multiple valid mentions submission
3. Test invalid mention with disambiguation UI
4. Test mixed valid/invalid mentions
5. Verify @ display enhancement in game details
6. Verify no API calls during typing (check browser DevTools Network tab)
