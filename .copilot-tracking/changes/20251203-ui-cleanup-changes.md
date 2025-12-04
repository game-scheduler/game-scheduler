<!-- markdownlint-disable-file -->

# Release Changes: UI Cleanup and Navigation Reorganization

**Related Plan**: 20251203-ui-cleanup-plan.instructions.md
**Implementation Date**: 2025-12-03

## Summary

Complete terminology consistency by changing remaining "Guild" user-facing text to "Server" and reorganize navigation to make My Games the home screen with streamlined game creation flow.

## Changes

### Added

- frontend/src/components/ServerSelectionDialog.tsx - Created reusable dialog component for selecting server when creating games
- frontend/src/components/__tests__/ServerSelectionDialog.test.tsx - Comprehensive unit tests for ServerSelectionDialog component (6 tests covering all user interactions)
- frontend/src/pages/__tests__/MyGames.test.tsx - Unit tests for MyGames server selection logic (5 tests covering single/multi/zero server scenarios)

### Modified

- frontend/src/pages/HomePage.tsx - Updated "View My Guilds" button text to "View My Servers"
- frontend/src/pages/GuildDashboard.tsx - Changed "Guild not found" error message to "Server not found"
- frontend/src/App.tsx - Made MyGames the default home route at "/" and wrapped in ProtectedRoute, removed HomePage import
- frontend/src/components/Layout.tsx - Removed "My Games" navigation button since MyGames is now the home screen
- frontend/src/pages/MyGames.tsx - Added server selection logic, fetches guilds on mount, navigates directly to create form for single-server users or shows selection dialog for multi-server users (uses database UUID for navigation); hides Hosting tab when user has no hosted games
- frontend/src/pages/AuthCallback.tsx - Fixed post-login redirect to navigate to "/" (My Games home) instead of "/guilds"
- frontend/src/pages/__tests__/MyGames.test.tsx - Updated test assertions to expect database UUID in navigation calls
- services/api/services/games.py - Fixed authorization in create_game to properly check bot manager roles and template-specific host roles using centralized role service
- services/api/auth/roles.py - Enhanced check_game_host_permission to handle template role restrictions (bot managers always allowed, otherwise checks allowed_host_role_ids)
- services/api/dependencies/permissions.py - Simplified can_manage_game to use check_bot_manager_permission instead of manually checking MANAGE_GUILD
- services/api/routes/templates.py - Simplified admin check to use check_bot_manager_permission and get_user_role_ids from role service

### Removed

- frontend/src/pages/HomePage.tsx - Removed obsolete HomePage component since MyGames is now the home screen

