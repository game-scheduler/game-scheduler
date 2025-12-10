<!-- markdownlint-disable-file -->

# Task Research Notes: OpenTelemetry Compatibility Assessment

## Research Executed

### File Analysis

- `docker-compose.base.yml` - Complete service inventory analyzed
- `pyproject.toml` - Python dependencies reviewed
- `frontend/package.json` - Frontend dependencies reviewed
- `RUNTIME_CONFIG.md` - Configuration patterns assessed

### External Research

#### OpenTelemetry Python Documentation

- #fetch:"https://opentelemetry.io/docs/languages/python/libraries/"
  - **Stable support** for Python 3.9+ (project uses Python 3.13 ✓)
  - Auto-instrumentation available via `opentelemetry-bootstrap` and
    `opentelemetry-instrument`
  - FastAPI instrumentation: `opentelemetry-instrumentation-fastapi`
  - HTTP client instrumentation: `opentelemetry-instrumentation-httpx`,
    `opentelemetry-instrumentation-aiohttp-client`
  - PostgreSQL instrumentation: `opentelemetry-instrumentation-asyncpg`,
    `opentelemetry-instrumentation-psycopg2`
  - Redis instrumentation: `opentelemetry-instrumentation-redis`
  - SQLAlchemy instrumentation: `opentelemetry-instrumentation-sqlalchemy`

#### OpenTelemetry JavaScript Documentation

- #fetch:"https://opentelemetry.io/docs/languages/js/"
  - **Stable support** for Node.js (used for frontend build)
  - **Experimental** browser instrumentation (user-agent based telemetry)
  - Auto-instrumentation available via
    `@opentelemetry/auto-instrumentations-node`

#### OpenTelemetry Registry

- #fetch:"https://opentelemetry.io/ecosystem/registry/"
  - **PostgreSQL Receiver** for collector - queries PostgreSQL statistics
  - **Redis Receiver** for collector - retrieves Redis INFO data
  - **RabbitMQ Client Instrumentation** for Python:
    `opentelemetry-instrumentation-pika` (aio-pika support)
  - **PostgreSQL instrumentation** for Python: Multiple options (asyncpg,
    psycopg2, psycopg)
  - **Redis instrumentation** for Python: `opentelemetry-instrumentation-redis`
  - JavaScript/Node.js instrumentation libraries available for PostgreSQL, Redis
  - No native RabbitMQ metrics exporter (requires client-side instrumentation)

#### RabbitMQ Prometheus Plugin

- #fetch:"https://www.rabbitmq.com/docs/prometheus"
  - **Built-in Plugin**: `rabbitmq_prometheus` ships with RabbitMQ 3.8.0+
  - **Default Endpoint**: `http://localhost:15692/metrics` (Prometheus text format)
  - **Comprehensive Metrics**: Queue metrics, connection/channel metrics, node metrics, Erlang VM metrics, Raft metrics, authentication metrics
  - **Multiple Endpoint Types**:
    - `/metrics` - Aggregated metrics (default, most efficient)
    - `/metrics/per-object` - Per-object metrics (queue/connection/channel specific)
    - `/metrics/detailed?family=<metric_family>&vhost=<vhost>` - Selective metrics (most efficient for large deployments)
  - **Metric Families**: `queue_coarse_metrics`, `queue_metrics`, `queue_delivery_metrics`, `channel_metrics`, `connection_metrics`, `exchange_metrics`, `node_metrics`, `ra_metrics` (Raft)
  - **Grafana Integration**: Official pre-built dashboards available at grafana.com/orgs/rabbitmq
  - **Configuration**: No configuration needed for basic usage, plugin enabled with `rabbitmq-plugins enable rabbitmq_prometheus`
  - **Scraping Recommendation**: 60s interval for Prometheus, 10s `collect_statistics_interval` for RabbitMQ (production)
  - **Performance**: Aggregated metrics scale well with large deployments (80k+ queues); per-object metrics expensive with many entities

#### OpenTelemetry Collector

- #fetch:"https://opentelemetry.io/docs/collector/"
  - **Vendor-agnostic** telemetry collection, processing, and export
  - Supports **OTLP** (OpenTelemetry Protocol) over gRPC and HTTP
  - Can receive from multiple sources, process with pipelines, export to
    multiple backends
  - Deployable as **sidecar, gateway, or agent**
  - Built-in receivers for PostgreSQL, Redis metrics collection
  - Batching, retry logic, and data transformation capabilities
  - **Prometheus Scraping**: Can scrape Prometheus endpoints (like RabbitMQ) and convert to OTLP

### Infrastructure Component Analysis

#### PostgreSQL 17-alpine

- **OpenTelemetry Support**: ✅ **YES - Via Collector Receiver**
- **Method**: OpenTelemetry Collector has `postgresqlreceiver` component
- **Capabilities**: Queries PostgreSQL statistics collector for metrics
- **Alternative**: Client-side instrumentation via
  `opentelemetry-instrumentation-asyncpg` in Python services

#### Redis 7.4-alpine

- **OpenTelemetry Support**: ✅ **YES - Via Collector Receiver**
- **Method**: OpenTelemetry Collector has `redisreceiver` component
- **Capabilities**: Retrieves Redis INFO data at configurable intervals
- **Alternative**: Client-side instrumentation via
  `opentelemetry-instrumentation-redis` in Python services

#### RabbitMQ 4.2-management-alpine

- **OpenTelemetry Support**: ✅ **YES - Via Built-in Prometheus Plugin + Collector Scraping**
- **Method**: Built-in `rabbitmq_prometheus` plugin exposes Prometheus metrics
- **Prometheus Endpoint**: `http://localhost:15692/metrics` (default port)
- **Client-side**: Python instrumentation via
  `opentelemetry-instrumentation-aio-pika` for aio-pika client (message tracing)
- **Integration Strategy**: Collector scrapes Prometheus endpoints and exports to OTLP
- **Metrics Available**: Queue depth, connection count, message rates, consumer count, node resources, Erlang VM metrics, Raft metrics (quorum queues), and more
- **Official Grafana Dashboards**: Pre-built dashboards available at grafana.com/orgs/rabbitmq

#### Nginx 1.28-alpine

