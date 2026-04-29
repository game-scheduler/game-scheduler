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


# ruff: noqa: PLC2701  # OTLPLogExporter is only available via a private module; no public alternative exists.

"""
OpenTelemetry instrumentation initialization for Python services.

Provides centralized telemetry configuration for traces, metrics, and logs
with automatic instrumentation for common frameworks.
"""

import logging
import os

from opentelemetry import metrics, trace

# OpenTelemetry's official public API for OTLP exporters
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# OpenTelemetry's official public API for logging
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)


def init_telemetry(service_name: str, views: list[View] | None = None) -> None:
    """
    Initialize OpenTelemetry instrumentation for a Python service.

    Configures distributed tracing, metrics collection, and log correlation
    with automatic instrumentation for FastAPI, SQLAlchemy, asyncpg, Redis,
    and aio-pika.

    Args:
        service_name: Name of the service for telemetry identification
    """
    # Skip telemetry initialization in test environment
    # PYTEST_RUNNING is set in conftest.py before any imports
    # PYTEST_CURRENT_TEST is set by pytest during test execution
    if os.getenv("PYTEST_RUNNING") or os.getenv("PYTEST_CURRENT_TEST"):
        logger.debug("Skipping telemetry initialization for %s (test environment)", service_name)
        return

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://grafana-alloy:4318")
    resource = Resource.create({"service.name": service_name})

    logger.info("Initializing OpenTelemetry for service: %s", service_name)
    logger.info("OTLP endpoint: %s", otlp_endpoint)

    # Configure tracing
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{otlp_endpoint}/v1/traces",
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)
    logger.info("OpenTelemetry tracing initialized: %s/v1/traces", otlp_endpoint)

    # Configure metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=f"{otlp_endpoint}/v1/metrics",
        ),
        export_interval_millis=60000,
    )
    meter_provider = MeterProvider(
        resource=resource, metric_readers=[metric_reader], views=views or []
    )
    metrics.set_meter_provider(meter_provider)
    logger.info(
        "OpenTelemetry metrics initialized: %s/v1/metrics (export every 60s)",
        otlp_endpoint,
    )

    # Configure logging with OTLP export and trace correlation
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{otlp_endpoint}/v1/logs",
            )
        )
    )

    # Add OpenTelemetry logging handler to root logger for trace correlation
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    logger.info("OpenTelemetry logging initialized: %s/v1/logs", otlp_endpoint)

    # Auto-instrument common libraries
    SQLAlchemyInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()
    AioPikaInstrumentor().instrument()

    logger.info(
        "OpenTelemetry instrumentation enabled for %s (SQLAlchemy, asyncpg, Redis, aio-pika)",
        service_name,
    )
    # FastAPI instrumentation happens via middleware, initialized when app is created


def flush_telemetry() -> None:
    """
    Flush all pending telemetry data.

    Call this before exiting short-lived processes to ensure all buffered
    traces, metrics, and logs are sent to the backend.
    """
    if os.getenv("PYTEST_RUNNING") or os.getenv("PYTEST_CURRENT_TEST"):
        return

    logger.debug("Flushing telemetry data...")

    # Flush traces
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, "force_flush"):
        tracer_provider.force_flush(timeout_millis=5000)

    # Flush metrics
    meter_provider = metrics.get_meter_provider()
    if hasattr(meter_provider, "force_flush"):
        meter_provider.force_flush(timeout_millis=5000)

    logger.info("Telemetry data flushed")


def get_tracer(name: str) -> Tracer:
    """
    Get a tracer for manual span creation.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        OpenTelemetry tracer instance
    """
    return trace.get_tracer(name)
