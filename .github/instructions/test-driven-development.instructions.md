---
description: 'Test-Driven Development (TDD) methodology and workflow for all code implementation'
applyTo: '**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx'
---

# Test-Driven Development (TDD) Instructions

TDD applies to writing **new production code and enhancing existing production code**. Writing the failing test first forces a clear definition of the required interface and behavior before any implementation decisions are made. The RED phase — seeing the test fail — proves the test is actually capable of detecting the regression it guards against, preventing false-confidence tests that always pass regardless of implementation. Tests written this way become executable documentation of intended behavior from day one.

| Scenario                            | Stub?                       | `xfail`? | Why                                             |
| ----------------------------------- | --------------------------- | -------- | ----------------------------------------------- |
| New feature                         | Yes (`NotImplementedError`) | Yes      | Implementation doesn't exist yet                |
| Bug fix                             | No                          | Yes      | Correct behavior not yet achieved               |
| Retrofitting tests for correct code | No                          | No       | Code is already correct; tests pass immediately |

## Applicability

**TDD methodology applies ONLY to languages with mature unit testing frameworks:**

- ✅ **Python** (pytest, unittest)
- ✅ **TypeScript/JavaScript** (Vitest, Jest, Mocha)
- ✅ **Other languages** with established testing frameworks

**TDD does NOT apply to:**

