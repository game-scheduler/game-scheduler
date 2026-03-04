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


"""Integration tests for participant action daemon.

Verifies that the participant-action-daemon container picks up overdue
ParticipantActionSchedule records, marks them as processed, and publishes
PARTICIPANT_DROP_DUE events to the bot_events RabbitMQ queue.
"""

import json
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.messaging.infrastructure import QUEUE_BOT_EVENTS
from shared.models.participant import ParticipantType
from tests.integration.conftest import consume_one_message, get_queue_message_count
from tests.shared.polling import wait_for_db_condition_sync

pytestmark = pytest.mark.integration


@pytest.fixture
def clean_bot_events_queue(rabbitmq_channel):
    """Purge the bot events queue before and after the test."""
    time.sleep(0.5)
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    yield

    time.sleep(0.5)
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)


def _insert_participant(admin_db_sync, game_id: str, user_id: str) -> str:
    """Insert a game participant and return its ID."""
    participant_id = str(uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": 1,
            "position_type": int(ParticipantType.HOST_ADDED),
        },
    )
    admin_db_sync.commit()
    return participant_id


class TestParticipantActionDaemonIntegration:
    """Integration tests for participant action daemon service.

    These tests run against the actual participant-action-daemon container
    started by docker-compose, validating that the running service processes
    overdue ParticipantActionSchedule records correctly.
    """

    def test_daemon_processes_overdue_action(
        self,
        admin_db_sync,
        clean_bot_events_queue,
        rabbitmq_channel,
        test_game_environment,
    ):
        """Running participant-action-daemon marks overdue records processed and publishes event."""
        env = test_game_environment()
        game_id = env["game"]["id"]
        user_id = env["user"]["id"]

        participant_id = _insert_participant(admin_db_sync, game_id, user_id)

        action_id = str(uuid4())
        action_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO participant_action_schedule
                    (id, game_id, participant_id, action, action_time, processed)
                VALUES (:id, :game_id, :participant_id, :action, :action_time, :processed)
                """
            ),
            {
                "id": action_id,
                "game_id": game_id,
                "participant_id": participant_id,
                "action": "drop",
                "action_time": action_time,
                "processed": False,
            },
        )
        admin_db_sync.commit()

        # Wake the daemon; the participant_action_schedule table has no automatic trigger,
        # so application code must send NOTIFY after inserting/deleting records.
        admin_db_sync.execute(text("SELECT pg_notify('participant_action_schedule_changed', '')"))
        admin_db_sync.commit()

        result = wait_for_db_condition_sync(
            admin_db_sync,
            "SELECT processed FROM participant_action_schedule WHERE id = :id",
            {"id": action_id},
            lambda row: row[0] is True,
            timeout=5,
            interval=0.5,
            description="participant action schedule marked as processed",
        )
        assert result[0] is True, "ParticipantActionSchedule record should be marked as processed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 1, "Should have published 1 PARTICIPANT_DROP_DUE event"

        _method, _properties, body = consume_one_message(
            rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5
        )
        assert body is not None, "RabbitMQ message body should not be None"
        message = json.loads(body)
        assert message["data"]["game_id"] == game_id
        assert message["data"]["participant_id"] == participant_id

    def test_daemon_waits_for_future_action(
        self,
        admin_db_sync,
        clean_bot_events_queue,
        rabbitmq_channel,
        test_game_environment,
    ):
        """Running daemon does not process future-dated ParticipantActionSchedule records."""
        env = test_game_environment()
        game_id = env["game"]["id"]
        user_id = env["user"]["id"]

        participant_id = _insert_participant(admin_db_sync, game_id, user_id)

        action_id = str(uuid4())
        action_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO participant_action_schedule
                    (id, game_id, participant_id, action, action_time, processed)
                VALUES (:id, :game_id, :participant_id, :action, :action_time, :processed)
                """
            ),
            {
                "id": action_id,
                "game_id": game_id,
                "participant_id": participant_id,
                "action": "drop",
                "action_time": action_time,
                "processed": False,
            },
        )
        admin_db_sync.commit()

        time.sleep(2)

        result = admin_db_sync.execute(
            text("SELECT processed FROM participant_action_schedule WHERE id = :id"),
            {"id": action_id},
        ).fetchone()

        assert result[0] is False, "Future action should not be processed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 0, "Should have no messages for future action"
