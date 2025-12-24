<!-- markdownlint-disable-file -->

# Task Research Notes: Participant Ordering Schema Refactoring

## Research Executed

### File Analysis

- [shared/models/participant.py](../../../shared/models/participant.py)
  - Current `pre_filled_position` field: `Mapped[int | None] = mapped_column(Integer, nullable=True)`
  - Model has CheckConstraint for user_id/display_name exclusivity
  - UniqueConstraint on `(game_session_id, user_id)`
- [shared/schemas/participant.py](../../../shared/schemas/participant.py)
  - `ParticipantResponse` schema includes `pre_filled_position: int | None`
  - Field described as "Position in pre-populated list (1-indexed, None for regular participants)"
- [shared/utils/participant_sorting.py](../../../shared/utils/participant_sorting.py)
  - `sort_participants()` function splits participants into priority (pre_filled_position set) and regular (NULL)
  - Priority participants sorted by `pre_filled_position` value
  - Regular participants sorted by `joined_at` timestamp
  - `partition_participants()` uses `sort_participants()` to divide into confirmed/overflow
- [services/api/services/games.py](../../../services/api/services/games.py) Lines 535-580
  - Updates `pre_filled_position` when editing participant lists
  - Queries for participants where `pre_filled_position.isnot(None)`
  - Direct assignment: `p.pre_filled_position = position`

### Code Search Results

- **pre_filled_position usages**: Found 30+ matches across codebase
  - Model definition in `shared/models/participant.py`
  - Schema definition in `shared/schemas/participant.py`
  - Sorting logic in `shared/utils/participant_sorting.py`
  - API routes in `services/api/routes/games.py` (serialization)
  - Game service in `services/api/services/games.py` (business logic)
  - Extensive test coverage in `tests/shared/utils/test_participant_sorting.py`
  - Test fixtures throughout test suite

- **sort_participants usages**: Found 25 references
  - Definition: `shared/utils/participant_sorting.py:73`
  - Primary caller: `partition_participants()` function
  - Used in API routes and bot event handlers
  - 23 test usages across test suite

### Database Schema Analysis

- **Current Schema** (from `alembic/versions/c2135ff3d5cd_initial_schema.py` Lines 200-230):

```python
op.create_table(
    "game_participants",
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("game_session_id", sa.String(length=36), nullable=False),
    sa.Column("user_id", sa.String(length=36), nullable=True),
    sa.Column("display_name", sa.String(length=100), nullable=True),
    sa.Column("joined_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    sa.Column("pre_filled_position", sa.Integer(), nullable=True),
    # ... constraints
)
```

- **Timestamp Resolution**: PostgreSQL `DateTime` provides microsecond precision
  - Format: `YYYY-MM-DD HH:MI:SS.mmmmmm`
  - Collision probability: Extremely low (requires same-microsecond joins)
  - Current behavior: `server_default=func.now()` provides high-resolution timestamps

### Project Conventions

- **Enum Patterns**: Project uses `str` enums (GameStatus in game.py Line 38)
- **Integer Types**: Project uses `Integer` type consistently for numeric fields
- **SQLAlchemy Imports**: Models import `func` and `text` for server defaults (per recent Phase 1 updates)

## Problem Statement

### Current Implementation Issues

**Gap Handling Problem**:

- When host adds participants at positions 1, 2, 3
- If position 1 participant drops out
- Remaining participants stay at positions 2, 3
- **Problem**: Some code treats these as absolute positions, creating gaps in the list

**Example of Current Bug**:

```
Initial State:
  Position 1: Alice (host-added)
  Position 2: Bob (host-added)
  Position 3: Carol (host-added)
  Position NULL: Dave (self-joined)
  Position NULL: Eve (self-joined)

Alice drops out:
  Position 2: Bob (host-added) ← Gap! Position 1 missing
  Position 3: Carol (host-added)
  Position NULL: Dave (self-joined)
  Position NULL: Eve (self-joined)

Problem: Code may treat position 2 as "second in line" when it should be first
```

**Limited Extensibility**:

- Current two-category system (priority vs regular) is inflexible
- Cannot distinguish between different participant types (host-added vs self-joined vs future types)
- No room for future participant categories without major refactoring

## Proposed Solution

### New Two-Field System

Replace single `pre_filled_position` field with two new fields:

