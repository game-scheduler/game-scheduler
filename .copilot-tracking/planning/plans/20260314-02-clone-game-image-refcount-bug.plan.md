---
applyTo: '.copilot-tracking/changes/20260314-02-clone-game-image-refcount-bug-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Fix clone_game image reference count bug

## Overview

Add `increment_image_ref` to `image_storage.py` and call it in `clone_game()` so that cloning a game with images correctly increments `reference_count` for each image.

## Objectives

- Ensure `game_images.reference_count` equals the number of `game_sessions` rows pointing at each image
- Prevent premature image deletion when one of two games sharing an image is deleted
- Add an integration test covering the full clone-then-delete lifecycle with images

## Research Summary

### Project Files

- `shared/services/image_storage.py` — `store_image()` and `release_image()` pattern to follow; new `increment_image_ref()` goes here
- `services/api/services/games.py` — `clone_game()` at line 741; bug at lines 808–809; import at line 63
- `tests/unit/shared/services/test_image_storage.py` — unit tests for `image_storage`; xfail tests go here
- `tests/integration/services/api/services/test_game_image_integration.py` — existing image lifecycle tests; new integration test goes here

### External References

- #file:../research/20260314-02-clone-game-image-refcount-bug-research.md — full bug analysis, root cause, and implementation guidance

## Implementation Checklist

### [x] Phase 1: Add `increment_image_ref` helper (TDD)

- [x] Task 1.1: Add stub for `increment_image_ref` in `shared/services/image_storage.py`
  - Details: .copilot-tracking/planning/details/20260314-02-clone-game-image-refcount-bug-details.md (Lines 11-23)

- [x] Task 1.2: Write unit tests marked xfail in `tests/unit/shared/services/test_image_storage.py` (RED)
  - Details: .copilot-tracking/planning/details/20260314-02-clone-game-image-refcount-bug-details.md (Lines 24-42)

- [x] Task 1.3: Implement `increment_image_ref` and remove xfail markers (GREEN)
  - Details: .copilot-tracking/planning/details/20260314-02-clone-game-image-refcount-bug-details.md (Lines 43-58)

### [x] Phase 2: Fix `clone_game()`

- [x] Task 2.1: Add `increment_image_ref` to the `image_storage` import in `services/api/services/games.py`
  - Details: .copilot-tracking/planning/details/20260314-02-clone-game-image-refcount-bug-details.md (Lines 61-79)

- [x] Task 2.2: Call `increment_image_ref` for both image IDs in `clone_game()`
  - Details: .copilot-tracking/planning/details/20260314-02-clone-game-image-refcount-bug-details.md (Lines 80-99)

### [x] Phase 3: Add integration test

- [x] Task 3.1: Add `test_clone_game_increments_image_refcounts` to `test_game_image_integration.py`
  - Details: .copilot-tracking/planning/details/20260314-02-clone-game-image-refcount-bug-details.md (Lines 102-130)

## Dependencies

- SQLAlchemy async session (`SELECT ... FOR UPDATE`)
- Existing `GameImage` model in `shared/models/game_image.py`
- Existing integration test fixtures in `test_game_image_integration.py`

## Success Criteria

- `increment_image_ref` correctly increments `reference_count` and is a no-op for `None`
- Unit tests for `increment_image_ref` pass
- Cloning a game with images results in `reference_count == 2` for each image
- Deleting the source game decrements to 1 and the image still exists
- Deleting the clone decrements to 0 and the image row is deleted
- All existing tests continue to pass
