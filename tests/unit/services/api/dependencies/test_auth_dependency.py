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


"""Unit tests for get_current_user authentication dependency."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.api.dependencies.auth import get_current_user


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.discord_id = "123456789012345678"
    return user


_VALID_TOKEN_DATA = {
    "user_id": "123456789012345678",
    "access_token": "test_access_token",
    "expires_at": 9999999999,
}


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_raises_401_when_no_session_cookie(self, mock_db):
        """Raises 401 when no session cookie is present."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(session_token=None, db=mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_session_not_found(self, mock_db):
        """Raises 401 when session token has no corresponding Redis entry."""
        with patch(
            "services.api.dependencies.auth.tokens.get_user_tokens",
            AsyncMock(return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(session_token="unknown_token", db=mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_token_expired(self, mock_db):
        """Raises 401 when session token has expired."""
        with patch(
            "services.api.dependencies.auth.tokens.get_user_tokens",
            AsyncMock(return_value=_VALID_TOKEN_DATA),
        ):
            with patch(
                "services.api.dependencies.auth.tokens.is_token_expired",
                AsyncMock(return_value=True),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(session_token="expired_token", db=mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_user_not_in_db(self, mock_db):
        """Raises 401 when Discord user is not found in the database."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch(
            "services.api.dependencies.auth.tokens.get_user_tokens",
            AsyncMock(return_value=_VALID_TOKEN_DATA),
        ):
            with patch(
                "services.api.dependencies.auth.tokens.is_token_expired",
                AsyncMock(return_value=False),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(session_token="valid_token", db=mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_current_user_for_valid_session(self, mock_db, mock_user):
        """Returns CurrentUser when session is valid and user exists in DB."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch(
            "services.api.dependencies.auth.tokens.get_user_tokens",
            AsyncMock(return_value=_VALID_TOKEN_DATA),
        ):
            with patch(
                "services.api.dependencies.auth.tokens.is_token_expired",
                AsyncMock(return_value=False),
            ):
                result = await get_current_user(session_token="valid_token", db=mock_db)

        assert result.user == mock_user
        assert result.access_token == "test_access_token"
        assert result.session_token == "valid_token"
