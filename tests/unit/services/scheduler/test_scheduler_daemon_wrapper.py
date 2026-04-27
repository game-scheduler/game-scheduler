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


"""Unit tests for the unified scheduler daemon wrapper."""

import signal
from unittest.mock import ANY, MagicMock, patch

import services.scheduler.scheduler_daemon_wrapper as wrapper


class TestMainStartsThreeDaemonThreads:
    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_creates_three_scheduler_daemon_instances(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush
    ):
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        wrapper.main()

        assert mock_daemon_cls.call_count == 3

    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_creates_notification_daemon(self, mock_daemon_cls, mock_init_telemetry, mock_flush):
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        wrapper.main()

        service_names = [c.kwargs["service_name"] for c in mock_daemon_cls.call_args_list]
        assert "notification" in service_names

    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_creates_status_transition_daemon(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush
    ):
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        wrapper.main()

        service_names = [c.kwargs["service_name"] for c in mock_daemon_cls.call_args_list]
        assert "status-transition" in service_names

    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_creates_participant_action_daemon(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush
    ):
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        wrapper.main()

        service_names = [c.kwargs["service_name"] for c in mock_daemon_cls.call_args_list]
        assert "participant-action" in service_names


class TestMainSignalHandling:
    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_registers_sigterm_and_sigint(self, mock_daemon_cls, mock_init_telemetry, mock_flush):
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.scheduler.daemon_runner.signal.signal") as mock_signal:
            wrapper.main()

        registered = {c.args[0] for c in mock_signal.call_args_list}
        assert signal.SIGTERM in registered
        assert signal.SIGINT in registered

    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_shutdown_flag_starts_false(self, mock_daemon_cls, mock_init_telemetry, mock_flush):
        captured = {}
        mock_instance = MagicMock()

        def capture_flag(flag):
            captured["initial"] = flag()

        mock_instance.run.side_effect = capture_flag
        mock_daemon_cls.return_value = mock_instance

        wrapper.main()

        assert captured["initial"] is False

    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_flushes_telemetry_after_join(self, mock_daemon_cls, mock_init_telemetry):
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry") as mock_flush:
            wrapper.main()

            mock_flush.assert_called_once_with()


class TestMainEdgeCases:
    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_thread_crash_does_not_block_other_daemons(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush
    ):
        """A crashing daemon thread does not prevent the others from running."""
        daemon_a, daemon_b, daemon_c = MagicMock(), MagicMock(), MagicMock()
        daemon_a.run.side_effect = RuntimeError("daemon a failed")
        daemon_b.run.side_effect = lambda flag: None
        daemon_c.run.side_effect = lambda flag: None
        mock_daemon_cls.side_effect = [daemon_a, daemon_b, daemon_c]

        wrapper.main()

        daemon_a.run.assert_called_once_with(ANY)
        daemon_b.run.assert_called_once_with(ANY)
        daemon_c.run.assert_called_once_with(ANY)

    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_log_level_defaults_to_info(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush, monkeypatch
    ):
        """LOG_LEVEL defaults to INFO when the env var is absent."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.scheduler.scheduler_daemon_wrapper.logging.basicConfig") as mock_cfg:
            wrapper.main()

        assert mock_cfg.call_args.kwargs["level"] == 20  # logging.INFO == 20

    @patch("services.scheduler.scheduler_daemon_wrapper.flush_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.init_telemetry")
    @patch("services.scheduler.scheduler_daemon_wrapper.SchedulerDaemon")
    def test_log_level_respects_env_var(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush, monkeypatch
    ):
        """LOG_LEVEL env var is passed to basicConfig."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.scheduler.scheduler_daemon_wrapper.logging.basicConfig") as mock_cfg:
            wrapper.main()

        assert mock_cfg.call_args.kwargs["level"] == 10  # logging.DEBUG == 10
