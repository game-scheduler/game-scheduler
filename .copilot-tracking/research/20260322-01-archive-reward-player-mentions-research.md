<!-- markdownlint-disable-file -->

# Task Research Notes: Archive Player @mentions for Reward Games

## Research Executed

### File Analysis

- `services/bot/events/handlers.py`
  - `_archive_game_announcement` (~line 1256): handles archive; optionally posts to archive channel and deletes original
  - `_handle_post_transition_actions` (~line 1233): calls `_archive_game_announcement` when `target_status == ARCHIVED`
  - `_create_game_announcement` (~line 1313): builds `(content, embed, view)` — `content` contains role mentions from `game.notify_role_ids`, or `None`
  - `partition_participants` already imported at module-level
- `services/bot/formatters/game_message.py`
  - `format_game_announcement` builds role-mention `content` from `notify_role_ids` → `<@&role_id>` or `@everyone`
  - `game.rewards` is `str | None`; truthy when rewards text present
- `shared/utils/participant_sorting.py`
  - `partition_participants(participants, max_players)` returns `PartitionedParticipants`
  - `.confirmed_real_user_ids: set[str]` — Discord IDs of confirmed (non-waitlist) players
  - Placeholder participants (no `.user`) are automatically excluded
- `shared/models/participant.py`
  - `ParticipantType.HOST_ADDED = 8000`, `ParticipantType.SELF_ADDED = 24000`
  - Sort key: `(position_type, position, joined_at)`

### Code Search Results

- Unit tests for `_archive_game_announcement`
  - `tests/unit/bot/events/test_handlers_misc.py` (lines 410–460): all error-path tests live here
  - `tests/unit/services/bot/events/test_handlers.py` (lines 616–751): happy-path tests, `sample_game` fixture
- E2E archive tests
  - `tests/e2e/test_game_archive.py`: full archive flow, no rewards, checks embed footer + no interactive controls
  - `tests/e2e/test_game_rewards.py` — contains three tests:
    - `test_save_and_archive_archives_game_within_seconds` (line 108): archive+rewards flow but **no participants added**; only checks `||rewards||` spoiler in embed
    - `test_rewards_reminder_dm_sent_on_completion_when_empty` (line 217): DM to host
    - `test_discord_embed_shows_rewards_spoiler` (line 286): embed field validation
  - None of these add a real user as a participant, so none can verify player mentions
  - New test goes **alongside** these, not as a modification to any of them
- Discord `Message.content` is a plain string and directly readable via REST API (confirmed by `test_player_removal.py` pattern and `test_channel_mentions.py`)
- Adding a real user as participant: pass `"initial_participants": json.dumps([f"<@{discord_user_id}>"])` at game creation (pattern from `test_player_removal.py`)
- Archive message `content` field: `archive_message.content` — contains raw text including `<@user_id>` strings

### Project Conventions

- TDD applies (Python)
- Stub (`NotImplementedError`) + `xfail(strict=True)` for new feature tests before implementation
- Unit tests for new archive behavior: `tests/unit/bot/events/test_handlers_misc.py`
- E2E tests: `tests/e2e/test_game_rewards.py` (new test alongside existing archive test)

## Key Discoveries

### Clarification: No Role Mentions in Archive Posts

The user confirmed archive posts should NOT carry role mentions. This is a **behavior change** — currently `_archive_game_announcement` passes the `content` from `_create_game_announcement` directly to `archive_channel.send()`, which includes `game.notify_role_ids` role mentions. The new implementation must:

1. Ignore the `content` from `_create_game_announcement` for the archive post
2. Build a new `content` containing only the confirmed player `<@user_id>` mentions (when `game.rewards` is set)

### How to Verify a User Was @mentioned (E2E)

Discord message `content` is a plain-text string directly returned by the Discord REST API. It contains the raw mention strings (`<@123456789>`). The `discord.py` library surfaces this as `message.content`.

This is already verified in the codebase at `tests/e2e/test_player_removal.py` (DM content) and `tests/e2e/test_channel_mentions.py` (embed field content). For the archive post, we check `archive_message.content` for the presence of `<@{discord_user_id}>`.

There is no separate "notification" system for @mentions — Discord's own notification system fires when a user is mentioned in a message they have access to. From the test's perspective, verifying `<@user_id>` is in `archive_message.content` is the definitive programmatic check.

### Complete Example: \_archive_game_announcement implementation

```python
async def _archive_game_announcement(self, game: GameSession) -> None:
    if not game.message_id or not game.channel:
        return

    channel = await self._get_bot_channel(game.channel.channel_id)
    if not channel:
        return

    if game.archive_channel_id and game.archive_channel:
        archive_channel = await self._get_bot_channel(game.archive_channel.channel_id)
        if archive_channel:
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

    try:
        message = await channel.fetch_message(int(game.message_id))
        await message.delete()
    except discord.NotFound:
        logger.warning(
            "Original announcement not found for archive deletion: %s",
            game.message_id,
        )
    except Exception as e:
        logger.exception("Failed to delete archived announcement %s: %s", game.message_id, e)
```