- **OpenTelemetry Support**: ⚠️ **PARTIAL - Module Available**
- **Method**: `opentelemetry` nginx module available (third-party)
- **Capabilities**: Can export traces and metrics from nginx
- **Complexity**: Requires custom nginx build with module
- **Alternative**: Access log parsing or upstream service instrumentation

### Python Service Instrumentation

#### FastAPI (services/api)

- **Instrumentation Library**: `opentelemetry-instrumentation-fastapi`
- **Auto-instrumentation**: ✅ YES via `opentelemetry-instrument`
- **Telemetry**: HTTP spans, metrics (request duration, active requests)
- **Dependencies**: Requires `opentelemetry-instrumentation-asgi`

#### discord.py (services/bot)

- **Instrumentation Library**: No official OpenTelemetry instrumentation
- **Manual Instrumentation**: ✅ POSSIBLE via OpenTelemetry API
- **Approach**: Wrap bot commands and event handlers with spans manually

#### SQLAlchemy + asyncpg (shared/database.py)

- **Instrumentation Library**: `opentelemetry-instrumentation-sqlalchemy`,
  `opentelemetry-instrumentation-asyncpg`
- **Auto-instrumentation**: ✅ YES
- **Telemetry**: Database query spans with statement, duration, connection
  details

#### Redis Client

- **Instrumentation Library**: `opentelemetry-instrumentation-redis`
- **Auto-instrumentation**: ✅ YES
- **Telemetry**: Redis command spans with operation, key, duration

#### RabbitMQ Client (aio-pika)

- **Instrumentation Library**: `opentelemetry-instrumentation-aio-pika` (in
  registry)
- **Auto-instrumentation**: ✅ YES
- **Telemetry**: Message publish/consume spans with queue, exchange, routing key

### Frontend Instrumentation

#### React Application

- **Browser Instrumentation**: ⚠️ EXPERIMENTAL in OpenTelemetry JS
- **Capabilities**: User interaction traces, resource loading, XHR/Fetch spans
- **Limitations**: Browser instrumentation less mature than Node.js
- **Recommendation**: Start with backend instrumentation, add frontend later

#### Nginx (Frontend Server)

- **Method**: Access log forwarding or custom module
- **Complexity**: HIGH - requires custom build or log collector setup
- **Recommendation**: Instrument at application layer instead

## Key Discoveries

### OpenTelemetry Architecture

**Three Signal Types**:

1. **Traces** - Distributed request flows across services
2. **Metrics** - Aggregated measurements (counters, gauges, histograms)
3. **Logs** - Structured event records with trace context injection

**Core Components**:

- **SDK**: Instrumentation libraries for each language
- **API**: Interface for manual instrumentation
- **Collector**: Vendor-agnostic telemetry pipeline
- **Exporters**: Send data to backends (Jaeger, Prometheus, OTLP)

**Instrumentation Strategies**:

1. **Auto-instrumentation**: Zero-code instrumentation via libraries
2. **Manual instrumentation**: Explicit span creation for custom logic
3. **Hybrid**: Auto-instrument frameworks, manually instrument business logic

### Complete Python Instrumentation Examples

**Auto-instrumentation Command**:

```bash
opentelemetry-bootstrap -a install
opentelemetry-instrument \
  --traces_exporter otlp \
  --metrics_exporter otlp \
  --service_name api-service \
  --exporter_otlp_endpoint http://localhost:4318 \
  python -m uvicorn main:app
```

**Manual Instrumentation Pattern**:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://collector:4317"))
)

# Create custom spans
with tracer.start_as_current_span("game_creation"):
    # Business logic here
    game = create_game(data)
    return game
```

### Collector Configuration Patterns

**Deployment Architectures**:

1. **Agent Pattern**: Collector sidecar per service/host
2. **Gateway Pattern**: Centralized collector receiving from all services
3. **Hybrid**: Service agents -> Gateway collector -> Backends

**Example Collector Pipeline**:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
  postgresql:
    endpoint: postgres:5432
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    databases: [game_scheduler]
  redis:
    endpoint: redis:6379
  prometheus:
    config:
      scrape_configs:
        - job_name: 'rabbitmq'
          static_configs:
            - targets: ['rabbitmq:15692']
          scrape_interval: 60s

processors:
  batch:
    timeout: 10s
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  otlp:
    endpoint: backend:4317
  prometheus:
    endpoint: 0.0.0.0:8889
  jaeger:
    endpoint: jaeger:14250

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, memory_limiter]
      exporters: [otlp, jaeger]
    metrics:
      receivers: [otlp, postgresql, redis, prometheus]
      processors: [batch, memory_limiter]
      exporters: [otlp, prometheus]
```

## Recommended Approach

### Phase 1: Backend Service Instrumentation (Traces & Metrics)

**Python Services** (api, bot, daemons):

```python
# Add to pyproject.toml
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy
opentelemetry-instrumentation-asyncpg
opentelemetry-instrumentation-redis
opentelemetry-instrumentation-aio-pika
opentelemetry-exporter-otlp
```

**Instrumentation Strategy**:

- Use auto-instrumentation for FastAPI, SQLAlchemy, asyncpg, redis, aio-pika
- Manual instrumentation for discord.py bot commands
- Manual spans for business logic (game creation, scheduling, notifications)

**Environment Variables**:

```bash
OTEL_SERVICE_NAME=api-service  # or bot-service, notification-daemon, etc.
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
```

### Phase 2: Infrastructure Metrics Collection

**OpenTelemetry Collector** (new service):

- Deploy as sidecar or gateway service in docker-compose
- Configure `postgresqlreceiver` for database metrics
- Configure `redisreceiver` for cache metrics
- Configure Prometheus receiver to scrape RabbitMQ's built-in `/metrics` endpoint

**Docker Compose Addition**:

```yaml
otel-collector:
  image: otel/opentelemetry-collector-contrib:0.141.0
  volumes:
    - ./otel-collector-config.yaml:/etc/otelcol/config.yaml
  ports:
    - "4317:4317" # OTLP gRPC
    - "4318:4318" # OTLP HTTP
    - "8889:8889" # Prometheus exporter
  environment:
    - DB_USER=${DATABASE_USER}
    - DB_PASSWORD=${DATABASE_PASSWORD}
  depends_on:
    - postgres
    - redis
    - rabbitmq
```

**RabbitMQ Metrics Configuration**:

