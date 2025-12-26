# Phase 4 Verification: API Service Instrumentation

This guide provides step-by-step verification that the API service is properly instrumented with OpenTelemetry and telemetry data is flowing to Grafana Cloud.

## Prerequisites

- Grafana Cloud account configured (see `SETUP_GRAFANA_CLOUD.md`)
- Grafana Alloy service running and connected to Grafana Cloud
- `.env` file configured with Grafana Cloud credentials (see **Critical Note** below)
- Docker containers built with latest code changes

**⚠️ Critical Note: Instance ID Configuration**

Grafana Cloud uses **different instance IDs for different services**. The most common mistake is using the Prometheus instance ID for OTLP metrics:

- **Tempo (traces via OTLP):** Use Tempo instance ID
- **Prometheus (infrastructure metrics):** Use Prometheus instance ID
- **Loki (logs):** Use Loki instance ID
- **OTLP Gateway (application metrics):** Use OTLP instance ID (NOT Prometheus ID!)

To find your OTLP instance ID:
1. In Grafana Cloud, go to **Connections** → **OTLP**
2. Copy the authorization header
3. Decode the base64 string - the instance ID is after the colon in the decoded value
4. Set `GRAFANA_CLOUD_OTLP_INSTANCE_ID` in your `.env` file (hardcoded in `config.alloy` for now)

## Step 1: Rebuild API Service Container

The API service needs to be rebuilt to include the new telemetry code:

```bash
docker compose build api
```

## Step 2: Restart API Service

Restart the API service to pick up the new instrumentation:

```bash
docker compose up -d api
```

## Step 3: Check API Service Logs

Verify that OpenTelemetry initialized successfully:

```bash
docker logs gamebot-api --tail 50
```

**Expected output:**

```
OpenTelemetry tracing initialized
OpenTelemetry metrics initialized
OpenTelemetry logging initialized
OpenTelemetry instrumentation enabled for api-service
FastAPI application created (environment: development)
```

**Note:** The "logging initialized" message may not appear consistently due to logging timing issues, but the functionality works (verified manually).

## Step 4: Send Test Request

Send a request to the API health endpoint:

```bash
curl http://localhost:8000/health
```

**Expected output:**

```json
{"status":"healthy","service":"api"}
```

## Step 5: Check Alloy Logs for Errors

Verify there are no authentication or export errors:

```bash
# Check for any errors in the last 2 minutes
docker logs gamebot-grafana-alloy --since 2m 2>&1 | grep -i "error\|401\|unauthenticated"
```

**Expected output:** No 401 or authentication errors

**If you see HTTP 401 errors:** This indicates incorrect instance ID configuration. The most common cause is using the Prometheus instance ID instead of the OTLP gateway instance ID. See the Prerequisites section above for how to find the correct OTLP instance ID.

```bash
# Verify OTLP HTTP requests are being made
docker logs gamebot-grafana-alloy --since 2m 2>&1 | grep -i "otlphttp"
```

**Expected output:** Log lines showing "Preparing to make HTTP request" to the OTLP gateway endpoint

## Step 6: Verify Traces in Grafana Cloud Tempo

1. Navigate to your Grafana Cloud instance
2. Go to **Explore** → Select **Tempo** data source
3. Use TraceQL query:

   ```traceql
   {service.name="api-service"}
   ```

4. Set time range to **Last 15 minutes**

4. Select time range: **Last 15 minutes**
5. Click **Run Query**

**Expected results:**

- At least one trace visible for the `/health` request
- Trace should show:
  - Root span: `GET /health` with HTTP attributes
  - Child spans may include database queries if health check accesses DB
  - Span attributes: `http.method`, `http.status_code`, `http.target`

## Step 7: Verify Metrics in Grafana Cloud Mimir

**⚠️ Important:** Metrics are exported in batches every 60 seconds. Wait at least 1-2 minutes after generating test traffic before querying.

1. Go to **Explore** → Select **Prometheus** data source
2. Use PromQL query:

   ```promql
   http_server_duration_bucket{service_name="api-service"}
   ```

3. Click **Run Query**
4. Set time range to **Last 5 minutes**

**Expected results:**

- Metrics visible for HTTP request duration
- Histogram buckets showing request latency distribution

**Alternative queries:**

```promql
# Request count
http_server_requests_total{service_name="api-service"}

# Active requests
http_server_active_requests{service_name="api-service"}
```

## Step 8: Verify Logs in Grafana Cloud Loki

1. Go to **Explore** → Select **Loki** data source
2. Use LogQL query:

   ```logql
   {service_name="api-service"}
   ```

3. Click **Run Query**

**Expected results:**

- Application logs visible with service_name label
- Logs should include initialization messages and request logs
- Look for trace correlation: logs may include `trace_id` fields

## Step 9: Test Database Query Tracing

Send a request that triggers a database query:

```bash
# Get guilds (requires authentication, may need valid token)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/guilds
```

**Verify in Tempo:**

- Trace should show database query as child span
- Child span should have operation name like `SELECT` or similar
- Attributes should include SQL statement details

## Step 10: Test Redis Operation Tracing

Send a request that uses Redis caching:

```bash
# Multiple requests to same endpoint (second should hit cache)
curl http://localhost:8000/health
curl http://localhost:8000/health
```

**Verify in Tempo:**

- Look for Redis operation spans in traces
- Spans should show Redis commands (GET, SET, etc.)

## Troubleshooting

### Issue: HTTP 401 Unauthenticated errors for metrics

**Symptom:** Alloy logs show repeated "HTTP Status Code 401" errors when trying to export metrics to the OTLP gateway.

**Root Cause:** Using incorrect instance ID for OTLP gateway authentication. The OTLP gateway requires its own specific instance ID, which is different from the Prometheus instance ID.

**Solution:**

1. Find your OTLP instance ID:
   - Go to Grafana Cloud → **Connections** → **OTLP**
   - Copy the authorization header value
   - Decode the base64 string: `echo "<header_value>" | base64 -d`
   - The instance ID is the number after the colon

2. Update `grafana-alloy/config.alloy`:
   ```alloy
   otelcol.auth.basic "grafana_cloud_otlp" {
     username = "<your_otlp_instance_id>"  // NOT the Prometheus ID!
     password = env("GRAFANA_CLOUD_API_KEY")
   }
   ```

3. Restart Alloy:
   ```bash
   docker compose restart grafana-alloy
   ```

4. Generate test traffic and wait 60+ seconds for next export cycle

5. Verify no more 401 errors:
   ```bash
   docker logs gamebot-grafana-alloy --since 2m | grep -i "401\|error"
   ```

### Issue: No "logging initialized" message in logs

**Status:** Known timing issue, logging functionality works despite missing message.

**Verification:** Manually test log export with Python:

```python
import requests
import json

# Send test log to Alloy
response = requests.post(
    "http://localhost:4318/v1/logs",
    json={
        "resourceLogs": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "test"}}]},
            "scopeLogs": [{"logRecords": [{"body": {"stringValue": "test log"}}]}]
        }]
    }
)
print(f"Status: {response.status_code}")
```

**Expected:** HTTP 200 response

### Issue: No traces visible in Tempo

**Possible causes:**

1. Alloy not forwarding to Grafana Cloud
   - Check Alloy logs for authentication errors
   - Verify GRAFANA_CLOUD_TEMPO_INSTANCE_ID is correct
2. API service not sending traces
   - Check API logs for initialization errors
   - Verify OTEL_EXPORTER_OTLP_ENDPOINT is `http://grafana-alloy:4318`
3. Time range issue in Grafana
   - Extend time range to last hour

### Issue: AttributeError in span attributes

**Cause:** Span attributes referencing removed schema fields (e.g., `guild_id` removed in refactoring)

**Solution:** Update span attributes to match current schema

### Issue: Container not picking up code changes

**Cause:** Docker images use copied code, not volume mounts

**Solution:** Rebuild container after code changes:

```bash
docker compose build api
docker compose up -d api
```

## Success Criteria

All of the following should be true:

- ✅ API service logs show telemetry initialization
- ✅ Test requests return successful responses
- ✅ Traces visible in Grafana Cloud Tempo with correct service name
- ✅ HTTP spans include proper attributes (method, status, target)
- ✅ Database query spans appear as children of HTTP spans (when applicable)
- ✅ Metrics visible in Grafana Cloud Mimir (http_server_duration_bucket)
- ✅ Logs visible in Grafana Cloud Loki with service_name label

## Verification Results (2025-12-09)

### Authentication Fix
**Issue:** Metrics failing with HTTP 401 Unauthenticated errors
**Root Cause:** Used Prometheus instance ID instead of OTLP gateway instance ID
**Solution:** Updated `grafana-alloy/config.alloy` to use correct instance ID in `otelcol.auth.basic`

```alloy
otelcol.auth.basic "grafana_cloud_otlp" {
  username = env("GRAFANA_CLOUD_OTLP_INSTANCE_ID")  // OTLP gateway instance ID, not Prometheus ID
  password = env("GRAFANA_CLOUD_API_KEY")
}
```

### Test Results
- ✅ **Traces:** Successfully flowing to Grafana Cloud Tempo (verified with service.name="api-service")
- ✅ **Metrics:** Authentication fixed, no more 401 errors in Alloy logs
- ✅ **Logs:** Flowing to Grafana Cloud with trace context
- ✅ Generated 10+ test requests, metrics exporting every 60 seconds
- ✅ Alloy logs confirm successful OTLP HTTP requests to gateway

### Instance ID Reference
Different Grafana Cloud services use different instance IDs:
- **Tempo (traces):** 1413606
- **Prometheus (metrics via remote_write):** (7-digit ID from Prometheus connection)
- **Loki (logs):** 1419296
- **OTLP Gateway (metrics via OTLP/HTTP):** (7-digit ID from OTLP endpoint) ← Critical for Phase 4

### Verification Queries
Access metrics in Grafana Cloud:
```promql
# HTTP request duration histogram
http_server_duration_bucket{service_name="api-service"}

# All metrics from API service
{service_name="api-service"}
```

## Next Steps

Once verification is complete, proceed to **Phase 5: Bot Service Instrumentation**.
