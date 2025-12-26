# Testing Grafana Alloy Connection to Grafana Cloud

This guide provides step-by-step instructions to verify that Grafana Alloy is
successfully connected to Grafana Cloud.

## Prerequisites

Before testing, ensure you have:

1. ✅ Completed Grafana Cloud account setup (Task 1.1)
2. ✅ Created `grafana-alloy/config.alloy` (Task 1.2)
3. ✅ Added `grafana-alloy` service to `compose.yaml` (Task 1.3)
4. ✅ Configured environment variables in `.env` file (Task 1.4)

## Step 1: Verify Environment Variables

Check that your `.env` file contains valid Grafana Cloud credentials:

```bash
# Check environment variables are set
grep -E "GRAFANA_CLOUD" .env

# Should show:
# GRAFANA_CLOUD_INSTANCE_ID=<7-digit number>
# GRAFANA_CLOUD_API_KEY=glc_<random string>
# GRAFANA_CLOUD_AUTH_TOKEN=<base64 string>
# GRAFANA_CLOUD_OTLP_ENDPOINT=otlp-gateway-prod-<region>.grafana.net/otlp
```

**Common Issues:**

- Missing `GRAFANA_CLOUD_AUTH_TOKEN`: Generate with
  `echo -n "INSTANCE_ID:API_KEY" | base64`
- Wrong instance ID: Must be OTLP instance ID, not Prometheus instance ID
- Missing `https://` on Prometheus endpoint but present on OTLP endpoint

## Step 2: Start Grafana Alloy

Start the Alloy service:

```bash
# Start Alloy (and any dependencies)
docker compose up -d grafana-alloy

# Check if container is running
docker compose ps grafana-alloy
```

Expected output:

```
NAME                      IMAGE                      STATUS    PORTS
gamebot-grafana-alloy     grafana/alloy:latest       Up        0.0.0.0:4317->4317/tcp, 0.0.0.0:4318->4318/tcp
```

## Step 3: Check Alloy Logs

Examine logs for startup success or authentication errors:

```bash
# View Alloy logs
docker compose logs grafana-alloy

# Watch logs in real-time
docker compose logs -f grafana-alloy
```

**Success Indicators:**

- ✅ `"Starting HTTP server" endpoint="[::]:4318"`
- ✅ `"Starting gRPC server" endpoint="[::]:4317"`
- ✅ No `401 Unauthorized` errors
- ✅ No `authentication failed` messages

**Common Errors:**

```
❌ "401 Unauthorized" - Wrong instance ID or API key
   Solution: Double-check GRAFANA_CLOUD_INSTANCE_ID matches OTLP instance ID

❌ "ALPN protocol negotiation failed" - Using gRPC exporter
   Solution: Verify config.alloy uses otelcol.exporter.otlphttp (NOT otlp)

❌ "connection refused" - Wrong endpoint URL
   Solution: Verify GRAFANA_CLOUD_OTLP_ENDPOINT format
```

## Step 4: Send Test Trace via Curl

Send a manual test trace to Alloy's OTLP HTTP endpoint:

```bash
# Create test trace payload
cat > /tmp/test-trace.json << 'EOF'
{
  "resourceSpans": [{
    "resource": {
      "attributes": [{
        "key": "service.name",
        "value": { "stringValue": "test-service" }
      }]
    },
    "scopeSpans": [{
      "scope": {
        "name": "manual-test"
      },
      "spans": [{
        "traceId": "5B8EFFF798038103D269B633813FC60C",
        "spanId": "EEE19B7EC3C1B174",
        "name": "test-span",
        "kind": 1,
        "startTimeUnixNano": "1609459200000000000",
        "endTimeUnixNano": "1609459200100000000",
        "attributes": [{
          "key": "test.attribute",
          "value": { "stringValue": "hello-grafana-cloud" }
        }]
      }]
    }]
  }]
}
EOF

# Send test trace to Alloy
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d @/tmp/test-trace.json \
  -v

# Expected response: HTTP 200 OK
```

**Expected Output:**

```
< HTTP/1.1 200 OK
< Content-Length: 0
< Date: Sat, 07 Dec 2025 ...
```

**If you get errors:**

- `Connection refused` - Alloy not running or wrong port
- `HTTP 500` - Check Alloy logs for backend connection errors
- `HTTP 401` - Alloy can't authenticate to Grafana Cloud

## Step 5: Verify Trace in Grafana Cloud