The collector's Prometheus receiver will scrape RabbitMQ's built-in metrics endpoint:

```yaml
receivers:
  prometheus:
    config:
      scrape_configs:
        - job_name: 'rabbitmq'
          static_configs:
            - targets: ['rabbitmq:15692']
          scrape_interval: 60s
          # Optional: scrape only specific metric families
          # metrics_path: '/metrics/detailed?family=queue_coarse_metrics&family=queue_consumer_count'
```

**Available RabbitMQ Metric Families**:
- `queue_coarse_metrics` - Queue depth (ready, unacked, total)
- `queue_consumer_count` - Consumer count per queue
- `queue_metrics` - Detailed queue metrics (memory, bytes, paging)
- `queue_delivery_metrics` - Message delivery rates
- `connection_metrics` - Connection statistics
- `channel_metrics` - Channel statistics
- `node_metrics` - Node resource usage
- `ra_metrics` - Raft consensus metrics (quorum queues)

### Phase 3: Observability Backend Selection

**Backend Options**:

1. **Jaeger** - Distributed tracing UI (traces only)
2. **Prometheus + Grafana** - Metrics storage and visualization
3. **Grafana Tempo + Loki + Prometheus** - Full observability stack
4. **Commercial SaaS** - Honeycomb, Datadog, New Relic, etc.

**Development Setup** (Docker Compose):

```yaml
jaeger:
  image: jaegertracing/all-in-one:latest
  ports:
    - "16686:16686" # UI
    - "14250:14250" # gRPC receiver

prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000" # Avoid conflict with app on 3000
  environment:
    - GF_AUTH_ANONYMOUS_ENABLED=true
```

### Phase 4: Frontend Instrumentation (Optional)

**Browser Instrumentation**:

- Use `@opentelemetry/instrumentation-document-load` for page load metrics
- Use `@opentelemetry/instrumentation-user-interaction` for user clicks
- Use `@opentelemetry/instrumentation-fetch` for API calls
- Export to collector via OTLP HTTP

**Caution**: Browser instrumentation is **experimental** - may have performance
impact

## Implementation Guidance

### Objectives

- Achieve full distributed tracing across Python microservices
- Collect application and infrastructure metrics
- Enable correlation between traces, metrics, and logs
- Maintain minimal performance overhead (<5% latency increase)

### Key Tasks

1. Add OpenTelemetry Python packages to `pyproject.toml`
2. Create OpenTelemetry Collector configuration file
3. Add `otel-collector` service to docker-compose
4. Configure environment variables for each Python service
5. Add manual instrumentation to discord.py bot
6. Deploy observability backend (Jaeger + Prometheus + Grafana)
7. Test trace propagation across service boundaries
8. Configure dashboards and alerting

### Dependencies

- OpenTelemetry Collector (otel/opentelemetry-collector-contrib)
- Python instrumentation libraries
- Observability backend (Jaeger, Prometheus, Grafana)
- No changes required to PostgreSQL, Redis, RabbitMQ containers

### Success Criteria

- ✅ API requests generate complete trace spans from ingress to database
- ✅ Bot commands create trace spans with Discord context
- ✅ Database queries appear as child spans with SQL statements
- ✅ Redis operations appear as child spans
- ✅ RabbitMQ message publish/consume creates linked spans
- ✅ Daemon scheduled tasks create root spans with context
- ✅ Infrastructure metrics (Postgres connections, Redis memory, RabbitMQ queue depth) collected
- ✅ RabbitMQ metrics (queue depth, consumer count, message rates) available
- ✅ Logs include trace IDs for correlation
- ✅ No critical performance degradation in production workload

## Third-Party Observability Platform Comparison

### Platform Research Overview

Comprehensive comparison of observability platforms with free tiers that support
OpenTelemetry.

### New Relic

#### Pricing & Free Tier

- **Free Tier**: 100 GB data ingest/month (permanent, no time limit)
- **Data Ingestion**: $0.40/GB beyond free tier
- **Users**: 1 free full platform user, unlimited basic users
- **Retention**: Standard data retention included
- **No Credit Card**: Required to start free tier

#### OpenTelemetry Support

- ✅ **Native OTLP Support**: Accepts OTLP over gRPC and HTTP
- ✅ **Auto-instrumentation**: Full support for Python, Node.js
- ✅ **All Signals**: Traces, metrics, logs with correlation
- **Integration**: Direct OTLP export from services or via collector

#### Key Features

- 50+ observability capabilities in one platform
- APM, infrastructure monitoring, logs, distributed tracing
- AI-powered insights and anomaly detection
- Query language (NRQL) for custom dashboards

#### Best For

- **Small to medium production workloads**
- Teams wanting comprehensive platform without complexity
- Applications with moderate telemetry volume (<100GB/month)

#### Limitations

- After 100 GB/month, costs $0.40/GB (can add up quickly)
- Single full platform user on free tier (viewers unlimited)
- Less control over data retention policies

---

### Grafana Cloud

#### Pricing & Free Tier

- **Metrics**: 10k active series/month free (14-day retention)
- **Logs**: 50 GB/month free (14-day retention)
- **Traces**: 50 GB/month free (14-day retention)
- **Profiles**: 50 GB/month free (14-day retention)
- **Visualization**: 3 active Grafana users free
- **Pro Tier**: $19/month platform fee + usage beyond free tier

#### OpenTelemetry Support

- ✅ **Native OTLP Support**: Grafana Alloy (OTel Collector distribution)
- ✅ **Full Stack**: Tempo (traces), Loki (logs), Mimir (metrics), Pyroscope
  (profiles)
- ✅ **Open Source**: All backend components are OSS
- **Integration**: OTLP export via Grafana Alloy or direct OTLP endpoints

#### Key Features

- **Adaptive Metrics**: Automatic cost optimization (up to 80% savings)
- **Adaptive Logs**: Pattern-based log volume reduction (up to 50% savings)
- Unified query experience across all signals
- Extensive plugin ecosystem for data sources
- Best-in-class visualization with Grafana dashboards

#### Pricing After Free Tier (Pro Plan)

- Metrics: $6.50 per 1k active series
- Logs/Traces/Profiles: $0.50 per GB ingested
- Platform fee: $19/month

#### Best For

- **Open source enthusiasts**
- Teams wanting full control over observability stack
- Applications with predictable telemetry patterns
- **Organizations already using Grafana ecosystem**

