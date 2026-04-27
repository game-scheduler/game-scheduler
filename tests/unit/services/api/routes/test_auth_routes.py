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


"""Unit tests for auth route error paths."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status

from services.api.routes import auth as auth_routes


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_exception(self):
        with patch(
            "services.api.auth.oauth2.generate_authorization_url",
            side_effect=RuntimeError("oauth service down"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_routes.login(redirect_uri="http://localhost/callback")

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "Failed to initiate login"


class TestCallback:
    @pytest.mark.asyncio
    async def test_callback_exchange_tokens_failure(self):
        mock_db = AsyncMock()
        mock_response = MagicMock()

        with (
            patch(
                "services.api.auth.oauth2.validate_state",
                new_callable=AsyncMock,
                return_value="http://localhost/callback",
            ),
            patch(
                "services.api.auth.oauth2.exchange_code_for_tokens",
                side_effect=RuntimeError("Discord unavailable"),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_routes.callback(
                    response=mock_response,
                    code="auth_code",
                    state="state_token",
                    db=mock_db,
                )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "Authentication failed"

    @pytest.mark.asyncio
    async def test_callback_maintainer_check_failure_defaults_false(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        mock_response = MagicMock()

        with (
            patch(
                "services.api.auth.oauth2.validate_state",
                new_callable=AsyncMock,
                return_value="http://localhost/callback",
            ),
            patch(
                "services.api.auth.oauth2.exchange_code_for_tokens",
                new_callable=AsyncMock,
                return_value={
                    "access_token": "access-tok",
                    "refresh_token": "refresh-tok",
                    "expires_in": 3600,
                },
            ),
            patch(
                "services.api.auth.oauth2.get_user_from_token",
                new_callable=AsyncMock,
                return_value={"id": "usr-discord-123"},
            ),
            patch(
                "services.api.auth.oauth2.is_app_maintainer",
                side_effect=RuntimeError("maintainer service down"),
            ),
            patch(
                "services.api.auth.tokens.store_user_tokens",
                new_callable=AsyncMock,
                return_value="session-tok",
            ) as mock_store,
            patch("services.api.routes.auth.get_api_config") as mock_config,
        ):
            mock_config.return_value.environment = "development"
            mock_config.return_value.cookie_domain = None
            result = await auth_routes.callback(
                response=mock_response,
                code="auth_code",
                state="state_token",
                db=mock_db,
            )

        assert result["success"] is True
        mock_store.assert_called_once()
        assert mock_store.call_args.kwargs["can_be_maintainer"] is False
        mock_config.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_callback_passes_username_and_avatar_to_store_user_tokens(self):
        """callback must forward username and avatar from user_data to store_user_tokens."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        mock_response = MagicMock()

        with (
            patch(
                "services.api.auth.oauth2.validate_state",
                new_callable=AsyncMock,
                return_value="http://localhost/callback",
            ),
            patch(
                "services.api.auth.oauth2.exchange_code_for_tokens",
                new_callable=AsyncMock,
                return_value={
                    "access_token": "access-tok",
                    "refresh_token": "refresh-tok",
                    "expires_in": 3600,
                },
            ),
            patch(
                "services.api.auth.oauth2.get_user_from_token",
                new_callable=AsyncMock,
                return_value={
                    "id": "usr-discord-123",
                    "username": "testuser",
                    "avatar": "abc123",
                },
            ),
            patch(
                "services.api.auth.oauth2.is_app_maintainer",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "services.api.auth.tokens.store_user_tokens",
                new_callable=AsyncMock,
                return_value="session-tok",
            ) as mock_store,
            patch("services.api.routes.auth.get_api_config") as mock_config,
        ):
            mock_config.return_value.environment = "development"
            mock_config.return_value.cookie_domain = None
            await auth_routes.callback(
                response=mock_response,
                code="auth_code",
                state="state_token",
                db=mock_db,
            )

        assert mock_store.call_args.kwargs.get("username") == "testuser"
        assert mock_store.call_args.kwargs.get("avatar") == "abc123"
        mock_config.assert_called_once_with()


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_no_session(self, mock_current_user_unit):
        with patch(
            "services.api.auth.tokens.get_user_tokens",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_routes.refresh(current_user=mock_current_user_unit)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "No session found"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, mock_current_user_unit):
        token_data = {
            "refresh_token": "old-refresh-tok",
            "access_token": "old-access-tok",
        }

        with (
            patch(
                "services.api.auth.tokens.get_user_tokens",
                new_callable=AsyncMock,
                return_value=token_data,
            ),
            patch(
                "services.api.auth.oauth2.refresh_access_token",
                side_effect=RuntimeError("refresh failed"),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_routes.refresh(current_user=mock_current_user_unit)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Failed to refresh token"


class TestGetUserInfo:
    @pytest.mark.asyncio
    async def test_get_user_info_no_guilds_field(self, mock_current_user_unit, mock_db_unit):
        """get_user_info must return username/avatar from session without calling oauth2."""
        token_data = {
            "refresh_token": "refresh-tok",
            "access_token": "access-tok",
            "expires_at": "2099-01-01T00:00:00Z",
            "username": "testuser",
            "avatar": "abc123",
        }
        with patch(
            "services.api.auth.tokens.get_user_tokens",
            new_callable=AsyncMock,
            return_value=token_data,
        ):
            result = await auth_routes.get_user_info(
                current_user=mock_current_user_unit, _db=mock_db_unit
            )

            assert not hasattr(result, "guilds")
            assert result.username == "testuser"
            assert result.avatar == "abc123"
