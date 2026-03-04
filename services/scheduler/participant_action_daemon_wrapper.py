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


"""
Participant action daemon wrapper for generic scheduler daemon.

Instantiates SchedulerDaemon with participant-action-specific parameters
to handle deadline-based participant drop actions (e.g. auto-drop when a
clone confirmation is not acknowledged before the deadline).
"""

import logging
import os

from shared.database import BASE_DATABASE_URL
from shared.models import ParticipantActionSchedule
from shared.telemetry import init_telemetry

from .daemon_runner import run_daemon
from .generic_scheduler_daemon import SchedulerDaemon
from .participant_action_event_builder import build_participant_action_event

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for participant action daemon."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    init_telemetry("participant-action-daemon")

    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    daemon = SchedulerDaemon(
        database_url=BASE_DATABASE_URL,
        rabbitmq_url=rabbitmq_url,
        notify_channel="participant_action_schedule_changed",
        model_class=ParticipantActionSchedule,
        time_field="action_time",
        status_field="processed",
        event_builder=build_participant_action_event,
        _process_dlq=False,
    )

    run_daemon(daemon)


if __name__ == "__main__":
    main()