#### Limitations

- Free tier has short retention (14 days for most signals)
- Requires understanding of LGTM stack concepts
- Multiple products to configure vs single platform
- Visualization limited to 3 active users on free tier

---

### Honeycomb

#### Pricing & Free Tier

- **Events**: Up to 20 million events/month free (forever)
- **Retention**: 60-day retention on free tier
- **Triggers**: 2 alert triggers
- **Features**: Full platform access (BubbleUp, distributed tracing, OTel
  support)
- **Users**: Unlimited seats on all tiers

#### OpenTelemetry Support

- ✅ **Native OTLP Support**: Direct OTLP ingestion
- ✅ **Event-based Model**: Treats spans/logs as structured events
- ✅ **High Cardinality**: Unlimited custom fields per event
- **Integration**: Direct OTLP export from services

#### Key Features

- **BubbleUp**: Automatic correlation analysis for debugging
- **Honeycomb Intelligence**: AI-powered query suggestions
- High-cardinality data analysis (unlimited dimensions)
- Sub-second query performance on billions of events
- Distributed tracing with full context

#### Pricing After Free Tier (Pro Plan)

- Starting at $130/month for 100M events
- Up to 1.5B events/month
- $0.10/GB for telemetry pipeline processing
- Volume discounts available for Enterprise

#### Best For

- **Debug-driven teams** focused on production troubleshooting
- Applications generating high-cardinality telemetry
- Teams valuing query performance over long retention
- **Smaller event volumes** (<20M/month on free tier)

#### Limitations

- Free tier limited to 20M events/month (can exhaust quickly with traces)
- Event-based pricing vs data volume (need to estimate event counts)
- Less comprehensive for metrics/dashboards vs full observability platforms
- Only 2 triggers on free tier (limited alerting)

---

### Datadog (No Free Tier)

#### Pricing Structure

- **APM**: Per host pricing (high watermark plan)
- **Infrastructure**: Per host + custom metrics pricing
- **Logs**: Per GB ingested + per million events indexed
- **No permanent free tier** - 14-day trial only

#### OpenTelemetry Support

- ✅ **OTLP Support**: Via Datadog Agent with OTel receiver
- ⚠️ **Proprietary Integration**: Converts OTLP to Datadog format
- Limited to Datadog's data model and retention policies

#### Why NOT Recommended for This Use Case

- ❌ **No free tier** - starts at ~$15/host/month for APM
- ❌ **Complex pricing** - multiple billable dimensions (hosts, spans, logs,
  metrics)
- ❌ **Vendor lock-in** - proprietary agent and data format
- ❌ **Cost unpredictability** - can escalate quickly with scale

---

### Elastic Cloud (Limited Free Tier)

#### Pricing & Free Tier

- **Free Trial**: 14-day trial (not permanent)
- **Observability**: Starting at ~$95/month after trial
- **Self-hosted**: Elastic Stack is free/open source

#### OpenTelemetry Support

- ✅ **OTLP Support**: Via APM Server
- ✅ **Full Stack**: Elasticsearch, Kibana, APM
- **Integration**: OTLP export to Elastic APM Server

#### Why NOT Ideal for Free Tier Requirement

- ❌ **No permanent free cloud tier**
- Self-hosted option requires infrastructure management
- Complex to operate at scale without managed service

---

## Recommendation Summary

### **Best Choice: Grafana Cloud**

**Reasoning:**

1. **Generous Free Tier**: 50GB logs + 50GB traces + 10k metric series is
   substantial for your application
2. **Open Source Foundation**: No vendor lock-in, can self-host if needed
3. **Native OpenTelemetry**: Built on OTel-native backends (Tempo, Loki, Mimir)
4. **Cost Optimization**: Adaptive Metrics/Logs can reduce costs significantly
5. **Visualization Excellence**: Industry-leading dashboarding with Grafana
6. **Ecosystem**: Already has RabbitMQ, PostgreSQL, Redis dashboard templates

**Estimated Usage for Game Scheduler:**

- **Traces**: ~10-20 GB/month (well within 50GB free tier)
- **Logs**: ~20-30 GB/month (well within 50GB free tier)
- **Metrics**: ~5k active series (well within 10k free tier)
- **Cost**: **$0/month on free tier**

### **Alternative: New Relic**

**Reasoning:**

1. **Simple Pricing**: Single 100GB/month limit across all signals
2. **Full Platform**: Everything in one place, less configuration
3. **AI Features**: Built-in AI for anomaly detection and insights
4. **Easy Onboarding**: Fastest time-to-value

**Estimated Usage:**

- Combined telemetry: ~40-60 GB/month (within 100GB free tier)
- **Cost**: **$0/month on free tier**

**Trade-off**: Less flexible than Grafana Cloud, but simpler to manage

### **Runner-up: Honeycomb**

**Good for:**

- High-cardinality debugging scenarios
- Teams with <20M events/month
- Focus on trace-driven debugging vs metrics/logs

**Limitation**: Event counting model may not align well with your mixed workload

---

## Implementation Path for Grafana Cloud

### Step 1: Sign Up and Configure

```bash
# Sign up at https://grafana.com/auth/sign-up/create-user
# Obtain API keys for:
# - Grafana Cloud Metrics (Prometheus endpoint)
# - Grafana Cloud Logs (Loki endpoint)
# - Grafana Cloud Traces (Tempo endpoint)
```

### Step 2: Deploy Grafana Alloy (OpenTelemetry Collector)

```yaml
# docker-compose addition
grafana-alloy:
  image: grafana/alloy:latest
  volumes:
    - ./alloy-config.yaml:/etc/alloy/config.alloy
  ports:
    - "4317:4317" # OTLP gRPC
    - "4318:4318" # OTLP HTTP
  environment:
    - GRAFANA_CLOUD_API_KEY=${GRAFANA_CLOUD_API_KEY}
    - GRAFANA_CLOUD_INSTANCE_ID=${GRAFANA_CLOUD_INSTANCE_ID}
  command: run --server.http.listen-addr=0.0.0.0:12345 /etc/alloy/config.alloy
```

### Step 3: Configure Alloy to Forward to Grafana Cloud

