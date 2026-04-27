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


"""Unit tests for services.scheduler.daemon_runner."""

import signal
from unittest.mock import MagicMock, patch

from services.scheduler.daemon_runner import register_shutdown_signals


class TestSignalHandlerCoverageFlush:
    """Tests for coverage flush inside the registered signal handler."""

    def test_flushes_active_coverage_on_signal(self):
        """Should stop and save coverage when an instance is active at signal time."""
        captured = {}

        def capture_signal(sig, fn):
            captured[sig] = fn

        mock_cov = MagicMock()

        with patch(
            "services.scheduler.daemon_runner.signal.signal",
            side_effect=capture_signal,
        ):
            register_shutdown_signals()

        with patch(
            "services.scheduler.daemon_runner._coverage.Coverage.current",
            return_value=mock_cov,
        ):
            captured[signal.SIGTERM](signal.SIGTERM, None)

        assert mock_cov.stop.call_count == 1
        assert mock_cov.save.call_count == 1

    def test_no_error_when_no_active_coverage(self):
        """Should not crash when no coverage instance is active."""
        captured = {}

        def capture_signal(sig, fn):
            captured[sig] = fn

        with patch(
            "services.scheduler.daemon_runner.signal.signal",
            side_effect=capture_signal,
        ):
            register_shutdown_signals()

        with patch(
            "services.scheduler.daemon_runner._coverage.Coverage.current",
            return_value=None,
        ):
            captured[signal.SIGTERM](signal.SIGTERM, None)

        assert True  # no error raised when no coverage instance is active
