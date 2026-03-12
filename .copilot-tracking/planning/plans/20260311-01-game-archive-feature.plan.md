---
applyTo: '.copilot-tracking/changes/20260311-01-game-archive-feature-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Announcement Archive Feature

## Overview

Plan and implement archive support for game announcements, including data model updates, API wiring, bot behavior, and tests.

## Objectives

- Add template and game archive fields with migration, schema, and service wiring
- Schedule and execute ARCHIVED transitions to delete/repost announcements

## Research Summary

### Project Files

- shared/models/template.py - archive fields and channel relationships
- shared/models/game.py - archive fields on sessions and channel relationships
- shared/utils/status_transitions.py - canonical GameStatus and transitions
- services/api/routes/templates.py - template API wiring
- services/api/services/games.py - game creation copy logic
- services/bot/events/handlers.py - status transition scheduling and archiving

### External References

- #file:../research/20260308-02-game-archive-feature-research.md - validated research and specifications

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD workflow requirements
- #file:../../.github/instructions/task-implementation.instructions.md - implementation workflow
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - commenting style

## Implementation Checklist

### [x] Phase 1: Data Model + Status Enum

- [x] Task 1.1: Add alembic migration for archive fields
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 11-24)

- [x] Task 1.2: Update GameTemplate and GameSession models for archive fields and relationships
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 26-39)

- [x] Task 1.3: Extend canonical GameStatus for ARCHIVED and transitions
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 41-54)

### [x] Phase 2: API + Services

- [x] Task 2.1: Extend template schemas with archive fields
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 58-70)

- [x] Task 2.2: Update template routes to pass and resolve archive fields
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 72-86)

- [x] Task 2.3: Copy archive fields in game session creation
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 88-100)

### [x] Phase 3: Bot Scheduling + Announcement Archiving (TDD)

- [x] Task 3.1: Add failing unit tests for archive scheduling and archiving behavior
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 104-116)

- [x] Task 3.2: Implement archive scheduling and announcement archive flow
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 118-130)

- [x] Task 3.3: Remove xfail markers and harden edge cases
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 132-145)

### [ ] Phase 4: Integration + E2E + Docs (TDD)

- [ ] Task 4.1: Add failing integration tests for template and game archive fields
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 149-161)

- [ ] Task 4.2: Implement integration behavior and remove xfail markers
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 163-179)

- [ ] Task 4.3: Add E2E archive tests and test infrastructure updates
  - Details: .copilot-tracking/planning/details/20260311-01-game-archive-feature-details.md (Lines 181-197)

## Dependencies

- Alembic migrations
- SQLAlchemy models
- Pytest (unit, integration, e2e)
- Discord test environment with archive channel

## Success Criteria

- Archive fields are persisted on templates and games
- ARCHIVED transitions schedule and archive announcements correctly