```hcl
// alloy-config.yaml
otelcol.receiver.otlp "default" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }
  http {
    endpoint = "0.0.0.0:4318"
  }

  output {
    traces  = [otelcol.exporter.otlp.grafana_cloud_tempo.input]
    metrics = [otelcol.exporter.prometheus.grafana_cloud.input]
    logs    = [otelcol.exporter.loki.grafana_cloud.input]
  }
}

otelcol.exporter.otlp "grafana_cloud_tempo" {
  client {
    endpoint = env("GRAFANA_CLOUD_TEMPO_ENDPOINT")
    auth     = otelcol.auth.basic.grafana_cloud.handler
  }
}

otelcol.exporter.prometheus "grafana_cloud" {
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
}

prometheus.remote_write "grafana_cloud" {
  endpoint {
    url = env("GRAFANA_CLOUD_PROMETHEUS_ENDPOINT")
    basic_auth {
      username = env("GRAFANA_CLOUD_INSTANCE_ID")
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}

otelcol.exporter.loki "grafana_cloud" {
  forward_to = [loki.write.grafana_cloud.receiver]
}

loki.write "grafana_cloud" {
  endpoint {
    url = env("GRAFANA_CLOUD_LOKI_ENDPOINT")
    basic_auth {
      username = env("GRAFANA_CLOUD_INSTANCE_ID")
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}
```

### Step 4: Update Python Services

```bash
# Add to .env
OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_SERVICE_NAME=api-service  # per service

# Services automatically send to Alloy, which forwards to Grafana Cloud
```

### Step 5: Access Grafana Cloud

- Navigate to your Grafana Cloud instance
- Explore → Tempo (traces)
- Explore → Loki (logs)
- Dashboards → Create (metrics visualization)
- Pre-built dashboards available for PostgreSQL, Redis, RabbitMQ

### Benefits of This Architecture

1. **Cost**: Stays within free tier limits
2. **Flexibility**: Can switch backends without changing app code
3. **Control**: Alloy handles batching, retry, filtering locally
4. **Privacy**: Sensitive data filtering before cloud export
5. **Resilience**: Local buffering if cloud endpoint unavailable

---

## Critical Implementation Learnings: Grafana Cloud Authentication

### CRITICAL: Grafana Cloud Uses Multiple Instance IDs

Grafana Cloud has **separate instance IDs** for different services. You
**CANNOT** use a single instance ID for all endpoints.

**Three Distinct Instance IDs Required:**

1. **OTLP Gateway Instance ID** (for traces, metrics, logs via OTLP)

   - Found in: Grafana Cloud Portal → Connections → "OTLP" section
   - Format: 7-digit number (e.g., `1461503`)
   - Used for: OTLP HTTP/gRPC authentication

2. **Prometheus/Mimir Instance ID** (for direct Prometheus remote_write)

   - Found in: Grafana Cloud Portal → Connections → "Prometheus" section
   - Format: 7-digit number (e.g., `2847239`)
   - Used for: Infrastructure metrics via prometheus.remote_write

3. **Loki Instance ID** (for direct log ingestion)
   - Found in: Grafana Cloud Portal → Connections → "Loki" section
   - Format: 7-digit number (e.g., `1419296`)
   - Used for: Log forwarding via loki.write

**IMPORTANT**: These instance IDs are **different numbers** for the same
account. Using the wrong instance ID results in **401 Unauthorized** errors.

### Authentication Token Formats

**OTLP Gateway Authentication:**

```bash
# Create Basic Auth token for OTLP
# Format: base64(instance_id:api_key)
echo -n "1461503:glc_xxxxx" | base64
# Result: MTQ2MTUwMzpnbGNfZXh4eHh4...

# Use in Alloy config:
headers = {
  "authorization" = "Basic MTQ2MTUwMzpnbGNfZXh4eHh4..."
}
```

**Prometheus Remote Write Authentication:**

```hcl
# Uses separate instance ID and API key
basic_auth {
  username = "2847239"  # Prometheus instance ID (NOT OTLP instance ID)
  password = "glc_xxxxx"  # Same API key works across services
}
```

**Loki Write Authentication:**

```hcl
# Uses Loki-specific instance ID
basic_auth {
  username = "1419296"  # Loki instance ID
  password = "glc_xxxxx"  # Same API key
}
```

### Endpoint Configuration Patterns

**OTLP Endpoints:**

```bash
# OTLP Gateway (all signals: traces, metrics, logs)
GRAFANA_CLOUD_OTLP_ENDPOINT="otlp-gateway-prod-us-west-0.grafana.net/otlp"

# Use with HTTPS prefix in Alloy:
endpoint = "https://otlp-gateway-prod-us-west-0.grafana.net/otlp"

# Protocol: HTTP/protobuf (NOT gRPC - ALPN issues)
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

**Prometheus Remote Write:**

```bash
# Direct Mimir endpoint
GRAFANA_CLOUD_PROMETHEUS_ENDPOINT="https://prometheus-prod-36-prod-us-west-0.grafana.net/api/prom/push"

# Must use matching Prometheus instance ID in basic_auth
```

**Loki Push:**

```bash
# Direct Loki endpoint
GRAFANA_CLOUD_LOKI_ENDPOINT="https://logs-prod-012.grafana.net/loki/api/v1/push"

# Must use matching Loki instance ID in basic_auth
```

### Working Alloy Configuration Pattern

**Complete verified configuration:**

```hcl
// OTLP Receiver (receives from Python services)
otelcol.receiver.otlp "default" {
  grpc { endpoint = "0.0.0.0:4317" }
  http { endpoint = "0.0.0.0:4318" }

  output {
    traces  = [otelcol.processor.batch.default.input]
    metrics = [otelcol.processor.batch.default.input]
    logs    = [otelcol.processor.batch.default.input]
  }
}

// Batch Processor (optimize export)
otelcol.processor.batch "default" {
  timeout = "10s"
  send_batch_size = 8192

  output {
    traces  = [otelcol.exporter.otlphttp.grafana_cloud.input]
    metrics = [otelcol.exporter.otlphttp.grafana_cloud.input]
    logs    = [otelcol.exporter.otlphttp.grafana_cloud.input]
  }
}

