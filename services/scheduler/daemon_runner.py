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


"""Shared signal handling and lifecycle runner for scheduler daemons."""

import logging
import signal
from types import FrameType

from shared.telemetry import flush_telemetry

from .generic_scheduler_daemon import SchedulerDaemon

logger = logging.getLogger(__name__)


def run_daemon(daemon: SchedulerDaemon) -> None:
    """
    Run a SchedulerDaemon with standard SIGTERM/SIGINT handling and telemetry flush.

    Registers signal handlers, starts the daemon loop, and ensures telemetry is
    flushed on exit regardless of how the process terminates.
    """
    shutdown_requested = False

    def _signal_handler(_signum: int, _frame: FrameType | None) -> None:
        nonlocal shutdown_requested
        logger.info("Received signal %s, initiating graceful shutdown", _signum)
        shutdown_requested = True

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        daemon.run(lambda: shutdown_requested)
    finally:
        flush_telemetry()
