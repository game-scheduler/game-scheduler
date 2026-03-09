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


"""Unit tests verifying config fields are forwarded to DiscordAPIClient callsites and oauth2.py."""

from unittest.mock import AsyncMock, patch

import pytest

import services.api.dependencies.discord as api_dep
import services.bot.dependencies.discord_client as bot_dep
from services.api.auth.oauth2 import generate_authorization_url

_FAKE_BASE = "http://fake-discord:8080"
_FAKE_OAUTH_URL = "http://fake-discord:8080/oauth2/authorize"


def _make_api_config(**overrides):
    """Build a minimal mock APIConfig with all required attributes."""
    defaults = {
        "discord_client_id": "test_client_id",
        "discord_client_secret": "test_secret",
        "discord_bot_token": "test_token",
        "discord_api_base_url": _FAKE_BASE,
        "discord_oauth_url": _FAKE_OAUTH_URL,
    }
    defaults.update(overrides)
    return type("MockAPIConfig", (), defaults)()


def _make_bot_config(**overrides):
    """Build a minimal mock BotConfig with all required attributes."""
    defaults = {
        "discord_bot_client_id": "test_client_id",
        "discord_bot_token": "test_token",
        "discord_api_base_url": _FAKE_BASE,
    }
    defaults.update(overrides)
    return type("MockBotConfig", (), defaults)()


def test_api_discord_client_uses_config_api_base_url():
    """API dependency passes discord_api_base_url from config to DiscordAPIClient."""
    api_dep._discord_client_instance = None
    try:
        with patch("services.api.config.get_api_config", return_value=_make_api_config()):
            client = api_dep.get_discord_client()
        assert client._api_base_url == _FAKE_BASE
    finally:
        api_dep._discord_client_instance = None


def test_bot_discord_client_uses_config_api_base_url():
    """Bot dependency passes discord_api_base_url from config to DiscordAPIClient."""
    bot_dep._discord_client_instance = None
    try:
        with patch("services.bot.config.get_config", return_value=_make_bot_config()):
            client = bot_dep.get_discord_client()
        assert client._api_base_url == _FAKE_BASE
    finally:
        bot_dep._discord_client_instance = None


@pytest.mark.asyncio
async def test_generate_authorization_url_uses_config_oauth_url():
    """generate_authorization_url builds redirect using config.discord_oauth_url."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()

    with (
        patch("services.api.config.get_api_config", return_value=_make_api_config()),
        patch(
            "services.api.auth.oauth2.cache_client.get_redis_client",
            AsyncMock(return_value=mock_redis),
        ),
    ):
        auth_url, _state = await generate_authorization_url("http://localhost/callback")

    assert auth_url.startswith(_FAKE_OAUTH_URL), (
        f"Expected URL to start with {_FAKE_OAUTH_URL!r}, got: {auth_url!r}"
    )