// OTLP HTTP Exporter to Grafana Cloud
// CRITICAL: Use otlphttp (NOT otlp) to avoid gRPC ALPN issues
otelcol.exporter.otlphttp "grafana_cloud" {
  client {
    endpoint = "https://" + env("GRAFANA_CLOUD_OTLP_ENDPOINT")
    headers = {
      "authorization" = "Basic " + env("GRAFANA_CLOUD_AUTH_TOKEN")
    }
  }
}

// PostgreSQL Built-in Exporter
prometheus.exporter.postgres "integrations_postgres_exporter" {
  data_source_names = ["postgresql://user:password@postgres:5432/dbname?sslmode=disable"]
}

// Discovery and Labeling for PostgreSQL
discovery.relabel "integrations_postgres_exporter" {
  targets = prometheus.exporter.postgres.integrations_postgres_exporter.targets

  rule {
    target_label = "job"
    replacement  = "integrations/postgres_exporter"
  }
  rule {
    target_label = "instance"
    replacement  = "postgres"
  }
}

// Metric Filtering (cost optimization)
prometheus.relabel "integrations_postgres_exporter" {
  forward_to = [prometheus.remote_write.grafana_cloud_mimir.receiver]

  rule {
    source_labels = ["__name__"]
    regex = "pg_settings_.*|pg_stat_activity_.*|pg_stat_bgwriter_.*|pg_stat_database_.*|pg_up|up"
    action = "keep"
  }
}

// Scrape PostgreSQL Exporter
prometheus.scrape "integrations_postgres_exporter" {
  targets    = discovery.relabel.integrations_postgres_exporter.output
  forward_to = [prometheus.relabel.integrations_postgres_exporter.receiver]
  job_name   = "integrations/postgres_exporter"
  scrape_interval = "60s"
}

