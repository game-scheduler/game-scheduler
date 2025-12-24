<!-- markdownlint-disable-file -->

# Task Details: Participant Ordering Schema Refactoring

## Research Reference

**Source Research**: #file:../research/20251224-participant-ordering-schema-refactor-research.md

## Phase 1: Enum Definition and Database Migration

### Task 1.1: Create ParticipantType IntEnum with sparse values

Define a new IntEnum to represent participant types with sparse numeric values that allow future type insertions.

- **Files**:
  - Create new module or add to existing: `shared/models/participant.py` - Add IntEnum definition
- **Success**:
  - ParticipantType enum defined with HOST_ADDED=8000 and SELF_ADDED=24000
  - Enum properly imported from Python's enum module
  - Values use sparse spacing (16,000 gap) for future insertions
  - All values fit within SmallInteger range (-32,768 to 32,767)
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 87-98) - Enum design rationale
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 100-109) - Sorting algorithm explanation
- **Code Specification**:

  ```python
  from enum import IntEnum

  class ParticipantType(IntEnum):
      """Participant type enumeration with sparse values for future expansion."""
      HOST_ADDED = 8000    # High priority (sorts first)
      SELF_ADDED = 24000   # Low priority (sorts last)
  ```

- **Dependencies**: None

### Task 1.2: Create Alembic migration to transform schema

Create a reversible Alembic migration that adds new fields, transforms existing data, and removes old field.

- **Files**:
  - `alembic/versions/YYYYMMDD_HHMMSS_replace_prefilled_position_with_position_fields.py` - New migration file
- **Success**:
  - Migration adds position_type and position columns with temporary NULL defaults
  - Data transformation converts pre_filled_position values to new schema
  - HOST_ADDED participants: position_type=8000, position=old_pre_filled_position
  - SELF_ADDED participants: position_type=24000, position=0
  - Columns made non-nullable after data migration
  - Old pre_filled_position column dropped
  - Downgrade migration restores original schema without data loss
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 190-254) - Complete migration code
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 256-263) - Migration safety notes
- **Dependencies**:
  - Task 1.1 completion (enum definition must exist)
  - Alembic revision system

### Task 1.3: Test migration on test database and verify schema changes

Validate migration correctness by running on test database and verifying data transformation.

- **Files**:
  - Test database instance
  - Any tests that create database schemas
- **Success**:
  - Migration upgrade runs without errors
  - Existing pre_filled_position values correctly transformed to position_type/position
  - NULL pre_filled_position values become (24000, 0)
  - Non-NULL pre_filled_position values become (8000, original_value)
  - Migration downgrade successfully restores original schema
  - Round-trip (upgrade + downgrade + upgrade) produces consistent results
  - Database schema tests pass
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 256-263) - Migration safety checklist
- **Dependencies**: Task 1.2 completion

## Phase 2: Model and Schema Updates

### Task 2.1: Update GameParticipant model with new fields

Replace pre_filled_position field with position_type and position fields in the SQLAlchemy model.

- **Files**:
  - `shared/models/participant.py` - Update GameParticipant class
- **Success**:
  - Import ParticipantType enum (already added in Task 1.1)
  - Remove pre_filled_position field definition
  - Add position_type: Mapped[int] with SmallInteger type, not nullable, default=24000
  - Add position: Mapped[int] with SmallInteger type, not nullable, default=0
  - Server defaults match application defaults (text('24000') and text('0'))
  - Existing constraints (UniqueConstraint, CheckConstraint) remain unchanged
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 265-294) - Model layer changes
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 155-188) - Field specifications
- **Code Pattern**:
  ```python
  position_type: Mapped[int] = mapped_column(
      SmallInteger, nullable=False, server_default=text('24000')
  )
  position: Mapped[int] = mapped_column(
      SmallInteger, nullable=False, server_default=text('0')
  )
  ```
- **Dependencies**: Task 1.3 completion (migration tested)

### Task 2.2: Update ParticipantResponse schema

Update Pydantic schema to expose new fields instead of pre_filled_position.

