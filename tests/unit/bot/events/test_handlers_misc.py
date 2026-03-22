# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Unit tests for remaining EventHandlers error and branch paths.

Covers _handle_clone_confirmation, _send_dm, _update_message_for_player_removal,
_handle_status_transition_due, _is_transition_ready, _handle_post_transition_actions,
and _archive_game_announcement.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.events.handlers import EventHandlers
from shared.messaging.events import NotificationDueEvent
from shared.utils.status_transitions import GameStatus


@pytest.fixture
def bot():
    return MagicMock(spec=discord.Client)


@pytest.fixture
def handlers(bot):
    return EventHandlers(bot)


def _db_ctx(mock_db=None):
    if mock_db is None:
        mock_db = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_db, ctx


def _forbidden():
    resp = MagicMock()
    resp.status = 403
    resp.reason = "Forbidden"
    return discord.Forbidden(resp, "DMs disabled")


def _http_exception(status=500):
    resp = MagicMock()
    resp.status = status
    resp.reason = "Error"
    return discord.HTTPException(resp, "server error")


def _not_found():
    resp = MagicMock()
    resp.status = 404
    resp.reason = "Not Found"
    return discord.NotFound(resp, "unknown message")


# ---------------------------------------------------------------------------
# _handle_clone_confirmation
# ---------------------------------------------------------------------------


def _clone_event():
    return NotificationDueEvent(
        game_id=uuid4(),
        notification_type="clone_confirmation",
        participant_id=str(uuid4()),
    )


def _clone_db_ctx(mock_schedule):
    """Build a DB context that returns mock_schedule for the schedule query."""
    mock_db = AsyncMock()
    schedule_result = MagicMock()
    schedule_result.scalar_one_or_none.return_value = mock_schedule
    mock_db.execute = AsyncMock(return_value=schedule_result)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_db, ctx


async def test_clone_confirmation_discord_forbidden(handlers):
    """discord.Forbidden from user.send() is handled without raising."""
    event = _clone_event()
    mock_game = MagicMock()
    mock_game.title = "Test Game"
    mock_participant = MagicMock()
    mock_participant.user.discord_id = "123456789012345678"

    mock_schedule = MagicMock()
    mock_schedule.id = str(uuid4())
    mock_schedule.action_time.timestamp.return_value = 1234567890.0

    _, ctx = _clone_db_ctx(mock_schedule)

    mock_user = AsyncMock()
    mock_user.send = AsyncMock(side_effect=_forbidden())
    handlers.bot.fetch_user = AsyncMock(return_value=mock_user)

    with (
        patch.object(
            handlers,
            "_fetch_join_notification_data",
            new=AsyncMock(return_value=(mock_game, mock_participant)),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
        patch("services.bot.events.handlers.get_bot_publisher"),
        patch("services.bot.events.handlers.CloneConfirmationView"),
        patch("services.bot.events.handlers.DMFormats"),
    ):
        await handlers._handle_clone_confirmation(event)


async def test_clone_confirmation_discord_http_exception(handlers):
    """discord.HTTPException from user.send() is handled without raising."""
    event = _clone_event()
    mock_game = MagicMock()
    mock_game.title = "Test Game"
    mock_participant = MagicMock()
    mock_participant.user.discord_id = "123456789012345678"

    mock_schedule = MagicMock()
    mock_schedule.id = str(uuid4())
    mock_schedule.action_time.timestamp.return_value = 1234567890.0

    _, ctx = _clone_db_ctx(mock_schedule)

    mock_user = AsyncMock()
    mock_user.send = AsyncMock(side_effect=_http_exception())
    handlers.bot.fetch_user = AsyncMock(return_value=mock_user)

    with (
        patch.object(
            handlers,
            "_fetch_join_notification_data",
            new=AsyncMock(return_value=(mock_game, mock_participant)),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
        patch("services.bot.events.handlers.get_bot_publisher"),
        patch("services.bot.events.handlers.CloneConfirmationView"),
        patch("services.bot.events.handlers.DMFormats"),
    ):
        await handlers._handle_clone_confirmation(event)


async def test_clone_confirmation_outer_exception_is_caught(handlers):
    """Exception propagating from inside the outer try is logged without raising."""
    event = _clone_event()
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_fetch_join_notification_data",
            new=AsyncMock(side_effect=RuntimeError("db failure")),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_clone_confirmation(event)


# ---------------------------------------------------------------------------
# _send_dm
# ---------------------------------------------------------------------------


async def test_send_dm_user_not_found_returns_false(handlers):
    """Returns False when Discord API cannot find the user."""
    mock_discord_api = MagicMock()
    mock_discord_api.fetch_user = AsyncMock(return_value=None)
    with patch("services.bot.events.handlers.get_discord_client", return_value=mock_discord_api):
        result = await handlers._send_dm("123456789012345678", "hello")
    assert result is False


async def test_send_dm_bot_fetch_returns_none_returns_false(handlers):
    """Returns False when the bot cannot resolve the user object."""
    mock_discord_api = MagicMock()
    mock_discord_api.fetch_user = AsyncMock(return_value=MagicMock())
    handlers.bot.fetch_user = AsyncMock(return_value=None)
    with patch("services.bot.events.handlers.get_discord_client", return_value=mock_discord_api):
        result = await handlers._send_dm("123456789012345678", "hello")
    assert result is False


async def test_send_dm_discord_forbidden_returns_false(handlers):
    """Returns False when Discord raises Forbidden (DMs disabled)."""
    mock_discord_api = MagicMock()
    mock_discord_api.fetch_user = AsyncMock(return_value=MagicMock())
    mock_user = AsyncMock()
    mock_user.send = AsyncMock(side_effect=_forbidden())
    handlers.bot.fetch_user = AsyncMock(return_value=mock_user)
    with patch("services.bot.events.handlers.get_discord_client", return_value=mock_discord_api):
        result = await handlers._send_dm("123456789012345678", "hello")
    assert result is False


async def test_send_dm_discord_http_exception_returns_false(handlers):
    """Returns False when Discord raises an HTTP error."""
    mock_discord_api = MagicMock()
    mock_discord_api.fetch_user = AsyncMock(return_value=MagicMock())
    mock_user = AsyncMock()
    mock_user.send = AsyncMock(side_effect=_http_exception())
    handlers.bot.fetch_user = AsyncMock(return_value=mock_user)
    with patch("services.bot.events.handlers.get_discord_client", return_value=mock_discord_api):
        result = await handlers._send_dm("123456789012345678", "hello")
    assert result is False


# ---------------------------------------------------------------------------
# _update_message_for_player_removal
# ---------------------------------------------------------------------------


async def test_update_message_discord_not_found_is_handled(handlers):
    """discord.NotFound raised during message.edit() is handled without propagating."""
    mock_game = MagicMock()
    mock_channel = MagicMock()
    mock_message = AsyncMock()
    mock_message.edit = AsyncMock(side_effect=_not_found())
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=mock_game),
        ),
        patch.object(
            handlers,
            "_fetch_channel_and_message",
            new=AsyncMock(return_value=(mock_channel, mock_message)),
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=(None, MagicMock(), MagicMock())),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._update_message_for_player_removal("g1", "m1", "c1")


