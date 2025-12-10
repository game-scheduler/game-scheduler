<!-- markdownlint-disable-file -->

# Task Details: OpenTelemetry Observability Implementation

## Research Reference

**Source Research**: #file:../research/20251206-opentelemetry-compatibility-research.md

## Phase 1: Grafana Alloy Deployment

### Task 1.1: Create Grafana Cloud account and obtain credentials

Sign up for Grafana Cloud free tier and obtain necessary credentials for OTLP gateway, Prometheus, and Loki.

- **Files**: N/A (external service signup)
- **Success**:
  - Grafana Cloud account created
  - OTLP instance ID obtained (format: 7-digit number)
  - Prometheus instance ID obtained (different from OTLP)
  - Grafana Cloud API key generated
  - OTLP endpoint URL recorded (format: otlp-gateway-prod-{region}.grafana.net/otlp)
  - Prometheus endpoint URL recorded
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 640-740) - Grafana Cloud configuration and authentication patterns
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 783-850) - Critical authentication learnings with multiple instance IDs
- **Dependencies**: None

### Task 1.2: Create Alloy configuration file

Create OpenTelemetry Collector configuration using Grafana Alloy format with OTLP receiver and exporter to Grafana Cloud.

- **Files**:
  - `grafana-alloy/config.alloy` - New Alloy configuration file
- **Success**:
  - OTLP receiver configured on ports 4317 (gRPC) and 4318 (HTTP)
  - Batch processor configured with 10s timeout
  - OTLP HTTP exporter configured (NOT gRPC to avoid ALPN issues)
  - Basic authentication configured with base64-encoded instance_id:api_key
  - Configuration syntax validated
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 263-297) - Collector pipeline examples
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 900-980) - Working Alloy configuration pattern
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1280-1320) - Verified configuration with OTLP HTTP exporter
- **Dependencies**: Task 1.1 completion

### Task 1.3: Add Grafana Alloy service to docker-compose

Add Grafana Alloy service to docker-compose.base.yml for local collector deployment.

- **Files**:
  - `docker-compose.base.yml` - Add grafana-alloy service
- **Success**:
  - Service using grafana/alloy:latest image
  - Configuration file mounted at /etc/alloy/config.alloy
  - Ports 4317 and 4318 exposed for OTLP
  - Environment variables passed from .env file
  - Service starts successfully
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 320-340) - Docker Compose addition example
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 659-677) - Grafana Alloy deployment pattern
- **Dependencies**: Task 1.2 completion

### Task 1.4: Configure environment variables

Add Grafana Cloud credentials and OpenTelemetry configuration to environment files.

- **Files**:
  - `.env.example` - Add OpenTelemetry configuration template
  - Documentation update in `RUNTIME_CONFIG.md` - Document new environment variables
- **Success**:
  - GRAFANA_CLOUD_INSTANCE_ID documented (OTLP instance ID)
  - GRAFANA_CLOUD_API_KEY documented
  - GRAFANA_CLOUD_AUTH_TOKEN documented (base64 encoded)
  - GRAFANA_CLOUD_OTLP_ENDPOINT documented
  - GRAFANA_CLOUD_PROMETHEUS_ENDPOINT documented
  - Example values provided in .env.example
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 299-315) - Environment variables example
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 982-1000) - Grafana Cloud environment configuration
- **Dependencies**: Task 1.1 completion

### Task 1.5: Test Alloy connection to Grafana Cloud

Verify that Alloy successfully connects to Grafana Cloud and forwards telemetry data.

- **Files**: N/A (testing task)
- **Success**:
  - Alloy container starts without errors
  - No authentication errors in Alloy logs
  - Manual curl test to Alloy OTLP endpoint returns 200 OK
  - Test trace visible in Grafana Cloud Tempo within 1 minute
  - Service name correctly set in test trace
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1240-1280) - Verification checklist
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1320-1340) - Phase 1 implementation steps
- **Dependencies**: Phase 1 Tasks 1.1-1.4 completion

## Phase 2: PostgreSQL Metrics Collection

### Task 2.1: Configure PostgreSQL exporter in Alloy

Add PostgreSQL metrics collection using Alloy's built-in prometheus.exporter.postgres.

- **Files**:
  - `grafana-alloy/config.alloy` - Add PostgreSQL exporter configuration