- **Files**:
  - `shared/schemas/participant.py` - Update ParticipantResponse class
- **Success**:
  - Remove pre_filled_position field
  - Add position_type: int with description of enum values
  - Add position: int with description of purpose
  - Schema validation passes for new field structure
  - from_attributes=True configuration maintained
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 296-314) - Schema layer changes
- **Code Pattern**:
  ```python
  position_type: int = Field(..., description="Participant type (8000=host-added, 24000=self-added)")
  position: int = Field(..., description="Priority within participant type")
  ```
- **Dependencies**: Task 2.1 completion

### Task 2.3: Update model/schema test fixtures and verify tests pass

Update test fixtures that create participant models and verify model/schema tests pass.

- **Files**:
  - `tests/shared/models/` - Model test fixtures
  - `tests/shared/schemas/` - Schema test fixtures
- **Success**:
  - Test fixtures updated to use position_type and position instead of pre_filled_position
  - Mock participant creation uses correct field names
  - All model tests pass
  - Schema validation tests pass
  - No new errors introduced by field changes
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 265-294) - Model changes context
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 404-426) - Test files requiring updates
- **Fixture Pattern**:
  ```python
  # OLD: mock_participant("user1", pre_filled_position=1)
  # NEW: mock_participant("user1", position_type=8000, position=1)
  ```
- **Dependencies**: Task 2.2 completion

## Phase 3: Sorting Logic Refactoring

### Task 3.1: Replace sort_participants() implementation

Simplify sorting logic to use single three-tuple sort key instead of two-list approach.

- **Files**:
  - `shared/utils/participant_sorting.py` - Replace sort_participants function
- **Success**:
  - Remove priority/regular participant list splitting
  - Remove NULL checking for pre_filled_position
  - Implement single sorted() call with three-tuple key
  - Sort key: (position_type, position, joined_at)
  - Function docstring explains sorting behavior
  - Edge cases (gaps, ties) handled correctly
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 316-341) - Complete new implementation
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 111-141) - How this fixes gap problem
- **Code Specification**:
  ```python
  def sort_participants(participants: list["GameParticipant"]) -> list["GameParticipant"]:
      """Sort participants by position_type, position, and join time."""
      return sorted(
          participants,
          key=lambda p: (p.position_type, p.position, p.joined_at)
      )
  ```
- **Dependencies**: Phase 2 completion (model/schema updated)

### Task 3.2: Update PartitionedParticipants docstrings

Update docstrings in participant_sorting.py to reflect new sorting behavior.

- **Files**:
  - `shared/utils/participant_sorting.py` - Update PartitionedParticipants dataclass docstring
- **Success**:
  - Docstring no longer references "priority" vs "regular" split
  - Documents position_type/position-based sorting
  - Explains confirmed/overflow/waitlist division remains unchanged
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 316-341) - Sorting logic changes
- **Dependencies**: Task 3.1 completion

### Task 3.3: Update sorting test fixtures and verify tests pass

Update test fixtures in sorting tests and verify all sorting tests pass with new implementation.

- **Files**:
  - `tests/shared/utils/test_participant_sorting.py` - 30+ test cases using pre_filled_position
- **Success**:
  - All test fixtures updated to use position_type and position
  - Test expectations updated to match new sorting behavior
  - All sorting tests pass
  - Edge case tests validate gap handling works correctly
  - Tie-breaking tests validate joined_at sort key
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 404-426) - Test file requiring updates
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 428-438) - Fixture pattern change
- **Dependencies**: Task 3.2 completion

## Phase 4: Business Logic Updates

### Task 4.1: Update game service participant creation

Modify game service to use new fields when creating host-added participants.

- **Files**:
  - `services/api/services/games.py` Lines 311, 318 - Participant creation in add_to_games()
