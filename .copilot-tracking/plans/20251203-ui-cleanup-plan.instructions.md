---
applyTo: '.copilot-tracking/changes/20251203-ui-cleanup-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: UI Cleanup and Navigation Reorganization

## Overview

Complete terminology consistency by changing remaining "Guild" user-facing text to "Server" and reorganize navigation to make My Games the home screen with streamlined game creation flow.

## Objectives

- Update remaining user-facing "Guild" references to "Server" terminology
- Make My Games page the default landing page (home screen)
- Remove redundant HomePage component
- Streamline game creation flow to skip server dashboard
- Update navigation to reflect new home screen

## Research Summary

### Project Files
- frontend/src/pages/HomePage.tsx - Contains "View My Guilds" button needing update
- frontend/src/pages/GuildDashboard.tsx - Contains "Guild not found" error message
- frontend/src/App.tsx - Route definitions requiring reorganization
- frontend/src/pages/MyGames.tsx - Will become new home screen
- frontend/src/components/Layout.tsx - Navigation buttons requiring updates

### External References
- #file:../research/20251203-ui-cleanup-research.md - Complete UI cleanup research with terminology analysis
- #file:../../.github/instructions/reactjs.instructions.md - ReactJS development standards

### Standards References
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript guidelines
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards

## Implementation Checklist

### [x] Phase 1: Complete Guild-to-Server Terminology

- [x] Task 1.1: Update HomePage button label
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 15-25)

- [x] Task 1.2: Update GuildDashboard error message
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 27-36)

### [x] Phase 2: Reorganize Home Screen Navigation

- [x] Task 2.1: Update App.tsx routing configuration
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 40-58)

- [x] Task 2.2: Remove HomePage component
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 60-68)

- [x] Task 2.3: Update Layout navigation
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 70-80)

### [x] Phase 3: Streamline Game Creation Flow

- [x] Task 3.1: Update MyGames create button
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 84-102)

- [x] Task 3.2: Implement server selection logic
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 104-127)

- [x] Task 3.3: Create ServerSelectionDialog component
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 129-154)

### [ ] Phase 4: Testing and Verification

- [ ] Task 4.1: Verify navigation flows
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 158-171)
  - Note: Login redirect fixed to navigate to "/" instead of "/guilds"

- [ ] Task 4.2: Test game creation paths
  - Details: .copilot-tracking/details/20251203-ui-cleanup-details.md (Lines 173-184)

## Dependencies

- React Router v6
- Material-UI (MUI) components
- TypeScript 5.x
- Existing authentication context

## Success Criteria

- All user-facing text consistently uses "Server" instead of "Guild"
- My Games page renders as home screen at `/` route
- HomePage component removed from codebase
- Navigation header updated with correct buttons
- Game creation skips server dashboard when coming from My Games
- Single server users go directly to create form
- Multi-server users see server selection then create form
- All navigation flows work correctly
- Build completes without errors
