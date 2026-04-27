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


"""Unit tests for GameSchedulerBot.on_ready."""

from contextlib import ExitStack
from unittest.mock import ANY, AsyncMock, MagicMock, PropertyMock, patch

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
    role.permissions = MagicMock()
    role.permissions.value = 8  # ADMINISTRATOR flag
    return role


def _make_channel(channel_id: int, name: str) -> MagicMock:
    ch = MagicMock(spec=discord.TextChannel)
    ch.id = channel_id
    ch.name = name
    ch.type = MagicMock()
    ch.type.value = 0
    perms = MagicMock(spec=discord.Permissions)
    perms.send_messages = True
    ch.permissions_for = MagicMock(return_value=perms)
    return ch


def _make_guild(guild_id: int, name: str) -> MagicMock:
    guild = MagicMock()
    guild.id = guild_id
    guild.name = name
    guild.owner_id = 9999
    ch = _make_channel(1001, "general")
    guild.channels = [ch]
    guild.me = MagicMock()
    guild.roles = [_make_role(2001, "Member")]
    return guild


@pytest.fixture
def bot() -> GameSchedulerBot:
    return _make_bot()


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.set_json = AsyncMock(return_value=True)
    mock_client = AsyncMock()
    mock_client.scan = AsyncMock(return_value=(0, []))
    mock_client.delete = AsyncMock()
    redis._client = mock_client
    return redis


@pytest.fixture
def on_ready_env(bot, mock_redis):
    """Apply all external patches needed to call on_ready, yielding the mock guild.

    Tests that need an additional patch (e.g. repopulate_all) add it inside
    the test body with a normal `with patch(...)` block — those patches nest
    inside the ones applied here.
    """
    guild = _make_guild(111, "Test Guild")
    mock_user = MagicMock()
    mock_user.id = 999

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(type(bot), "guilds", new_callable=PropertyMock, return_value=[guild])
        )
        stack.enter_context(
            patch.object(type(bot), "user", new_callable=PropertyMock, return_value=mock_user)
        )
        stack.enter_context(
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            )
        )
        stack.enter_context(patch.object(bot, "_recover_pending_workers", new_callable=AsyncMock))
        stack.enter_context(patch.object(bot, "_trigger_sweep", new_callable=AsyncMock))
        stack.enter_context(patch.object(bot, "_sweep_orphaned_embeds", new_callable=AsyncMock))
        stack.enter_context(patch("services.bot.bot.tracer"))
        stack.enter_context(patch("services.bot.bot.os.getenv", return_value=None))
        stack.enter_context(
            patch(
                "services.bot.bot.sync_guilds_from_gateway",
                new_callable=AsyncMock,
                return_value={"new_guilds": 0, "new_channels": 0},
            )
        )
        stack.enter_context(
            patch(
                "services.bot.bot.get_db_session",
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=AsyncMock()),
                    __aexit__=AsyncMock(return_value=None),
                ),
            )
        )
        yield guild


# ---------------------------------------------------------------------------
# Delegation tests — each would fail if that step were removed from on_ready.
# ---------------------------------------------------------------------------


async def test_on_ready_calls_rebuild_redis_from_gateway(bot, mock_redis, on_ready_env) -> None:
    """on_ready calls _rebuild_redis_from_gateway to populate guild/channel/role cache."""
    with (
        patch.object(bot, "_rebuild_redis_from_gateway", new_callable=AsyncMock) as mock_rebuild,
        patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock),
    ):
        await bot.on_ready()

    mock_rebuild.assert_awaited_once()


async def test_on_ready_calls_sync_guilds_from_gateway(bot, mock_redis, on_ready_env) -> None:
    """on_ready calls sync_guilds_from_gateway after _rebuild_redis_from_gateway."""
    with (
        patch("services.bot.bot.sync_guilds_from_gateway", new_callable=AsyncMock) as mock_sync,
        patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock),
    ):
        await bot.on_ready()

    mock_sync.assert_awaited_once()


async def test_on_ready_calls_recover_pending_workers(bot, mock_redis, on_ready_env) -> None:
    """on_ready calls _recover_pending_workers."""
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    bot._recover_pending_workers.assert_awaited_once()


async def test_on_ready_calls_trigger_sweep(bot, mock_redis, on_ready_env) -> None:
    """on_ready calls _trigger_sweep."""
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    bot._trigger_sweep.assert_awaited_once()


async def test_on_ready_calls_sweep_orphaned_embeds(bot, mock_redis, on_ready_env) -> None:
    """on_ready calls _sweep_orphaned_embeds."""
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    bot._sweep_orphaned_embeds.assert_awaited_once()


async def test_on_ready_calls_repopulate_all(bot, mock_redis, on_ready_env) -> None:
    """on_ready calls guild_projection.repopulate_all without reason= after refactor."""
    with patch(
        "services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock
    ) as mock_repopulate:
        await bot.on_ready()

    mock_repopulate.assert_awaited_once_with(bot=bot, redis=mock_redis)


async def test_on_ready_touches_bot_ready_file(bot, mock_redis, on_ready_env) -> None:
    """on_ready touches /tmp/bot-ready after projection is populated."""
    with (
        patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock),
        patch("services.bot.bot.Path") as mock_path,
    ):
        await bot.on_ready()

    mock_path.assert_called_with("/tmp/bot-ready")
    mock_path.return_value.touch.assert_called_once()


