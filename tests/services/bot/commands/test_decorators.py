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


"""Tests for permission decorators."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord import Interaction

from services.bot.commands.decorators import (
    require_manage_channels,
    require_manage_guild,
)


@pytest.fixture
def mock_interaction():
    """Create mock Discord interaction."""
    interaction = MagicMock(spec=Interaction)
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    return interaction


@pytest.fixture
def mock_guild():
    """Create mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_member_with_manage_guild():
    """Create mock member with MANAGE_GUILD permission."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    member.guild_permissions = discord.Permissions(manage_guild=True)
    return member


@pytest.fixture
def mock_member_with_manage_channels():
    """Create mock member with MANAGE_CHANNELS permission."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    member.guild_permissions = discord.Permissions(manage_channels=True)
    return member


@pytest.fixture
def mock_member_no_permissions():
    """Create mock member with no special permissions."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    member.guild_permissions = discord.Permissions()
    return member


@pytest.mark.asyncio
async def test_require_manage_guild_success(
    mock_interaction, mock_guild, mock_member_with_manage_guild
):
    """Test require_manage_guild allows member with permission."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_with_manage_guild

    @require_manage_guild()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result == "success"
    mock_interaction.response.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_require_manage_guild_no_permission(
    mock_interaction, mock_guild, mock_member_no_permissions
):
    """Test require_manage_guild blocks member without permission."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_no_permissions

    @require_manage_guild()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result is None
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "Manage Server" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_require_manage_guild_no_guild(mock_interaction):
    """Test require_manage_guild blocks when not in a guild."""
    mock_interaction.guild = None
    mock_interaction.user = MagicMock()

    @require_manage_guild()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result is None
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "server" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_require_manage_guild_not_member(mock_interaction, mock_guild):
    """Test require_manage_guild blocks when user is not a Member."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = MagicMock(spec=discord.User)

    @require_manage_guild()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result is None
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "permissions" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_require_manage_channels_success(
    mock_interaction, mock_guild, mock_member_with_manage_channels
):
    """Test require_manage_channels allows member with permission."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_with_manage_channels

    @require_manage_channels()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result == "success"
    mock_interaction.response.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_require_manage_channels_no_permission(
    mock_interaction, mock_guild, mock_member_no_permissions
):
    """Test require_manage_channels blocks member without permission."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member_no_permissions

    @require_manage_channels()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result is None
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "Manage Channels" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_require_manage_channels_no_guild(mock_interaction):
    """Test require_manage_channels blocks when not in a guild."""
    mock_interaction.guild = None
    mock_interaction.user = MagicMock()

    @require_manage_channels()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result is None
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "server" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_require_manage_channels_not_member(mock_interaction, mock_guild):
    """Test require_manage_channels blocks when user is not a Member."""
    mock_interaction.guild = mock_guild
    mock_interaction.user = MagicMock(spec=discord.User)

    @require_manage_channels()
    async def test_command(interaction: Interaction):
        return "success"

    result = await test_command(mock_interaction)
    assert result is None
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert "permissions" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True
