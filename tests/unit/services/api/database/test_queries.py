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


"""Unit tests for database query functions."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.database import queries
from shared.models.guild import GuildConfiguration


@pytest.mark.asyncio
async def test_require_guild_by_id_success_context_already_set():
    """Guild exists, RLS context already set, user authorized → returns guild."""
    # Arrange
    guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            return_value=[guild_uuid],  # Context now stores UUIDs
        ),
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
        patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
    ):
        # Act
        result = await queries.require_guild_by_id(
            mock_db, guild_uuid, access_token, user_discord_id
        )

        # Assert
        assert result == mock_guild
        mock_get_guilds.assert_not_called()  # Should not fetch guilds when context already set


@pytest.mark.asyncio
async def test_require_guild_by_id_success_context_not_set():
    """Guild exists, NO RLS context → fetches guilds, sets context, returns guild."""
    # Arrange
    guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)
    mock_user_guilds = [{"id": guild_discord_id, "name": "Test Guild"}]

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            side_effect=[None, [guild_uuid]],  # Second call returns UUID
        ),
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
        patch(
            "services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds
        ) as mock_get_guilds,
        patch(
            "services.api.database.queries.setup_rls_and_convert_guild_ids",
            return_value=[guild_uuid],
        ) as mock_setup_rls,
    ):
        # Act
        result = await queries.require_guild_by_id(
            mock_db, guild_uuid, access_token, user_discord_id
        )

        # Assert
        assert result == mock_guild
        mock_get_guilds.assert_called_once_with(access_token, user_discord_id)
        mock_setup_rls.assert_called_once_with(mock_db, [guild_discord_id])


@pytest.mark.asyncio
async def test_require_guild_by_id_guild_not_found():
    """Guild does not exist → HTTPException(404)."""
    # Arrange
    guild_uuid = str(uuid4())
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            return_value=["other_guild"],
        ),
        patch("services.api.database.queries.get_guild_by_id", return_value=None),
    ):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(mock_db, guild_uuid, access_token, user_discord_id)

        assert exc_info.value.status_code == 404
        assert "Guild configuration not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_guild_by_id_user_not_authorized():
    """Guild exists but user NOT in guild → HTTPException(404) to prevent info disclosure."""
    # Arrange
    guild_uuid = str(uuid4())
    other_guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            return_value=[other_guild_uuid],  # User authorized for different guild UUID
        ),
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
    ):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(mock_db, guild_uuid, access_token, user_discord_id)

        assert exc_info.value.status_code == 404  # 404 not 403 to prevent info disclosure
        assert "Guild configuration not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_guild_by_id_context_none_after_query():
    """RLS context is None even after query → HTTPException(404) for safety."""
    # Arrange
    guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            side_effect=[None, None],
        ),
        patch("services.api.database.queries.set_current_guild_ids"),
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
        patch(
            "services.api.auth.oauth2.get_user_guilds",
            return_value=[{"id": guild_discord_id}],
        ),
        patch(
            "services.api.database.queries.convert_discord_guild_ids_to_uuids",
            return_value=[],  # Conversion returns empty list
        ),
    ):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(mock_db, guild_uuid, access_token, user_discord_id)

        assert exc_info.value.status_code == 404
        assert "Guild configuration not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_guild_by_id_custom_error_message():
    """Custom not_found_detail parameter → used in HTTPException."""
    # Arrange
    guild_uuid = str(uuid4())
    user_discord_id = "987654321"
    access_token = "test_token"
    custom_message = "Template not found"

    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            return_value=["some_guild"],
        ),
        patch("services.api.database.queries.get_guild_by_id", return_value=None),
    ):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(
                mock_db, guild_uuid, access_token, user_discord_id, custom_message
            )

        assert exc_info.value.status_code == 404
        assert custom_message in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_guild_by_id_multiple_guilds_authorized():
    """User member of multiple guilds, one matches target → success."""
    # Arrange
    guild_uuid = str(uuid4())
    other_guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            return_value=[other_guild_uuid, guild_uuid],  # Multiple guild UUIDs
        ),
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
    ):
        # Act
        result = await queries.require_guild_by_id(
            mock_db, guild_uuid, access_token, user_discord_id
        )

        # Assert
        assert result == mock_guild


@pytest.mark.asyncio
async def test_require_guild_by_id_idempotent_context_set():
    """Context already set → doesn't refetch guilds from Discord API."""
    # Arrange
    guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            return_value=[guild_uuid],  # Context has UUID
        ),
        patch("services.api.database.queries.set_current_guild_ids") as mock_set_context,
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
        patch("services.api.auth.oauth2.get_user_guilds") as mock_get_guilds,
    ):
        # Act
        result = await queries.require_guild_by_id(
            mock_db, guild_uuid, access_token, user_discord_id
        )

        # Assert
        assert result == mock_guild
        mock_get_guilds.assert_not_called()
        mock_set_context.assert_not_called()


@pytest.mark.asyncio
async def test_require_guild_by_id_oauth2_get_user_guilds_called_only_when_needed():
    """OAuth2 guild fetch only called when context is None."""
    # Arrange
    guild_uuid = str(uuid4())
    guild_discord_id = "123456789"
    user_discord_id = "987654321"
    access_token = "test_token"

    mock_guild = GuildConfiguration(id=guild_uuid, guild_id=guild_discord_id)
    mock_db = AsyncMock(spec=AsyncSession)
    mock_user_guilds = [{"id": guild_discord_id}]

    call_count = 0

    async def get_guilds_mock(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_user_guilds

    with (
        patch(
            "services.api.database.queries.get_current_guild_ids",
            side_effect=[None, [guild_uuid]],  # Second call returns UUID
        ),
        patch("services.api.database.queries.set_current_guild_ids"),
        patch("services.api.database.queries.get_guild_by_id", return_value=mock_guild),
        patch("services.api.auth.oauth2.get_user_guilds", side_effect=get_guilds_mock),
        patch(
            "services.api.database.queries.convert_discord_guild_ids_to_uuids",
            return_value=[guild_uuid],  # Mock conversion
        ),
    ):
        # Act
        await queries.require_guild_by_id(mock_db, guild_uuid, access_token, user_discord_id)

        # Assert
        assert call_count == 1  # Called exactly once when context was None
