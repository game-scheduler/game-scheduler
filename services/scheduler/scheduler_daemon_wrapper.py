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


"""Unified scheduler daemon wrapper running all three schedulers as threads."""

import logging
import os
import threading

from shared.database import BASE_DATABASE_URL
from shared.models import (
    GameStatusSchedule,
    NotificationSchedule,
    ParticipantActionSchedule,
)
from shared.telemetry import flush_telemetry, init_telemetry

from .daemon_runner import register_shutdown_signals
from .event_builders import build_notification_event, build_status_transition_event
from .generic_scheduler_daemon import SchedulerDaemon
from .participant_action_event_builder import build_participant_action_event

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for the unified scheduler daemon.

    Starts three SchedulerDaemon instances as daemon threads sharing a single
    shutdown flag. SIGTERM and SIGINT set the flag; the main thread then waits
    for all threads to finish before flushing telemetry.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    init_telemetry("scheduler-daemon")

    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    shutdown_flag = register_shutdown_signals()

    daemons = [
        SchedulerDaemon(
            service_name="notification",
            database_url=BASE_DATABASE_URL,
            rabbitmq_url=rabbitmq_url,
            notify_channel="notification_schedule_changed",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=build_notification_event,
        ),
        SchedulerDaemon(
            service_name="status-transition",
            database_url=BASE_DATABASE_URL,
            rabbitmq_url=rabbitmq_url,
            notify_channel="game_status_schedule_changed",
            model_class=GameStatusSchedule,
            time_field="transition_time",
            status_field="executed",
            event_builder=build_status_transition_event,
        ),
        SchedulerDaemon(
            service_name="participant-action",
            database_url=BASE_DATABASE_URL,
            rabbitmq_url=rabbitmq_url,
            notify_channel="participant_action_schedule_changed",
            model_class=ParticipantActionSchedule,
            time_field="action_time",
            status_field="processed",
            event_builder=build_participant_action_event,
        ),
    ]

    def _run_daemon(daemon: SchedulerDaemon) -> None:
        try:
            daemon.run(shutdown_flag)
        except Exception:
            logger.exception(
                "Scheduler daemon for channel %s exited unexpectedly",
                daemon.notify_channel,
            )

    threads = [threading.Thread(target=_run_daemon, args=(d,), daemon=True) for d in daemons]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    flush_telemetry()


if __name__ == "__main__":
    main()