- **Success**:
  - prometheus.exporter.postgres configured with correct DSN
  - DSN uses environment variables: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable
  - discovery.relabel configured with job="integrations/postgres_exporter" and instance="postgres"
  - prometheus.relabel configured with metric filtering (pg_settings_*, pg_stat_activity_*, pg_stat_bgwriter_*, pg_stat_database_*, pg_up, up)
  - prometheus.scrape configured with 60s interval
  - Alloy restarts successfully with new config
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 70-78) - PostgreSQL instrumentation capabilities
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 900-980) - PostgreSQL exporter configuration example
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1342-1360) - Phase 2 implementation steps
- **Dependencies**: Phase 1 completion

### Task 2.2: Configure Prometheus remote write

Configure Prometheus remote_write to send PostgreSQL metrics to Grafana Cloud Mimir with correct instance ID.

- **Files**:
  - `grafana-alloy/config.alloy` - Add prometheus.remote_write configuration
- **Success**:
  - prometheus.remote_write configured with Grafana Cloud Mimir endpoint
  - Basic authentication uses Prometheus instance ID (NOT OTLP instance ID)
  - Username set to Prometheus-specific instance ID (e.g., "2847239")
  - Password uses same Grafana Cloud API key
  - prometheus.relabel forwards to prometheus.remote_write
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 783-850) - Critical authentication with multiple instance IDs
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 982-1000) - Prometheus remote write configuration
- **Dependencies**: Task 2.1 completion

### Task 2.3: Verify PostgreSQL metrics in Grafana Cloud

Confirm PostgreSQL metrics are flowing to Grafana Cloud Mimir and queryable.

- **Files**: N/A (verification task)
- **Success**:
  - No authentication errors in Alloy logs for Prometheus endpoint
  - Wait 60 seconds for initial scrape
  - Query pg_up in Grafana Cloud Mimir returns value 1
  - Query pg_stat_database_numbackends returns connection counts
  - Metrics have correct labels (job="integrations/postgres_exporter", instance="postgres")
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1240-1280) - Verification checklist
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1433-1445) - Grafana Cloud Mimir queries
- **Dependencies**: Phase 2 Tasks 2.1-2.2 completion

### Task 2.4: Remove redundant postgres-exporter service

Remove standalone postgres-exporter service from docker-compose now that Alloy has built-in PostgreSQL exporter.

- **Files**:
  - `docker-compose.base.yml` - Remove postgres-exporter service if present
- **Success**:
  - postgres-exporter service removed from docker-compose.base.yml
  - No duplicate PostgreSQL metrics being collected
  - Docker compose up succeeds without postgres-exporter
  - PostgreSQL metrics still flowing via Alloy
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1150-1170) - PostgreSQL Exporter Redundancy problem
- **Dependencies**: Task 2.3 completion

## Phase 3: Redis Metrics Collection

### Task 3.1: Configure Redis exporter scraping in Alloy

Configure Alloy to scrape Redis metrics from existing redis-exporter service.

- **Files**:
  - `grafana-alloy/config.alloy` - Add Redis metrics scraping
- **Success**:
  - prometheus.scrape configured to scrape redis-exporter:9121
  - discovery.relabel adds job="integrations/redis_exporter" and instance="redis"
  - Scrape interval set to 60s
  - prometheus.relabel forwards metrics to prometheus.remote_write
  - Alloy logs show successful Redis scrape target
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 80-88) - Redis instrumentation capabilities
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 900-980) - Metrics scraping patterns
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1362-1380) - Phase 3 implementation steps
- **Dependencies**: Phase 2 completion

### Task 3.2: Verify Redis metrics in Grafana Cloud

Confirm Redis metrics are visible and queryable in Grafana Cloud Mimir.

- **Files**: N/A (verification task)
- **Success**:
  - Query redis_up in Grafana Cloud Mimir returns value 1
  - Query redis_memory_used_bytes returns Redis memory usage
  - Metrics have correct labels (job="integrations/redis_exporter", instance="redis")
  - No scrape errors in Alloy logs
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1433-1445) - Grafana Cloud Mimir queries
- **Dependencies**: Task 3.1 completion

## Phase 4: API Service Instrumentation

### Task 4.1: Add OpenTelemetry Python packages