1. **`position_type`**: `SmallInteger` - Enumerated type indicating participant category
2. **`position`**: `SmallInteger` - Priority within that category

### Enum Design

Use sparse numeric values to allow future insertions:

```python
class ParticipantType(IntEnum):
    """Participant type enumeration with sparse values for future expansion."""
    HOST_ADDED = 8000    # High priority (sorts first)
    SELF_ADDED = 24000   # Low priority (sorts last)
    # Future types can use: 12000, 16000, 20000, etc.
```

**Rationale for Values**:

- HOST_ADDED = 8000: Low numeric value → sorts **first** in ascending order
- SELF_ADDED = 24000: High numeric value → sorts **last** in ascending order
- Gap of 16,000 between them allows inserting multiple new types
- All values fit in SmallInteger (-32,768 to 32,767)

### Sorting Algorithm

New sorting logic will be simple and consistent:

```python
def sort_participants(participants: list["GameParticipant"]) -> list["GameParticipant"]:
    """Sort participants by position_type, position, then join time."""
    return sorted(
        participants,
        key=lambda p: (p.position_type, p.position, p.joined_at)
    )
```

**Sorting Behavior**:

- First sort key: `position_type` (8000 for host-added, 24000 for self-added)
- Second sort key: `position` (priority within type)
- Third sort key: `joined_at` (timestamp for tie-breaking)

### How This Fixes the Gap Problem

**New Behavior After Refactoring**:

```
Initial State:
  (8000, 0, t1): Alice (host-added, position 0)
  (8000, 1, t2): Bob (host-added, position 1)
  (8000, 2, t3): Carol (host-added, position 2)
  (24000, 0, t4): Dave (self-added)
  (24000, 0, t5): Eve (self-added)

Alice drops out:
  (8000, 1, t2): Bob (host-added, position 1) ← No gap issue!
  (8000, 2, t3): Carol (host-added, position 2)
  (24000, 0, t4): Dave (self-added)
  (24000, 0, t5): Eve (self-added)

Result: Sorted correctly regardless of gaps in position values
        Position value is only used for sorting, not indexing
```

**Key Insight**: Position values are **sort keys only**, not array indices. Gaps don't matter because we sort, not index.

## Database Schema Changes

### Field Specifications

```python
position_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
```

**Type Choice: SmallInteger**

- PostgreSQL: 2-byte integer (-32,768 to 32,767)
- Sufficient range for sparse enum values (8000, 24000, etc.)
- Space-efficient compared to Integer (4 bytes)
- Consistent with small numeric values used in the application

**Nullability**: Both fields NOT NULL

- Every participant must have a type and position
- Simplifies query logic (no NULL handling)
- Migration will set defaults based on current state

### Constraints

**Keep Existing Unique Constraint**:

```python
UniqueConstraint("game_session_id", "user_id", name="unique_game_participant")
```

**No Need for New Unique Constraint**:

- Original proposal: Add `(game_session_id, position_type, position, joined_at)` constraint
- **Decision**: Not needed because:
  - Real users already have unique constraint via `(game_session_id, user_id)`
  - Placeholders (user_id=NULL) can share same type/position
  - Multiple NULLs are allowed in unique constraints anyway
  - Timestamp collision probability is negligible (microsecond resolution)

### Migration Strategy

**Single Migration: Transform pre_filled_position → (position_type, position)**

```python
def upgrade() -> None:
    """Replace pre_filled_position with position_type and position fields."""

    # Add new columns with temporary defaults
    op.add_column(
        "game_participants",
        sa.Column("position_type", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "game_participants",
        sa.Column("position", sa.SmallInteger(), nullable=True)
    )

    # Data migration: Transform existing values
    op.execute("""
        UPDATE game_participants
        SET
            position_type = CASE
                WHEN pre_filled_position IS NOT NULL THEN 8000  -- HOST_ADDED
                ELSE 24000  -- SELF_ADDED
            END,
            position = CASE
                WHEN pre_filled_position IS NOT NULL THEN pre_filled_position
                ELSE 0
            END
    """)

    # Make columns non-nullable now that data is migrated
    op.alter_column("game_participants", "position_type", nullable=False)
    op.alter_column("game_participants", "position", nullable=False)

    # Remove old column
    op.drop_column("game_participants", "pre_filled_position")

def downgrade() -> None:
    """Restore pre_filled_position from position_type and position."""

    # Add back old column
    op.add_column(
        "game_participants",
        sa.Column("pre_filled_position", sa.Integer(), nullable=True)
    )

    # Reverse data migration: Only restore host-added positions
    op.execute("""
        UPDATE game_participants
        SET pre_filled_position = CASE
            WHEN position_type = 8000 THEN position  -- HOST_ADDED
            ELSE NULL  -- SELF_ADDED
        END
    """)

    # Remove new columns
    op.drop_column("game_participants", "position")
    op.drop_column("game_participants", "position_type")
```

