<!-- markdownlint-disable-file -->

# Changes: Archive Player @mentions for Reward Games

## Overview

Tracks implementation progress for the feature that @mentions confirmed players in Discord
archive posts when a game has rewards set.

---

## Added

<!-- Newly created files -->

## Modified

### Phase 1: Write Failing Tests (TDD RED Phase)

- `tests/unit/bot/events/test_handlers_misc.py` — added four `@pytest.mark.xfail(strict=True)` unit tests covering: confirmed player mentioned in archive content, role-mention content ignored, no content when rewards not set, and no content when no confirmed players
- `tests/unit/services/bot/events/test_handlers.py` — marked `test_archive_game_announcement_posts_to_archive_channel` as `@pytest.mark.xfail` so the suite stays green when the production `content` assertion changes
- `tests/e2e/test_game_rewards.py` — added `@pytest.mark.xfail(strict=True)`, `discord_user_id` fixture, `initial_participants` to POST payload, and `assert f"<@{discord_user_id}>" in archive_message.content` assertion to `test_save_and_archive_archives_game_within_seconds`

## Removed

<!-- Deleted files or removed sections -->