Add OpenTelemetry instrumentation libraries to pyproject.toml for Python services.

- **Files**:
  - `pyproject.toml` - Add OpenTelemetry dependencies
- **Success**:
  - opentelemetry-api added
  - opentelemetry-sdk added
  - opentelemetry-instrumentation-fastapi added
  - opentelemetry-instrumentation-sqlalchemy added
  - opentelemetry-instrumentation-asyncpg added
  - opentelemetry-instrumentation-redis added
  - opentelemetry-instrumentation-aio-pika added
  - opentelemetry-exporter-otlp added
  - Dependencies installed successfully with uv sync
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 299-315) - Python package list
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 100-135) - Python service instrumentation details
- **Dependencies**: None

### Task 4.2: Create shared telemetry initialization module

Create reusable telemetry initialization module in shared/ for all Python services.

- **Files**:
  - `shared/telemetry.py` - New telemetry initialization module
- **Success**:
  - init_telemetry(service_name: str) function created
  - Configures TracerProvider with OTLP exporter
  - Configures MeterProvider with OTLP exporter
  - Configures LoggingInstrumentor for log-trace correlation
  - Uses environment variables for OTLP endpoint and protocol
  - Logs initialization success for traces, metrics, and logs
  - Manual span creation helper provided
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 187-215) - Manual instrumentation pattern
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1382-1410) - Python service implementation steps
- **Dependencies**: Task 4.1 completion

### Task 4.3: Instrument API service startup

Add telemetry initialization to API service startup sequence.

- **Files**:
  - `services/api/app.py` - Add telemetry initialization
- **Success**:
  - Import shared.telemetry.init_telemetry
  - Call init_telemetry("api-service") in startup event or before app creation
  - FastAPI auto-instrumentation activates
  - SQLAlchemy and asyncpg auto-instrumentation activates
  - Redis auto-instrumentation activates
  - aio-pika auto-instrumentation activates
  - Service starts without errors
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 100-125) - FastAPI instrumentation
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1382-1410) - API service instrumentation steps
- **Dependencies**: Task 4.2 completion

### Task 4.4: Configure API service environment variables

Add OpenTelemetry environment variables to API service configuration.

- **Files**:
  - `docker-compose.base.yml` - Add OTEL_* environment variables to api service
  - `.env.example` - Add OpenTelemetry service configuration template
- **Success**:
  - OTEL_SERVICE_NAME=api-service
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318
  - OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
  - OTEL_TRACES_EXPORTER=otlp
  - OTEL_METRICS_EXPORTER=otlp
  - OTEL_LOGS_EXPORTER=otlp
  - Environment variables documented in RUNTIME_CONFIG.md
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 299-315) - Environment variables
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 982-1000) - Python service configuration
- **Dependencies**: Task 4.3 completion

### Task 4.5: Verify API traces, metrics, and logs

Confirm API service telemetry is flowing to Grafana Cloud via Alloy.

- **Files**: N/A (verification task)
- **Success**:
  - API service logs show "OpenTelemetry tracing initialized"
  - API service logs show "OpenTelemetry metrics initialized"
  - API service logs show "OpenTelemetry logging initialized" (or confirmed working via manual test)
  - Send test request to /health endpoint
  - Trace visible in Grafana Cloud Tempo with service.name="api-service"
  - HTTP spans include method, status_code, target attributes
  - Database query spans appear as child spans
  - Metrics visible in Grafana Cloud Mimir (http_server_duration_bucket)
  - Logs visible in Grafana Cloud Loki with service_name="api-service"
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1240-1280) - Verification checklist
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1382-1410) - Phase 4 implementation and validation
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1130-1150) - Logging initialization verification
- **Dependencies**: Phase 4 Tasks 4.1-4.4 completion

## Phase 5: Bot Service Instrumentation

### Task 5.1: Instrument bot service startup

Add telemetry initialization to Discord bot service.

- **Files**:
  - `services/bot/main.py` - Add telemetry initialization
- **Success**:
  - Import shared.telemetry.init_telemetry
  - Call init_telemetry("bot-service") before bot.start()
  - SQLAlchemy, asyncpg, Redis, aio-pika auto-instrumentation activates
  - Bot starts successfully
  - Initialization logged
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 109-115) - discord.py instrumentation approach
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1412-1430) - Bot service implementation steps
- **Dependencies**: Phase 4 completion