- **Success**:
  - Replace pre_filled_position=position with two fields
  - Set position_type=ParticipantType.HOST_ADDED
  - Set position=position (sequential value)
  - Import ParticipantType enum at top of file
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 343-357) - Business logic changes
- **Code Pattern**:
  ```python
  # OLD: pre_filled_position=position,
  # NEW:
  position_type=ParticipantType.HOST_ADDED,
  position=position,
  ```
- **Dependencies**: Phase 3 completion (sorting logic working)

### Task 4.2: Update game service participant queries

Modify queries that filter for pre-filled participants to use new field.

- **Files**:
  - `services/api/services/games.py` Lines 542, 648 - Queries in edit_participants() and related functions
- **Success**:
  - Replace `pre_filled_position.isnot(None)` with `position_type == ParticipantType.HOST_ADDED`
  - Queries return same participants as before
  - Query performance remains unchanged
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 343-357) - Business logic query changes
- **Code Pattern**:
  ```python
  # OLD: participant_model.GameParticipant.pre_filled_position.isnot(None)
  # NEW: participant_model.GameParticipant.position_type == ParticipantType.HOST_ADDED
  ```
- **Dependencies**: Task 4.1 completion

### Task 4.3: Update game service position updates

Modify position update logic to only update position field, not position_type.

- **Files**:
  - `services/api/services/games.py` Line 574 - Position update in edit_participants()
- **Success**:
  - Replace `p.pre_filled_position = position` with `p.position = position`
  - position_type remains unchanged (stays HOST_ADDED)
  - Update logic preserves participant type
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 343-357) - Position update logic
- **Code Pattern**:
  ```python
  # OLD: p.pre_filled_position = position
  # NEW: p.position = position
  ```
- **Dependencies**: Task 4.2 completion

### Task 4.4: Update service test fixtures and run service tests

Update test fixtures in service tests and verify all service-level tests pass.

- **Files**:
  - `tests/services/api/services/test_participant_creation_order.py` - Fixture usage
  - `tests/services/api/services/test_games_edit_participants.py` - Editing tests
  - Other service test files
- **Success**:
  - All service test fixtures updated to use position_type and position
  - Mock data reflects new field structure
  - All service tests pass
  - Participant creation tests validate new fields
  - Query tests verify filtering works correctly
  - Position update tests confirm behavior
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 404-426) - Test files requiring updates
- **Dependencies**: Task 4.3 completion

## Phase 5: API Route Updates

### Task 5.1: Update participant serialization in routes

Modify API routes to serialize new fields instead of pre_filled_position.

- **Files**:
  - `services/api/routes/games.py` Lines 527, 625 - Participant serialization in get_game() and list_games()
- **Success**:
  - Replace `pre_filled_position=participant.pre_filled_position` with two new fields
  - Add `position_type=participant.position_type`
  - Add `position=participant.position`
  - API responses include new fields
  - Response schema validation passes
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 359-384) - API route changes
- **Code Pattern**:
  ```python
  # OLD: pre_filled_position=participant.pre_filled_position,
  # NEW:
  position_type=participant.position_type,
  position=participant.position,
  ```
- **Dependencies**: Phase 4 completion (service layer working)

### Task 5.2: Update participant creation in join endpoints

Modify join endpoint to set new fields for self-added participants.

- **Files**:
  - `services/api/routes/games.py` Line 644 - Participant creation in join_game()
- **Success**:
  - Replace `pre_filled_position=None` with two new fields
  - Set `position_type=ParticipantType.SELF_ADDED`
  - Set `position=0` (default for self-added)
  - Import ParticipantType enum at top of file
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 359-384) - Join endpoint changes
- **Code Pattern**:
  ```python
  # OLD: pre_filled_position=None,
  # NEW:
  position_type=ParticipantType.SELF_ADDED,
  position=0,
  ```
- **Dependencies**: Task 5.1 completion

### Task 5.3: Update API test fixtures and run API tests

Update test fixtures in API route tests and verify all API tests pass.

- **Files**:
  - `tests/services/api/routes/` - API route test fixtures
  - API integration tests
