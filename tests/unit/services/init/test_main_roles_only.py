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


"""Tests for INIT_ROLES_ONLY behavior in services/init/main.py."""

import os
from unittest.mock import ANY, Mock, patch

from services.init.main import main


class TestMainWithInitRolesOnly:
    """Tests verifying INIT_ROLES_ONLY=true causes main() to exit after role creation."""

    @patch("services.init.main.flush_telemetry")
    @patch("services.init.main.trace")
    @patch("services.init.main._complete_initialization")
    @patch("services.init.main.initialize_rabbitmq")
    @patch("services.init.main.verify_schema")
    @patch("services.init.main.run_migrations")
    @patch("services.init.main.create_database_users")
    @patch("services.init.main.wait_for_postgres")
    @patch("services.init.main._initialize_telemetry_and_logging")
    @patch.dict("os.environ", {"INIT_ROLES_ONLY": "true"})
    def test_exits_zero_after_role_creation_when_flag_set(
        self,
        mock_init_telemetry,
        mock_wait,
        mock_create_users,
        mock_migrations,
        mock_verify,
        mock_rabbitmq,
        mock_complete,
        mock_trace,
        mock_flush,
    ):
        """When INIT_ROLES_ONLY=true, main() returns 0 after create_database_users."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_init_telemetry.return_value = (mock_tracer, Mock())
        mock_trace.Status = Mock()
        mock_trace.StatusCode = Mock()

        result = main()

        assert result == 0
        mock_wait.assert_called_once_with()  # assert-not-weak: predates reason
        mock_create_users.assert_called_once_with()  # assert-not-weak: predates reason
        mock_complete.assert_called_once_with(ANY)
        mock_migrations.assert_not_called()
        mock_verify.assert_not_called()
        mock_rabbitmq.assert_not_called()

    @patch("services.init.main.flush_telemetry")
    @patch("services.init.main.trace")
    @patch("services.init.main._complete_initialization")
    @patch("services.init.main.initialize_rabbitmq")
    @patch("services.init.main.verify_schema")
    @patch("services.init.main.run_migrations")
    @patch("services.init.main.create_database_users")
    @patch("services.init.main.wait_for_postgres")
    @patch("services.init.main._initialize_telemetry_and_logging")
    @patch("services.init.main.logger")
    @patch.dict("os.environ", {"INIT_ROLES_ONLY": "true"})
    def test_logs_early_exit_message_when_flag_set(
        self,
        mock_logger,
        mock_init_telemetry,
        mock_wait,
        mock_create_users,
        mock_migrations,
        mock_verify,
        mock_rabbitmq,
        mock_complete,
        mock_trace,
        mock_flush,
    ):
        """When INIT_ROLES_ONLY=true, main() logs that it is exiting early."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_init_telemetry.return_value = (mock_tracer, Mock())
        mock_trace.Status = Mock()
        mock_trace.StatusCode = Mock()

        main()

        log_messages = [c[0][0] for c in mock_logger.info.call_args_list]
        assert any("INIT_ROLES_ONLY" in msg for msg in log_messages)


class TestMainWithoutInitRolesOnly:
    """Tests verifying all five phases run when INIT_ROLES_ONLY is absent."""

    @patch("services.init.main.flush_telemetry")
    @patch("services.init.main.trace")
    @patch("services.init.main._complete_initialization")
    @patch("services.init.main.initialize_rabbitmq")
    @patch("services.init.main.verify_schema")
    @patch("services.init.main.run_migrations")
    @patch("services.init.main.create_database_users")
    @patch("services.init.main.wait_for_postgres")
    @patch("services.init.main._initialize_telemetry_and_logging")
    @patch.dict("os.environ", {}, clear=False)
    def test_all_five_phases_run_when_flag_absent(
        self,
        mock_init_telemetry,
        mock_wait,
        mock_create_users,
        mock_migrations,
        mock_verify,
        mock_rabbitmq,
        mock_complete,
        mock_trace,
        mock_flush,
    ):
        """When INIT_ROLES_ONLY is not set, all five phases execute."""
        os.environ.pop("INIT_ROLES_ONLY", None)

        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_init_telemetry.return_value = (mock_tracer, Mock())
        mock_trace.Status = Mock()
        mock_trace.StatusCode = Mock()

        main()

        mock_wait.assert_called_once_with()  # assert-not-weak: predates reason
        mock_create_users.assert_called_once_with()  # assert-not-weak: predates reason
        mock_migrations.assert_called_once_with()  # assert-not-weak: predates reason
        mock_verify.assert_called_once_with()  # assert-not-weak: predates reason
        mock_rabbitmq.assert_called_once_with()  # assert-not-weak: predates reason

    @patch("services.init.main.flush_telemetry")
    @patch("services.init.main.trace")
    @patch("services.init.main._complete_initialization")
    @patch("services.init.main.initialize_rabbitmq")
    @patch("services.init.main.verify_schema")
    @patch("services.init.main.run_migrations")
    @patch("services.init.main.create_database_users")
    @patch("services.init.main.wait_for_postgres")
    @patch("services.init.main._initialize_telemetry_and_logging")
    @patch.dict("os.environ", {"INIT_ROLES_ONLY": ""})
    def test_all_five_phases_run_when_flag_empty(
        self,
        mock_init_telemetry,
        mock_wait,
        mock_create_users,
        mock_migrations,
        mock_verify,
        mock_rabbitmq,
        mock_complete,
        mock_trace,
        mock_flush,
    ):
        """When INIT_ROLES_ONLY is set to empty string, all five phases execute."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_init_telemetry.return_value = (mock_tracer, Mock())
        mock_trace.Status = Mock()
        mock_trace.StatusCode = Mock()

        main()

        mock_wait.assert_called_once_with()  # assert-not-weak: predates reason
        mock_create_users.assert_called_once_with()  # assert-not-weak: predates reason
        mock_migrations.assert_called_once_with()  # assert-not-weak: predates reason
        mock_verify.assert_called_once_with()  # assert-not-weak: predates reason
        mock_rabbitmq.assert_called_once_with()  # assert-not-weak: predates reason