async def test_on_ready_starts_message_refresh_listener(bot, mock_redis, on_ready_env) -> None:
    """on_ready starts MessageRefreshListener task when not already running."""
    del bot._refresh_listener_started
    with (
        patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock),
        patch("services.bot.bot.MessageRefreshListener") as mock_listener_cls,
    ):
        mock_listener_cls.return_value.start = AsyncMock()
        await bot.on_ready()

    mock_listener_cls.assert_called_once_with(ANY, ANY)


async def test_on_ready_does_not_restart_message_refresh_listener(
    bot, mock_redis, on_ready_env
) -> None:
    """on_ready does not start a second MessageRefreshListener if already running."""
    # bot._refresh_listener_started is set by _make_bot, so the flag is present
    with (
        patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock),
        patch("services.bot.bot.MessageRefreshListener") as mock_listener_cls,
    ):
        await bot.on_ready()

    mock_listener_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Content tests — verify _rebuild_redis_from_gateway writes correct payloads.
# repopulate_all is patched out so its own writes don't interfere with
# the set_json assertions below.
# ---------------------------------------------------------------------------


async def test_on_ready_writes_guild_key(bot, mock_redis, on_ready_env) -> None:
    """on_ready writes discord:guild:{id} for each connected guild."""
    guild = on_ready_env
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild(str(guild.id)),
        {"id": str(guild.id), "name": guild.name, "owner_id": str(guild.owner_id)},
        CacheTTL.DISCORD_GUILD,
    )


async def test_on_ready_writes_guild_key_with_owner_id(bot, mock_redis, on_ready_env) -> None:
    """on_ready writes owner_id to discord:guild:{id} for each connected guild."""
    guild = on_ready_env
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild(str(guild.id)),
        {"id": str(guild.id), "name": guild.name, "owner_id": str(guild.owner_id)},
        CacheTTL.DISCORD_GUILD,
    )


async def test_on_ready_writes_guild_channels_key(bot, mock_redis, on_ready_env) -> None:
    """on_ready writes discord:guild_channels:{id} with the channel list for each guild."""
    guild = on_ready_env
    ch = guild.channels[0]
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_channels(str(guild.id)),
        [{"id": str(ch.id), "name": ch.name, "type": ch.type.value}],
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )


async def test_on_ready_writes_channel_key(bot, mock_redis, on_ready_env) -> None:
    """on_ready writes discord:channel:{id} for every channel in every guild."""
    guild = on_ready_env
    ch = guild.channels[0]
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_channel(str(ch.id)),
        {"name": ch.name},
        CacheTTL.DISCORD_CHANNEL,
    )


async def test_on_ready_writes_guild_roles_key_with_permissions(
    bot, mock_redis, on_ready_env
) -> None:
    """on_ready writes discord:guild_roles:{id} including permissions bitfield."""
    guild = on_ready_env
    role = guild.roles[0]
    with patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock):
        await bot.on_ready()

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_roles(str(guild.id)),
        [
            {
                "id": str(role.id),
                "name": role.name,
                "color": role.color.value,
                "position": role.position,
                "managed": role.managed,
                "permissions": role.permissions.value,
            }
        ],
        CacheTTL.DISCORD_GUILD_ROLES,
    )


async def test_on_ready_excludes_non_postable_channels_from_guild_channels_key(
    bot, mock_redis
) -> None:
    """on_ready omits channels where bot lacks send_messages from the guild channel list."""
    guild = _make_guild(111, "Test Guild")
    restricted = _make_channel(1002, "restricted")
    restricted.permissions_for.return_value.send_messages = False
    guild.channels = [guild.channels[0], restricted]

    mock_user = MagicMock()
    mock_user.id = 999
    postable_ch = guild.channels[0]

    stack = ExitStack()
    with stack:
        stack.enter_context(
            patch.object(type(bot), "guilds", new_callable=PropertyMock, return_value=[guild])
        )
        stack.enter_context(
            patch.object(type(bot), "user", new_callable=PropertyMock, return_value=mock_user)
        )
        stack.enter_context(
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            )
        )
        stack.enter_context(patch.object(bot, "_recover_pending_workers", new_callable=AsyncMock))
        stack.enter_context(patch.object(bot, "_trigger_sweep", new_callable=AsyncMock))
        stack.enter_context(patch.object(bot, "_sweep_orphaned_embeds", new_callable=AsyncMock))
        stack.enter_context(patch("services.bot.bot.tracer"))
        stack.enter_context(patch("services.bot.bot.os.getenv", return_value=None))
        stack.enter_context(
            patch(
                "services.bot.bot.sync_guilds_from_gateway",
                new_callable=AsyncMock,
                return_value={"new_guilds": 0, "new_channels": 0},
            )
        )
        stack.enter_context(
            patch(
                "services.bot.bot.get_db_session",
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=AsyncMock()),
                    __aexit__=AsyncMock(return_value=None),
                ),
            )
        )
        stack.enter_context(
            patch("services.bot.bot.guild_projection.repopulate_all", new_callable=AsyncMock)
        )
        await bot.on_ready()

    mock_redis.set_json.assert_any_call(
        CacheKeys.discord_guild_channels(str(guild.id)),
        [{"id": str(postable_ch.id), "name": postable_ch.name, "type": postable_ch.type.value}],
        CacheTTL.DISCORD_GUILD_CHANNELS,
    )
