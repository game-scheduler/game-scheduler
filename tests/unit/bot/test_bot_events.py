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

import discord
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
    return instance


def _make_channel(
    channel_id: int,
    guild_id: int,
    name: str = "general",
    guild_channels: list | None = None,
    send_messages: bool = True,
) -> MagicMock:
    ch = MagicMock(spec=discord.TextChannel)
    ch.id = channel_id
    ch.name = name
    ch.type = MagicMock()
    ch.type.value = 0
    perms = MagicMock(spec=discord.Permissions)
    perms.send_messages = send_messages
    ch.permissions_for = MagicMock(return_value=perms)
    guild = MagicMock()
    guild.id = guild_id
    guild.me = MagicMock()
    guild.channels = guild_channels if guild_channels is not None else [ch]
    ch.guild = guild
    return ch


def _make_role(
    role_id: int, guild_id: int, name: str = "Member", guild_roles: list | None = None
) -> MagicMock:
    role = MagicMock()
    role.id = role_id
    role.name = name
    role.color = MagicMock()
    role.color.value = 0
    role.position = 1
    role.managed = False
    role.permissions = MagicMock()
    role.permissions.value = 0
    guild = MagicMock()
    guild.id = guild_id
    guild.roles = guild_roles if guild_roles is not None else [role]
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


async def test_on_guild_channel_create_writes_channel_and_list(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_create writes discord:channel:{id} and rewrites the full channel list."""
    channel = _make_channel(1001, 111)
    expected_channels = [{"id": str(channel.id), "name": channel.name, "type": channel.type.value}]
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_create(channel)

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_channel(str(channel.id)),
        {"name": channel.name},
        CacheTTL.DISCORD_CHANNEL,
    )
    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_channels(str(channel.guild.id)),
        expected_channels,
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )
    mock_redis.delete.assert_not_called()


async def test_on_guild_channel_update_writes_channel_and_list(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_update writes discord:channel:{id} and rewrites the full channel list."""
    before = _make_channel(1001, 111, "old-name")
    after = _make_channel(1001, 111, "new-name")
    expected_channels = [{"id": str(after.id), "name": after.name, "type": after.type.value}]
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_update(before, after)

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_channel(str(after.id)),
        {"name": after.name},
        CacheTTL.DISCORD_CHANNEL,
    )
    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_channels(str(after.guild.id)),
        expected_channels,
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )
    mock_redis.delete.assert_not_called()


async def test_on_guild_channel_delete_removes_channel_and_rewrites_list(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_delete deletes discord:channel:{id} and rewrites the channel list."""
    remaining = _make_channel(1002, 111, "other")
    channel = _make_channel(1001, 111, "deleted", guild_channels=[remaining])
    expected_channels = [
        {"id": str(remaining.id), "name": remaining.name, "type": remaining.type.value}
    ]
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_delete(channel)

    mock_redis.delete.assert_called_once_with(CacheKeys.discord_channel(str(channel.id)))
    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_guild_channels(str(channel.guild.id)),
        expected_channels,
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )


async def test_on_guild_channel_create_skips_channel_key_when_no_send_messages(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_create skips writing discord:channel:{id} when bot lacks send_messages."""
    channel = _make_channel(1001, 111, send_messages=False)
    channel.guild.channels = []
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_create(channel)

    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_guild_channels(str(channel.guild.id)),
        [],
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )


async def test_on_guild_channel_update_deletes_channel_key_when_no_send_messages(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_channel_update removes discord:channel:{id} when bot loses send_messages."""
    before = _make_channel(1001, 111, "general")
    after = _make_channel(1001, 111, "restricted", send_messages=False)
    after.guild.channels = []
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_channel_update(before, after)

    mock_redis.delete.assert_called_once_with(CacheKeys.discord_channel(str(after.id)))
    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_guild_channels(str(after.guild.id)),
        [],
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )


# ---------------------------------------------------------------------------
# Role event handlers
# ---------------------------------------------------------------------------


async def test_on_guild_role_create_writes_roles_list(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_role_create rewrites discord:guild_roles:{guild_id} from gateway state."""
    role = _make_role(2001, 111)
    expected_roles = [
        {
            "id": str(role.id),
            "name": role.name,
            "color": role.color.value,
            "position": role.position,
            "managed": role.managed,
            "permissions": role.permissions.value,
        }
    ]
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_role_create(role)

    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_guild_roles(str(role.guild.id)),
        expected_roles,
        CacheTTL.DISCORD_GUILD_ROLES,
    )
    mock_redis.delete.assert_not_called()


async def test_on_guild_role_update_writes_roles_list(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_role_update rewrites discord:guild_roles:{guild_id} from gateway state."""
    before = _make_role(2001, 111, "old-role")
    after = _make_role(2001, 111, "new-role")
    expected_roles = [
        {
            "id": str(after.id),
            "name": after.name,
            "color": after.color.value,
            "position": after.position,
            "managed": after.managed,
            "permissions": after.permissions.value,
        }
    ]
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_role_update(before, after)

    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_guild_roles(str(after.guild.id)),
        expected_roles,
        CacheTTL.DISCORD_GUILD_ROLES,
    )
    mock_redis.delete.assert_not_called()


async def test_on_guild_role_delete_writes_roles_list(
    bot: GameSchedulerBot, mock_redis: AsyncMock
) -> None:
    """on_guild_role_delete rewrites discord:guild_roles:{guild_id} with the role removed."""
    remaining = _make_role(2002, 111, "remaining")
    role = _make_role(2001, 111, "deleted", guild_roles=[remaining])
    expected_roles = [
        {
            "id": str(remaining.id),
            "name": remaining.name,
            "color": remaining.color.value,
            "position": remaining.position,
            "managed": remaining.managed,
            "permissions": remaining.permissions.value,
        }
    ]
    with patch(
        "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ):
        await bot.on_guild_role_delete(role)

    mock_redis.set_json.assert_called_once_with(
        CacheKeys.discord_guild_roles(str(role.guild.id)),
        expected_roles,
        CacheTTL.DISCORD_GUILD_ROLES,
    )
    mock_redis.delete.assert_not_called()
