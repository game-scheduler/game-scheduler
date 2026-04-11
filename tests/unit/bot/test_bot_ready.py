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


"""Unit tests for GameSchedulerBot.on_ready Redis cache rebuild from gateway data."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from services.bot.bot import GameSchedulerBot
from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL


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
    instance._refresh_listener_started = True
    return instance


def _make_role(role_id: int, name: str) -> MagicMock:
    role = MagicMock()
    role.id = role_id
    role.name = name
    role.color = MagicMock()
    role.color.value = 255
    role.position = 2
    role.managed = False
    return role


def _make_channel(channel_id: int, name: str) -> MagicMock:
    ch = MagicMock()
    ch.id = channel_id
    ch.name = name
    ch.type = MagicMock()
    ch.type.value = 0
    return ch


def _make_guild(guild_id: int, name: str) -> MagicMock:
    guild = MagicMock()
    guild.id = guild_id
    guild.name = name
    guild.channels = [_make_channel(1001, "general")]
    guild.roles = [_make_role(2001, "Member")]
    return guild


@pytest.fixture
def bot() -> GameSchedulerBot:
    return _make_bot()


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.set_json = AsyncMock(return_value=True)
    return redis


async def _call_on_ready(bot: GameSchedulerBot, mock_redis: AsyncMock) -> MagicMock:
    guild = _make_guild(111, "Test Guild")
    mock_user = MagicMock()
    mock_user.id = 999
    with (
        patch.object(type(bot), "guilds", new_callable=PropertyMock, return_value=[guild]),
        patch.object(type(bot), "user", new_callable=PropertyMock, return_value=mock_user),
        patch(
            "services.bot.bot.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
        patch.object(bot, "_recover_pending_workers", new_callable=AsyncMock),
        patch.object(bot, "_trigger_sweep", new_callable=AsyncMock),
        patch("services.bot.bot.tracer"),
        patch("services.bot.bot.os.getenv", return_value=None),
    ):
        await bot.on_ready()
    return guild


async def test_on_ready_writes_guild_key(bot: GameSchedulerBot, mock_redis: AsyncMock) -> None:
    """on_ready writes discord:guild:{id} for each connected guild."""
    guild = await _call_on_ready(bot, mock_redis)

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild(str(guild.id)),
        {"id": str(guild.id), "name": guild.name},
        CacheTTL.DISCORD_GUILD,
    )


async def test_on_ready_writes_guild_channels_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_ready writes discord:guild_channels:{id} with the channel list for each guild."""
    guild = await _call_on_ready(bot, mock_redis)
    ch = guild.channels[0]
    expected = [{"id": str(ch.id), "name": ch.name, "type": ch.type.value}]

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_channels(str(guild.id)),
        expected,
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )


async def test_on_ready_writes_channel_key(bot: GameSchedulerBot, mock_redis: AsyncMock) -> None:
    """on_ready writes discord:channel:{id} for every channel in every guild."""
    guild = await _call_on_ready(bot, mock_redis)
    ch = guild.channels[0]

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_channel(str(ch.id)),
        {"name": ch.name},
        CacheTTL.DISCORD_CHANNEL,
    )


async def test_on_ready_writes_guild_roles_key(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_ready writes discord:guild_roles:{id} with correct role dict shape."""
    guild = await _call_on_ready(bot, mock_redis)
    role = guild.roles[0]
    expected = [
        {
            "id": str(role.id),
            "name": role.name,
            "color": role.color.value,
            "position": role.position,
            "managed": role.managed,
        }
    ]

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_roles(str(guild.id)),
        expected,
        CacheTTL.DISCORD_GUILD_ROLES,
    )