### Task 5.2: Add manual spans for Discord event handlers

Create manual trace spans for Discord event handlers and bot commands.

- **Files**:
  - `services/bot/main.py` - Add manual spans to event handlers
  - Relevant bot command files - Add manual spans
- **Success**:
  - Import opentelemetry.trace.get_tracer
  - Create tracer = trace.get_tracer(__name__)
  - Wrap Discord event handlers (on_message, on_interaction) with tracer.start_as_current_span()
  - Add span attributes: discord.user_id, discord.channel_id, discord.guild_id, discord.command
  - Downstream operations (database, RabbitMQ) inherit trace context
  - Manual spans created successfully
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1260-1290) - Discord bot event handling pattern
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 187-215) - Manual instrumentation pattern
- **Dependencies**: Task 5.1 completion

### Task 5.3: Configure bot service environment variables

Add OpenTelemetry configuration to bot service.

- **Files**:
  - `docker-compose.base.yml` - Add OTEL_* variables to bot service
- **Success**:
  - OTEL_SERVICE_NAME=bot-service
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318
  - OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
  - OTEL_TRACES_EXPORTER=otlp
  - OTEL_METRICS_EXPORTER=otlp
  - OTEL_LOGS_EXPORTER=otlp
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 299-315) - Environment variables
- **Dependencies**: Task 5.2 completion

### Task 5.4: Verify bot traces

Confirm Discord bot generates traces with proper context propagation.

- **Files**: N/A (verification task)
- **Success**:
  - Bot logs show OpenTelemetry initialization
  - Trigger Discord command (e.g., /create-game)
  - Trace visible in Tempo with service.name="bot-service"
  - Root span has name like "discord.on_interaction" or "discord.on_message"
  - Span attributes include discord.user_id, discord.channel_id, discord.guild_id
  - Child spans show database queries and RabbitMQ publishes
  - RabbitMQ message context propagates to daemons (verify after Phase 6)
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1412-1430) - Bot service verification
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1260-1290) - Discord event tracing
- **Dependencies**: Phase 5 Tasks 5.1-5.3 completion

## Phase 6: Daemon Services Instrumentation

### Task 6.1: Instrument notification daemon

Add telemetry to notification daemon with manual spans for scheduled tasks.

- **Files**:
  - `services/scheduler/notification_daemon.py` - Add telemetry initialization and manual spans
- **Success**:
  - Import init_telemetry and call init_telemetry("notification-daemon")
  - Import opentelemetry.trace.get_tracer
  - Wrap scheduled job functions with tracer.start_as_current_span()
  - Add span attributes: scheduler.job_id, scheduler.trigger, notification.type
  - Wrap RabbitMQ message consumer with manual span if needed (or rely on aio-pika auto-instrumentation)
  - Daemon starts successfully
  - Initialization logged
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1292-1320) - Scheduled task tracing pattern
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1222-1260) - RabbitMQ message context propagation
- **Dependencies**: Phase 5 completion

### Task 6.2: Instrument status transition daemon

Add telemetry to status transition daemon with manual spans for scheduled tasks.

- **Files**:
  - `services/scheduler/status_transition_daemon.py` - Add telemetry initialization and manual spans
- **Success**:
  - Import init_telemetry and call init_telemetry("status-transition-daemon")
  - Import opentelemetry.trace.get_tracer
  - Wrap scheduled job functions with tracer.start_as_current_span()
  - Add span attributes: scheduler.job_id, scheduler.trigger, game.status_transition
  - Daemon starts successfully
  - Initialization logged
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1292-1320) - Scheduled task tracing pattern
- **Dependencies**: Phase 5 completion

### Task 6.3: Configure daemon environment variables

Add OpenTelemetry configuration to both daemon services.

- **Files**:
  - `docker-compose.base.yml` - Add OTEL_* variables to notification-daemon and status-transition-daemon
- **Success**:
  - notification-daemon: OTEL_SERVICE_NAME=notification-daemon
  - status-transition-daemon: OTEL_SERVICE_NAME=status-transition-daemon
  - Both: OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318
  - Both: OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
  - Both: OTEL_TRACES_EXPORTER=otlp, OTEL_METRICS_EXPORTER=otlp, OTEL_LOGS_EXPORTER=otlp
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 299-315) - Environment variables
- **Dependencies**: Tasks 6.1 and 6.2 completion

