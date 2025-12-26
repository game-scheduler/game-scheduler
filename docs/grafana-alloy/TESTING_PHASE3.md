<!-- markdownlint-disable-file -->

# Phase 3 Testing Guide: Redis Metrics Verification

## Prerequisites

- Phase 2 completed successfully
- PostgreSQL metrics visible in Grafana Cloud Mimir
- Alloy container running without errors

## Overview

Phase 3 uses Grafana Alloy's **built-in `prometheus.exporter.redis` component**,
which embeds the redis_exporter directly in Alloy. This approach eliminates the
need for a separate redis-exporter container and uses Alloy's efficient
in-memory traffic for metric collection.

## Step-by-Step Testing Procedure

### Step 1: Restart Alloy with Updated Configuration

```bash
# Restart Alloy to load new Redis exporter configuration
docker compose restart grafana-alloy

# Wait 10 seconds for initialization
sleep 10
```

### Step 2: Check Alloy Logs for Redis Connection

```bash
# Check for Redis exporter initialization
docker logs gamebot-grafana-alloy --since 1m | grep -i redis

# Expected output should include:
# - "Starting Redis exporter"
# - "Connected to Redis"
# - No connection errors or authentication failures
```

### Step 3: Verify Redis Scrape Target

```bash
# Check that Redis scrape target is active
docker logs gamebot-grafana-alloy --since 1m | grep "integrations/redis_exporter"

# Expected output:
# - Scrape target configured
# - Scrape successful messages
# - No scrape errors
```

### Step 4: Wait for First Metrics Collection

```bash
# Wait 60 seconds for first scrape interval to complete
echo "Waiting 60 seconds for Redis metrics scrape..."
sleep 60
```

### Step 5: Query Redis Metrics in Grafana Cloud

**Navigate to Grafana Cloud:**

1. Open your Grafana Cloud instance
2. Go to **Explore** → **Prometheus** (Mimir)

**Query 1: Redis Uptime**

```promql
redis_up
```

**Expected Result:**

- Value: `1` (Redis is up and reachable)
- Labels: `job="integrations/redis_exporter"`, `instance="redis"`

**Query 2: Redis Memory Usage**

```promql
redis_memory_used_bytes
```

**Expected Result:**

- Value: Numeric value representing bytes (e.g., `1048576` for ~1MB)
- Labels: `job="integrations/redis_exporter"`, `instance="redis"`

**Query 3: Redis Commands Processed**

```promql
redis_commands_processed_total
```

**Expected Result:**

- Value: Counter showing total commands processed since Redis started
- Labels: `job="integrations/redis_exporter"`, `instance="redis"`

**Query 4: Redis Connected Clients**

```promql
redis_connected_clients
```

**Expected Result:**

- Value: Number of currently connected clients (typically 1-5 for
  game-scheduler)
- Labels: `job="integrations/redis_exporter"`, `instance="redis"`

### Step 6: Verify Metric Filtering (Cost Optimization)

**Query for filtered metrics only:**

```promql
{job="integrations/redis_exporter"}
```

**Expected Result:**

- Only metrics matching the filter regex should appear:
  - `redis_up`
  - `redis_memory_*` (various memory metrics)
  - `redis_commands_*` (command statistics)
  - `redis_connected_clients`
  - `redis_blocked_clients`
  - `redis_keyspace_*` (keyspace statistics)
  - `up`
- Metrics NOT matching the filter should be absent

### Step 7: Check for Scrape Errors

```bash
# Check Alloy logs for any scrape errors
docker logs gamebot-grafana-alloy --since 5m | grep -i "error.*redis"

# Expected: No error messages
# If errors appear, check Redis connectivity and Alloy configuration
```

## Success Criteria Verification

- [x] **Alloy Logs**: Redis exporter initialized, no connection errors
- [x] **Scrape Target**: Redis scrape target active in Alloy logs
- [x] **Metrics Visible**: All expected metrics queryable in Grafana Cloud Mimir
- [x] **Correct Labels**: Metrics have `job="integrations/redis_exporter"` and
      `instance="redis"`
- [x] **Filtering Active**: Only configured metrics appear (cost optimization)
- [x] **No Errors**: No scrape errors in Alloy logs

## Troubleshooting

### Problem: Redis Exporter Not Starting

**Symptoms**: No Redis logs in Alloy output

**Solutions**:

1. Check Alloy configuration syntax:
   ```bash
   docker exec gamebot-grafana-alloy alloy fmt --write /etc/alloy/config.alloy
   ```
2. Verify Redis service is running:
   ```bash
   docker ps | grep redis
   ```

### Problem: Connection Refused to Redis

**Symptoms**: "connection refused" errors in Alloy logs

**Solutions**:

1. Verify Redis hostname resolution:
   ```bash
   docker exec gamebot-grafana-alloy ping -c 1 redis
   ```
2. Check Redis port is accessible:
   ```bash
   docker exec gamebot-grafana-alloy nc -zv redis 6379
   ```
3. Ensure both containers are on same network (`app-network`)

### Problem: Metrics Not Appearing in Grafana Cloud

**Symptoms**: Queries return "No data"

**Solutions**:

1. Wait at least 60 seconds after restart (scrape interval)
2. Check Alloy logs for remote_write errors:
   ```bash
   docker logs gamebot-grafana-alloy | grep -i "remote_write\|401\|unauthorized"
   ```
3. Verify `GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID` matches Prometheus instance
   (NOT OTLP instance)
4. Test Prometheus endpoint authentication manually

### Problem: Too Many Metrics (Cost Concern)

**Symptoms**: High metric cardinality in Grafana Cloud

**Solutions**:

1. Review `prometheus.relabel` regex filter in `config.alloy`
2. Add more restrictive metric filtering
3. Increase scrape interval to reduce data points

## Next Steps

After Phase 3 completion:

- **Phase 4**: Python service instrumentation (API, bot, daemons)
- **Dashboard Creation**: Import Redis dashboard from Grafana Labs
- **Alerting**: Configure alerts for Redis memory usage, connection failures

## Verification Command Summary

```bash
# Quick verification script
echo "=== Checking Redis Exporter Status ==="
docker logs gamebot-grafana-alloy --since 2m | grep -i redis | tail -20

echo ""
echo "=== Checking Scrape Success ==="
docker logs gamebot-grafana-alloy --since 2m | grep "integrations/redis_exporter" | tail -10

echo ""
echo "=== Next Step: Query Grafana Cloud Mimir ==="
echo "Query: redis_up"
echo "Expected: Value 1 with job=integrations/redis_exporter"
```
