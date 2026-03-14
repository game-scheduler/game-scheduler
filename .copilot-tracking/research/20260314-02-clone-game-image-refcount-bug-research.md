<!-- markdownlint-disable-file -->

# Task Research Notes: clone_game does not increment image reference counts

## Research Executed

### File Analysis

- `services/api/services/games.py` — `clone_game()` (line ~790–810)
  - Directly assigns `thumbnail_id=source_game.thumbnail_id` and `banner_image_id=source_game.banner_image_id` to the new `GameSession` object
  - Never calls `store_image()` for either field
  - `store_image()` is the only mechanism that increments `reference_count`; it deduplicates by SHA256 hash and bumps the count on the existing row if the same content is already present
- `shared/services/image_storage.py`
  - `store_image()`: finds existing row by `content_hash` with `SELECT ... FOR UPDATE`, increments `reference_count`, returns existing `id` — or creates new row with `reference_count=1`
  - `release_image()`: decrements `reference_count`; deletes row when count reaches zero
  - No triggers, no automatic reference management — purely application-managed
- `shared/models/game.py`
  - `thumbnail_id` and `banner_image_id`: `ForeignKey("game_images.id", ondelete="SET NULL")`
  - `ON DELETE SET NULL` direction: if the `game_images` row is deleted, the FK column on the game is nulled — protects games from dangling pointers, has no effect when game is deleted

### Code Search Results

- No test in `tests/unit/services/test_clone_game.py` covers cloning a game that has a non-None `thumbnail_id` or `banner_image_id`; both are set to `None` in the test fixture (line 67–68)
- No test in `tests/integration/test_clone_game_endpoint.py` creates games with images before cloning
- `test_delete_game_releases_images` and `test_delete_shared_image_keeps_image_until_all_refs_gone` in `tests/integration/services/api/services/test_game_image_integration.py` cover deletion but not cloning

### Project Conventions

- Standards referenced: `store_image()` / `release_image()` pattern in `shared/services/image_storage.py`
- TDD applicable (Python)

## Key Discoveries

### The Bug

`clone_game()` copies the source game's `thumbnail_id` and `banner_image_id` UUID values directly onto the new `GameSession` row. This creates a second database row referencing the same `game_images` entry without calling `store_image()`, so `reference_count` stays at 1 even though two games now point at the image.

### Consequence

When either game is deleted via `release_image()`:

- Count is decremented from 1 to 0
- Image row is deleted
- The other game's FK column is nulled by `ON DELETE SET NULL` — the image silently disappears from the still-live game

This is currently masked because cancellation only sets `status=CANCELLED` and never actually deletes de game row (so `release_image()` is never called in practice today). Once the delete-on-cancel work is implemented, this bug becomes reachable.

### Correct Fix

`clone_game()` must call `store_image()` for each non-None image ID. However, `store_image()` takes `image_data` bytes and `mime_type` — not an existing ID. The fix requires either:

1. **Fetch then re-store**: load the `GameImage` row by ID, then pass its `image_data` and `mime_type` to `store_image()` — this increments the count and returns the same ID (due to hash deduplication)
2. **Direct increment**: skip `store_image()` and instead directly increment `reference_count` on the existing `GameImage` row by ID — simpler, avoids reading large blob data

Option 2 is preferable: it avoids loading potentially large binary image data just to hash it again, and it is a single targeted `UPDATE` by primary key.

## Recommended Approach

**Direct reference count increment** in `clone_game()` for each non-None image ID, using a helper analogous to `store_image()` / `release_image()` in `shared/services/image_storage.py`.

Add `async def increment_image_ref(db, image_id)` to `image_storage.py`:

- `SELECT ... FOR UPDATE` on `GameImage` by `image_id`
- `image.reference_count += 1` + `flush`
- No-op if `image_id` is `None`

Call it in `clone_game()` immediately after the `GameSession` is constructed, before `db.flush()`.

## Implementation Guidance

- **Objectives**: Ensure `game_images.reference_count` correctly reflects the number of `game_sessions` rows pointing at each image
- **Key Tasks**:
  1. Add `increment_image_ref(db, image_id)` to `shared/services/image_storage.py`
  2. Call it twice in `clone_game()` — once for `thumbnail_id`, once for `banner_image_id`
  3. Add integration test in `tests/integration/services/api/services/test_game_image_integration.py`: clone a game with thumbnail/banner, assert `reference_count == 2`; delete source game, assert count drops to 1 and image still exists; delete clone, assert image is deleted
- **Test level**: Integration only — the bug is purely in application logic and DB state; no Discord interaction is involved. The existing `test_game_image_integration.py` already follows this pattern (real DB, mocked Discord/RabbitMQ) for `create_game`, `update_game`, and `delete_game`. An e2e test would add full-stack cost with no additional coverage of the actual fault.
- **Dependencies**: Should be implemented alongside or after the delete-on-cancel work (makes the bug reachable); safe to implement independently
- **Success Criteria**:
  - Cloning a game with images results in `reference_count` incremented for each image
  - Deleting either game decrements the count correctly
  - No image is deleted while another game still references it
  - TDD: integration test written first against `test_game_image_integration.py`
