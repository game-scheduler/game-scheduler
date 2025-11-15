# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Tests for config_channel command."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Interaction

from services.bot.commands.config_channel import (
    _create_config_display_embed,
    config_channel_command,
)
from shared.models import ChannelConfiguration, GuildConfiguration


@pytest.fixture
def mock_interaction():
    """Create mock Discord interaction."""
    interaction = MagicMock(spec=Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_guild():
    """Create mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_channel():
    """Create mock Discord text channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.name = "general"
    return channel


@pytest.fixture
def mock_member_admin():
    """Create mock member with manage channels permission."""
    member = MagicMock(spec=discord.Member)
    member.id = 111222333
    member.guild_permissions = discord.Permissions(manage_channels=True)
    return member


@pytest.fixture
def sample_guild_config():
    """Create sample guild configuration."""
    return GuildConfiguration(
        id=1,
        guild_id="123456789",
        guild_name="Test Guild",
        default_max_players=10,
        default_reminder_minutes=[60, 15],
        default_rules="Guild rules",
        allowed_host_role_ids=[],
        require_host_role=False,
    )


@pytest.fixture
def sample_channel_config():
    """Create sample channel configuration."""
    return ChannelConfiguration(
        id=1,
        guild_id=1,
        channel_id="987654321",
        channel_name="general",
        is_active=True,
        max_players=None,
        reminder_minutes=None,
        default_rules=None,
        allowed_host_role_ids=None,
        game_category=None,
    )


@pytest.mark.asyncio
async def test_config_channel_no_guild(mock_interaction):
    """Test config_channel_command when not in a guild."""
    mock_interaction.guild = None
    mock_interaction.user = MagicMock()

    await config_channel_command(mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "server" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_config_channel_display_current(
    mock_interaction,
    mock_guild,
    mock_channel,
    mock_member_admin,
    sample_guild_config,
    sample_channel_config,
):
    """Test config_channel_command displays current config."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_guild_result = MagicMock()
        mock_guild_result.scalar_one_or_none.return_value = sample_guild_config

        mock_channel_result = MagicMock()
        mock_channel_result.scalar_one_or_none.return_value = sample_channel_config

        mock_session.execute = AsyncMock(side_effect=[mock_guild_result, mock_channel_result])

        await config_channel_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "Current channel configuration" in call_args[0][0]
    assert "embed" in call_args[1]


@pytest.mark.asyncio
async def test_config_channel_no_guild_config(
    mock_interaction, mock_guild, mock_channel, mock_member_admin
):
    """Test config_channel_command when guild config missing."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        await config_channel_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "/config-guild" in call_args[0][0]


@pytest.mark.asyncio
async def test_config_channel_update_max_players(
    mock_interaction,
    mock_guild,
    mock_channel,
    mock_member_admin,
    sample_guild_config,
    sample_channel_config,
):
    """Test config_channel_command updates max players."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_guild_result = MagicMock()
        mock_guild_result.scalar_one_or_none.return_value = sample_guild_config

        mock_channel_result = MagicMock()
        mock_channel_result.scalar_one_or_none.return_value = sample_channel_config

        mock_session.execute = AsyncMock(side_effect=[mock_guild_result, mock_channel_result])
        mock_session.commit = AsyncMock()

        await config_channel_command(mock_interaction, max_players=15)

    assert sample_channel_config.max_players == 15
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_config_channel_update_category(
    mock_interaction,
    mock_guild,
    mock_channel,
    mock_member_admin,
    sample_guild_config,
    sample_channel_config,
):
    """Test config_channel_command updates game category."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_guild_result = MagicMock()
        mock_guild_result.scalar_one_or_none.return_value = sample_guild_config

        mock_channel_result = MagicMock()
        mock_channel_result.scalar_one_or_none.return_value = sample_channel_config

        mock_session.execute = AsyncMock(side_effect=[mock_guild_result, mock_channel_result])
        mock_session.commit = AsyncMock()

        await config_channel_command(mock_interaction, game_category="D&D")

    assert sample_channel_config.game_category == "D&D"
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_config_channel_toggle_active(
    mock_interaction,
    mock_guild,
    mock_channel,
    mock_member_admin,
    sample_guild_config,
    sample_channel_config,
):
    """Test config_channel_command toggles is_active."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_guild_result = MagicMock()
        mock_guild_result.scalar_one_or_none.return_value = sample_guild_config

        mock_channel_result = MagicMock()
        mock_channel_result.scalar_one_or_none.return_value = sample_channel_config

        mock_session.execute = AsyncMock(side_effect=[mock_guild_result, mock_channel_result])
        mock_session.commit = AsyncMock()

        await config_channel_command(mock_interaction, is_active=False)

    assert sample_channel_config.is_active is False
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_config_channel_specific_channel(
    mock_interaction,
    mock_guild,
    mock_member_admin,
    sample_guild_config,
    sample_channel_config,
):
    """Test config_channel_command with specific channel parameter."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    target_channel = MagicMock(spec=discord.TextChannel)
    target_channel.id = 111111111
    target_channel.name = "gaming"

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_guild_result = MagicMock()
        mock_guild_result.scalar_one_or_none.return_value = sample_guild_config

        mock_channel_result = MagicMock()
        mock_channel_result.scalar_one_or_none.return_value = sample_channel_config

        mock_session.execute = AsyncMock(side_effect=[mock_guild_result, mock_channel_result])

        await config_channel_command(mock_interaction, channel=target_channel)

    mock_interaction.followup.send.assert_called_once()


@pytest.mark.asyncio
async def test_config_channel_error_handling(
    mock_interaction, mock_guild, mock_channel, mock_member_admin
):
    """Test config_channel_command error handling."""
    mock_interaction.guild = mock_guild
    mock_interaction.channel = mock_channel
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_channel.get_db_session") as mock_db:
        mock_db.return_value.__aenter__.side_effect = Exception("Database error")

        await config_channel_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "error" in call_args[0][0].lower()


def test_create_config_display_embed(mock_channel, sample_channel_config, sample_guild_config):
    """Test _create_config_display_embed creates proper embed."""
    embed = _create_config_display_embed(mock_channel, sample_channel_config, sample_guild_config)

    assert "#general" in embed.title
    assert len(embed.fields) == 5


def test_create_config_display_embed_with_overrides(
    mock_channel, sample_channel_config, sample_guild_config
):
    """Test _create_config_display_embed shows overrides."""
    sample_channel_config.max_players = 20
    sample_channel_config.game_category = "D&D"
    sample_channel_config.is_active = False

    embed = _create_config_display_embed(mock_channel, sample_channel_config, sample_guild_config)

    max_players_field = next(f for f in embed.fields if f.name == "Max Players")
    assert "20" in max_players_field.value

    category_field = next(f for f in embed.fields if f.name == "Category")
    assert "D&D" in category_field.value

    status_field = next(f for f in embed.fields if f.name == "Status")
    assert "Inactive" in status_field.value
