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


"""Tests for bot main entry point."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.main import main, setup_logging


class TestSetupLogging:
    """Test suite for setup_logging function."""

    def test_setup_logging_info_level(self) -> None:
        """Test logging setup with INFO level."""
        with patch("logging.basicConfig") as mock_basic_config:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                setup_logging("INFO")

                mock_basic_config.assert_called_once()
                call_kwargs = mock_basic_config.call_args[1]
                assert call_kwargs["level"] == logging.INFO

    def test_setup_logging_debug_level(self) -> None:
        """Test logging setup with DEBUG level."""
        with patch("logging.basicConfig") as mock_basic_config:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                setup_logging("DEBUG")

                call_kwargs = mock_basic_config.call_args[1]
                assert call_kwargs["level"] == logging.DEBUG

    def test_setup_logging_warning_level(self) -> None:
        """Test logging setup with WARNING level."""
        with patch("logging.basicConfig") as mock_basic_config:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                setup_logging("WARNING")

                call_kwargs = mock_basic_config.call_args[1]
                assert call_kwargs["level"] == logging.WARNING

    def test_setup_logging_sets_discord_logger_level(self) -> None:
        """Test that discord.py logger levels are set to WARNING."""
        with (
            patch("logging.basicConfig"),
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_discord_logger = MagicMock()
            mock_http_logger = MagicMock()

            def get_logger_side_effect(name: str) -> MagicMock:
                if name == "discord":
                    return mock_discord_logger
                if name == "discord.http":
                    return mock_http_logger
                return MagicMock()

            mock_get_logger.side_effect = get_logger_side_effect

            setup_logging("INFO")

            mock_discord_logger.setLevel.assert_called_once_with(logging.WARNING)
            mock_http_logger.setLevel.assert_called_once_with(logging.WARNING)

    def test_setup_logging_format(self) -> None:
        """Test that logging format is correctly configured."""
        with (
            patch("logging.basicConfig") as mock_basic_config,
            patch("logging.getLogger"),
        ):
            setup_logging("INFO")

            call_kwargs = mock_basic_config.call_args[1]
            assert "format" in call_kwargs
            assert "%(asctime)s" in call_kwargs["format"]
            assert "%(name)s" in call_kwargs["format"]
            assert "%(levelname)s" in call_kwargs["format"]
            assert "%(message)s" in call_kwargs["format"]


class TestMain:
    """Test suite for main function."""

    @pytest.mark.asyncio
    async def test_main_successful_startup(self) -> None:
        """Test main function with successful bot startup."""
        mock_config = MagicMock()
        mock_config.log_level = "INFO"
        mock_config.environment = "development"
        mock_config.discord_bot_token = "test_token"

        mock_bot = MagicMock()
        mock_bot.start = AsyncMock()
        mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
        mock_bot.__aexit__ = AsyncMock()

        with patch("services.bot.main.get_config", return_value=mock_config):
            with patch("services.bot.main.setup_logging"):
                with patch("services.bot.main.create_bot", return_value=mock_bot):
                    with patch("logging.getLogger"):
                        with patch.dict("os.environ", {}, clear=False) as env:
                            env.pop("PYTEST_RUNNING", None)
                            await main()

                            mock_bot.start.assert_awaited_once_with("test_token")

    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self) -> None:
        """Test main function handles KeyboardInterrupt gracefully."""
        mock_config = MagicMock()
        mock_config.log_level = "INFO"
        mock_config.environment = "development"
        mock_config.discord_bot_token = "test_token"

        mock_bot = MagicMock()
        mock_bot.start = AsyncMock(side_effect=KeyboardInterrupt())
        mock_bot.__aenter__ = AsyncMock(side_effect=KeyboardInterrupt())
        mock_bot.__aexit__ = AsyncMock()

        with patch("services.bot.main.get_config", return_value=mock_config):
            with patch("services.bot.main.setup_logging"):
                with patch("services.bot.main.create_bot", return_value=mock_bot):
                    with patch("logging.getLogger") as mock_get_logger:
                        with patch.dict("os.environ", {}, clear=False) as env:
                            env.pop("PYTEST_RUNNING", None)
                            mock_logger = MagicMock()
                            mock_get_logger.return_value = mock_logger

                            await main()

                            mock_logger.info.assert_any_call(
                                "Received interrupt signal, shutting down"
                            )

    @pytest.mark.asyncio
    async def test_main_exception_handling(self) -> None:
        """Test main function handles exceptions and exits with error code."""
        mock_config = MagicMock()
        mock_config.log_level = "INFO"
        mock_config.environment = "development"
        mock_config.discord_bot_token = "test_token"

        test_exception = Exception("Test error")
        mock_bot = MagicMock()
        mock_bot.start = AsyncMock(side_effect=test_exception)
        mock_bot.__aenter__ = AsyncMock(side_effect=test_exception)
        mock_bot.__aexit__ = AsyncMock()

        with patch("services.bot.main.get_config", return_value=mock_config):
            with patch("services.bot.main.setup_logging"):
                with patch("services.bot.main.create_bot", return_value=mock_bot):
                    with patch("logging.getLogger") as mock_get_logger:
                        with patch("sys.exit") as mock_exit:
                            with patch.dict("os.environ", {}, clear=False) as env:
                                env.pop("PYTEST_RUNNING", None)
                                mock_logger = MagicMock()
                                mock_get_logger.return_value = mock_logger

                                await main()

                                mock_logger.exception.assert_called_once()
                                mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_logs_startup_information(self) -> None:
        """Test main function logs startup information."""
        mock_config = MagicMock()
        mock_config.log_level = "INFO"
        mock_config.environment = "production"
        mock_config.discord_bot_token = "test_token"

        mock_bot = MagicMock()
        mock_bot.start = AsyncMock()
        mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
        mock_bot.__aexit__ = AsyncMock()

        with patch("services.bot.main.get_config", return_value=mock_config):
            with patch("services.bot.main.setup_logging"):
                with patch("services.bot.main.create_bot", return_value=mock_bot):
                    with patch("logging.getLogger") as mock_get_logger:
                        with patch.dict("os.environ", {}, clear=False) as env:
                            env.pop("PYTEST_RUNNING", None)
                            mock_logger = MagicMock()
                            mock_get_logger.return_value = mock_logger

                            await main()

                            mock_logger.info.assert_any_call("Starting Discord Game Scheduler Bot")
                            mock_logger.info.assert_any_call("Environment: %s", "production")
