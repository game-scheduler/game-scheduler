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


"""Unit tests for init service main module helpers."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from services.init.main import (
    SECONDS_PER_DAY,
    _complete_initialization,
    _initialize_telemetry_and_logging,
    _log_phase,
)


class TestInitializeTelemetryAndLogging:
    """Tests for _initialize_telemetry_and_logging helper."""

    @patch("services.init.main.init_telemetry")
    @patch("services.init.main.trace.get_tracer")
    @patch("services.init.main.datetime")
    @patch("services.init.main.logger")
    def test_initializes_telemetry_and_returns_tracer_and_time(
        self, mock_logger, mock_datetime, mock_get_tracer, mock_init_telemetry
    ):
        """Should initialize telemetry and return tracer with start time."""
        mock_tracer = Mock()
        mock_get_tracer.return_value = mock_tracer
        mock_start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_start_time

        tracer, start_time = _initialize_telemetry_and_logging()

        mock_init_telemetry.assert_called_once_with("init-service")
        mock_get_tracer.assert_called_once_with("services.init.main")
        mock_datetime.now.assert_called_once_with(UTC)
        assert tracer == mock_tracer
        assert start_time == mock_start_time
        assert mock_logger.info.call_count == 4

    @patch("services.init.main.init_telemetry")
    @patch("services.init.main.trace.get_tracer")
    @patch("services.init.main.datetime")
    @patch("services.init.main.logger")
    def test_logs_startup_banner_with_timestamp(
        self, mock_logger, mock_datetime, mock_get_tracer, mock_init_telemetry
    ):
        """Should log formatted startup banner with timestamp."""
        mock_start_time = datetime(2026, 1, 17, 15, 30, 45, tzinfo=UTC)
        mock_datetime.now.return_value = mock_start_time

        _initialize_telemetry_and_logging()

        # Verify the format string and arguments separately
        calls = mock_logger.info.call_args_list
        log_messages = [call[0][0] for call in calls]
        assert "=" * 60 in log_messages
        assert "Environment Initialization Started" in log_messages
        assert "Timestamp: %s" in log_messages
        # Verify timestamp argument was passed
        timestamp_call = [c for c in calls if len(c[0]) > 1 and "Timestamp" in c[0][0]]
        assert len(timestamp_call) == 1
        assert timestamp_call[0][0][1] == "2026-01-17 15:30:45 UTC"


class TestLogPhase:
    """Tests for _log_phase helper."""

    @patch("services.init.main.logger")
    def test_logs_phase_without_completion_status(self, mock_logger):
        """Should log phase message without completion checkmark."""
        _log_phase(1, 6, "Waiting for PostgreSQL...")

        mock_logger.info.assert_called_once_with(
            "%s[%s/%s] %s", "", 1, 6, "Waiting for PostgreSQL..."
        )

    @patch("services.init.main.logger")
    def test_logs_phase_with_completion_status(self, mock_logger):
        """Should log phase message with completion checkmark."""
        _log_phase(3, 6, "Migrations complete", completed=True)

        mock_logger.info.assert_called_once_with("%s[%s/%s] %s", "✓", 3, 6, "Migrations complete")

    @patch("services.init.main.logger")
    def test_logs_all_phases_sequentially(self, mock_logger):
        """Should log multiple phases in sequence."""
        _log_phase(1, 6, "Step 1...")
        _log_phase(1, 6, "Step 1 done", completed=True)
        _log_phase(2, 6, "Step 2...")
        _log_phase(2, 6, "Step 2 done", completed=True)

        assert mock_logger.info.call_count == 4


class TestCompleteInitialization:
    """Tests for _complete_initialization helper."""

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.tempfile.gettempdir")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_logs_completion_banner_with_duration(
        self, mock_datetime, mock_path, mock_gettempdir, mock_logger, mock_time
    ):
        """Should log completion banner with calculated duration."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        end_time = datetime(2026, 1, 17, 12, 5, 30, tzinfo=UTC)
        mock_datetime.now.return_value = end_time
        mock_gettempdir.return_value = "/tmp"

        mock_marker = Mock()
        mock_path_instance = Mock()
        mock_path_instance.__truediv__ = Mock(return_value=mock_marker)
        mock_path.return_value = mock_path_instance
        mock_time.sleep.side_effect = KeyboardInterrupt  # Prevent infinite loop

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        mock_datetime.now.assert_called_once_with(UTC)
        calls = mock_logger.info.call_args_list
        log_messages = [call[0][0] for call in calls]
        assert "Environment Initialization Complete" in log_messages
        # Check for duration format string
        assert "Duration: %.2f seconds" in log_messages
        # Verify duration value was passed
        duration_call = [c for c in calls if len(c[0]) > 1 and "Duration" in c[0][0]]
        assert len(duration_call) == 1
        assert duration_call[0][0][1] == pytest.approx(330.0)

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.tempfile.gettempdir")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_creates_completion_marker_file(
        self, mock_datetime, mock_path, mock_gettempdir, mock_logger, mock_time
    ):
        """Should create init-complete marker file in temp directory."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = datetime(2026, 1, 17, 12, 0, 10, tzinfo=UTC)
        mock_gettempdir.return_value = "/tmp"

        mock_marker = Mock()
        mock_path_instance = Mock()
        mock_path_instance.__truediv__ = Mock(return_value=mock_marker)
        mock_path.return_value = mock_path_instance
        mock_time.sleep.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        mock_gettempdir.assert_called_once()
        mock_path.assert_called_once_with("/tmp")
        mock_marker.touch.assert_called_once()

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_enters_infinite_sleep_loop(self, mock_datetime, mock_path, mock_logger, mock_time):
        """Should enter infinite sleep loop with SECONDS_PER_DAY interval."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = datetime(2026, 1, 17, 12, 0, 5, tzinfo=UTC)

        mock_time.sleep.side_effect = [None, None, KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        assert mock_time.sleep.call_count == 3
        mock_time.sleep.assert_called_with(SECONDS_PER_DAY)

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_logs_sleep_mode_message(self, mock_datetime, mock_path, mock_logger, mock_time):
        """Should log message about entering sleep mode."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = datetime(2026, 1, 17, 12, 0, 5, tzinfo=UTC)

        mock_time.sleep.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "Entering sleep mode. Container will remain healthy." in log_calls