Key changes:

- `_content` (role mentions) is discarded
- New `content` is built from player IDs only, scoped to `game.rewards` being set
- Sorted for determinism

### Archive Channel Send: Existing Tests That Need Updating

The test `test_archive_game_announcement_posts_to_archive_channel` in `tests/unit/services/bot/events/test_handlers.py` currently asserts:

```python
mock_archive_channel.send.assert_awaited_once_with(content="content", embed="embed")
```

With `_create_game_announcement` returning `("content", "embed", "view")`. After the change, the role-mention content is discarded, so that assertion must change. This test does not set `game.rewards`, meaning the archive post `content` should be `None`.

### E2E Test Pattern: Adding a Real User as Participant

From `test_player_removal.py`:

```python
"initial_participants": json.dumps([f"<@{discord_user_id}>"]),
```

This adds the `DISCORD_USER_ID` bot as a confirmed participant at game creation time.

### E2E Detection: Verifying Mention in Archive Post

```python
assert f"<@{discord_user_id}>" in archive_message.content, (
    f"Archive post should @mention confirmed player. Got: {archive_message.content!r}"
)
```

`archive_message.content` surfaces the raw Discord content string, which contains `<@user_id>` mention tokens exactly as sent.

### E2E Test Location

Modify `test_save_and_archive_archives_game_within_seconds` in `tests/e2e/test_game_rewards.py` — it already performs the full archive+rewards flow. The only additions needed are:

1. Add `discord_user_id` to the fixture parameter list
2. Add `"initial_participants": json.dumps([f"<@{discord_user_id}>"])` to the `POST /api/v1/games` call
3. Add an assertion after the existing rewards embed check: `assert f"<@{discord_user_id}>" in archive_message.content`

This avoids running the expensive full-stack archive flow a second time in a separate test.

## Recommended Approach

**Two-part change:**

### Part 1 — Production code (`_archive_game_announcement`)

Discard the `content` from `_create_game_announcement`. When `game.rewards` is set, build `content` from `partition_participants(...).confirmed_real_user_ids`, sorted, formatted as `<@uid>`. Pass this as `content` to `archive_channel.send()`.

### Part 2 — Tests

**Unit tests** (new, in `test_handlers_misc.py`):

1. `test_archive_announcement_with_rewards_mentions_confirmed_players` — `game.rewards` set, confirmed player present → `content` contains `<@player_id>`; xfail before implementation
2. `test_archive_announcement_with_rewards_ignores_role_mention_content` — even when `_create_game_announcement` would return role-mention content, archive post uses only player mentions; xfail before implementation
3. `test_archive_announcement_without_rewards_sends_no_content` — `game.rewards = None` → `content=None`; xfail before implementation
4. `test_archive_announcement_with_rewards_no_confirmed_players` — rewards set but no confirmed real users → `content=None`; xfail before implementation

**Update existing unit test** (`test_handlers.py`):

- `test_archive_game_announcement_posts_to_archive_channel`: the game has no `rewards`, so `content` should be `None` not `"content"` after the change. Mark `xfail` first, then fix the assertion.

**E2E test** (modify existing `test_save_and_archive_archives_game_within_seconds` in `test_game_rewards.py`):

- Add `discord_user_id` fixture parameter
- Add `initial_participants` to game creation
- Add `archive_message.content` assertion after the existing embed check
- No new test function needed — avoids running the expensive archive flow twice

## Implementation Guidance

- **Objectives**: When a game with rewards is archived to an archive channel, @mention the confirmed players (not waitlist, not roles) in the archive post `content`
- **Key Tasks**:
  1. Write failing unit tests (xfail) in `tests/unit/bot/events/test_handlers_misc.py`
  2. Mark existing `test_archive_game_announcement_posts_to_archive_channel` as xfail (it will break)
  3. Write the failing e2e test (xfail) in `tests/e2e/test_game_rewards.py`
  4. Run unit tests to confirm xfail state (RED phase)
  5. Implement in `services/bot/events/handlers.py::_archive_game_announcement`
  6. Remove xfail markers, verify all tests pass
- **Dependencies**: `partition_participants` (already imported in `handlers.py`)
- **Success Criteria**:
  - Archive post `content` = space-separated `<@uid>` for each confirmed player when rewards present
  - No role mentions in archive post under any condition
  - Waitlist and placeholder participants are NOT mentioned
  - When rewards not set, `content=None`
  - All existing tests pass
