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
from services.api.services.login_refresh import refresh_display_name_on_login
from shared.discord.client import DiscordAPIError


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
                    background_tasks=MagicMock(),
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
                background_tasks=MagicMock(),
            )

        assert result["success"] is True
        mock_store.assert_called_once()
        assert mock_store.call_args.kwargs["can_be_maintainer"] is False


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
    async def test_get_user_info_expired_token_refresh_failure(
        self, mock_current_user_unit, mock_db_unit
    ):
        token_data = {
            "refresh_token": "old-refresh-tok",
            "access_token": "old-access-tok",
            "expires_at": "2026-01-01T00:00:00Z",
        }

        with (
            patch(
                "services.api.auth.tokens.get_user_tokens",
                new_callable=AsyncMock,
                return_value=token_data,
            ),
            patch(
                "services.api.auth.tokens.is_token_expired",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.api.auth.oauth2.refresh_access_token",
                side_effect=RuntimeError("token refresh failed"),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_routes.get_user_info(
                    current_user=mock_current_user_unit, _db=mock_db_unit
                )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Session expired"


class TestCallbackEnqueuesDisplayNameRefresh:
    @pytest.mark.asyncio
    async def test_callback_enqueues_background_refresh_task(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        mock_response = MagicMock()
        mock_bg_tasks = MagicMock()

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
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "services.api.auth.tokens.store_user_tokens",
                new_callable=AsyncMock,
                return_value="session-tok",
            ),
            patch("services.api.routes.auth.get_api_config") as mock_config,
        ):
            mock_config.return_value.environment = "development"
            mock_config.return_value.cookie_domain = None
            await auth_routes.callback(
                response=mock_response,
                code="auth_code",
                state="state_token",
                db=mock_db,
                background_tasks=mock_bg_tasks,
            )

        mock_bg_tasks.add_task.assert_called_once_with(
            refresh_display_name_on_login, "usr-discord-123", "access-tok"
        )


class TestRefreshDisplayNameOnLogin:
    @pytest.mark.asyncio
    async def test_upserts_display_names_for_registered_guilds(self):
        mock_guild = MagicMock()
        mock_guild.guild_id = "guild123"
        member_data = {
            "nick": "TestNick",
            "avatar": None,
            "user": {
                "id": "usr123",
                "global_name": "TestGlobal",
                "username": "testuser",
                "avatar": "user_avatar_hash",
            },
        }

        with (
            patch(
                "services.api.services.login_refresh.get_user_guilds",
                return_value=[{"id": "guild123"}],
            ) as _,
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch("services.api.services.login_refresh.AsyncSessionLocal") as mock_session_local,
            patch("services.api.services.login_refresh.get_discord_client") as mock_get_client,
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session
            mock_execute_result = MagicMock()
            mock_execute_result.scalars.return_value.all.return_value = [mock_guild]
            mock_session.execute = AsyncMock(return_value=mock_execute_result)

            mock_client = MagicMock()
            mock_client.get_current_user_guild_member = AsyncMock(return_value=member_data)
            mock_get_client.return_value = mock_client

            with patch(
                "services.api.services.login_refresh.UserDisplayNameService"
            ) as mock_svc_cls:
                mock_svc = AsyncMock()
                mock_svc_cls.return_value = mock_svc

                await refresh_display_name_on_login("usr123", "oauth-token")

        mock_svc.upsert_batch.assert_called_once()
        entries = mock_svc.upsert_batch.call_args[0][0]
        assert len(entries) == 1
        assert entries[0]["user_discord_id"] == "usr123"
        assert entries[0]["guild_discord_id"] == "guild123"
        assert entries[0]["display_name"] == "TestNick"

    @pytest.mark.asyncio
    async def test_skips_guild_when_discord_returns_error(self):
        mock_guild = MagicMock()
        mock_guild.guild_id = "guild123"

        with (
            patch(
                "services.api.services.login_refresh.get_user_guilds",
                return_value=[{"id": "guild123"}],
            ) as _,
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch("services.api.services.login_refresh.AsyncSessionLocal") as mock_session_local,
            patch("services.api.services.login_refresh.get_discord_client") as mock_get_client,
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session
            mock_execute_result = MagicMock()
            mock_execute_result.scalars.return_value.all.return_value = [mock_guild]
            mock_session.execute = AsyncMock(return_value=mock_execute_result)

            mock_client = MagicMock()
            mock_client.get_current_user_guild_member = AsyncMock(
                side_effect=DiscordAPIError(403, "Not in guild")
            )
            mock_get_client.return_value = mock_client

            with patch(
                "services.api.services.login_refresh.UserDisplayNameService"
            ) as mock_svc_cls:
                mock_svc = AsyncMock()
                mock_svc_cls.return_value = mock_svc

                await refresh_display_name_on_login("usr123", "oauth-token")

        mock_svc.upsert_batch.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_no_guilds_skips_upsert(self):
        with (
            patch("services.api.services.login_refresh.get_user_guilds", return_value=[]),
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch("services.api.services.login_refresh.AsyncSessionLocal") as mock_session_local,
            patch("services.api.services.login_refresh.get_discord_client"),
        ):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session
            mock_execute_result = MagicMock()
            mock_execute_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_execute_result)

            with patch(
                "services.api.services.login_refresh.UserDisplayNameService"
            ) as mock_svc_cls:
                await refresh_display_name_on_login("usr123", "oauth-token")

        mock_svc_cls.assert_not_called()
