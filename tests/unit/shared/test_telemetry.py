# Copyright 2025-2026 Bret McKee
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


"""Tests for OpenTelemetry instrumentation initialization."""

from unittest.mock import MagicMock, patch

from shared.telemetry import flush_telemetry, get_tracer, init_telemetry


class TestInitTelemetry:
    """Tests for init_telemetry function."""

    def test_skips_initialization_when_pytest_running(self, monkeypatch):
        """Should skip telemetry initialization when PYTEST_RUNNING is set."""
        monkeypatch.setenv("PYTEST_RUNNING", "1")

        with patch("shared.telemetry.TracerProvider") as mock_tracer_provider:
            init_telemetry("test-service")

            mock_tracer_provider.assert_not_called()

    def test_skips_initialization_when_pytest_current_test(self, monkeypatch):
        """Should skip telemetry initialization when PYTEST_CURRENT_TEST is set."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_something.py::test_func")

        with patch("shared.telemetry.TracerProvider") as mock_tracer_provider:
            init_telemetry("test-service")

            mock_tracer_provider.assert_not_called()

    def test_initializes_tracing_with_default_endpoint(self, monkeypatch):
        """Should initialize tracing with default OTLP endpoint."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        mock_tracer_provider = MagicMock()
        mock_span_processor = MagicMock()
        mock_span_exporter = MagicMock()

        with (
            patch("shared.telemetry.TracerProvider", return_value=mock_tracer_provider),
            patch("shared.telemetry.BatchSpanProcessor", return_value=mock_span_processor),
            patch("shared.telemetry.OTLPSpanExporter", return_value=mock_span_exporter),
            patch("shared.telemetry.trace.set_tracer_provider"),
            patch("shared.telemetry.MeterProvider"),
            patch("shared.telemetry.LoggerProvider"),
            patch("shared.telemetry.SQLAlchemyInstrumentor"),
            patch("shared.telemetry.AsyncPGInstrumentor"),
            patch("shared.telemetry.RedisInstrumentor"),
            patch("shared.telemetry.AioPikaInstrumentor"),
            patch("shared.telemetry.logging.getLogger"),
        ):
            init_telemetry("test-service")

            mock_tracer_provider.add_span_processor.assert_called_once_with(mock_span_processor)

    def test_initializes_tracing_with_custom_endpoint(self, monkeypatch):
        """Should initialize tracing with custom OTLP endpoint from environment."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://custom:4318")

        mock_span_exporter = MagicMock()

        with (
            patch("shared.telemetry.TracerProvider"),
            patch("shared.telemetry.BatchSpanProcessor"),
            patch(
                "shared.telemetry.OTLPSpanExporter", return_value=mock_span_exporter
            ) as mock_exporter_class,
            patch("shared.telemetry.trace.set_tracer_provider"),
            patch("shared.telemetry.MeterProvider"),
            patch("shared.telemetry.LoggerProvider"),
            patch("shared.telemetry.SQLAlchemyInstrumentor"),
            patch("shared.telemetry.AsyncPGInstrumentor"),
            patch("shared.telemetry.RedisInstrumentor"),
            patch("shared.telemetry.AioPikaInstrumentor"),
            patch("shared.telemetry.logging.getLogger"),
        ):
            init_telemetry("test-service")

            mock_exporter_class.assert_called_once_with(endpoint="http://custom:4318/v1/traces")

    def test_initializes_metrics_with_periodic_export(self, monkeypatch):
        """Should initialize metrics with 60-second export interval."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_meter_provider = MagicMock()
        mock_metric_reader = MagicMock()

        with (
            patch("shared.telemetry.TracerProvider"),
            patch("shared.telemetry.BatchSpanProcessor"),
            patch("shared.telemetry.OTLPSpanExporter"),
            patch("shared.telemetry.trace.set_tracer_provider"),
            patch(
                "shared.telemetry.PeriodicExportingMetricReader",
                return_value=mock_metric_reader,
            ) as mock_reader_class,
            patch("shared.telemetry.OTLPMetricExporter"),
            patch("shared.telemetry.MeterProvider", return_value=mock_meter_provider),
            patch("shared.telemetry.metrics.set_meter_provider"),
            patch("shared.telemetry.LoggerProvider"),
            patch("shared.telemetry.SQLAlchemyInstrumentor"),
            patch("shared.telemetry.AsyncPGInstrumentor"),
            patch("shared.telemetry.RedisInstrumentor"),
            patch("shared.telemetry.AioPikaInstrumentor"),
            patch("shared.telemetry.logging.getLogger"),
        ):
            init_telemetry("test-service")

            mock_reader_class.assert_called_once()
            call_kwargs = mock_reader_class.call_args[1]
            assert call_kwargs["export_interval_millis"] == 60000

    def test_initializes_logging_with_trace_correlation(self, monkeypatch):
        """Should initialize logging with OpenTelemetry handler for trace correlation."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_logger_provider = MagicMock()
        mock_logging_handler = MagicMock()
        mock_root_logger = MagicMock()

        with (
            patch("shared.telemetry.TracerProvider"),
            patch("shared.telemetry.BatchSpanProcessor"),
            patch("shared.telemetry.OTLPSpanExporter"),
            patch("shared.telemetry.trace.set_tracer_provider"),
            patch("shared.telemetry.MeterProvider"),
            patch("shared.telemetry.metrics.set_meter_provider"),
            patch("shared.telemetry.LoggerProvider", return_value=mock_logger_provider),
            patch("shared.telemetry.BatchLogRecordProcessor"),
            patch("shared.telemetry.OTLPLogExporter"),
            patch(
                "shared.telemetry.LoggingHandler", return_value=mock_logging_handler
            ) as mock_handler_class,
            patch("shared.telemetry.logging.getLogger", return_value=mock_root_logger),
            patch("shared.telemetry.SQLAlchemyInstrumentor"),
            patch("shared.telemetry.AsyncPGInstrumentor"),
            patch("shared.telemetry.RedisInstrumentor"),
            patch("shared.telemetry.AioPikaInstrumentor"),
        ):
            init_telemetry("test-service")

            mock_handler_class.assert_called_once()
            mock_root_logger.addHandler.assert_called_once_with(mock_logging_handler)

    def test_enables_auto_instrumentation(self, monkeypatch):
        """Should enable auto-instrumentation for common libraries."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_sqlalchemy = MagicMock()
        mock_asyncpg = MagicMock()
        mock_redis = MagicMock()
        mock_aiopika = MagicMock()

        with (
            patch("shared.telemetry.TracerProvider"),
            patch("shared.telemetry.BatchSpanProcessor"),
            patch("shared.telemetry.OTLPSpanExporter"),
            patch("shared.telemetry.trace.set_tracer_provider"),
            patch("shared.telemetry.MeterProvider"),
            patch("shared.telemetry.metrics.set_meter_provider"),
            patch("shared.telemetry.LoggerProvider"),
            patch("shared.telemetry.BatchLogRecordProcessor"),
            patch("shared.telemetry.OTLPLogExporter"),
            patch("shared.telemetry.LoggingHandler"),
            patch("shared.telemetry.logging.getLogger"),
            patch("shared.telemetry.SQLAlchemyInstrumentor", return_value=mock_sqlalchemy),
            patch("shared.telemetry.AsyncPGInstrumentor", return_value=mock_asyncpg),
            patch("shared.telemetry.RedisInstrumentor", return_value=mock_redis),
            patch("shared.telemetry.AioPikaInstrumentor", return_value=mock_aiopika),
        ):
            init_telemetry("test-service")

            mock_sqlalchemy.instrument.assert_called_once()
            mock_asyncpg.instrument.assert_called_once()
            mock_redis.instrument.assert_called_once()
            mock_aiopika.instrument.assert_called_once()