async def test_update_message_general_exception_is_handled(handlers):
    """General exception raised during message.edit() is handled without propagating."""
    mock_game = MagicMock()
    mock_channel = MagicMock()
    mock_message = AsyncMock()
    mock_message.edit = AsyncMock(side_effect=RuntimeError("network error"))
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_get_game_with_participants",
            new=AsyncMock(return_value=mock_game),
        ),
        patch.object(
            handlers,
            "_fetch_channel_and_message",
            new=AsyncMock(return_value=(mock_channel, mock_message)),
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=(None, MagicMock(), MagicMock())),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._update_message_for_player_removal("g1", "m1", "c1")


# ---------------------------------------------------------------------------
# _handle_status_transition_due
# ---------------------------------------------------------------------------


async def test_status_transition_due_execution_exception_is_caught(handlers):
    """Exception during status transition execution is logged without propagating."""
    data = {
        "game_id": str(uuid4()),
        "target_status": "IN_PROGRESS",
        "transition_time": "2026-03-16T00:00:00+00:00",
    }
    _, ctx = _db_ctx()
    with (
        patch.object(
            handlers,
            "_get_game_with_participants",
            new=AsyncMock(side_effect=RuntimeError("db error")),
        ),
        patch("services.bot.events.handlers.get_db_session", return_value=ctx),
    ):
        await handlers._handle_status_transition_due(data)


# ---------------------------------------------------------------------------
# _is_transition_ready
# ---------------------------------------------------------------------------


def test_is_transition_ready_same_status_returns_false(handlers):
    """Returns False when game is already at the target status."""
    game = MagicMock()
    game.status = "SCHEDULED"
    with patch("services.bot.events.handlers.is_valid_transition", return_value=True):
        result = handlers._is_transition_ready(game, "game-id", "SCHEDULED")
    assert result is False


# ---------------------------------------------------------------------------
# _handle_post_transition_actions
# ---------------------------------------------------------------------------


async def test_handle_post_transition_actions_triggers_archive(handlers):
    """Calls _archive_game_announcement when target status is ARCHIVED."""
    game = MagicMock()
    with patch.object(handlers, "_archive_game_announcement", new=AsyncMock()) as mock_archive:
        await handlers._handle_post_transition_actions(game, GameStatus.ARCHIVED.value)
    mock_archive.assert_called_once_with(game)


