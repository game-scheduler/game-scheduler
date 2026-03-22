<!-- markdownlint-disable-file -->

# Task Details: Archive Player @mentions for Reward Games

## Research Reference

**Source Research**: #file:../research/20260322-01-archive-reward-player-mentions-research.md

## Phase 1: Write Failing Tests (TDD RED Phase)

### Task 1.1: Add xfail unit tests in test_handlers_misc.py

Add four new unit tests to `tests/unit/bot/events/test_handlers_misc.py`, each decorated with
`@pytest.mark.xfail(strict=True)`. Insert after the existing error-path tests around line 460.

Tests to add:

1. `test_archive_announcement_with_rewards_mentions_confirmed_players` — `game.rewards` set,
   confirmed player present → `archive_channel.send` is awaited with `content` containing `<@player_id>`
2. `test_archive_announcement_with_rewards_ignores_role_mention_content` — even when
   `_create_game_announcement` returns role-mention content, archive post uses only player mention content
3. `test_archive_announcement_without_rewards_sends_no_content` — `game.rewards = None` →
   `archive_channel.send` called with `content=None`
4. `test_archive_announcement_with_rewards_no_confirmed_players` — rewards set but
   `partition_participants` returns empty `confirmed_real_user_ids` → `content=None`

- **Files**:
  - `tests/unit/bot/events/test_handlers_misc.py` — add xfail tests after line ~460
- **Success**:
  - All four tests collected and reported as `XFAIL`
  - `uv run pytest tests/unit/bot/events/test_handlers_misc.py -v` shows these as XFAIL
- **Research References**:
  - #file:../research/20260322-01-archive-reward-player-mentions-research.md (Lines 127–153) — unit test names and expected behavior
- **Dependencies**:
  - None; first task in phase

### Task 1.2: Mark existing archive test as xfail in test_handlers.py

In `tests/unit/services/bot/events/test_handlers.py`, the test
`test_archive_game_announcement_posts_to_archive_channel` currently asserts:

```python
mock_archive_channel.send.assert_awaited_once_with(content="content", embed="embed")
```

Mark it with `@pytest.mark.xfail(reason="content assertion will break when role mentions removed from archive post")`.
This keeps the suite green when the production change lands — the test will XFAIL, not break the run.

- **Files**:
  - `tests/unit/services/bot/events/test_handlers.py` — mark test at lines 616–751
- **Success**:
  - Test is marked xfail and suite still runs cleanly (currently XPASS — acceptable with non-strict xfail)
- **Research References**:
  - #file:../research/20260322-01-archive-reward-player-mentions-research.md (Lines 104–114) — existing test assertion that must change
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Modify e2e test to add player mention assertion

In `tests/e2e/test_game_rewards.py`, modify `test_save_and_archive_archives_game_within_seconds`
(starting at line 108). Three changes needed:

1. Add `discord_user_id` to the test's fixture parameter list
2. Add `"initial_participants": json.dumps([f"<@{discord_user_id}>"])` to the `POST /api/v1/games` payload
3. After the existing rewards-embed assertion, add:

```python
assert f"<@{discord_user_id}>" in archive_message.content, (
    f"Archive post should @mention confirmed player. Got: {archive_message.content!r}"
)
```

Mark the test function with `@pytest.mark.xfail(strict=True)` so it fails before the production
change and passes after.

- **Files**:
  - `tests/e2e/test_game_rewards.py` — modify test at line ~108
- **Success**:
  - Modified test is `xfail(strict=True)` and reflects the full assertion
- **Research References**:
  - #file:../research/20260322-01-archive-reward-player-mentions-research.md (Lines 115–131) — e2e test modification pattern
- **Dependencies**:
  - None; can be done in parallel with Tasks 1.1 and 1.2

### Task 1.4: Run unit tests to confirm RED / xfail state

Run the unit test suite to confirm the new xfail tests are in their expected state before
making any production changes.

```bash
uv run pytest tests/unit/bot/events/test_handlers_misc.py tests/unit/services/bot/events/test_handlers.py -v
```

- **Success**:
  - New tests (Task 1.1): reported as `XFAIL`
  - Existing marked test (Task 1.2): reported as `XPASS` — acceptable with non-strict xfail

## Phase 2: Implement Production Code (TDD GREEN Phase)

### Task 2.1: Implement player @mention logic in \_archive_game_announcement

In `services/bot/events/handlers.py`, modify `_archive_game_announcement` (~line 1256).
Replace the current `content` passthrough from `_create_game_announcement` with:

```python
_content, embed, _view = await self._create_game_announcement(game)
# Build player mentions for archive post, ignoring role mentions
content = None
if game.rewards:
    player_mentions = " ".join(
        f"<@{uid}>" for uid in sorted(
            partition_participants(
                game.participants, game.max_players
            ).confirmed_real_user_ids
        )
    )
    if player_mentions:
        content = player_mentions
await archive_channel.send(content=content, embed=embed)
```

Key points:

- `_content` (role mentions) is discarded (prefix `_` suppresses unused-variable lint)
- `partition_participants` is already imported at module level in `handlers.py`
- IDs are sorted for determinism
- `content` falls back to `None` when no confirmed real users exist

- **Files**:
  - `services/bot/events/handlers.py` — modify `_archive_game_announcement` at ~line 1256
- **Success**:
  - The four new unit tests now pass (xfail markers will become XPASS — remove them in Phase 3)
  - `test_archive_game_announcement_posts_to_archive_channel` now fails as expected (XFAIL)
- **Research References**:
  - #file:../research/20260322-01-archive-reward-player-mentions-research.md (Lines 71–100) — complete example implementation
- **Dependencies**:
  - Phase 1 fully complete

## Phase 3: Clean Up and Verify (TDD REFACTOR Phase)

### Task 3.1: Remove xfail markers and fix existing test assertion

After production implementation, clean up all temporary xfail markers:

1. Remove all `@pytest.mark.xfail` decorators added in Phase 1 (Tasks 1.1, 1.2, 1.3)
2. Update the assertion in `test_archive_game_announcement_posts_to_archive_channel`:

```python
# Change from:
mock_archive_channel.send.assert_awaited_once_with(content="content", embed="embed")
# Change to:
mock_archive_channel.send.assert_awaited_once_with(content=None, embed="embed")
```

- **Files**:
  - `tests/unit/bot/events/test_handlers_misc.py` — remove xfail decorators
  - `tests/unit/services/bot/events/test_handlers.py` — remove xfail marker, fix assertion
  - `tests/e2e/test_game_rewards.py` — remove xfail decorator
- **Success**:
  - All four new tests PASS
  - `test_archive_game_announcement_posts_to_archive_channel` PASS with `content=None`
- **Research References**:
  - #file:../research/20260322-01-archive-reward-player-mentions-research.md (Lines 104–114) — existing assertion to update
- **Dependencies**:
  - Task 2.1 complete

### Task 3.2: Run full unit test suite and confirm all pass

```bash
uv run pytest tests/unit/ -v
```

- **Success**:
  - Zero failures, zero errors
  - No xfail markers remaining in the modified test files

## Dependencies

- `partition_participants` — already imported in `services/bot/events/handlers.py`
- Discord message `content` string — surfaced as `message.content` via discord.py

## Success Criteria

- Archive post `content` = space-separated `<@uid>` for confirmed players when rewards are set
- No role mentions in archive post under any condition
- Waitlist and placeholder participants are NOT mentioned
- `content=None` when rewards not set or no confirmed players
- All existing and new tests pass without overrides
