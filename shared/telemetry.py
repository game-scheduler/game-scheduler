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
OpenTelemetry instrumentation initialization for Python services.

Provides centralized telemetry configuration for traces, metrics, and logs
with automatic instrumentation for common frameworks.
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def init_telemetry(service_name: str) -> None:
    """
    Initialize OpenTelemetry instrumentation for a Python service.

    Configures distributed tracing, metrics collection, and log correlation
    with automatic instrumentation for FastAPI, SQLAlchemy, asyncpg, Redis,
    and aio-pika.

    Args:
        service_name: Name of the service for telemetry identification
    """
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://grafana-alloy:4318")
    resource = Resource.create({"service.name": service_name})

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
    logger.info("OpenTelemetry tracing initialized")

    # Configure metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=f"{otlp_endpoint}/v1/metrics",
        ),
        export_interval_millis=60000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    logger.info("OpenTelemetry metrics initialized")

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
    logger.info("OpenTelemetry logging initialized")

    # Auto-instrument common libraries
    SQLAlchemyInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()
    AioPikaInstrumentor().instrument()

    # FastAPI instrumentation happens via middleware, initialized when app is created
    logger.info(f"OpenTelemetry instrumentation enabled for {service_name}")


def get_tracer(name: str):
    """
    Get a tracer for manual span creation.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        OpenTelemetry tracer instance
    """
    return trace.get_tracer(name)