// Prometheus Remote Write (infrastructure metrics)
// CRITICAL: Uses DIFFERENT instance ID than OTLP
prometheus.remote_write "grafana_cloud_mimir" {
  endpoint {
    url = env("GRAFANA_CLOUD_PROMETHEUS_ENDPOINT")
    basic_auth {
      username = "2847239"  // Hardcoded Prometheus instance ID
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}
```

### Environment Variables (.env)

```bash
# OTLP Gateway Configuration
GRAFANA_CLOUD_INSTANCE_ID=1461503  # OTLP instance ID
GRAFANA_CLOUD_API_KEY=glc_xxxxx    # Cloud API key
GRAFANA_CLOUD_AUTH_TOKEN="MTQ2MTUwMzpnbGNfZXh4eHh4..."  # base64(1461503:glc_xxxxx)
GRAFANA_CLOUD_OTLP_ENDPOINT="otlp-gateway-prod-us-west-0.grafana.net/otlp"

# Prometheus Remote Write Configuration
GRAFANA_CLOUD_PROMETHEUS_ENDPOINT=https://prometheus-prod-36-prod-us-west-0.grafana.net/api/prom/push
# Uses hardcoded instance 2847239 in Alloy config

# Python Service Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp  # Enable logging
```

### Common Pitfalls and Solutions

**Problem 1: 401 Unauthorized from Tempo/Mimir**

- **Cause**: Using wrong instance ID for the service
- **Solution**: Get correct instance ID from Grafana Cloud portal for specific
  service
- **Verification**: Test with curl using correct instance:token combination

**Problem 2: gRPC Connection Failures with ALPN**

- **Cause**: Using `otelcol.exporter.otlp` (gRPC) instead of HTTP
- **Solution**: Use `otelcol.exporter.otlphttp` with `http/protobuf` protocol
- **Evidence**: ALPN negotiation failures in logs

**Problem 3: Logs Not Appearing in Loki**

- **Cause**: `OTEL_LOGS_EXPORTER` not set (defaults to none)
- **Solution**: Explicitly set `OTEL_LOGS_EXPORTER=otlp` in service environment
- **Verification**: Check for "OpenTelemetry logging initialized" message in
  service logs

**Problem 4: PostgreSQL Exporter Authentication Failure**

- **Cause**: Wrong database name or password in DSN
- **Solution**: Match DSN exactly to environment variables:
  `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable`
- **Common error**: Using `gamebot` database when actual name is
  `game_scheduler`

**Problem 5: Container Not Picking Up Code Changes**

- **Cause**: Docker images use copied code, not mounted volumes
- **Solution**: Rebuild image with `docker compose build <service>` after code
  changes
- **Alternative**: Use volume mounts in development docker-compose override

**Problem 6: Python Logging Not Initializing (Silent Success)**

- **Cause**: Logging initialization code executes but success message doesn't
  appear
- **Symptoms**: "OpenTelemetry tracing initialized" and "metrics initialized"
  appear, but NOT "logging initialized"
- **Root Cause**: Code works correctly (manual test confirms HTTP 200 to Alloy),
  but logger may not be fully configured when message is logged
- **Solution**: Logging IS working (verified with manual test), message timing
  issue only
- **Verification**: Test manually with Python code to confirm logs reach Alloy
  with HTTP 200 response

**Problem 7: AttributeError After Schema Changes**

- **Cause**: OpenTelemetry span attributes referencing fields removed in
  refactoring
- **Example**: `span.set_attribute("guild_id", game_data.guild_id)` when
  `guild_id` removed from `GameCreateRequest`
- **Solution**: Update span attributes to match current schema (e.g., use
  `template_id` instead of `guild_id`)
- **Prevention**: Review telemetry code when making schema changes

**Problem 8: PostgreSQL Exporter Redundancy**

- **Cause**: Both separate postgres-exporter container AND Alloy built-in
  exporter running simultaneously
- **Impact**: Unnecessary container consuming resources, potential duplicate
  metrics
- **Solution**: Remove postgres-exporter service from docker-compose.base.yml
  after configuring Alloy's built-in prometheus.exporter.postgres
- **Benefit**: Alloy's built-in exporter supports metric filtering (cost
  optimization) and native integration

### Verification Checklist

**Alloy Health Check:**

```bash
# Check Alloy is receiving OTLP
docker logs gamebot-grafana-alloy | grep "Starting HTTP server"
# Should show: endpoint=[::]:4318

# Check for authentication errors
docker logs gamebot-grafana-alloy | grep -i "error\|unauthorized\|401"
# Should be empty

# Check PostgreSQL exporter connection
docker logs gamebot-grafana-alloy | grep "postgres"
# Should show connection established, no auth errors
```

**Python Service Check:**

```bash
# Verify OpenTelemetry initialization
docker logs gamebot-api | grep "OpenTelemetry.*initialized"
# Should show: tracing, metrics, AND logging initialized

# Check OTLP endpoint is set
docker exec gamebot-api env | grep OTEL
# Should show OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318
```

**End-to-End Trace Test:**

```bash
# Send test request
curl -X GET http://localhost:8000/health

# Check Alloy received and forwarded
docker logs gamebot-grafana-alloy --since 1m | grep -i "batch"

# Verify in Grafana Cloud:
# Navigate to Explore → Tempo → Search for service.name="api-service"
```

### Systematic Implementation Sequence

**Phase 1: Alloy + Grafana Cloud Connection**

1. Deploy Alloy container with minimal config (OTLP receiver only)
2. Configure OTLP exporter with correct instance ID and auth token
3. Test with curl to OTLP endpoint, verify 200 response
4. Check Grafana Cloud for test traces
5. **Do not proceed until traces visible in Tempo**

**Phase 2: PostgreSQL Metrics**

1. Add prometheus.exporter.postgres to Alloy config
2. Add discovery.relabel and prometheus.relabel
3. Add prometheus.remote_write with Prometheus instance ID (2847239)
4. Restart Alloy, check for connection success
5. Verify metrics in Grafana Cloud Prometheus/Mimir
6. **Do not proceed until pg\_\* metrics visible**

**Phase 3: Redis Metrics**

1. Add redis-exporter container OR use prometheus.exporter.redis in Alloy
2. Add prometheus.scrape configuration
3. Restart Alloy, verify connection
4. Check redis\_\* metrics in Grafana Cloud
5. **Do not proceed until redis metrics visible**

**Phase 4: Python Services (ONE AT A TIME)**

**For each service (api, bot, notification-daemon, status-transition-daemon):**

1. Add OpenTelemetry packages to pyproject.toml
2. Add init_telemetry() call in service startup
3. Set environment variables (OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT,
   etc.)
4. Rebuild and restart ONLY this service
5. Check service logs for "OpenTelemetry tracing/metrics/logging initialized"
6. Generate test traffic for this service
7. Verify in Grafana Cloud:
   - Traces in Tempo (service.name filter)
   - Metrics in Mimir (filter by service name)
   - Logs in Loki (filter by service name)
8. **Do not proceed to next service until all three signals confirmed**

---

## Distributed Tracing and Context Propagation

### Do You Need Transaction IDs in Database Tables?

**Short Answer: NO** - OpenTelemetry handles trace context propagation
automatically for most cases.

**How OpenTelemetry Trace Context Works:**

1. **HTTP Requests**: Trace context automatically propagated via headers
   (`traceparent`, `tracestate`)
2. **Database Queries**: Span created with parent trace context, no DB schema
   changes needed
3. **Redis Operations**: Span linked to parent trace context automatically
4. **RabbitMQ Messages**: Context propagated via message properties/headers
   (with instrumentation)

**When Trace Context Breaks:**

- **Asynchronous jobs** that don't receive context (e.g., cron triggers)
- **Database-triggered events** that don't have upstream context
- **Long-lived background tasks** that lose connection to originating request

### Trace Propagation Architecture in Game Scheduler

**Request Flow with Automatic Context Propagation:**

```
1. User → Frontend → API (HTTP request)
   └─ traceparent header → API receives trace context

2. API → Database (SQLAlchemy query)
   └─ Span inherits trace context from HTTP request span

3. API → RabbitMQ (publish message)
   └─ Trace context embedded in message properties

4. Daemon → RabbitMQ (consume message)
   └─ Trace context extracted from message properties

5. Daemon → Discord API (HTTP call)
   └─ traceparent header propagated to Discord
```

**What Gets Traced Automatically:**

- ✅ HTTP request from frontend to API
- ✅ API handler function execution
- ✅ Database queries (asyncpg/SQLAlchemy)
- ✅ Redis operations (get/set/delete)
- ✅ RabbitMQ message publish (with `opentelemetry-instrumentation-aio-pika`)
- ✅ RabbitMQ message consume (extracts context from message)
- ✅ HTTP calls to Discord API (httpx/aiohttp instrumentation)

**What Creates NEW Root Traces:**

- ⚠️ Scheduled tasks (APScheduler triggers) - no upstream context
- ⚠️ Discord events (bot receives event) - Discord doesn't send trace context
- ⚠️ Database triggers/notifications - PostgreSQL doesn't propagate OTel context

### When to Store Trace IDs in Database

**You MAY want trace IDs in database if:**

1. **Long-term Audit Trail**: Need to look up traces from historical records
   weeks/months later
2. **Cross-System Correlation**: Correlating with external systems that use
   trace IDs
3. **Custom Analytics**: Running SQL queries that join business data with
   observability data

**Implementation Pattern:**

```python
from opentelemetry import trace

# During game creation
current_span = trace.get_current_span()
trace_id = format(current_span.get_span_context().trace_id, '032x')

game = Game(
    title="Game Night",
    trace_id=trace_id,  # Optional: store for long-term lookup
    # ... other fields
)
```

**Schema Addition:**

```sql
ALTER TABLE games ADD COLUMN trace_id VARCHAR(32);
ALTER TABLE notifications ADD COLUMN trace_id VARCHAR(32);
CREATE INDEX idx_games_trace_id ON games(trace_id);
```

**HOWEVER, for most use cases, this is NOT necessary because:**

- Grafana Cloud Tempo retains traces for 14 days (free tier)
- You can filter by time range and service name to find relevant traces
- Trace context automatically flows through synchronous operations

### RabbitMQ Message Context Propagation

**With `opentelemetry-instrumentation-aio-pika`:**

**Publisher (API service):**

```python
# Trace context automatically injected into message properties
await channel.default_exchange.publish(
    aio_pika.Message(body=json.dumps(data).encode()),
    routing_key=queue_name
)
# No manual trace ID handling needed!
```

**Consumer (Notification Daemon):**

```python
# Trace context automatically extracted and span linked
async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        # This span is automatically linked to publisher's trace
        notification = await send_notification(message.body)
# No manual trace ID extraction needed!
```

**Message Properties Include:**

- `traceparent`: W3C trace context header
- `tracestate`: Additional vendor-specific context
- Automatically handled by instrumentation library

### Discord Bot Event Handling

**Discord events DON'T have trace context** (Discord doesn't support
OpenTelemetry).

**Solution: Create root spans for bot events:**

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@bot.event
async def on_message(message):
    # Create new root span for this Discord event
    with tracer.start_as_current_span(
        "discord.on_message",
        attributes={
            "discord.user_id": str(message.author.id),
            "discord.channel_id": str(message.channel.id),
            "discord.guild_id": str(message.guild.id) if message.guild else None,
        }
    ):
        # All downstream operations inherit this trace context
        await process_message(message)
```

**Result**: Complete trace from Discord event → database queries → RabbitMQ
publish → daemon processing

### Scheduled Task Tracing

**APScheduler jobs have no upstream context:**

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@scheduler.scheduled_job('interval', minutes=5)
async def check_upcoming_games():
    # Create root span for scheduled job
    with tracer.start_as_current_span(
        "scheduled.check_upcoming_games",
        attributes={
            "scheduler.job_id": "check_upcoming_games",
            "scheduler.trigger": "interval",
        }
    ):
        games = await fetch_upcoming_games()
        await send_notifications(games)
```

### Recommendation: Start Simple

**Phase 1 Implementation (DO THIS):**

- ✅ Auto-instrument HTTP, database, Redis, RabbitMQ
- ✅ Add manual spans for Discord events and scheduled tasks
- ✅ Use built-in context propagation (no DB schema changes)

**Phase 2 Enhancements (OPTIONAL, LATER):**

- Add trace_id columns to key tables if long-term audit trail needed
- Implement custom span attributes for business metrics
- Add manual spans for complex business logic

**You do NOT need:**

- ❌ Transaction ID columns in database (trace context propagates automatically)
- ❌ Manual trace context serialization to RabbitMQ (instrumentation handles it)
- ❌ Custom context injection (OpenTelemetry SDK does this)

---

## Recommended Phased Implementation Plan

### Phase 1: Foundation (1-2 hours)

**Goal: Alloy connected to Grafana Cloud, verified with test traces**

1. Deploy Alloy container with OTLP receiver only
2. Configure OTLP HTTP exporter to Grafana Cloud (correct instance ID, auth
   token)
3. Test with manual curl POST to Alloy OTLP endpoint
4. Verify traces appear in Grafana Cloud Tempo
5. **Success Criteria**: Curl test trace visible in Tempo with proper service
   name

### Phase 2: PostgreSQL Metrics (1 hour)

**Goal: Database metrics flowing to Grafana Cloud Mimir**

1. Add prometheus.exporter.postgres to Alloy config with correct DSN
2. Add discovery.relabel and prometheus.relabel (metric filtering)
3. Configure prometheus.remote_write with Prometheus instance ID (2847239)
4. Restart Alloy, verify no authentication errors
5. Wait 60 seconds for scrape, query metrics in Grafana Cloud
6. **Success Criteria**: `pg_up`, `pg_stat_database_*` metrics visible in Mimir

### Phase 3: Redis Metrics (30 minutes)

**Goal: Cache metrics flowing to Grafana Cloud**

1. Add prometheus.scrape for redis-exporter (or add prometheus.exporter.redis)
2. Restart Alloy, verify scrape target
3. Query redis\_\* metrics in Grafana Cloud
4. **Success Criteria**: `redis_up`, `redis_memory_*` metrics visible in Mimir

### Phase 4: API Service (1 hour)

**Goal: Complete traces, metrics, logs from FastAPI service**

1. Add OpenTelemetry packages to pyproject.toml (fastapi, sqlalchemy, asyncpg,
   redis, aio-pika)
2. Add init_telemetry() to services/api/app.py startup
3. Configure environment variables (OTEL_SERVICE_NAME=api-service, etc.)
4. Rebuild API container: `docker compose build api`
5. Restart API: `docker compose up -d api`
6. Check logs for "OpenTelemetry tracing/metrics/logging initialized"
7. Send test request: `curl http://localhost:8000/health`
8. Verify in Grafana Cloud:
   - Traces: Search Tempo for service.name="api-service"
   - Metrics: Query Mimir for
     http_server_request_duration{service_name="api-service"}
   - Logs: Search Loki for {service_name="api-service"}
9. **Success Criteria**: All three signals present with correct service name

### Phase 5: Bot Service (1 hour)

**Goal: Discord bot traces with manual instrumentation**

1. Add OpenTelemetry packages (same as API)
2. Add init_telemetry() to services/bot/main.py
3. Add manual spans for Discord event handlers (@bot.event)
4. Configure OTEL_SERVICE_NAME=bot-service
5. Rebuild and restart bot
6. Trigger Discord command
7. Verify bot traces in Tempo (should show discord.\* span names)
8. **Success Criteria**: Bot command creates trace from Discord event → database
   → RabbitMQ

### Phase 6: Daemons (1 hour each)

**Goal: Scheduled task traces and message consumer traces**

For each daemon (notification-daemon, status-transition-daemon):

1. Add OpenTelemetry packages
2. Add init_telemetry() to daemon startup
3. Add manual spans for scheduled tasks and message handlers
4. Configure unique OTEL_SERVICE_NAME
5. Rebuild and restart daemon
6. Trigger scheduled task or send message via API
7. Verify daemon traces showing task execution
8. **Success Criteria**: Scheduled tasks create root spans, message consumers
   link to publisher traces

### Total Estimated Time: 6-8 hours (with systematic debugging at each phase)

### Success Validation Queries

**Grafana Cloud Tempo (Traces):**

```
# All traces in last hour
{}

# Traces from specific service
{service.name="api-service"}

# Traces with errors
{status.code="ERROR"}

# Traces for specific HTTP endpoint
{http.target="/api/games"}
```

**Grafana Cloud Mimir (Metrics):**

```
# PostgreSQL connection count
pg_stat_database_numbackends

# API request duration
http_server_duration_bucket{service_name="api-service"}

# Redis memory usage
redis_memory_used_bytes

# Request rate by service
rate(http_server_requests_total[5m])
```

**Grafana Cloud Loki (Logs):**

```
# All logs from API
{service_name="api-service"}

# Error logs only
{service_name="api-service"} |= "ERROR"

# Logs with trace context
{service_name="api-service"} | json | trace_id != ""
```
