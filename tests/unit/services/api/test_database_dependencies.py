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


"""Tests for database dependency functions."""

from unittest.mock import AsyncMock, patch

import pytest

from shared.data_access.guild_isolation import get_current_guild_ids
from shared.database import get_db_with_user_guilds
from shared.schemas.auth import CurrentUser


@pytest.fixture
def mock_current_user():
    """Mock CurrentUser for dependency testing."""
    user_mock = AsyncMock()
    user_mock.discord_id = "123456789"
    user_mock.id = "user_uuid_123"

    return CurrentUser(
        user=user_mock,
        access_token="mock_access_token",
        session_token="mock_session_token",
    )


@pytest.fixture
def mock_user_guilds():
    """Mock user guilds from Discord API."""
    return [
        {"id": "guild_1", "name": "Test Guild 1"},
        {"id": "guild_2", "name": "Test Guild 2"},
    ]


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_sets_context(
    mock_current_user, mock_user_guilds, mock_get_user_tokens
):
    """Enhanced dependency sets guild_ids in ContextVar."""
    mock_db_session = AsyncMock()

    with (
        patch("services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds),
        patch("shared.database.AsyncSessionLocal", return_value=mock_db_session),
        patch(
            "services.api.database.queries.convert_discord_guild_ids_to_uuids",
            return_value=["uuid1", "uuid2"],
        ),
    ):
        # Factory function returns the actual dependency
        dependency_func = get_db_with_user_guilds()
        # Call the dependency with mock_current_user
        generator = dependency_func(mock_current_user)
        try:
            async for _session in generator:
                # Inside context, guild_ids should be set to UUIDs
                guild_ids = get_current_guild_ids()
                assert guild_ids == ["uuid1", "uuid2"]
                break  # Only need to test context setting
        finally:
            # Properly close generator
            await generator.aclose()


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_clears_context_on_exit(
    mock_current_user, mock_user_guilds, mock_get_user_tokens
):
    """Enhanced dependency clears ContextVar in finally block."""
    mock_db_session = AsyncMock()

    with (
        patch("services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds),
        patch("shared.database.AsyncSessionLocal", return_value=mock_db_session),
        patch(
            "services.api.database.queries.convert_discord_guild_ids_to_uuids",
            return_value=["uuid1", "uuid2"],
        ),
    ):
        # Factory function returns the actual dependency
        dependency_func = get_db_with_user_guilds()
        async for _session in dependency_func(mock_current_user):
            pass  # Consume generator

    # After generator exits, guild_ids should be cleared
    guild_ids = get_current_guild_ids()
    assert guild_ids is None


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_clears_context_on_exception(
    mock_current_user, mock_user_guilds, mock_get_user_tokens
):
    """Enhanced dependency clears ContextVar even if exception raised."""
    mock_db_session = AsyncMock()

    with (
        patch("services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds),
        patch("shared.database.AsyncSessionLocal", return_value=mock_db_session),
        patch(
            "services.api.database.queries.convert_discord_guild_ids_to_uuids",
            return_value=["uuid1", "uuid2"],
        ),
    ):
        # Factory function returns the actual dependency
        dependency_func = get_db_with_user_guilds()
        generator = dependency_func(mock_current_user)
        try:
            with pytest.raises(RuntimeError):
                async for _session in generator:
                    msg = "Simulated error"
                    raise RuntimeError(msg)
        finally:
            # Properly close the generator to trigger finally block
            await generator.aclose()

    # Even after exception, guild_ids should be cleared
    guild_ids = get_current_guild_ids()
    assert guild_ids is None