**Migration Safety**:

- ✅ Can run on live database (adds columns first, drops last)
- ✅ Preserves all existing data semantics
- ✅ Reversible via downgrade()
- ✅ No data loss in upgrade/downgrade cycle

## Code Changes Required

### 1. Model Layer (shared/models/participant.py)

**Changes**:

- Remove: `pre_filled_position: Mapped[int | None]`
- Add: `position_type: Mapped[int]` and `position: Mapped[int]`
- Add enum import and definition

**New Code**:

```python
from enum import IntEnum
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, UniqueConstraint, func

class ParticipantType(IntEnum):
    """Participant type enumeration with sparse values for future expansion."""
    HOST_ADDED = 8000
    SELF_ADDED = 24000

class GameParticipant(Base):
    # ... existing fields ...
    joined_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
    position_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text('24000')
    )
    position: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text('0')
    )
    # ... relationships and constraints ...
```

### 2. Schema Layer (shared/schemas/participant.py)

**Changes**:

- Remove: `pre_filled_position: int | None` field
- Add: `position_type: int` and `position: int` fields
- Update field descriptions

**New Code**:

```python
class ParticipantResponse(BaseModel):
    # ... existing fields ...
    joined_at: str = Field(..., description="Join timestamp (UTC ISO)")
    position_type: int = Field(..., description="Participant type (8000=host-added, 24000=self-added)")
    position: int = Field(..., description="Priority within participant type")

    model_config = {"from_attributes": True}
```

### 3. Sorting Logic (shared/utils/participant_sorting.py)

**Complete Replacement**:

```python
def sort_participants(participants: list["GameParticipant"]) -> list["GameParticipant"]:
    """Sort participants by position_type, position, and join time.

    Participants are sorted using three keys in priority order:
    1. position_type: Lower values sort first (e.g., HOST_ADDED=8000 before SELF_ADDED=24000)
    2. position: Lower values sort first within same type
    3. joined_at: Earlier timestamps sort first for tie-breaking

    Args:
        participants: List of GameParticipant models to sort

    Returns:
        Sorted list with consistent ordering regardless of position value gaps
    """
    return sorted(
        participants,
        key=lambda p: (p.position_type, p.position, p.joined_at)
    )
```

**Key Changes**:

- Remove: Separate priority/regular participant lists
- Remove: NULL checking for `pre_filled_position`
- Add: Single unified sort with three-tuple key
- Benefit: Simpler logic, no branching, handles all cases uniformly

### 4. Business Logic (services/api/services/games.py)

**Locations Requiring Updates**:

**Lines 311, 318** - Creating host-added participants:

```python
# OLD:
pre_filled_position=position,

# NEW:
position_type=ParticipantType.HOST_ADDED,
position=position,
```

**Lines 542, 648** - Querying pre-filled participants:

```python
# OLD:
participant_model.GameParticipant.pre_filled_position.isnot(None),

# NEW:
participant_model.GameParticipant.position_type == ParticipantType.HOST_ADDED,
```

**Line 574** - Updating positions:

```python
# OLD:
p.pre_filled_position = position

# NEW:
p.position = position
# position_type remains HOST_ADDED, unchanged
```

### 5. API Routes (services/api/routes/games.py)

**Lines 527, 625** - Serializing participants:

```python
# OLD:
pre_filled_position=participant.pre_filled_position,

# NEW:
position_type=participant.position_type,
position=participant.position,
```

**Line 644** - Creating self-joined participants:

```python
# OLD:
pre_filled_position=None,

# NEW:
position_type=ParticipantType.SELF_ADDED,
position=0,
```

### 6. Test Updates

**Test Files Requiring Updates**:

- `tests/shared/utils/test_participant_sorting.py` - 30+ test cases using `pre_filled_position`
- `tests/services/api/services/test_participant_creation_order.py` - Test fixtures
- `tests/services/api/services/test_games_edit_participants.py` - Participant editing tests
- `tests/services/bot/events/test_handlers.py` - Mock participant setup

