<!-- markdownlint-disable-file -->

# Task Details: Fix clone_game image reference count bug

## Research Reference

**Source Research**: #file:../research/20260314-02-clone-game-image-refcount-bug-research.md

## Phase 1: Add `increment_image_ref` helper

### Task 1.1: Add stub for `increment_image_ref` in `shared/services/image_storage.py`

Add a stub function after `release_image` (currently ending around line 120) that raises `NotImplementedError`. The signature must match the final interface.

- **Files**:
  - `shared/services/image_storage.py` — append after `release_image`
- **Success**:
  - Function exists, is callable, and raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260314-02-clone-game-image-refcount-bug-research.md (Lines 50-58) — recommended approach and signature
- **Dependencies**:
  - None

### Task 1.2: Write unit tests for `increment_image_ref` marked xfail (RED)

Add tests to `tests/unit/shared/services/test_image_storage.py` following the existing mock-session patterns. Mark all new tests with `@pytest.mark.xfail(strict=True, reason="increment_image_ref not yet implemented")`. Write real assertions against expected behavior — do not assert `NotImplementedError`.

Tests to write:

- `test_increment_image_ref_none_is_noop`: calling with `image_id=None` returns without executing any DB query
- `test_increment_image_ref_increments_count`: with a valid `image_id`, `reference_count` is incremented by 1 and `flush` is called
- `test_increment_image_ref_uses_for_update`: the SELECT uses `with_for_update()`

- **Files**:
  - `tests/unit/shared/services/test_image_storage.py` — append after existing tests
- **Success**:
  - All new tests are collected and xfail (not xpass, not error)
- **Research References**:
  - #file:../research/20260314-02-clone-game-image-refcount-bug-research.md (Lines 50-58) — helper spec
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Implement `increment_image_ref` and remove xfail markers (GREEN)

Replace the stub with a full implementation. Follow the same `SELECT ... FOR UPDATE` pattern as `release_image`. Must be a no-op when `image_id` is `None`. Remove the `@pytest.mark.xfail` decorators added in Task 1.2 — do NOT modify the test assertions.

- **Files**:
  - `shared/services/image_storage.py` — replace stub with implementation
  - `tests/unit/shared/services/test_image_storage.py` — remove xfail markers only
- **Success**:
  - All three new tests pass (no longer xfail)
  - Calling with `None` returns without touching the DB
  - Calling with a valid `image_id` increments `reference_count` by 1 and flushes
- **Research References**:
  - #file:../research/20260314-02-clone-game-image-refcount-bug-research.md (Lines 50-58) — implementation spec
- **Dependencies**:
  - Task 1.2 complete

## Phase 2: Fix `clone_game()`

### Task 2.1: Add `increment_image_ref` to the `image_storage` import in `services/api/services/games.py`

Update line 63:

```python
# before
from shared.services.image_storage import release_image, store_image

# after
from shared.services.image_storage import increment_image_ref, release_image, store_image
```

- **Files**:
  - `services/api/services/games.py` — line 63
- **Success**:
  - Import resolves without error
- **Dependencies**:
  - Task 1.3 complete

### Task 2.2: Call `increment_image_ref` for both image IDs in `clone_game()`

After the `GameSession` object is constructed (lines 789–809) and before `self.db.flush()` (line 811), add:

```python
await increment_image_ref(self.db, source_game.thumbnail_id)
await increment_image_ref(self.db, source_game.banner_image_id)
```

- **Files**:
  - `services/api/services/games.py` — after line 809, before `self.db.flush()`
- **Success**:
  - After cloning a game with images, `reference_count` for each image is 2
  - After cloning a game with `thumbnail_id=None` and `banner_image_id=None`, no DB error occurs
- **Research References**:
  - #file:../research/20260314-02-clone-game-image-refcount-bug-research.md (Lines 34-48) — bug root cause
  - #file:../research/20260314-02-clone-game-image-refcount-bug-research.md (Lines 60-82) — implementation guidance
- **Dependencies**:
  - Task 2.1 complete

## Phase 3: Add integration test

### Task 3.1: Add `test_clone_game_increments_image_refcounts` to `test_game_image_integration.py`

Add a new test after the last existing test (`test_delete_shared_image_keeps_image_until_all_refs_gone` at line 497). The test should:

1. Create a game with a thumbnail and a banner image (both distinct), commit
2. Assert `reference_count == 1` for each image
3. Clone the game, commit
4. Assert `reference_count == 2` for each image
5. Delete the source game, commit
6. Assert `reference_count == 1` for each image and both images still exist
7. Delete the clone game, commit
8. Assert both `GameImage` rows are gone

Follow the patterns established by `test_delete_shared_image_keeps_image_until_all_refs_gone` for querying `GameImage` rows directly. No xfail markers — integration tests do not use TDD.

- **Files**:
  - `tests/integration/services/api/services/test_game_image_integration.py` — append after existing tests
- **Success**:
  - Test passes against real DB
  - Test confirms the bug is fixed (would fail on the unfixed code)
- **Research References**:
  - #file:../research/20260314-02-clone-game-image-refcount-bug-research.md (Lines 60-82) — test scenario
- **Dependencies**:
  - Phase 2 complete

## Dependencies

- PostgreSQL available (integration test DB)
- Existing integration test infrastructure in `test_game_image_integration.py`

## Success Criteria

- `increment_image_ref` is implemented in `image_storage.py`
- `clone_game()` calls it for both image IDs
- Unit tests pass for `increment_image_ref`
- Integration test passes and would fail on the pre-fix code