async def test_handle_post_transition_actions_sends_rewards_dm_on_completed(handlers):
    """Sends rewards reminder DM to host when game completes with no rewards set."""
    game = MagicMock()
    game.remind_host_rewards = True
    game.rewards = None
    game.title = "Test Game"
    game.id = str(uuid4())
    game.host = MagicMock()
    game.host.discord_id = "123456789"

    with (
        patch.object(handlers, "_send_dm", new=AsyncMock()) as mock_dm,
        patch.object(handlers, "_archive_game_announcement", new=AsyncMock()),
        patch("services.bot.events.handlers.get_config") as mock_cfg,
    ):
        mock_cfg.return_value.frontend_url = "https://example.com"
        await handlers._handle_post_transition_actions(game, GameStatus.COMPLETED.value)

    mock_dm.assert_called_once()
    call_args = mock_dm.call_args
    assert call_args[0][0] == "123456789"
    assert "Test Game" in call_args[0][1]
    assert "rewards" in call_args[0][1].lower()


async def test_handle_post_transition_actions_no_dm_when_rewards_set(handlers):
    """Does not send DM when game already has rewards set."""
    game = MagicMock()
    game.remind_host_rewards = True
    game.rewards = "Gold coins for everyone"
    game.host = MagicMock()

    with patch.object(handlers, "_send_dm", new=AsyncMock()) as mock_dm:
        await handlers._handle_post_transition_actions(game, GameStatus.COMPLETED.value)

    mock_dm.assert_not_called()


async def test_handle_post_transition_actions_no_dm_when_flag_false(handlers):
    """Does not send DM when remind_host_rewards is False."""
    game = MagicMock()
    game.remind_host_rewards = False
    game.rewards = None
    game.host = MagicMock()

    with patch.object(handlers, "_send_dm", new=AsyncMock()) as mock_dm:
        await handlers._handle_post_transition_actions(game, GameStatus.COMPLETED.value)

    mock_dm.assert_not_called()


async def test_handle_post_transition_actions_non_terminal_status_skips_archive(
    handlers,
):
    """Does not call archive for statuses that are not COMPLETED or ARCHIVED."""
    game = MagicMock()
    game.remind_host_rewards = False
    game.rewards = None

    with patch.object(handlers, "_archive_game_announcement", new=AsyncMock()) as mock_archive:
        await handlers._handle_post_transition_actions(game, GameStatus.IN_PROGRESS.value)

    mock_archive.assert_not_called()


# ---------------------------------------------------------------------------
# _archive_game_announcement
# ---------------------------------------------------------------------------


async def test_archive_announcement_no_bot_channel_returns_early(handlers):
    """Returns early when the bot cannot access the announcement channel."""
    game = MagicMock()
    game.message_id = "123456"
    game.channel = MagicMock()
    game.channel.channel_id = "111222333"
    game.archive_channel_id = None
    with patch.object(handlers, "_get_bot_channel", new=AsyncMock(return_value=None)):
        await handlers._archive_game_announcement(game)


async def test_archive_announcement_message_not_found_is_handled(handlers):
    """discord.NotFound during message deletion is handled without propagating."""
    game = MagicMock()
    game.message_id = "123456"
    game.channel = MagicMock()
    game.channel.channel_id = "111222333"
    game.archive_channel_id = None

    mock_channel = AsyncMock()
    mock_channel.fetch_message = AsyncMock(side_effect=_not_found())

    with patch.object(handlers, "_get_bot_channel", new=AsyncMock(return_value=mock_channel)):
        await handlers._archive_game_announcement(game)


async def test_archive_announcement_delete_exception_is_handled(handlers):
    """General exception during message deletion is handled without propagating."""
    game = MagicMock()
    game.message_id = "123456"
    game.channel = MagicMock()
    game.channel.channel_id = "111222333"
    game.archive_channel_id = None

    mock_message = AsyncMock()
    mock_message.delete = AsyncMock(side_effect=RuntimeError("connection reset"))
    mock_channel = AsyncMock()
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)

    with patch.object(handlers, "_get_bot_channel", new=AsyncMock(return_value=mock_channel)):
        await handlers._archive_game_announcement(game)


