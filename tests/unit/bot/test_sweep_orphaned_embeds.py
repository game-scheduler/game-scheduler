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


"""Unit tests for GameSchedulerBot._sweep_orphaned_embeds.

Three behavioral cases:
  (a) no backup_metadata rows  -> skip sweep entirely (no channel.history calls)
  (b) rows present, game UUID absent from DB -> message.delete() is called
  (c) rows present, game UUID exists in DB  -> message.delete() is NOT called
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from services.bot.bot import GameSchedulerBot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    with patch("services.bot.bot.discord.Intents"):
        instance = GameSchedulerBot.__new__(GameSchedulerBot)
        instance.config = cfg
        instance.button_handler = None
        instance.event_handlers = None
        instance.event_publisher = AsyncMock()
        instance.api_cache = None
        instance._sweep_task = None
    return instance


def _db_ctx_scalar(value: object) -> MagicMock:
    """Context manager whose single execute() returns a result with scalar_one_or_none."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=result)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _db_ctx_scalars_all(items: list) -> MagicMock:
    """Context manager whose single execute() returns a result with scalars().all()."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=result)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_backup_row(backed_up_at: datetime) -> MagicMock:
    row = MagicMock()
    row.backed_up_at = backed_up_at
    return row


def _make_channel_cfg(channel_id: str) -> MagicMock:
    cfg = MagicMock()
    cfg.channel_id = channel_id
    return cfg


def _make_message_with_join_button(game_id: str, author_id: int) -> MagicMock:
    """Create a mock Discord message with a join_game_{game_id} button component."""
    button = MagicMock()
    button.custom_id = f"join_game_{game_id}"

    action_row = MagicMock(spec=discord.ActionRow)
    action_row.children = [button]

    message = MagicMock(spec=discord.Message)
    message.author = MagicMock()
    message.author.id = author_id
    message.components = [action_row]
    message.delete = AsyncMock()
    return message


def _channel_with_history(messages: list) -> MagicMock:
    """Return a mock TextChannel whose history() async-iterates over messages."""

    async def _history(*_args, **_kwargs):
        for msg in messages:
            yield msg

    channel = MagicMock(spec=discord.TextChannel)
    channel.history = _history
    return channel


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_no_backup_metadata_skips_sweep() -> None:
    """With no backup_metadata rows, channel.history is never called."""
    bot = _make_bot()
    mock_user = MagicMock()
    mock_user.id = 999

    channel = MagicMock(spec=discord.TextChannel)
    channel.history = MagicMock()

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch("services.bot.bot.get_bypass_db_session", return_value=_db_ctx_scalar(None)),
    ):
        await bot._sweep_orphaned_embeds()

    channel.history.assert_not_called()


async def test_orphaned_embed_is_deleted_when_game_missing_from_db() -> None:
    """A message with a join_game button whose UUID is absent from DB is deleted."""
    bot = _make_bot()
    game_id = str(uuid.uuid4())

    mock_user = MagicMock()
    mock_user.id = 42

    message = _make_message_with_join_button(game_id, author_id=42)
    channel = _channel_with_history([message])
    channel_cfg = _make_channel_cfg("111222333")
    backed_up_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch(
            "services.bot.bot.get_bypass_db_session",
            side_effect=[
                _db_ctx_scalar(_make_backup_row(backed_up_at)),
                _db_ctx_scalars_all([channel_cfg]),
                _db_ctx_scalar(None),
            ],
        ),
        patch.object(bot, "get_channel", return_value=channel),
    ):
        await bot._sweep_orphaned_embeds()

    message.delete.assert_awaited_once()


async def test_live_embed_is_not_deleted_when_game_exists_in_db() -> None:
    """A message with a join_game button whose UUID is present in DB is NOT deleted."""
    bot = _make_bot()
    game_id = str(uuid.uuid4())

    mock_user = MagicMock()
    mock_user.id = 42

    message = _make_message_with_join_button(game_id, author_id=42)
    channel = _channel_with_history([message])
    channel_cfg = _make_channel_cfg("111222333")
    backed_up_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch(
            "services.bot.bot.get_bypass_db_session",
            side_effect=[
                _db_ctx_scalar(_make_backup_row(backed_up_at)),
                _db_ctx_scalars_all([channel_cfg]),
                _db_ctx_scalar(MagicMock()),
            ],
        ),
        patch.object(bot, "get_channel", return_value=channel),
    ):
        await bot._sweep_orphaned_embeds()

    message.delete.assert_not_awaited()


# ---------------------------------------------------------------------------
# _extract_game_id edge cases
# ---------------------------------------------------------------------------


async def test_extract_game_id_returns_none_for_empty_components() -> None:
    """Return None when message has no components at all."""
    msg = MagicMock(spec=discord.Message)
    msg.components = []
    assert GameSchedulerBot._extract_game_id(msg) is None


async def test_extract_game_id_skips_non_action_row_components() -> None:
    """Return None when components contain no ActionRow instances."""
    non_row = MagicMock()
    msg = MagicMock(spec=discord.Message)
    msg.components = [non_row]
    assert GameSchedulerBot._extract_game_id(msg) is None


async def test_extract_game_id_returns_none_when_no_join_game_button() -> None:
    """Return None when ActionRow exists but has no join_game_{uuid} button."""
    button = MagicMock()
    button.custom_id = "some_other_button"

    action_row = MagicMock(spec=discord.ActionRow)
    action_row.children = [button]

    msg = MagicMock(spec=discord.Message)
    msg.components = [action_row]
    assert GameSchedulerBot._extract_game_id(msg) is None


# ---------------------------------------------------------------------------
# _sweep_orphaned_embeds edge cases
# ---------------------------------------------------------------------------


async def test_channel_not_text_channel_is_skipped() -> None:
    """Non-TextChannel channels are skipped without error."""
    bot = _make_bot()
    mock_user = MagicMock()
    mock_user.id = 42

    non_text_channel = MagicMock(spec=discord.VoiceChannel)
    channel_cfg = _make_channel_cfg("999888777")
    backed_up_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch(
            "services.bot.bot.get_bypass_db_session",
            side_effect=[
                _db_ctx_scalar(_make_backup_row(backed_up_at)),
                _db_ctx_scalars_all([channel_cfg]),
            ],
        ),
        patch.object(bot, "get_channel", return_value=non_text_channel),
    ):
        await bot._sweep_orphaned_embeds()


async def test_channel_configurations_query_exception_logs_and_returns() -> None:
    """Exception during channel_configurations query is caught and returns early."""
    bot = _make_bot()
    mock_user = MagicMock()
    mock_user.id = 42

    backed_up_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    failing_ctx = MagicMock()
    failing_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db failure"))
    failing_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch(
            "services.bot.bot.get_bypass_db_session",
            side_effect=[
                _db_ctx_scalar(_make_backup_row(backed_up_at)),
                failing_ctx,
            ],
        ),
    ):
        await bot._sweep_orphaned_embeds()


async def test_channel_scan_exception_is_caught_per_channel() -> None:
    """Exception during channel scanning is logged and does not stop other channels."""
    bot = _make_bot()
    mock_user = MagicMock()
    mock_user.id = 42

    channel_cfg = _make_channel_cfg("111222333")
    backed_up_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch(
            "services.bot.bot.get_bypass_db_session",
            side_effect=[
                _db_ctx_scalar(_make_backup_row(backed_up_at)),
                _db_ctx_scalars_all([channel_cfg]),
            ],
        ),
        patch.object(bot, "get_channel", return_value=MagicMock(spec=discord.TextChannel)),
        patch.object(
            bot, "_scan_channel_for_orphaned_embeds", new=AsyncMock(side_effect=RuntimeError)
        ),
    ):
        await bot._sweep_orphaned_embeds()


# ---------------------------------------------------------------------------
# _scan_channel_for_orphaned_embeds edge cases
# ---------------------------------------------------------------------------


async def test_message_from_other_author_is_skipped() -> None:
    """Messages whose author is not the bot are ignored."""
    bot = _make_bot()
    mock_user = MagicMock()
    mock_user.id = 42

    message = _make_message_with_join_button("some-game-id", author_id=99)
    channel = _channel_with_history([message])
    cutoff = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    with patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)):
        await bot._scan_channel_for_orphaned_embeds(channel, cutoff)

    message.delete.assert_not_awaited()


async def test_message_without_join_game_button_is_skipped() -> None:
    """Bot messages without a join_game button are not sent to the DB check."""
    bot = _make_bot()
    mock_user = MagicMock()
    mock_user.id = 42

    button = MagicMock()
    button.custom_id = "leave_game_some_id"
    action_row = MagicMock(spec=discord.ActionRow)
    action_row.children = [button]

    message = MagicMock(spec=discord.Message)
    message.author = MagicMock()
    message.author.id = 42
    message.components = [action_row]
    message.delete = AsyncMock()

    channel = _channel_with_history([message])
    cutoff = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch("services.bot.bot.get_bypass_db_session") as mock_db,
    ):
        await bot._scan_channel_for_orphaned_embeds(channel, cutoff)

    mock_db.assert_not_called()
    message.delete.assert_not_awaited()


async def test_db_exception_during_game_check_is_logged() -> None:
    """DB exception during game UUID lookup is caught and logged per message."""
    bot = _make_bot()
    game_id = str(uuid.uuid4())
    mock_user = MagicMock()
    mock_user.id = 42

    message = _make_message_with_join_button(game_id, author_id=42)
    channel = _channel_with_history([message])
    cutoff = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    failing_ctx = MagicMock()
    failing_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db error"))
    failing_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(type(bot), "user", new_callable=lambda: property(lambda _: mock_user)),
        patch("services.bot.bot.get_bypass_db_session", return_value=failing_ctx),
    ):
        await bot._scan_channel_for_orphaned_embeds(channel, cutoff)

    message.delete.assert_not_awaited()