- **Success**:
  - All API test fixtures updated to use position_type and position
  - All API tests pass
  - Response schemas validate correctly
  - Join endpoint creates participants with correct fields
  - Get/list endpoints return new field structure
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 404-426) - Test coverage
- **Dependencies**: Task 5.2 completion

## Phase 6: Bot and Additional Component Updates

### Task 6.1: Update bot event handler test fixtures

Update test fixtures in bot event handler tests to use new field structure.

- **Files**:
  - `tests/services/bot/events/test_handlers.py` - Mock participants
  - Other bot-related test files
- **Success**:
  - All bot test fixtures updated to use position_type and position
  - Mock participant creation uses correct field names
  - All bot tests pass
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 404-426) - Test files list
- **Dependencies**: Phase 5 completion

### Task 6.2: Update remaining test fixtures and helpers

Update any remaining test fixtures and helper functions across the codebase.

- **Files**:
  - Various test utility files with mock participant factories
  - Test conftest files with fixture definitions
- **Success**:
  - Mock factories accept position_type and position parameters
  - Default values match application defaults (24000, 0)
  - Helper functions produce valid test data
  - All callers of helpers updated
  - No references to pre_filled_position remain in tests
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 404-426) - Test helper context
- **Dependencies**: Task 6.1 completion

### Task 6.3: Run full test suite validation

Execute complete test suite to verify all changes work together across all components.

- **Files**:
  - Entire `tests/` directory
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - No test failures related to field changes
  - Code coverage maintained or improved
  - No warnings about deprecated fields
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 483-487) - Success criteria
- **Dependencies**: Task 6.2 completion

## Phase 7: End-to-End Validation

### Task 7.1: Run integration tests

Execute integration test suite to verify system-level behavior.

- **Files**:
  - `tests/integration/` test suite
- **Success**:
  - Integration tests pass
  - Multi-component interactions work correctly
  - Database queries return expected results
  - API contracts satisfied
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 510-526) - Implementation phases
- **Dependencies**: Phase 6 completion

### Task 7.2: Run E2E tests

Execute end-to-end test suite to verify complete user workflows.

- **Files**:
  - `tests/e2e/` test suite
- **Success**:
  - E2E tests pass
  - User workflows function correctly
  - No regressions in functionality
  - Participant ordering behaves as expected
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 510-526) - Validation phase
- **Dependencies**: Task 7.1 completion

### Task 7.3: Manual testing of participant ordering

Perform manual testing to verify gap handling and sorting work correctly.

- **Files**:
  - Running application instance
- **Success**:
  - Create game with host-added participants at positions 1, 2, 3
  - Remove participant at position 1
  - Verify remaining participants (2, 3) sort correctly as first/second
  - Add self-joined participants
  - Verify host-added sort before self-joined
  - Verify tie-breaking by join time works
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 111-141) - Gap handling fix explanation
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 28-54) - Problem statement with examples
- **Dependencies**: Task 7.2 completion

### Task 7.4: Verify gap handling works correctly

Specifically test that position value gaps no longer cause issues.

- **Files**:
  - Running application instance
- **Success**:
  - Create participants with non-consecutive position values (e.g., 2, 5, 7)
  - Verify they sort in correct order (position 2 first, then 5, then 7)
  - Confirm no array indexing errors occur
  - Verify partition logic still works (confirmed vs overflow)
  - Document that gap problem is resolved
- **Research References**:
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 111-141) - How refactoring fixes gaps
  - #file:../research/20251224-participant-ordering-schema-refactor-research.md (Lines 440-474) - Benefits section
- **Dependencies**: Task 7.3 completion

## Dependencies

- PostgreSQL database (version 15+)
- Alembic migration framework
- SQLAlchemy ORM (version 2.x)
- Pydantic schemas (version 2.x)
- Pytest test framework
- FastAPI web framework

## Success Criteria

- Gap handling bug fixed - position values can have gaps without causing issues
- All tests pass incrementally after each phase
- Migration is reversible and safe for production deployment
- API responses use new field structure
- Code is simpler than previous implementation
- No functionality regressions
- Documentation reflects new schema design
