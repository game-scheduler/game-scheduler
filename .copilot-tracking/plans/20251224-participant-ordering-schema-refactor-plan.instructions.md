---
applyTo: ".copilot-tracking/changes/20251224-participant-ordering-schema-refactor-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Participant Ordering Schema Refactoring

## Overview

Replace single `pre_filled_position` field with two-field system (`position_type`, `position`) to fix gap handling bugs and enable extensible participant type system.

## Objectives

- Fix gap handling bug where position values are incorrectly treated as array indices
- Enable future participant type additions through sparse enum design
- Simplify sorting logic from two-list system to single unified sort
- Maintain backward compatibility through reversible database migration
- Preserve all existing functionality while improving code maintainability

## Research Summary

### Project Files

- [shared/models/participant.py](../../shared/models/participant.py) - Current `pre_filled_position` field definition
- [shared/schemas/participant.py](../../shared/schemas/participant.py) - API response schema with `pre_filled_position`
- [shared/utils/participant_sorting.py](../../shared/utils/participant_sorting.py) - Sorting logic splitting priority/regular participants
- [services/api/services/games.py](../../services/api/services/games.py) Lines 535-580 - Business logic updating positions
- [services/api/routes/games.py](../../services/api/routes/games.py) - API route serialization

### External References

- #file:../research/20251224-participant-ordering-schema-refactor-research.md - Comprehensive analysis of current implementation and proposed solution

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment guidelines

## Implementation Checklist

### [ ] Phase 1: Enum Definition and Database Migration

- [ ] Task 1.1: Create ParticipantType IntEnum with sparse values
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 16-35)

- [ ] Task 1.2: Create Alembic migration to transform schema
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 37-69)

- [ ] Task 1.3: Test migration on test database and verify schema changes
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 71-88)

### [ ] Phase 2: Model and Schema Updates

- [ ] Task 2.1: Update GameParticipant model with new fields
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 90-122)

- [ ] Task 2.2: Update ParticipantResponse schema
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 124-142)

- [ ] Task 2.3: Update model/schema test fixtures and verify tests pass
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 144-164)

### [ ] Phase 3: Sorting Logic Refactoring

- [ ] Task 3.1: Replace sort_participants() implementation
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 166-197)

- [ ] Task 3.2: Update PartitionedParticipants docstrings
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 199-212)

- [ ] Task 3.3: Update sorting test fixtures and verify tests pass
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 214-234)

### [ ] Phase 4: Business Logic Updates

- [ ] Task 4.1: Update game service participant creation
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 236-257)

- [ ] Task 4.2: Update game service participant queries
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 259-278)

- [ ] Task 4.3: Update game service position updates
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 280-296)

- [ ] Task 4.4: Update service test fixtures and run service tests
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 298-319)

### [ ] Phase 5: API Route Updates

- [ ] Task 5.1: Update participant serialization in routes
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 321-342)

- [ ] Task 5.2: Update participant creation in join endpoints
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 344-362)

- [ ] Task 5.3: Update API test fixtures and run API tests
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 364-381)

### [ ] Phase 6: Bot and Additional Component Updates

- [ ] Task 6.1: Update bot event handler test fixtures
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 383-400)

- [ ] Task 6.2: Update remaining test fixtures and helpers
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 402-420)

- [ ] Task 6.3: Run full test suite validation
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 422-439)

### [ ] Phase 7: End-to-End Validation

- [ ] Task 7.1: Run integration tests
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 441-452)

- [ ] Task 7.2: Run E2E tests
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 454-465)

- [ ] Task 7.3: Manual testing of participant ordering
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 467-485)

- [ ] Task 7.4: Verify gap handling works correctly
  - Details: .copilot-tracking/details/20251224-participant-ordering-schema-refactor-details.md (Lines 487-504)

## Dependencies

- PostgreSQL database with Alembic migrations
- SQLAlchemy ORM for model updates
- Pydantic for schema validation
- Pytest for test execution
- FastAPI for API route updates

## Success Criteria

- Gap handling works correctly (no indexing issues with non-consecutive position values)
- All tests pass incrementally after each phase (not deferred to end)
- Migration runs successfully and is reversible via downgrade
- API responses include new fields (position_type, position) instead of pre_filled_position
- Sorting behavior matches current behavior for existing participant types
- Code is simpler and more maintainable than previous two-list approach
- Documentation and docstrings reflect new schema
