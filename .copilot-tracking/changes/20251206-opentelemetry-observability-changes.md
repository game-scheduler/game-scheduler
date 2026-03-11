<!-- markdownlint-disable-file -->

# Release Changes: OpenTelemetry Observability Implementation

**Related Plan**: 20251206-opentelemetry-observability.plan.md
**Implementation Date**: 2025-12-07

## Summary

Implementation of comprehensive distributed tracing, metrics collection, and log
aggregation using OpenTelemetry with Grafana Cloud as the observability backend.

## Changes

### Added

- grafana-alloy/SETUP_GRAFANA_CLOUD.md - Comprehensive instructions for Grafana
  Cloud account setup and credential collection
- grafana-alloy/config.alloy - OpenTelemetry Collector configuration with OTLP
  receiver and HTTP exporter to Grafana Cloud
- grafana-alloy/TESTING_PHASE1.md - Step-by-step testing guide for Phase 1 Alloy
  connection verification
- grafana-alloy/TESTING_PHASE2.md - Step-by-step testing guide for Phase 2
  PostgreSQL metrics verification
- grafana-alloy/TESTING_PHASE3.md - Step-by-step testing guide for Phase 3 Redis
  metrics verification
- shared/telemetry.py - Centralized OpenTelemetry initialization module with TracerProvider, MeterProvider, LoggingInstrumentor configuration and auto-instrumentation for FastAPI, SQLAlchemy, asyncpg, Redis, and aio-pika
- grafana-alloy/TESTING_PHASE4.md - Step-by-step testing guide for Phase 4 API service instrumentation verification
- shared/telemetry.py - Fixed import paths for OTLP exporters (metric_exporter instead of metric_export, removed LoggingInstrumentor dependency); Added proper log export with LoggerProvider, BatchLogRecordProcessor, and LoggingHandler for trace correlation
- grafana-alloy/TESTING_PHASE5.md - Step-by-step testing guide for Phase 5 bot service instrumentation verification with Discord command trace validation
- grafana-alloy/TESTING_PHASE7.md - Step-by-step testing guide for Phase 7 RabbitMQ metrics verification with queue metrics and message rate validation

### Modified

- docker-compose.base.yml - Added grafana-alloy service for OpenTelemetry
  collection; updated environment variables to pass all three instance IDs;
  Added PostgreSQL environment variables (POSTGRES_USER, POSTGRES_PASSWORD,
  POSTGRES_DB) to Alloy service for PostgreSQL exporter connection
- .env.example - Added Grafana Cloud configuration variables with all three
  instance IDs (OTLP, Prometheus, Loki) and comprehensive documentation
- RUNTIME_CONFIG.md - Added comprehensive OpenTelemetry configuration
  documentation with all three instance IDs
- grafana-alloy/config.alloy - Fixed Alloy configuration syntax: unquoted header
  keys with trailing comma, removed send_batch_size to use defaults; Updated to
  use otelcol.exporter.otlp (gRPC) with otelcol.auth.basic per Grafana Cloud
  documentation, targeting Tempo endpoint directly; Added PostgreSQL metrics
  collection with prometheus.exporter.postgres using format() function for DSN
  construction, discovery.relabel, prometheus.relabel for metric filtering, and
  prometheus.scrape with 60s interval; Added prometheus.remote_write to send
  infrastructure metrics to Grafana Cloud Mimir with Prometheus-specific
  instance ID
- grafana-alloy/SETUP_GRAFANA_CLOUD.md - Added Step 3.5 for Loki instance ID
  collection
- .copilot-tracking/planning/plans/20251206-opentelemetry-observability.plan.md -
  Marked Phase 1 tasks as complete; Marked Phase 2 tasks as complete; Marked
  Phase 3 tasks as complete
- grafana-alloy/config.alloy - Added Redis metrics collection with
  prometheus.exporter.redis built-in component connecting to redis:6379,
  prometheus.relabel for metric filtering (cost optimization), and
  prometheus.scrape using exported targets with 60s interval; Uses in-memory
  traffic for efficient scraping without external container
