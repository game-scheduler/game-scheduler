---
applyTo: '.copilot-tracking/changes/20260301-03-remove-require-host-role-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove `require_host_role` Field

## Overview

Eliminate the dead `require_host_role` field from the database, ORM model, schemas, API routes, frontend, tests, and documentation.

## Objectives

- Drop `require_host_role` column via a new Alembic migration
- Remove all Python references (model, schemas, routes)
- Remove all frontend references (form state, API payload, checkbox UI)
- Remove all test references and fix any mocks that set the attribute
- Update GUILD-ADMIN.md to document the `@everyone` template role approach

## Research Summary

### Project Files

- `shared/models/guild.py` — ORM column definition (line 50)
- `shared/schemas/guild.py` — three schema class fields (lines 31, 41, 61)
- `services/api/routes/guilds.py` — two usage sites (lines 71, 187)
- `frontend/src/pages/GuildConfig.tsx` — five usage sites (lines 57, 74, 116, 226-230)
- `frontend/src/pages/__tests__/GuildConfig.test.tsx` — three usage sites (lines 124, 161, 165)
- `tests/services/api/routes/test_guilds.py` — ten usage sites (lines 49, 229, 237, 295, 302, 312, 432, 444, 458, 468)
- `tests/services/bot/test_guild_sync.py` — two usage sites (lines 461, 480)
- `alembic/versions/c2135ff3d5cd_initial_schema.py` — original column definition

### External References

- #file:../research/20260301-03-remove-require-host-role-research.md — complete analysis

## Implementation Checklist

### [x] Phase 1: Database Migration

- [x] Task 1.1: Generate new Alembic migration to drop `require_host_role` from `guild_configurations`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 18-42)

### [x] Phase 2: Backend Removal

- [x] Task 2.1: Remove `require_host_role` column mapping from `shared/models/guild.py`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 45-64)

- [x] Task 2.2: Remove `require_host_role` from all three schema classes in `shared/schemas/guild.py`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 67-90)

- [x] Task 2.3: Remove `require_host_role` from `services/api/routes/guilds.py`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 93-112)

### [x] Phase 3: Backend Test Cleanup

- [x] Task 3.1: Remove all `require_host_role` references from `tests/services/api/routes/test_guilds.py` and fix mocks
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 115-149)

- [x] Task 3.2: Remove `require_host_role` attribute assignments from `tests/services/bot/test_guild_sync.py`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 152-168)

### [x] Phase 4: Frontend Removal

- [x] Task 4.1: Remove form state, API payload field, and checkbox UI from `frontend/src/pages/GuildConfig.tsx`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 171-202)

- [x] Task 4.2: Remove checkbox assertion and comment from `frontend/src/pages/__tests__/GuildConfig.test.tsx`
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 205-225)

### [x] Phase 5: Documentation

- [x] Task 5.1: Update `docs/GUILD-ADMIN.md` to replace `require_host_role` guidance with `@everyone` template role instructions
  - Details: .copilot-tracking/details/20260301-03-remove-require-host-role-details.md (Lines 228-248)

## Dependencies

- Alembic (migration generation via `uv run alembic revision --autogenerate`)
- Existing pre-commit hooks (tests must pass before commit)

## Success Criteria

- `grep -r "require_host_role" services/ shared/ tests/ frontend/src/ docs/` returns no results
- `uv run pytest tests/` passes
- `cd frontend && npm test` passes
- Alembic migration applies cleanly (`uv run alembic upgrade head`)
