---
applyTo: '.copilot-tracking/changes/20260324-01-role-based-scheduling-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Role-Based Scheduling Method

## Overview

Add a `ROLE_BASED` signup method that resolves Discord role priority once at join time
and stores it in the existing `position_type`/`position` DB columns, leaving all sort
and partition logic completely unchanged.

## Objectives

- Add `ROLE_MATCHED = 16000` ParticipantType tier between HOST_ADDED and SELF_ADDED
- Add `ROLE_BASED` SignupMethod that activates when `signup_priority_role_ids` is non-empty
- Store `signup_priority_role_ids` on `GameTemplate` (JSON, max 8, nullable)
- Resolve role priority at join time in both the API and bot paths
- Seed the role cache from the Discord interaction payload (bot path, zero extra API calls)
- Add draggable role-priority UI to TemplateForm (locked settings section)
- Verify full flow with a parametrized E2E test

## Research Summary

### Project Files

- `shared/models/participant.py` — `ParticipantType` IntEnum, `position_type`/`position` columns
- `shared/models/signup_method.py` — `SignupMethod` StrEnum
- `shared/models/template.py` — `GameTemplate`, existing JSON array column pattern
- `shared/utils/participant_sorting.py` — sort/partition logic (unchanged)
- `shared/schemas/template.py` — template Pydantic schemas
- `services/api/routes/games.py` — join route; `role_service` already injected
- `services/api/services/games.py` — `GameService.join_game` (line ~1844)
- `services/bot/handlers/join_game.py` — `handle_join_game`; interaction provides member roles free
- `services/bot/auth/role_checker.py` — `RoleChecker.get_user_role_ids`
- `services/api/routes/templates.py` — `TemplateResponse`
- `frontend/src/types/index.ts` — TypeScript enums in sync with Python
- `frontend/src/components/TemplateForm.tsx` — existing role multi-select pickers as UI pattern

### External References

- #file:../research/20260324-01-role-based-scheduling-research.md — Full role-based scheduling research

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md — FastAPI patterns
- #file:../../.github/instructions/reactjs.instructions.md — React component conventions

## Implementation Checklist

### [ ] Phase 1: Enum Updates (Python + TypeScript)

- [ ] Task 1.1: Add `ROLE_MATCHED = 16000` to Python `ParticipantType`
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 11-28)

- [ ] Task 1.2: Add `ROLE_BASED` to Python `SignupMethod`
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 29-42)

- [ ] Task 1.3: Sync TypeScript enums and `SIGNUP_METHOD_INFO`; add `signup_priority_role_ids` to template interfaces
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 43-63)

### [ ] Phase 2: Database Migration and Model/Schema Updates

- [ ] Task 2.1: Alembic migration — add nullable JSON `signup_priority_role_ids` to `game_templates`
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 66-86)

- [ ] Task 2.2: Update `GameTemplate` SQLAlchemy model with new column mapping
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 87-102)

- [ ] Task 2.3: Update Pydantic schemas (max-8 validator) and `TemplateResponse`
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 103-120)

### [ ] Phase 3: Core Logic (TDD)

- [ ] Task 3.1: TDD `resolve_role_position` pure function in `shared/utils/participant_sorting.py`
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 123-152)

- [ ] Task 3.2: TDD `seed_user_roles` method on `RoleChecker`
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 153-175)

### [ ] Phase 4: Join Path Updates

- [ ] Task 4.1: Update `GameService.join_game` to accept optional `position_type`/`position` params
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 178-197)

- [ ] Task 4.2: Update API `join_game` route to resolve role priority and pass to service
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 198-221)

- [ ] Task 4.3: Update bot `handle_join_game` to resolve role priority from interaction payload
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 222-248)

### [ ] Phase 5: Frontend Updates

- [ ] Task 5.2: Add draggable role-priority list to `TemplateForm.tsx` (locked settings section)
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 251-275)

### [ ] Phase 6: E2E Test

- [ ] Task 6.1: Write `tests/e2e/test_role_based_signup.py` with 4 parametrized cases
  - Details: .copilot-tracking/planning/details/20260324-01-role-based-scheduling-details.md (Lines 278-315)

## Dependencies

- Python: `alembic`, `sqlalchemy`, `pydantic`, `discord.py` (all installed)
- Frontend: check `frontend/package.json` for existing drag library before choosing one
- TDD applies to all Python and TypeScript changes

## Success Criteria

- Sort order for ROLE_BASED game: HOST_ADDED → ROLE_MATCHED (by role index, then `joined_at`) → SELF_ADDED (by `joined_at`)
- `partition_participants`, `sort_participants`, and all 6 call sites are completely unchanged
- Non-ROLE_BASED games behave identically to today
- Max 8 role IDs enforced at API layer (HTTP 422)
- All new code has passing unit tests written before implementation
