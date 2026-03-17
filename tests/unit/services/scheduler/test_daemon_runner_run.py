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


"""Unit tests for the shared daemon runner."""

import signal
from unittest.mock import MagicMock, patch

from services.scheduler.daemon_runner import run_daemon


class TestRunDaemon:
    @patch("services.scheduler.daemon_runner.flush_telemetry")
    def test_calls_daemon_run(self, mock_flush):
        mock_daemon = MagicMock()

        run_daemon(mock_daemon)

        mock_daemon.run.assert_called_once()

    @patch("services.scheduler.daemon_runner.flush_telemetry")
    def test_registers_sigterm_and_sigint(self, mock_flush):
        mock_daemon = MagicMock()

        with patch("services.scheduler.daemon_runner.signal.signal") as mock_signal:
            run_daemon(mock_daemon)

        registered = {c.args[0] for c in mock_signal.call_args_list}
        assert signal.SIGTERM in registered
        assert signal.SIGINT in registered

    @patch("services.scheduler.daemon_runner.flush_telemetry")
    def test_shutdown_flag_initially_false(self, mock_flush):
        mock_daemon = MagicMock()
        captured = {}

        def capture_run(shutdown_fn):
            captured["initial"] = shutdown_fn()

        mock_daemon.run.side_effect = capture_run

        run_daemon(mock_daemon)

        assert captured["initial"] is False

    @patch("services.scheduler.daemon_runner.flush_telemetry")
    def test_signal_sets_shutdown_flag(self, mock_flush):
        mock_daemon = MagicMock()
        captured_handler = {}

        def capture_run(shutdown_fn):
            captured_handler["fn"] = shutdown_fn

        mock_daemon.run.side_effect = capture_run

        with patch("services.scheduler.daemon_runner.signal.signal") as mock_signal:
            run_daemon(mock_daemon)

        # Simulate SIGTERM delivery
        sigterm_handler = next(
            c.args[1] for c in mock_signal.call_args_list if c.args[0] == signal.SIGTERM
        )
        # Prevent the signal handler from calling cov.stop()/cov.save() on the live
        # pytest-cov instance, which would halt coverage measurement for subsequent tests.
        with patch(
            "services.scheduler.daemon_runner._coverage.Coverage.current",
            return_value=None,
        ):
            sigterm_handler(signal.SIGTERM, None)

        assert captured_handler["fn"]() is True

    @patch("services.scheduler.daemon_runner.flush_telemetry")
    def test_flush_telemetry_called_on_clean_exit(self, mock_flush):
        mock_daemon = MagicMock()

        run_daemon(mock_daemon)

        mock_flush.assert_called_once()

    @patch("services.scheduler.daemon_runner.flush_telemetry")
    def test_flush_telemetry_called_even_on_exception(self, mock_flush):
        mock_daemon = MagicMock()
        mock_daemon.run.side_effect = RuntimeError("daemon failure")

        try:
            run_daemon(mock_daemon)
        except RuntimeError:
            pass

        mock_flush.assert_called_once()