### Task 6.4: Verify daemon traces and message context propagation

Confirm daemons generate traces and inherit context from RabbitMQ messages.

- **Files**: N/A (verification task)
- **Success**:
  - Daemon logs show OpenTelemetry initialization
  - Trigger scheduled task or send message via bot/API
  - Scheduled task creates root span in Tempo (e.g., "scheduled.check_upcoming_games")
  - RabbitMQ consumer span links to publisher span (trace context propagated)
  - Verify trace continuity: bot → RabbitMQ publish → daemon consume → Discord API call
  - Span attributes include scheduler.job_id, notification.type, etc.
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1222-1260) - RabbitMQ context propagation
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1292-1320) - Scheduled task tracing
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1382-1410) - Phase 6 implementation steps
- **Dependencies**: Phase 6 Tasks 6.1-6.3 completion

## Phase 7: RabbitMQ Metrics Collection

### Task 7.1: Enable RabbitMQ Prometheus plugin

Enable the built-in rabbitmq_prometheus plugin in RabbitMQ to expose metrics on port 15692.

- **Files**:
  - `docker-compose.base.yml` - Add plugin enable command to rabbitmq service
- **Success**:
  - RabbitMQ container has rabbitmq_prometheus plugin enabled
  - Metrics endpoint accessible at http://rabbitmq:15692/metrics
  - Endpoint returns Prometheus-formatted metrics
  - Metrics include queue depth, connection count, message rates, consumer count
  - No errors in RabbitMQ logs related to prometheus plugin
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 51-66) - RabbitMQ Prometheus Plugin capabilities and configuration
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 97-107) - RabbitMQ metrics collection method
- **Dependencies**: Phase 6 completion

### Task 7.2: Configure RabbitMQ metrics scraping in Alloy

Add RabbitMQ metrics scraping configuration to Grafana Alloy using Prometheus receiver.

- **Files**:
  - `grafana-alloy/config.alloy` - Add RabbitMQ scraping configuration
- **Success**:
  - prometheus.scrape configured to scrape rabbitmq:15692
  - discovery.relabel adds job="integrations/rabbitmq" and instance="rabbitmq"
  - Scrape interval set to 60s (per research recommendation)
  - prometheus.relabel forwards metrics to prometheus.remote_write
  - Alloy logs show successful RabbitMQ scrape target
  - Configuration follows same pattern as PostgreSQL and Redis exporters
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 350-370) - RabbitMQ metrics configuration and available metric families
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 254-258) - Prometheus scrape config example for RabbitMQ
- **Dependencies**: Task 7.1 completion

### Task 7.3: Verify RabbitMQ metrics in Grafana Cloud

Confirm RabbitMQ metrics are flowing to Grafana Cloud Mimir and queryable.

- **Files**: N/A (verification task)
- **Success**:
  - No scrape errors in Alloy logs for RabbitMQ endpoint
  - Wait 60 seconds for initial scrape
  - Query rabbitmq_up in Grafana Cloud Mimir returns value 1
  - Query rabbitmq_queue_messages shows queue depths
  - Query rabbitmq_connections shows connection count
  - Query rabbitmq_consumers shows consumer count
  - Metrics have correct labels (job="integrations/rabbitmq", instance="rabbitmq")
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 350-370) - Available RabbitMQ metric families
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 56-62) - Comprehensive RabbitMQ metrics list
- **Dependencies**: Task 7.2 completion

## Phase 8: Grafana Cloud Dashboards

### Task 8.1: Import pre-built PostgreSQL dashboard

Import official PostgreSQL dashboard from Grafana dashboard library.

- **Files**: N/A (Grafana Cloud UI)
- **Success**:
  - Navigate to Grafana Cloud Dashboards → Import
  - Search for "PostgreSQL" in dashboard library
  - Import dashboard (e.g., dashboard ID 9628 or similar)
  - Configure data source to use Grafana Cloud Mimir
  - Dashboard displays PostgreSQL metrics (connections, transactions, cache hit ratio)
  - Metrics match labels from Alloy (job="integrations/postgres_exporter")
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 610-630) - Grafana Cloud benefits including dashboard templates
- **Dependencies**: Phase 2 completion

