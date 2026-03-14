# Copyright 2025-2026 Bret McKee
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
    interaction.permissions = discord.Permissions.none()
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
    permissions = discord.Permissions(manage_guild=True)
    member.guild_permissions = permissions
    type(member).guild_permissions = property(lambda self: permissions)
    return member


@pytest.fixture
def mock_member_with_manage_channels():
    """Create mock member with MANAGE_CHANNELS permission."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    permissions = discord.Permissions(manage_channels=True)
    member.guild_permissions = permissions
    type(member).guild_permissions = property(lambda self: permissions)
    return member


@pytest.fixture
def mock_member_no_permissions():
    """Create mock member with no special permissions."""
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    permissions = discord.Permissions()
    member.guild_permissions = permissions
    type(member).guild_permissions = property(lambda self: permissions)
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
    assert "permission" in call_args[0][0].lower()
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
    assert "permission" in call_args[0][0].lower()
    assert call_args[1]["ephemeral"] is True
