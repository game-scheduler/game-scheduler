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


"""Tests for API main entry point."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api import main


def test_setup_logging_configures_level():
    """Test that setup_logging configures the correct log level."""
    with patch("logging.basicConfig") as mock_basic_config:
        main.setup_logging("WARNING")

        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.WARNING


def test_setup_logging_with_debug_level():
    """Test that setup_logging handles DEBUG level correctly."""
    with patch("logging.basicConfig") as mock_basic_config:
        main.setup_logging("DEBUG")

        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.DEBUG


def test_setup_logging_with_lowercase_level():
    """Test that setup_logging handles lowercase log level strings."""
    with patch("logging.basicConfig") as mock_basic_config:
        main.setup_logging("info")

        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.INFO


@pytest.mark.asyncio
async def test_main_starts_uvicorn_server():
    """Test that main function starts Uvicorn server with correct configuration."""
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()

    with patch("services.api.main.get_api_config") as mock_config:
        mock_config.return_value.api_host = "127.0.0.1"
        mock_config.return_value.api_port = 9000
        mock_config.return_value.log_level = "INFO"
        mock_config.return_value.debug = True

        with patch("services.api.main.uvicorn.Server", return_value=mock_server):
            with patch("services.api.main.create_app"):
                with patch("services.api.main.setup_logging"):
                    await main.main()

                    mock_server.serve.assert_called_once()


@pytest.mark.asyncio
async def test_main_uses_config_values():
    """Test that main function uses configuration values correctly."""
    with patch("services.api.main.get_api_config") as mock_config:
        mock_config.return_value.api_host = "0.0.0.0"
        mock_config.return_value.api_port = 8080
        mock_config.return_value.log_level = "DEBUG"
        mock_config.return_value.debug = False

        with patch("services.api.main.uvicorn.Config") as mock_uvicorn_config:
            with patch("services.api.main.uvicorn.Server") as mock_server:
                mock_server.return_value.serve = AsyncMock()

                with patch("services.api.main.create_app"):
                    with patch("services.api.main.setup_logging"):
                        await main.main()

                        # Verify uvicorn.Config was called with correct values
                        call_kwargs = mock_uvicorn_config.call_args[1]
                        assert call_kwargs["host"] == "0.0.0.0"
                        assert call_kwargs["port"] == 8080
                        assert call_kwargs["log_level"] == "debug"
                        assert call_kwargs["access_log"] is False