class TestFlushTelemetry:
    """Tests for flush_telemetry function."""

    def test_skips_flush_when_pytest_running(self, monkeypatch):
        """Should skip flush when PYTEST_RUNNING is set."""
        monkeypatch.setenv("PYTEST_RUNNING", "1")

        with patch("shared.telemetry.trace.get_tracer_provider") as mock_get_tracer:
            flush_telemetry()

            mock_get_tracer.assert_not_called()

    def test_skips_flush_when_pytest_current_test(self, monkeypatch):
        """Should skip flush when PYTEST_CURRENT_TEST is set."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_something.py::test_func")

        with patch("shared.telemetry.trace.get_tracer_provider") as mock_get_tracer:
            flush_telemetry()

            mock_get_tracer.assert_not_called()

    def test_flushes_tracer_provider(self, monkeypatch):
        """Should flush tracer provider with 5-second timeout."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_tracer_provider = MagicMock()
        mock_tracer_provider.force_flush = MagicMock()

        with (
            patch(
                "shared.telemetry.trace.get_tracer_provider",
                return_value=mock_tracer_provider,
            ),
            patch("shared.telemetry.metrics.get_meter_provider"),
        ):
            flush_telemetry()

            mock_tracer_provider.force_flush.assert_called_once_with(timeout_millis=5000)

    def test_flushes_meter_provider(self, monkeypatch):
        """Should flush meter provider with 5-second timeout."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_meter_provider = MagicMock()
        mock_meter_provider.force_flush = MagicMock()

        with (
            patch("shared.telemetry.trace.get_tracer_provider"),
            patch(
                "shared.telemetry.metrics.get_meter_provider",
                return_value=mock_meter_provider,
            ),
        ):
            flush_telemetry()

            mock_meter_provider.force_flush.assert_called_once_with(timeout_millis=5000)

    def test_handles_provider_without_force_flush(self, monkeypatch):
        """Should handle providers that don't have force_flush method."""
        monkeypatch.delenv("PYTEST_RUNNING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_tracer_provider = MagicMock(spec=[])  # No force_flush method
        mock_meter_provider = MagicMock(spec=[])  # No force_flush method

        with (
            patch(
                "shared.telemetry.trace.get_tracer_provider",
                return_value=mock_tracer_provider,
            ),
            patch(
                "shared.telemetry.metrics.get_meter_provider",
                return_value=mock_meter_provider,
            ),
        ):
            flush_telemetry()


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_returns_tracer_from_global_provider(self):
        """Should return tracer from global tracer provider."""
        mock_tracer = MagicMock()
        mock_global_tracer_provider = MagicMock()
        mock_global_tracer_provider.get_tracer.return_value = mock_tracer

        with patch(
            "shared.telemetry.trace.get_tracer", return_value=mock_tracer
        ) as mock_get_tracer:
            result = get_tracer("test-module")

            mock_get_tracer.assert_called_once_with("test-module")
            assert result == mock_tracer