# ---------------------------------------------------------------------------
# _archive_game_announcement — player @mention logic (rewards)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True)
async def test_archive_announcement_with_rewards_mentions_confirmed_players(handlers):
    """Archive post content contains <@uid> for each confirmed real player when rewards are set."""
    player_id = "111222333444555666"
    game = MagicMock()
    game.message_id = "999"
    game.channel = MagicMock()
    game.channel.channel_id = "aaa"
    game.archive_channel_id = "bbb"
    game.archive_channel = MagicMock()
    game.archive_channel.channel_id = "ccc"
    game.rewards = "magic sword"
    game.participants = []
    game.max_players = 4

    mock_active_channel = AsyncMock()
    mock_active_channel.fetch_message = AsyncMock(return_value=AsyncMock())
    mock_archive_channel = AsyncMock()

    mock_partitioned = MagicMock()
    mock_partitioned.confirmed_real_user_ids = [player_id]

    with (
        patch.object(
            handlers,
            "_get_bot_channel",
            new=AsyncMock(side_effect=[mock_active_channel, mock_archive_channel]),
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=("<@role_123>", "embed", "view")),
        ),
        patch(
            "services.bot.events.handlers.partition_participants",
            return_value=mock_partitioned,
        ),
    ):
        await handlers._archive_game_announcement(game)

    call_kwargs = mock_archive_channel.send.call_args.kwargs
    assert f"<@{player_id}>" in call_kwargs["content"]


@pytest.mark.xfail(strict=True)
async def test_archive_announcement_with_rewards_ignores_role_mention_content(handlers):
    """Archive post ignores role-mention content from _create_game_announcement when rewards set."""
    player_id = "777888999000111222"
    game = MagicMock()
    game.message_id = "999"
    game.channel = MagicMock()
    game.channel.channel_id = "aaa"
    game.archive_channel_id = "bbb"
    game.archive_channel = MagicMock()
    game.archive_channel.channel_id = "ccc"
    game.rewards = "gold"
    game.participants = []
    game.max_players = 4

    mock_active_channel = AsyncMock()
    mock_active_channel.fetch_message = AsyncMock(return_value=AsyncMock())
    mock_archive_channel = AsyncMock()

    mock_partitioned = MagicMock()
    mock_partitioned.confirmed_real_user_ids = [player_id]

    with (
        patch.object(
            handlers,
            "_get_bot_channel",
            new=AsyncMock(side_effect=[mock_active_channel, mock_archive_channel]),
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=("<@&role_999>", "embed", "view")),
        ),
        patch(
            "services.bot.events.handlers.partition_participants",
            return_value=mock_partitioned,
        ),
    ):
        await handlers._archive_game_announcement(game)

    call_kwargs = mock_archive_channel.send.call_args.kwargs
    assert "<@&role_999>" not in (call_kwargs.get("content") or "")
    assert f"<@{player_id}>" in call_kwargs["content"]


@pytest.mark.xfail(strict=True)
async def test_archive_announcement_without_rewards_sends_no_content(handlers):
    """Archive post content is None when game.rewards is not set."""
    game = MagicMock()
    game.message_id = "999"
    game.channel = MagicMock()
    game.channel.channel_id = "aaa"
    game.archive_channel_id = "bbb"
    game.archive_channel = MagicMock()
    game.archive_channel.channel_id = "ccc"
    game.rewards = None
    game.participants = []
    game.max_players = 4

    mock_active_channel = AsyncMock()
    mock_active_channel.fetch_message = AsyncMock(return_value=AsyncMock())
    mock_archive_channel = AsyncMock()

    with (
        patch.object(
            handlers,
            "_get_bot_channel",
            new=AsyncMock(side_effect=[mock_active_channel, mock_archive_channel]),
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=("content", "embed", "view")),
        ),
    ):
        await handlers._archive_game_announcement(game)

    mock_archive_channel.send.assert_awaited_once_with(content=None, embed="embed")


@pytest.mark.xfail(strict=True)
async def test_archive_announcement_with_rewards_no_confirmed_players(handlers):
    """Archive post content is None when rewards are set but no confirmed real players exist."""
    game = MagicMock()
    game.message_id = "999"
    game.channel = MagicMock()
    game.channel.channel_id = "aaa"
    game.archive_channel_id = "bbb"
    game.archive_channel = MagicMock()
    game.archive_channel.channel_id = "ccc"
    game.rewards = "treasure"
    game.participants = []
    game.max_players = 4

    mock_active_channel = AsyncMock()
    mock_active_channel.fetch_message = AsyncMock(return_value=AsyncMock())
    mock_archive_channel = AsyncMock()

    mock_partitioned = MagicMock()
    mock_partitioned.confirmed_real_user_ids = []

    with (
        patch.object(
            handlers,
            "_get_bot_channel",
            new=AsyncMock(side_effect=[mock_active_channel, mock_archive_channel]),
        ),
        patch.object(
            handlers,
            "_create_game_announcement",
            new=AsyncMock(return_value=("content", "embed", "view")),
        ),
        patch(
            "services.bot.events.handlers.partition_participants",
            return_value=mock_partitioned,
        ),
    ):
        await handlers._archive_game_announcement(game)

    mock_archive_channel.send.assert_awaited_once_with(content=None, embed="embed")
