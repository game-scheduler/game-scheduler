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


"""Unit tests for GameSchedulerBot gateway event handlers (channel and role)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.bot import GameSchedulerBot
from shared.cache.keys import CacheKeys


def _make_bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    instance = GameSchedulerBot.__new__(GameSchedulerBot)
    instance.config = cfg
    instance.button_handler = None
    instance.event_handlers = None
    instance.event_publisher = None
    instance.api_cache = None
    instance._sweep_task = None
    return instance


def _make_channel(channel_id: int, guild_id: int, name: str = "general") -> MagicMock:
    ch = MagicMock()
    ch.id = channel_id
    ch.name = name
    guild = MagicMock()
    guild.id = guild_id
    ch.guild = guild
    return ch


def _make_role(role_id: int, guild_id: int, name: str = "Member") -> MagicMock:
    role = MagicMock()
    role.id = role_id
    role.name = name
    guild = MagicMock()
    guild.id = guild_id
    role.guild = guild
    return role


@pytest.fixture
def bot() -> GameSchedulerBot:
    return _make_bot()


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.set_json = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


# ---------------------------------------------------------------------------
# Channel event handlers
# ---------------------------------------------------------------------------


async def test_on_guild_channel_create_writes_channel_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_create writes discord:channel:{id} with channel name."""
    channel = _make_channel(1001, 111)
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_create(channel)

    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_channel(str(channel.id)),
        {"name": channel.name},
        None,
    )


async def test_on_guild_channel_create_invalidates_guild_channels_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_create deletes discord:guild_channels:{guild_id}."""
    channel = _make_channel(1001, 111)
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_create(channel)

    mock_redis.delete.assert_called_once_with(
        CacheKeys.discord_guild_channels(str(channel.guild.id))
    )


async def test_on_guild_channel_update_writes_channel_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_update writes discord:channel:{id} with the updated channel name."""
    before = _make_channel(1001, 111, "old-name")
    after = _make_channel(1001, 111, "new-name")
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_update(before, after)

    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_channel(str(after.id)),
        {"name": after.name},
        None,
    )


async def test_on_guild_channel_update_invalidates_guild_channels_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_update deletes discord:guild_channels:{guild_id}."""
    before = _make_channel(1001, 111, "old-name")
    after = _make_channel(1001, 111, "new-name")
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_update(before, after)

    mock_redis.delete.assert_called_once_with(CacheKeys.discord_guild_channels(str(after.guild.id)))


async def test_on_guild_channel_delete_removes_channel_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_delete deletes discord:channel:{id}."""
    channel = _make_channel(1001, 111)
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_delete(channel)

    mock_redis.delete.assert_any_call(CacheKeys.discord_channel(str(channel.id)))


async def test_on_guild_channel_delete_invalidates_guild_channels_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_delete deletes discord:guild_channels:{guild_id}."""
    channel = _make_channel(1001, 111)
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_delete(channel)

    mock_redis.delete.assert_any_call(CacheKeys.discord_guild_channels(str(channel.guild.id)))


# ---------------------------------------------------------------------------
# Role event handlers
# ---------------------------------------------------------------------------


async def test_on_guild_role_create_invalidates_guild_roles_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_role_create deletes discord:guild_roles:{guild_id}."""
    role = _make_role(2001, 111)
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_role_create(role)

    mock_redis.delete.assert_called_once_with(CacheKeys.discord_guild_roles(str(role.guild.id)))


async def test_on_guild_role_update_invalidates_guild_roles_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_role_update deletes discord:guild_roles:{guild_id}."""
    before = _make_role(2001, 111, "old-role")
    after = _make_role(2001, 111, "new-role")
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_role_update(before, after)

    mock_redis.delete.assert_called_once_with(CacheKeys.discord_guild_roles(str(after.guild.id)))


async def test_on_guild_role_delete_invalidates_guild_roles_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_role_delete deletes discord:guild_roles:{guild_id}."""
    role = _make_role(2001, 111)
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_role_delete(role)

    mock_redis.delete.assert_called_once_with(CacheKeys.discord_guild_roles(str(role.guild.id)))
