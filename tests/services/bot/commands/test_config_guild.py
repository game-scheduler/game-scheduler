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


"""Tests for config_guild command."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Interaction

from services.bot.commands.config_guild import (
    _create_config_display_embed,
    config_guild_command,
)
from shared.models import GuildConfiguration


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
def mock_member_admin():
    """Create mock member with admin permissions."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    member.guild_permissions = discord.Permissions(manage_guild=True)
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
        default_rules="Be respectful",
        allowed_host_role_ids=[],
        require_host_role=False,
    )


@pytest.mark.asyncio
async def test_config_guild_no_guild(mock_interaction):
    """Test config_guild_command when not in a guild."""
    mock_interaction.guild = None
    mock_interaction.user = MagicMock()

    await config_guild_command(mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "server" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_config_guild_display_current(
    mock_interaction, mock_guild, mock_member_admin, sample_guild_config
):
    """Test config_guild_command displays current config when no params."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild_config
        mock_session.execute = AsyncMock(return_value=mock_result)

        await config_guild_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "Current guild configuration" in call_args[0][0]
    assert "embed" in call_args[1]


@pytest.mark.asyncio
async def test_config_guild_update_max_players(
    mock_interaction, mock_guild, mock_member_admin, sample_guild_config
):
    """Test config_guild_command updates max players."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild_config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        await config_guild_command(mock_interaction, max_players=20)

    assert sample_guild_config.default_max_players == 20
    mock_session.commit.assert_called_once()
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "updated" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_config_guild_invalid_max_players(
    mock_interaction, mock_guild, mock_member_admin, sample_guild_config
):
    """Test config_guild_command rejects invalid max players."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild_config
        mock_session.execute = AsyncMock(return_value=mock_result)

        await config_guild_command(mock_interaction, max_players=150)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "between 1 and 100" in call_args[0][0]


@pytest.mark.asyncio
async def test_config_guild_update_reminders(
    mock_interaction, mock_guild, mock_member_admin, sample_guild_config
):
    """Test config_guild_command updates reminder minutes."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild_config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        await config_guild_command(mock_interaction, reminder_minutes="30,10,5")

    assert sample_guild_config.default_reminder_minutes == [30, 10, 5]
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_config_guild_invalid_reminders(
    mock_interaction, mock_guild, mock_member_admin, sample_guild_config
):
    """Test config_guild_command rejects invalid reminder format."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild_config
        mock_session.execute = AsyncMock(return_value=mock_result)

        await config_guild_command(mock_interaction, reminder_minutes="abc,xyz")

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "Invalid reminder format" in call_args[0][0]


@pytest.mark.asyncio
async def test_config_guild_update_rules(
    mock_interaction, mock_guild, mock_member_admin, sample_guild_config
):
    """Test config_guild_command updates default rules."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guild_config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        new_rules = "New rules for games"
        await config_guild_command(mock_interaction, default_rules=new_rules)

    assert sample_guild_config.default_rules == new_rules
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_config_guild_creates_new_config(mock_interaction, mock_guild, mock_member_admin):
    """Test config_guild_command creates new config if not exists."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        await config_guild_command(mock_interaction)

    assert mock_session.add.called
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_config_guild_error_handling(mock_interaction, mock_guild, mock_member_admin):
    """Test config_guild_command error handling."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_admin

    with patch("services.bot.commands.config_guild.get_db_session") as mock_db:
        mock_db.return_value.__aenter__.side_effect = Exception("Database error")

        await config_guild_command(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert "error" in call_args[0][0].lower()


def test_create_config_display_embed(mock_guild, sample_guild_config):
    """Test _create_config_display_embed creates proper embed."""
    embed = _create_config_display_embed(mock_guild, sample_guild_config)

    assert "Test Guild" in embed.title
    assert len(embed.fields) == 3
    assert embed.fields[0].name == "Default Max Players"
    assert "10" in embed.fields[0].value
    assert embed.fields[1].name == "Default Reminders"
    assert "60, 15" in embed.fields[1].value
    assert embed.fields[2].name == "Default Rules"
    assert "Be respectful" in embed.fields[2].value


def test_create_config_display_embed_long_rules(mock_guild, sample_guild_config):
    """Test _create_config_display_embed truncates long rules."""
    sample_guild_config.default_rules = "A" * 200

    embed = _create_config_display_embed(mock_guild, sample_guild_config)

    rules_field = embed.fields[2]
    assert "..." in rules_field.value
    assert len([c for c in rules_field.value if c == "A"]) == 100
