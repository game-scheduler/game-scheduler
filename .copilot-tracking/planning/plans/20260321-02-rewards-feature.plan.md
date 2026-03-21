---
applyTo: '.copilot-tracking/changes/20260321-02-rewards-feature-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Rewards Feature

## Overview

Add a `rewards` field with spoiler display to games, a `remind_host_rewards` flag on games and templates, a "Save and Archive" shortcut button, and a host DM reminder when a completed game has no rewards yet.

## Objectives

- Persist `rewards` (nullable text) and `remind_host_rewards` (bool) on `GameSession`
- Persist `remind_host_rewards` (bool) on `GameTemplate`
- Gate the rewards textarea in the edit UI by game status (hidden on SCHEDULED)
- Show "Save and Archive" button when rewards and archive channel are both set
- Display rewards as a click-to-reveal spoiler in Discord (spoiler tags) and on the web (blur)
- Send host a DM at COMPLETED transition if `remind_host_rewards=True` and rewards are empty

## Research Summary

### Project Files

- `shared/models/game.py` — GameSession model; target for `rewards` and `remind_host_rewards` columns
- `shared/models/template.py` — GameTemplate model; target for `remind_host_rewards` column
- `shared/schemas/game.py` — Game schemas; `archive_delay_seconds` missing from `GameUpdateRequest`
- `shared/schemas/template.py` — Template schemas; need `remind_host_rewards` added
- `services/api/services/games.py` — Service functions for create/update/clone
- `services/api/routes/games.py` — Route definitions and response builders
- `services/bot/formatters/game_message.py` — Discord embed creation; trim logic
- `services/bot/events/handlers.py` — Post-transition handler; needs COMPLETED branch
- `shared/message_formats.py` — DM format strings; needs `rewards_reminder` method
- `frontend/src/types/index.ts` — Frontend type definitions
- `frontend/src/components/GameForm.tsx` — Game creation/edit form
- `frontend/src/pages/EditGame.tsx` — Edit page; needs Save and Archive handler
- `frontend/src/pages/GameDetails.tsx` — Read-only game display
- `alembic/versions/` — Latest migration: `20260311_add_archive_fields.py`

### External References

- #file:../research/20260321-02-rewards-feature-research.md — Comprehensive rewards feature research

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md — FastAPI service and transaction patterns
- #file:../../.github/instructions/reactjs.instructions.md — React component conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md — TypeScript conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/integration-tests.instructions.md — Integration test patterns

## Implementation Checklist

### [x] Phase 1: Database Migration

- [x] Task 1.1: Create Alembic migration adding rewards and remind_host_rewards columns
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 13-30)

### [x] Phase 2: Backend Models & Schemas

- [x] Task 2.1: Update GameSession and GameTemplate models
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 33-49)

- [x] Task 2.2: Update game and template schemas
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 50-68)

### [x] Phase 3: API Service & Routes

- [x] Task 3.1: Update game service layer functions
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 71-87)

- [x] Task 3.2: Update game API routes and response builder
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 88-103)

### [ ] Phase 4: Bot Formatters & Handlers

- [ ] Task 4.1: Add rewards spoiler field to Discord embed formatter
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 106-121)

- [ ] Task 4.2: Add DMFormats.rewards_reminder and COMPLETED handler DM
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 122-141)

### [ ] Phase 5: Frontend

- [ ] Task 5.1: Update TypeScript type definitions
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 144-157)

- [ ] Task 5.2: Update GameForm with rewards textarea, checkbox, and Save and Archive button
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 158-173)

- [ ] Task 5.3: Update EditGame page with new fields and Save and Archive handler
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 174-189)

- [ ] Task 5.4: Add spoiler display to GameDetails and GameCard
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 190-207)

### [ ] Phase 6: Tests (TDD)

- [ ] Task 6.1: Write and pass integration tests for rewards fields and Save and Archive
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 210-229)

- [ ] Task 6.2: Write and pass E2E tests for rewards flows
  - Details: .copilot-tracking/planning/details/20260321-02-rewards-feature-details.md (Lines 230-247)

## Dependencies

- Bug fix from research doc `20260321-01-*` must be implemented first
- Python, SQLAlchemy, Alembic (existing)
- Discord.py (existing)
- FastAPI + MUI (existing)

## Success Criteria

- Rewards field persists and returns from API
- Rewards textarea hidden on SCHEDULED edit page, visible on IN_PROGRESS/COMPLETED/ARCHIVED
- `remind_host_rewards` checkbox visible on all edit/create pages
- Save and Archive button appears when `rewards` non-empty and `archive_channel_id` non-empty
- Save and Archive triggers archival within ~1 second
- Discord embed shows `||rewards||` spoiler field when rewards set
- Web display shows blur spoiler for rewards
- Bot sends host DM at COMPLETED when `remind_host_rewards=True` and `rewards` is empty
- All integration and E2E tests pass