**Test Fixture Pattern Change**:

```python
# OLD:
mock_participant("user1", joined_at=base_time, pre_filled_position=1)

# NEW:
mock_participant("user1", joined_at=base_time, position_type=8000, position=1)
```

## Implementation Phases

### Phase 1: Enum Definition and Database Migration

1. Define `ParticipantType` IntEnum in new module
2. Create Alembic migration to transform schema
3. Run migration on test database
4. Verify data transformation correctness

### Phase 2: Model and Schema Updates

1. Update `GameParticipant` model with new fields
2. Update `ParticipantResponse` schema
3. Verify model tests pass
4. Update model repr/str methods if needed

### Phase 3: Sorting Logic Refactoring

1. Replace `sort_participants()` implementation
2. Update `PartitionedParticipants` docstrings
3. Run existing sorting tests (should pass with new logic)
4. Add new test cases for edge scenarios

### Phase 4: Business Logic Updates

1. Update game service participant creation
2. Update game service participant queries
3. Update game service participant position updates
4. Run service-level unit tests

### Phase 5: API Route Updates

1. Update participant serialization in routes
2. Update participant creation in join endpoints
3. Run API integration tests
4. Verify API response schemas

### Phase 6: Test Suite Updates

1. Update test fixtures across all test files
2. Update mock participant creation helpers
3. Run full test suite
4. Fix any remaining test failures

### Phase 7: End-to-End Validation

1. Run integration tests
2. Run E2E tests
3. Manual testing of participant ordering
4. Verify gap handling works correctly

## Benefits of New Approach

### 1. Fixes Gap Handling Bug

- **Current**: Gaps in position values cause indexing issues
- **New**: Position values are sort keys only, gaps don't matter
- **Example**: Positions 2, 5, 7 sort correctly without requiring 1, 3, 4, 6

### 2. Extensible Type System

- **Current**: Binary system (priority vs regular)
- **New**: Sparse enum allows unlimited future types
- **Future Types**: Co-host (12000), VIP (16000), Backup (20000), etc.

### 3. Simpler Sorting Logic

- **Current**: Two separate lists, branching, NULL checks
- **New**: Single sort with three-tuple key
- **Benefit**: Fewer lines of code, easier to understand

### 4. Consistent Semantics

- **Current**: `pre_filled_position` name implies pre-filling only
- **New**: `position_type` and `position` clearly describe purpose
- **Benefit**: Code is more self-documenting

### 5. Future-Proof Design

- Sparse enum values (8000, 24000) leave room for additions
- Can add new types without renumbering existing types
- SmallInteger provides range -32,768 to 32,767 (plenty of room)

## Potential Risks and Mitigations

### Risk 1: Breaking API Compatibility

- **Risk**: Frontend expects `pre_filled_position` in API responses
- **Mitigation**: Update frontend simultaneously with backend
- **Testing**: Verify API schema changes in integration tests

### Risk 2: Test Suite Churn

- **Risk**: 30+ tests reference `pre_filled_position`
- **Mitigation**: Update tests incrementally by phase
- **Validation**: Run tests after each phase completion

### Risk 3: Migration Data Loss

- **Risk**: Incorrect data transformation in migration
- **Mitigation**: Test migration on copy of production data
- **Rollback**: Downgrade migration restores original schema

### Risk 4: Performance Impact

- **Risk**: Three-key sort slower than current two-list approach
- **Assessment**: Negligible - games typically have <100 participants
- **Optimization**: If needed, can add composite index

## Success Criteria

1. ✅ Gap handling works correctly (no indexing issues)
2. ✅ All existing tests pass with updated fixtures
3. ✅ Migration runs successfully on test database
4. ✅ API responses include new fields instead of old field
5. ✅ Sorting behavior matches current behavior for existing participant types
6. ✅ Code is simpler and more maintainable
7. ✅ Documentation updated to reflect new schema

## Open Questions

None - all design questions resolved through research and discussion.

## Recommended Approach

Proceed with implementation using phased approach:

1. Create enum definition
2. Write and test migration
3. Update model layer
4. Update business logic
5. Update API layer
6. Update test suite
7. E2E validation

This approach minimizes risk by validating each layer before proceeding to the next.