1. Log into your Grafana Cloud instance (https://your-stack.grafana.net)
2. Navigate to **Explore** → Select **Tempo** data source
3. Search for traces:
   - **Service name:** `test-service`
   - **Time range:** Last 5 minutes
4. You should see the test trace with span name `test-span`

**Query Examples:**

```
# Search by service name
{service.name="test-service"}

# Search by attribute
{test.attribute="hello-grafana-cloud"}
```

**Troubleshooting:**

- **No traces found after 1 minute:** Check Alloy logs for export errors
- **Traces visible but delayed:** This is normal (batching delay up to 10s)
- **Wrong service name:** Verify JSON payload structure

## Step 6: Validate Configuration

Run final validation checks:

```bash
# Check Alloy is listening on OTLP ports
netstat -tuln | grep -E "4317|4318"
# Should show: 0.0.0.0:4317 and 0.0.0.0:4318 LISTEN

# Check for authentication errors
docker compose logs grafana-alloy | grep -i "error\|unauthorized\|401"
# Should be empty or show only transient startup errors

# Verify environment variables are passed correctly
docker compose exec grafana-alloy env | grep GRAFANA_CLOUD
```

## Success Criteria Checklist

Mark each item complete when verified:

- [ ] Alloy container starts without errors
- [ ] No `401 Unauthorized` errors in Alloy logs
- [ ] Alloy HTTP server listening on port 4318
- [ ] Alloy gRPC server listening on port 4317
- [ ] Manual curl test returns HTTP 200 OK
- [ ] Test trace visible in Grafana Cloud Tempo within 1 minute
- [ ] Service name `test-service` correctly set in trace
- [ ] Trace attributes visible and correct

## Next Steps

Once all success criteria are met:

1. **Phase 1 Complete** ✅
2. Update plan file: Mark Phase 1 tasks as complete `[x]`
3. Proceed to **Phase 2: PostgreSQL Metrics Collection**

## Troubleshooting Resources

- **Grafana Cloud Portal:** Check "Connections" page for endpoint verification
- **Alloy Logs:** `docker compose logs grafana-alloy --tail=100`
- **Research Document:**
  `.copilot-tracking/research/20251206-opentelemetry-compatibility-research.md`
  (Lines 1050-1200)
- **Setup Guide:** `grafana-alloy/SETUP_GRAFANA_CLOUD.md`

## Common Issues and Solutions

### Issue: Container Restarts Continuously

```bash
# Check logs for config syntax errors
docker compose logs grafana-alloy --tail=50

# Validate config syntax (if Alloy provides CLI validation)
docker compose exec grafana-alloy alloy fmt /etc/alloy/config.alloy
```

### Issue: Port Already in Use

```bash
# Check what's using the ports
sudo lsof -i :4317
sudo lsof -i :4318

# If needed, change ports in .env:
ALLOY_OTLP_GRPC_PORT=14317
ALLOY_OTLP_HTTP_PORT=14318
```

### Issue: Environment Variables Not Set

```bash
# Verify docker-compose is loading .env
docker compose config | grep GRAFANA_CLOUD

# If empty, ensure .env symlink is configured correctly
ls -la .env
```

## Manual Test Script

For automated testing, save this as `test-alloy-connection.sh`:

```bash
#!/bin/bash
set -e

echo "Testing Grafana Alloy Connection..."

# Check Alloy is running
if ! docker compose ps grafana-alloy | grep -q "Up"; then
    echo "❌ Alloy container is not running"
    exit 1
fi
echo "✅ Alloy container is running"

# Send test trace
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:4318/v1/traces \
    -H "Content-Type: application/json" \
    -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"test-service"}}]},"scopeSpans":[{"scope":{"name":"manual-test"},"spans":[{"traceId":"5B8EFFF798038103D269B633813FC60C","spanId":"EEE19B7EC3C1B174","name":"test-span","kind":1,"startTimeUnixNano":"1609459200000000000","endTimeUnixNano":"1609459200100000000"}]}]}]}')

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✅ Test trace sent successfully (HTTP $HTTP_CODE)"
else
    echo "❌ Test trace failed (HTTP $HTTP_CODE)"
    exit 1
fi

# Check for errors in logs
if docker compose logs grafana-alloy --tail=50 | grep -qi "error\|401\|unauthorized"; then
    echo "⚠️  Errors found in Alloy logs - check manually"
    docker compose logs grafana-alloy --tail=20
else
    echo "✅ No errors in recent Alloy logs"
fi

echo ""
echo "✅ Phase 1 Testing Complete!"
echo "Next: Check Grafana Cloud Tempo for trace with service.name='test-service'"
```

Run with: `chmod +x test-alloy-connection.sh && ./test-alloy-connection.sh`
