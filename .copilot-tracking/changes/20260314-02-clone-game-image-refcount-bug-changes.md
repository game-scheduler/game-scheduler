<!-- markdownlint-disable-file -->

# Changes: Fix clone_game image reference count bug

## Summary

Add `increment_image_ref` to `image_storage.py` and call it in `clone_game()` so that cloning a game with images correctly increments `reference_count` for each image.

## Added

- `shared/services/image_storage.py` — added `increment_image_ref(db, image_id)`: no-op for `None`, otherwise selects image with `FOR UPDATE` and increments `reference_count` by 1
- `tests/unit/shared/services/test_image_storage.py` — added three unit tests for `increment_image_ref`: `test_increment_image_ref_none_is_noop`, `test_increment_image_ref_increments_count`, `test_increment_image_ref_uses_for_update`

## Modified

- `tests/integration/services/api/services/test_game_image_integration.py` — added `CloneGameRequest`/`CarryoverOption` import and new test `test_clone_game_increments_image_refcounts` verifying clone increments refcounts to 2, source-delete brings to 1, clone-delete removes both images

## Removed
