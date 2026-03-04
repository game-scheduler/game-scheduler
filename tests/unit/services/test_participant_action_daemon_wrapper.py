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


"""Unit tests for participant action daemon wrapper."""

from unittest.mock import MagicMock, patch

import services.scheduler.participant_action_daemon_wrapper as wrapper
from services.scheduler.participant_action_event_builder import (
    build_participant_action_event,
)
from shared.models import ParticipantActionSchedule


class TestMain:
    @patch("services.scheduler.participant_action_daemon_wrapper.run_daemon")
    @patch("services.scheduler.participant_action_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.participant_action_daemon_wrapper.SchedulerDaemon")
    def test_creates_daemon_with_correct_parameters(
        self, mock_daemon_cls, mock_init, mock_run_daemon
    ):
        mock_daemon_cls.return_value = MagicMock()

        wrapper.main()

        mock_daemon_cls.assert_called_once()
        kwargs = mock_daemon_cls.call_args.kwargs
        assert kwargs["notify_channel"] == "participant_action_schedule_changed"
        assert kwargs["model_class"] is ParticipantActionSchedule
        assert kwargs["time_field"] == "action_time"
        assert kwargs["status_field"] == "processed"
        assert kwargs["event_builder"] is build_participant_action_event
        assert kwargs["_process_dlq"] is False

    @patch("services.scheduler.participant_action_daemon_wrapper.run_daemon")
    @patch("services.scheduler.participant_action_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.participant_action_daemon_wrapper.SchedulerDaemon")
    def test_passes_daemon_to_run_daemon(self, mock_daemon_cls, mock_init, mock_run_daemon):
        mock_instance = MagicMock()
        mock_daemon_cls.return_value = mock_instance

        wrapper.main()

        mock_run_daemon.assert_called_once_with(mock_instance)