- pyproject.toml - Added OpenTelemetry Python instrumentation packages: opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-sqlalchemy, opentelemetry-instrumentation-asyncpg, opentelemetry-instrumentation-redis, opentelemetry-instrumentation-aio-pika, opentelemetry-exporter-otlp
- services/api/app.py - Added init_telemetry() call and FastAPIInstrumentor.instrument_app() for automatic HTTP tracing, metrics, and log correlation
- docker-compose.base.yml - Added OpenTelemetry environment variables to API service (OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_PROTOCOL, OTEL_TRACES_EXPORTER, OTEL_METRICS_EXPORTER, OTEL_LOGS_EXPORTER)
- grafana-alloy/config.alloy - Added otelcol.exporter.otlphttp for application metrics with basic auth using OTLP gateway instance ID (XXXX-OTLP-ID); Fixed authentication issue where Prometheus instance ID (XXXX-PROM-ID) was incorrectly used instead of OTLP gateway ID; Updated batch processor to route metrics separately from traces/logs; Updated logs routing to send through OTLP gateway (same as metrics) instead of direct Loki connection, as OTLP gateway handles all three signals (traces, metrics, logs) and routes them appropriately
- .env.example - Added GRAFANA_CLOUD_OTLP_INSTANCE_ID with documentation explaining it differs from Prometheus instance ID and how to find it from OTLP gateway authorization header; Added GRAFANA_CLOUD_LOKI_ENDPOINT for reference
- docker-compose.base.yml - Added GRAFANA_CLOUD_LOKI_ENDPOINT environment variable to Alloy service; Added OpenTelemetry environment variables to bot service (OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_PROTOCOL, OTEL_TRACES_EXPORTER, OTEL_METRICS_EXPORTER, OTEL_LOGS_EXPORTER)
- grafana-alloy/TESTING_PHASE4.md - Added verification results section documenting authentication fix, instance ID reference table, and successful test results; Added troubleshooting section for HTTP 401 authentication errors with complete solution
- .copilot-tracking/planning/plans/20251206-opentelemetry-observability.plan.md - Marked Phase 5 tasks as complete
- services/bot/main.py - Added init_telemetry("bot-service") call for OpenTelemetry initialization at bot startup
- services/bot/bot.py - Added OpenTelemetry tracer and manual spans for Discord event handlers (on_ready, on_interaction, on_guild_join, on_guild_remove) with Discord-specific attributes (user_id, channel_id, guild_id, interaction_type)
- services/bot/commands/list_games.py - Added OpenTelemetry tracer and manual span for list_games command with Discord command attributes
- services/bot/commands/my_games.py - Added OpenTelemetry tracer and manual span for my_games command with Discord command attributes
- services/scheduler/notification_daemon_wrapper.py - Added init_telemetry("notification-daemon") call for OpenTelemetry initialization at daemon startup
- services/scheduler/generic_scheduler_daemon.py - Added OpenTelemetry tracer import and manual spans for scheduled task processing (\_process_item) and DLQ processing (\_process_dlq_messages) with scheduler-specific attributes (job_id, model, time_field, dlq_check_interval)
- services/scheduler/status_transition_daemon_wrapper.py - Added init_telemetry("status-transition-daemon") call for OpenTelemetry initialization at daemon startup
- docker-compose.base.yml - Added OpenTelemetry environment variables to notification-daemon and status-transition-daemon services (OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_PROTOCOL, OTEL_TRACES_EXPORTER, OTEL_METRICS_EXPORTER, OTEL_LOGS_EXPORTER)
- grafana-alloy/TESTING_PHASE6.md - Step-by-step testing guide for Phase 6 daemon services instrumentation verification with scheduled task and RabbitMQ context propagation validation
- shared/database.py - Fixed BASE_DATABASE_URL to strip driver specifications (postgresql+asyncpg:// or postgresql+psycopg2://) from DATABASE_URL environment variable, ensuring daemons using psycopg2 receive plain postgresql:// URLs
- docker-compose.base.yml - Fixed notification-daemon and status-transition-daemon healthcheck commands to use Python instead of pgrep (which is not available in Alpine images), resolving persistent unhealthy status
- rabbitmq/rabbitmq.conf - Added prometheus.return_per_object_metrics configuration to enable detailed per-queue metrics export
- docker-compose.base.yml - Added port mapping for RabbitMQ Prometheus metrics endpoint (15692:15692) and mounted rabbitmq.conf for Prometheus plugin configuration
- grafana-alloy/config.alloy - Added RabbitMQ metrics collection with discovery.static for endpoint discovery, discovery.relabel for job/instance labels, and prometheus.scrape with 60s interval; Removed cost optimization filtering for PostgreSQL, Redis, and RabbitMQ metrics as all exporters have reasonable defaults with high-cardinality collectors disabled
- .copilot-tracking/planning/plans/20251206-opentelemetry-observability.plan.md - Marked Phase 7 tasks as complete

### Removed

- N/A - No postgres-exporter service found to remove (Task 2.4 verification
  confirmed no redundant service exists)
