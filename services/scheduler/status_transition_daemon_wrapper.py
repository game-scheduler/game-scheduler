# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""
Status transition daemon wrapper for generic scheduler daemon.

Instantiates SchedulerDaemon with status-transition-specific parameters
to handle automatic game status transitions.
"""

import logging
import os
import signal

from shared.database import BASE_DATABASE_URL
from shared.models import GameStatusSchedule

from .event_builders import build_status_transition_event
from .generic_scheduler_daemon import SchedulerDaemon

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_requested = True


def main() -> None:
    """Entry point for status transition daemon."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    daemon = SchedulerDaemon(
        database_url=BASE_DATABASE_URL,
        rabbitmq_url=rabbitmq_url,
        notify_channel="game_status_schedule_changed",
        model_class=GameStatusSchedule,
        time_field="transition_time",
        status_field="executed",
        event_builder=build_status_transition_event,
        process_dlq=True,
        dlq_check_interval=900,
    )

    daemon.run(lambda: shutdown_requested)


if __name__ == "__main__":
    main()
