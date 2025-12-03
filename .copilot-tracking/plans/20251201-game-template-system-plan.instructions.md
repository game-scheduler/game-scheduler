---
applyTo: ".copilot-tracking/changes/20251201-game-template-system-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Template System

## Overview

Replace three-level inheritance system (Guild → Channel → Game) with template-based game types that provide locked and pre-populated settings, ensuring system remains usable after each task completion.

## Objectives

- Remove SettingsResolver and inheritance resolution logic
- Create GameTemplate model with locked and pre-populated fields
- Implement template-based game creation workflow
- Build template management UI with role-based access
- Ensure system is deployable and functional after each task

## Research Summary

### Project Files

- `shared/models/guild.py` - Current inheritance fields: default_max_players, default_reminder_minutes, allowed_host_role_ids
- `shared/models/channel.py` - Current inheritance fields: max_players, reminder_minutes, allowed_host_role_ids
- `shared/models/game.py` - Override fields: max_players, reminder_minutes
- `services/api/services/config.py` - SettingsResolver with three-level resolution hierarchy
- `services/api/services/games.py` - Uses SettingsResolver for game creation and join validation
- `services/api/auth/roles.py` - Uses SettingsResolver for host permission checks
- `services/bot/auth/role_checker.py` - Uses SettingsResolver for host permission checks

### External References

- #file:../research/20251201-game-template-system-research.md - Complete template system design with models, services, and migration strategy
- #githubRepo:"sqlalchemy/sqlalchemy unique constraint composite index" - Composite unique constraints and index patterns
- #githubRepo:"discord/discord-api-docs role permissions" - Discord role ID patterns and permission hierarchy

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python type hints, SQLAlchemy 2.0 patterns
- #file:../../.github/instructions/coding-best-practices.instructions.md - Modularity and DRY principles
- #file:../../.github/instructions/reactjs.instructions.md - React component patterns and state management

## Implementation Checklist

### [x] Phase 1: Extract Services & Remove SettingsResolver

- [x] Task 1.1: Create database queries module

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 19-38)

- [x] Task 1.2: Create guild and channel services

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 40-65)

- [x] Task 1.3: Update routes to use new services

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 67-86)

- [x] Task 1.4: Remove SettingsResolver from game operations

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 88-107)

- [x] Task 1.5: Delete ConfigurationService and update all tests
  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 109-136)
  - Note: Route test files (test_guilds.py, test_channels.py) need manual updates to patch individual functions

### [x] Phase 2: Database Schema Migration

- [x] Task 2.1: Create GameTemplate model

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 138-172)

- [x] Task 2.2: Update GuildConfiguration and ChannelConfiguration models

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 174-191)

- [x] Task 2.3: Update GameSession model for templates

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 193-207)

- [x] Task 2.4: Create database migration

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 209-239)

- [x] Task 2.5: Create default template data migration script

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 241-266)

- [ ] Task 2.5: Create default template data migration script
  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 241-266)

### [x] Phase 3: Template Service & Schemas

- [x] Task 3.1: Create template schemas

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 192-221)

- [x] Task 3.2: Create TemplateService

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 223-239)

- [x] Task 3.3: Update game schemas for template-based creation

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 241-254)

- [x] Task 3.4: Create template service tests
  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 256-273)

### [ ] Phase 4: Template API Endpoints

- [ ] Task 4.1: Create guild sync endpoint

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 381-408)

- [ ] Task 4.2: Create template API endpoints

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 410-449)

- [ ] Task 4.3: Update game creation endpoint for templates

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 451-477)

- [ ] Task 4.4: Create template endpoint tests
  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 479-501)

### [ ] Phase 5: Frontend Template Management

- [ ] Task 5.1: Create template management components

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 503-532)

- [ ] Task 5.2: Add guild sync functionality

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 534-555)

- [ ] Task 5.3: Update game creation form for templates

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 557-578)

- [ ] Task 5.4: Remove inheritance UI components

  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 580-596)

- [ ] Task 5.5: Create frontend template tests
  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 598-616)

### [ ] Phase 6: Bot Command Cleanup

- [ ] Task 6.1: Remove bot config commands
  - Details: .copilot-tracking/details/20251201-game-template-system-details.md (Lines 618-637)

## Dependencies

- SQLAlchemy 2.0 with async session support
- Alembic for database migrations
- React with TypeScript for frontend
- Discord.py for bot interactions
- Pytest for testing

## Success Criteria

- System remains functional and deployable after each phase completion
- No SettingsResolver or inheritance code remains
- All games require template selection at creation
- Templates properly enforce locked vs editable fields
- Default template exists for all guilds and cannot be deleted
- Template visibility filtered by allowed_host_role_ids
- Frontend shows template management UI with drag-to-reorder
- All tests pass (480+ unit tests, integration tests)
- Documentation updated to reflect template system