### Task 8.2: Import pre-built Redis dashboard

Import official Redis dashboard from Grafana dashboard library.

- **Files**: N/A (Grafana Cloud UI)
- **Success**:
  - Navigate to Grafana Cloud Dashboards → Import
  - Search for "Redis" in dashboard library
  - Import dashboard (e.g., dashboard ID 763 or similar)
  - Configure data source to use Grafana Cloud Mimir
  - Dashboard displays Redis metrics (memory usage, operations per second, hit rate)
  - Metrics match labels from Alloy (job="integrations/redis_exporter")
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 610-630) - Grafana Cloud dashboard templates
- **Dependencies**: Phase 3 completion

### Task 8.3: Import pre-built RabbitMQ dashboard

Import official RabbitMQ dashboard from Grafana dashboard library.

- **Files**: N/A (Grafana Cloud UI)
- **Success**:
  - Navigate to Grafana Cloud Dashboards → Import
  - Search for official RabbitMQ dashboard from grafana.com/orgs/rabbitmq
  - Import dashboard (e.g., RabbitMQ Overview or RabbitMQ Monitoring)
  - Configure data source to use Grafana Cloud Mimir
  - Dashboard displays RabbitMQ metrics (queue depth, message rates, connections, consumers)
  - Metrics match labels from Alloy (job="integrations/rabbitmq")
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 62-63) - Official Grafana RabbitMQ dashboards
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 106-107) - Pre-built dashboard availability
- **Dependencies**: Phase 7 completion

### Task 8.4: Create custom service overview dashboard

Build custom dashboard showing service health, request rates, and latencies.

- **Files**: N/A (Grafana Cloud UI)
- **Success**:
  - Create new dashboard "Game Scheduler Services"
  - Add panel: Request rate by service (rate(http_server_requests_total[5m]))
  - Add panel: Request latency P99 by service (histogram_quantile(0.99, http_server_duration_bucket))
  - Add panel: Error rate by service and status code
  - Add panel: Active database connections (pg_stat_database_numbackends)
  - Add panel: Redis memory usage (redis_memory_used_bytes)
  - Add panel: RabbitMQ queue depth (rabbitmq_queue_messages)
  - Variables configured for filtering by service name
  - Dashboard saved in Grafana Cloud
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1433-1455) - Grafana Cloud metric queries
- **Dependencies**: Phases 2-7 completion

### Task 8.5: Configure alerting rules

Set up basic alerting for critical issues.

- **Files**: N/A (Grafana Cloud UI)
- **Success**:
  - Create alert: "API Service Down" when up{job="api-service"} == 0 for 2 minutes
  - Create alert: "PostgreSQL Down" when pg_up == 0 for 1 minute
  - Create alert: "Redis Down" when redis_up == 0 for 1 minute
  - Create alert: "RabbitMQ Down" when rabbitmq_up == 0 for 1 minute
  - Create alert: "High Error Rate" when rate(http_server_requests_total{status=~"5.."}[5m]) > 0.05 for 5 minutes
  - Create alert: "High API Latency" when histogram_quantile(0.99, http_server_duration_bucket{service_name="api-service"}) > 1.0 for 10 minutes
  - Create alert: "RabbitMQ Queue Backlog" when rabbitmq_queue_messages > 1000 for 5 minutes
  - Alert notification channel configured (email or webhook)
  - Test alerts trigger correctly
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 385-395) - Success criteria including performance monitoring
- **Dependencies**: Phases 2-7 completion

## Dependencies

- Grafana Cloud free tier account
- OpenTelemetry Collector Contrib (Grafana Alloy)
- OpenTelemetry Python instrumentation libraries
- Existing PostgreSQL, Redis, and RabbitMQ services

## Success Criteria

- API requests generate complete trace spans from HTTP ingress to database queries
- Bot commands create trace spans with Discord event context
- Scheduled daemon tasks create root spans with proper attributes
- RabbitMQ message context propagates from publishers to consumers
- PostgreSQL, Redis, and RabbitMQ metrics visible in Grafana Cloud Mimir
- Structured logs with trace correlation available in Grafana Cloud Loki
- All services remain within Grafana Cloud free tier limits (50GB traces, 50GB logs, 10k metric series)
- No critical performance degradation (<5% latency increase)