- ❌ **Bash scripts** (no practical unit test framework)
- ❌ **Dockerfiles** (no unit test framework)
- ❌ **YAML/JSON configuration files** (no unit tests)
- ❌ **SQL migration scripts** (use integration tests instead)
- ❌ **Infrastructure-as-Code** without test frameworks
- ❌ **Writing tests for already-correct code** (retrofitting coverage at any level — unit, integration, or e2e): the correct behavior already exists, so there is no stub to create and no xfail marker needed; tests should pass immediately. Note: a bug fix is **not** this case — see [TDD for Bug Fixes](#tdd-for-bug-fixes) below.

**For non-testable file types:** Create and verify functionality through integration tests, manual testing, or other appropriate validation methods.

## TDD for Bug Fixes

Bug fixes follow a modified Red-Green-Refactor cycle. There is no stub to create — the buggy code already exists — but you still need the RED phase to prove the test actually detects the bug.

### Bug Fix Workflow

**Step 1: Write the regression test and mark it `xfail`**

Write a test that asserts the _correct_ (post-fix) behavior. It will fail because the bug still exists. Mark it `xfail` with `strict=True` and a reason describing the bug:

```python
@pytest.mark.xfail(reason="Bug: completed schedule deleted when IN_PROGRESS game is updated", strict=True)
def test_updating_in_progress_game_preserves_completed_schedule():
    # ... test asserting correct behavior ...
    assert completed_schedule is not None
```

**Step 2: Run the test to confirm it shows as `xfailed`**

This proves the test is actually capable of detecting the bug. If it unexpectedly passes, the bug may already be fixed or the test is wrong.

**Step 3: Fix the bug**

Implement the fix in production code. Do NOT modify the test assertions.

**Step 4: Remove the `xfail` marker**

With the bug fixed the test should now pass. Remove only the `@pytest.mark.xfail` decorator — the assertion is unchanged. With `strict=True`, if you forget to remove the marker after the fix, the suite will error on an unexpected pass, which prevents the marker from lingering.

```python
# xfail removed — the only change
def test_updating_in_progress_game_preserves_completed_schedule():
    # ... same assertions, unchanged ...
    assert completed_schedule is not None
```

**❌ WRONG — Do not skip the RED phase:**

```python
# WRONG: written after the fix, so you never verified the test can catch a regression
def test_updating_in_progress_game_preserves_completed_schedule():
    assert completed_schedule is not None
```

## Core TDD Principle

**ALL new functionality in testable languages MUST follow the Red-Green-Refactor cycle. Write tests BEFORE writing implementation code.**

## TDD Workflow (Red-Green-Refactor)

### Step 1: RED - Create Stub and Failing Tests

**ALWAYS start by creating the interface with NotImplementedError:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session.

    Args:
        game: The game session to calculate capacity for
        participants: Current list of participants

    Returns:
        Number of available slots

    Raises:
        NotImplementedError: Function not yet implemented
    """
    raise NotImplementedError("calculate_game_capacity not yet implemented")
```

```typescript
export function calculateGameCapacity(game: GameSession, participants: Participant[]): number {
  throw new Error('calculateGameCapacity not yet implemented');
}
```

**Then write tests for the ACTUAL desired behavior using expected failure markers:**

```python
import pytest

@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
def test_calculate_game_capacity_with_available_slots():
    """Test capacity calculation when slots are available."""
    game = GameSession(max_participants=5)
    participants = [Participant(), Participant()]

    result = calculate_game_capacity(game, participants)
    assert result == 3  # REAL assertion from day 1
```

```typescript
import { describe, test, expect } from 'vitest';

describe('calculateGameCapacity', () => {
  test.failing('should calculate available slots correctly', () => {
    const game = { maxParticipants: 5 };
    const participants = [{}, {}];

    const result = calculateGameCapacity(game, participants);
    expect(result).toBe(3); // REAL assertion from day 1
  });
});
```

**Run tests to verify expected failures:**

- `uv run pytest tests/unit/test_game_capacity.py -v` (Python - shows "1 xfailed")
- `npm test -- test_game_capacity` (TypeScript - shows test as expected failure)

**Key Point:** Tests contain REAL assertions for the desired behavior, just marked as expected failures. Tests are NOT modified after implementation - only the xfail marker is removed.

**❌ WRONG - Do NOT write tests that assert `NotImplementedError` is raised:**

```python
# WRONG: This test is useless — it only proves the stub exists, not that the feature works
@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
def test_calculate_game_capacity_not_implemented():
    with pytest.raises(NotImplementedError):
        calculate_game_capacity(game, participants)
```

A test expecting `NotImplementedError` tells you nothing about the desired behavior and must be rewritten entirely after implementation — violating the rule that only the xfail marker is removed. Always assert the real expected outcome from day one.

### Step 2: GREEN - Implement and Remove xfail Markers

**Replace NotImplementedError with the simplest solution that makes tests pass:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session."""
    return game.max_participants - len(participants)
```

**Remove the xfail marker from tests (no other changes to tests):**

```python
import pytest

# @pytest.mark.xfail removed - that's the ONLY change
def test_calculate_game_capacity_with_available_slots():
    """Test capacity calculation when slots are available."""
    game = GameSession(max_participants=5)
    participants = [Participant(), Participant()]

    result = calculate_game_capacity(game, participants)
    assert result == 3  # SAME assertion - unchanged
```

```typescript
import { describe, test, expect } from 'vitest';

describe('calculateGameCapacity', () => {
  test('should calculate available slots correctly', () => {
    // .failing removed
    const game = { maxParticipants: 5 };
    const participants = [{}, {}];

    const result = calculateGameCapacity(game, participants);
    expect(result).toBe(3); // SAME assertion - unchanged
  });
});
```

**Run tests to verify they now pass:**

- `uv run pytest tests/unit/test_game_capacity.py -v` (Python - shows "1 passed")
- `npm test -- test_game_capacity` (TypeScript - shows "1 passed")

**Critical:** The test assertions are NEVER modified - only the xfail/failing marker is removed.

### Step 3: REFACTOR - Improve Implementation

**Only after tests pass, refactor for quality:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session.

    Accounts for confirmed participants only, excluding waitlist.
    """
    confirmed_count = sum(1 for p in participants if p.status == ParticipantStatus.CONFIRMED)
    return max(0, game.max_participants - confirmed_count)
```

**Add additional tests for edge cases:**

```python
def test_calculate_game_capacity_at_full_capacity():
    """Test that capacity returns 0 when game is full."""
    game = GameSession(max_participants=3)
    participants = [Participant() for _ in range(3)]

    result = calculate_game_capacity(game, participants)
    assert result == 0

def test_calculate_game_capacity_over_capacity():
    """Test that capacity handles over-booking gracefully."""
    game = GameSession(max_participants=2)
    participants = [Participant() for _ in range(5)]

    result = calculate_game_capacity(game, participants)
    assert result == 0  # Should not return negative
```

**Run full test suite to ensure refactoring didn't break anything.**

## TDD in Task Plans

### Phase Structure with TDD

Every implementation phase MUST follow this pattern:

```markdown
### Phase N: Feature Name

- [ ] Task N.1: Create stub function with NotImplementedError
  - Create function signature with complete type hints
  - Add comprehensive docstring
  - Raise NotImplementedError with descriptive message
  - Details: [details file reference]

- [ ] Task N.2: Write tests with real assertions marked as expected failures
  - Use @pytest.mark.xfail (Python) or test.failing (TypeScript) markers
  - Write ACTUAL assertions for desired behavior (not expecting NotImplementedError)
  - Test happy path with real expected values
  - Test edge cases with real expected behavior
  - Test error conditions
  - Document expected behavior in test docstrings
  - Verify tests show as "xfailed" or "expected failure" when run
  - Details: [details file reference]

- [ ] Task N.3: Implement solution and remove xfail markers
  - Replace NotImplementedError with minimal working implementation
  - Remove @pytest.mark.xfail or test.failing markers from tests
  - DO NOT modify test assertions - they are already correct
  - Run tests to verify they pass
  - Details: [details file reference]

- [ ] Task N.4: Refactor and add comprehensive tests
  - Improve implementation for edge cases
  - Add additional tests for boundary conditions
  - Add integration tests if needed
  - Refactor for clarity and performance
  - Verify full test suite passes
  - Details: [details file reference]
```

### ❌ INCORRECT Phase Structure (Testing Separated from Implementation)

**DO NOT structure phases like this:**

```markdown
### Phase 1: Implement Game Capacity Feature

- [ ] Create calculate_game_capacity function
- [ ] Add capacity check to join handler
- [ ] Update game model with capacity field

### Phase 2: Add Database Migration

- [ ] Create migration for capacity field
- [ ] Update schema

### Phase 3: Testing ❌ TOO LATE!

- [ ] Write unit tests for capacity calculation
- [ ] Write integration tests
```

### ✅ CORRECT Phase Structure (TDD Integrated)

```markdown
### Phase 1: Game Capacity Calculation

- [ ] Task 1.1: Create calculate_game_capacity stub
- [ ] Task 1.2: Write tests with real assertions marked xfail
- [ ] Task 1.3: Implement capacity calculation and remove xfail markers
- [ ] Task 1.4: Refactor and add edge case tests

### Phase 2: Database Schema for Capacity

- [ ] Task 2.1: Create migration stub
- [ ] Task 2.2: Write migration tests with xfail markers
- [ ] Task 2.3: Implement migration and remove xfail markers
- [ ] Task 2.4: Test with real database and add edge cases

### Phase 3: Join Handler Integration

- [ ] Task 3.1: Create join_with_capacity_check stub
- [ ] Task 3.2: Write unit tests with xfail markers
- [ ] Task 3.3: Implement handler and remove xfail markers
- [ ] Task 3.4: Add integration/e2e tests against the completed implementation (no xfail markers)
```

## TDD for Different Test Levels

### Unit Tests (Always TDD for New or Enhanced Code)

**TDD is REQUIRED for unit tests when writing new or enhanced production code. Write tests BEFORE writing implementation:**

**Exception**: When the task is adding unit tests for code that already has an implementation, see [Writing Tests for Already-Implemented Code](#writing-tests-for-already-implemented-code-tdd-not-required) below.

1. Create stub with NotImplementedError
2. Write tests with REAL assertions marked with @pytest.mark.xfail or test.failing
3. Implement function and remove xfail markers (DO NOT modify test assertions)
4. Add edge case tests and refactor

### Integration Tests (TDD NOT Required)

**Integration tests are written AFTER the implementation exists.** The function or endpoint under test already exists by the time integration tests are added, so the Red-Green-Refactor cycle with stubs and xfail markers does not apply.

**Write integration tests to verify the already-implemented behavior:**

- Write tests against the real running service or database
- Tests should pass from the start (no xfail markers)
- Cover happy paths, error paths, and edge cases
- Do NOT use stubs, NotImplementedError, or xfail markers

### E2E Tests (TDD NOT Required)

**E2E tests are written AFTER unit and integration tests are green.** The full workflow already exists, so TDD does not apply.

- E2E tests verify complete user workflows against a real environment
- Tests should pass from the start (no xfail markers)
- Test cross-service interactions and realistic user scenarios
- Do NOT use stubs, NotImplementedError, or xfail markers

### Writing Tests for Already-Correct Code (TDD NOT Required)

When the task is **adding tests for code that is already correctly implemented** — at any test level — TDD does not apply. This does NOT cover bug fixes; see [TDD for Bug Fixes](#tdd-for-bug-fixes).

TDD's Red-Green-Refactor cycle works because you can stub the _production code_ and write a failing test against it. But when the task itself is writing tests, there is no production code to stub: you cannot stub the _tests_ and write test-tests. The test you are writing is the artifact, and it should either pass or fail against the existing implementation immediately.

**Absolute rules — no exceptions:**

- **NEVER use `xfail` or `failing` markers** when writing tests for existing code, even if you are uncertain whether the test will pass
- **NEVER create `NotImplementedError` stubs** for code that already has an implementation
- **Tests must be written to pass** — run them immediately and deal with failures directly

**When a test for existing code fails, there are exactly two valid responses:**

1. **The implementation has a bug** → fix the implementation
2. **The assertion is wrong** → fix the assertion

There is no third option. Marking a failing test `xfail` because you are unsure of the outcome hides real bugs rather than surfacing them. "Uncertain outcome" is not the same as "expected failure" — `xfail` means "the implementation does not exist yet," not "I don't know what this code does."

**Write tests that pass from the start:**

- Write assertions directly against the live implementation
- Run the test immediately — if it fails, fix the code or fix the assertion before moving on
- Cover happy paths, error paths, and edge cases
- No RED phase, no stubs, no `xfail` markers

This applies whether you are adding unit tests to an existing module, writing integration tests for a completed endpoint, or adding e2e coverage for a working workflow.

**❌ WRONG - Do NOT use xfail as a "discovery probe" for uncertain test outcomes:**

```python
# WRONG: xfail used because you're unsure whether the test will pass
@pytest.mark.xfail(reason="Not sure if this path works", strict=False)
def test_some_existing_function():
    assert some_existing_function(edge_case) == expected
```

**✅ CORRECT - Write the assertion, run it, fix what fails:**

```python
# RIGHT: write the test, run it immediately
def test_some_existing_function():
    assert some_existing_function(edge_case) == expected
# If this fails: is the expected value wrong? Fix the assertion.
# Is the function returning the wrong result? Fix the implementation.
# Either way, fix it — do not add xfail.
```

## TDD Quality Checklist

Before marking any implementation task complete:

- [ ] Language is appropriate for TDD (Python, TypeScript/JavaScript, etc.)
- [ ] Function stub created with NotImplementedError first
- [ ] Tests with REAL assertions written before implementation
- [ ] Tests marked with xfail/failing markers (red phase)
- [ ] Tests verified to show as "xfailed" or "expected failure" when run
- [ ] Implementation makes tests pass (green phase)
- [ ] xfail/failing markers removed (test assertions NOT modified)
- [ ] Tests now show as "passed"
- [ ] Refactoring performed with passing tests
- [ ] Edge cases covered with additional tests
- [ ] Full test suite passes
- [ ] No untested code paths remain

## Common TDD Patterns

### Testing Exceptions and Errors

```python
# RED: Stub that raises NotImplementedError
def validate_game_data(data: dict) -> Game:
    raise NotImplementedError("validate_game_data not yet implemented")

# RED: Test for desired exception behavior marked as xfail
@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
def test_validate_game_throws_on_invalid_data():
    with pytest.raises(ValidationError, match="Invalid game data"):
        validate_game_data(invalid_data)

# Test shows as "xfailed" - expects ValidationError but gets NotImplementedError

# GREEN: After implementation, remove xfail marker
def validate_game_data(data: dict) -> Game:
    if not data.get('title'):
        raise ValidationError("Invalid game data")
    return Game(**data)

# Remove @pytest.mark.xfail decorator - test assertions unchanged
def test_validate_game_throws_on_invalid_data():
    with pytest.raises(ValidationError, match="Invalid game data"):
        validate_game_data(invalid_data)

# Test now passes - ValidationError is raised as expected
```

### Testing Async Functions

```python
# RED: Async stub
async def fetch_game_from_api(game_id: int) -> Game:
    raise NotImplementedError("fetch_game_from_api not yet implemented")

# RED: Test for desired behavior marked as xfail
@pytest.mark.asyncio
@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
async def test_fetch_game_from_api():
    game = await fetch_game_from_api(123)
    assert game.id == 123  # REAL assertion from day 1
    assert game.title is not None

# Test shows as "xfailed"

# GREEN: Implement and remove xfail marker
async def fetch_game_from_api(game_id: int) -> Game:
    response = await api_client.get(f"/games/{game_id}")
    return Game(**response.json())

# Remove @pytest.mark.xfail decorator only
@pytest.mark.asyncio
async def test_fetch_game_from_api():
    game = await fetch_game_from_api(123)
    assert game.id == 123  # SAME assertion - unchanged
    assert game.title is not None

# Test now passes - returns Game with correct attributes
```

### Testing Database Operations

```python
# RED: Stub repository method
class GameRepository:
    def get_by_id(self, game_id: int) -> Game | None:
        raise NotImplementedError("get_by_id not yet implemented")

# RED: Test for desired behavior marked as xfail
@pytest.mark.xfail(reason="Method not yet implemented", strict=True)
def test_get_game_by_id(mock_db_session):
    repo = GameRepository(mock_db_session)
    game = repo.get_by_id(123)
    assert game is not None  # REAL assertion from day 1
    assert game.id == 123

# Test shows as "xfailed"

# GREEN: Implement and remove xfail marker
class GameRepository:
    def get_by_id(self, game_id: int) -> Game | None:
        return self.session.query(Game).filter(Game.id == game_id).first()

# Remove @pytest.mark.xfail decorator only
def test_get_game_by_id(mock_db_session):
    repo = GameRepository(mock_db_session)
    game = repo.get_by_id(123)
    assert game is not None  # SAME assertion - unchanged
    assert game.id == 123

# Test now passes - returns Game from database
```

## Anti-Patterns to Avoid

### ❌ Writing Implementation Before Tests

```python
# WRONG: Implementation first
def calculate_capacity(game, participants):
    return game.max_participants - len(participants)

# Then later writing tests (too late!)
def test_calculate_capacity():
    assert calculate_capacity(game, []) == 5
```

### ❌ Skipping NotImplementedError Phase

```python
# WRONG: Going straight to implementation
def calculate_capacity(game, participants):
    return game.max_participants - len(participants)
```

### ❌ Testing Implementation Details

```python
# WRONG: Testing how it works instead of what it does
def test_calculate_capacity_calls_len():
    with patch('builtins.len') as mock_len:
        calculate_capacity(game, participants)
        mock_len.assert_called_once()
```

### ❌ Separating Testing Phase from Implementation

```python
# WRONG: Plan structure
Phase 1: Implement all features
Phase 2: Write tests for features  # ❌ TOO LATE
```

## Benefits of TDD

- **Prevents bugs**: Tests catch issues before code is written
- **Better design**: Writing tests first leads to better interfaces
- **Documentation**: Tests serve as executable documentation
- **Confidence**: Refactoring is safe with comprehensive tests
- **Coverage**: TDD naturally achieves high test coverage
- **Focus**: Writing tests first clarifies requirements

## Summary

**TDD is required for all testable languages (Python, TypeScript/JavaScript, etc.):**

1. **RED**: Create stub with NotImplementedError → Write tests with REAL assertions marked xfail/failing
2. **GREEN**: Implement minimal solution → Remove xfail/failing markers (DO NOT modify test assertions)
3. **REFACTOR**: Improve code → Keep tests passing

**Key principles:**

- Tests contain correct assertions from day 1
- Only xfail/failing markers are removed after implementation
- Test assertions are NEVER modified between RED and GREEN phases
- Every task plan MUST integrate tests adjacent to implementation, never as a separate later phase
- TDD applies to writing **new or enhanced production code** — NOT to tasks whose primary work is adding tests for already-implemented code
- TDD only applies to languages with unit testing frameworks (not bash, Dockerfiles, YAML, etc.)
