<!-- markdownlint-disable-file -->

# Phase 7 Testing Guide: RabbitMQ Metrics Collection

## Overview

Verify that RabbitMQ metrics are being collected by Grafana Alloy and successfully exported to Grafana Cloud Mimir.

## Prerequisites

- Phase 1-6 completed successfully
- RabbitMQ service running with Prometheus plugin enabled
- Grafana Alloy service running and connected to Grafana Cloud
- Access to Grafana Cloud account

## Step 1: Restart RabbitMQ and Alloy Services

Restart services to apply the new configuration:

```bash
# Restart RabbitMQ to enable Prometheus plugin with new config
docker compose restart rabbitmq

# Restart Alloy to apply RabbitMQ scraping configuration
docker compose restart grafana-alloy

# Wait for services to be healthy
sleep 30
docker compose ps
```

**Expected Output:**
- Both rabbitmq and grafana-alloy should show status "healthy" or "Up"

## Step 2: Verify RabbitMQ Prometheus Endpoint

Check that RabbitMQ is exposing Prometheus metrics:

```bash
# Test RabbitMQ Prometheus endpoint from host
curl -s http://localhost:15692/metrics | head -20

# Verify the plugin is enabled
docker exec gamebot-rabbitmq rabbitmq-plugins list | grep prometheus
```

**Expected Output:**
```
# TYPE rabbitmq_build_info gauge
# HELP rabbitmq_build_info RabbitMQ & Erlang/OTP version info
rabbitmq_build_info{rabbitmq_version="4.2.0",erlang_version="26.2.5.5"} 1
# TYPE rabbitmq_identity_info gauge
# HELP rabbitmq_identity_info RabbitMQ node & cluster identity info
rabbitmq_identity_info{rabbitmq_node="rabbit@hostname",rabbitmq_cluster_name="rabbit@hostname"} 1
...
rabbitmq_queue_messages{queue="notifications",...} 0
rabbitmq_connections 1
rabbitmq_consumers 2
```

**Success Criteria:**
- Metrics endpoint returns HTTP 200
- Output contains Prometheus-formatted metrics
- Includes rabbitmq_queue_messages, rabbitmq_connections, rabbitmq_consumers

## Step 3: Check Alloy Configuration and Scraping

Verify Alloy has loaded the RabbitMQ scraping configuration:

```bash
# Check Alloy logs for RabbitMQ configuration
docker logs gamebot-grafana-alloy |& grep -i rabbitmq

# Look for scrape target registration
docker logs gamebot-grafana-alloy --since 2m |& grep "integrations/rabbitmq"
```

**Expected Output:**
```
level=info msg="component started" component=discovery.static.integrations_rabbitmq
level=info msg="component started" component=prometheus.scrape.integrations_rabbitmq
level=info msg="Scrape target added" job=integrations/rabbitmq target=rabbitmq:15692
```

**Success Criteria:**
- No errors related to RabbitMQ scraping
- Scrape target shows as active
- No "connection refused" or authentication errors

## Step 4: Verify Alloy is Scraping RabbitMQ

Check that Alloy is successfully scraping metrics from RabbitMQ:

```bash
# Check for successful scrapes in last 5 minutes
docker logs gamebot-grafana-alloy --since 5m |& grep -E "integrations/rabbitmq.*scrape"

# Check Alloy HTTP API for targets (if exposed)
curl http://localhost:12345/targets 2>/dev/null | jq '.data[] | select(.job_name=="integrations/rabbitmq")'
```

**Expected Output:**
- Log entries showing successful scrapes
- No HTTP errors (401, 403, 404, 500)
- Scrape duration metrics showing sub-second times

## Step 5: Wait for Metric Propagation

Allow time for metrics to reach Grafana Cloud:

```bash
# Wait 60 seconds for scrape interval
echo "Waiting 60 seconds for RabbitMQ metrics scrape..."
sleep 60
```

## Step 6: Query RabbitMQ Metrics in Grafana Cloud

Log into Grafana Cloud and verify RabbitMQ metrics:

1. Navigate to Grafana Cloud → Explore → Prometheus
2. Query for basic RabbitMQ metrics:

### Query 1: RabbitMQ Up Status
```promql
rabbitmq_up
```

**Expected:** Value of 1 (RabbitMQ is up)

### Query 2: Queue Messages
```promql
rabbitmq_queue_messages
```

**Expected:** One or more time series showing queue message counts

### Query 3: Connection Count
```promql
rabbitmq_connections
```

**Expected:** Time series showing current connection count

### Query 4: Consumer Count
```promql
rabbitmq_consumers
```

**Expected:** Time series showing current consumer count

### Query 5: Message Rates
```promql
rate(rabbitmq_queue_messages_published_total[5m])
```

**Expected:** Message publish rate per queue

### Query 6: Node Memory Usage
```promql
rabbitmq_node_mem_used
```

**Expected:** RabbitMQ node memory usage in bytes

## Step 7: Verify Metric Labels

Check that metrics have correct job and instance labels:

```promql
rabbitmq_up{job="integrations/rabbitmq", instance="rabbitmq"}
```

**Expected:**
- job label: `integrations/rabbitmq`
- instance label: `rabbitmq`
- Additional labels for queue names, vhosts, etc.

## Step 8: Generate RabbitMQ Activity

Create some RabbitMQ activity to verify dynamic metrics:

```bash
# Publish messages via API (creates RabbitMQ activity)
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Game","scheduled_time":"2025-12-10T20:00:00Z",...}'

# Wait 60 seconds for next scrape
sleep 60
```

Then query message rates in Grafana Cloud:

```promql
rate(rabbitmq_queue_messages_published_total{queue="notifications"}[5m])
```

**Expected:** Non-zero rate showing messages being published

## Troubleshooting

### Issue: rabbitmq_up not found in Grafana Cloud

**Possible Causes:**
1. RabbitMQ Prometheus endpoint not accessible
2. Alloy not scraping RabbitMQ
3. Metrics filtered out by prometheus.relabel

**Solutions:**
```bash
# Check RabbitMQ Prometheus plugin status
docker exec gamebot-rabbitmq rabbitmq-plugins list | grep prometheus

# Check Alloy can reach RabbitMQ
docker exec gamebot-grafana-alloy wget -qO- http://rabbitmq:15692/metrics | head -10

# Check Alloy configuration syntax
docker logs gamebot-grafana-alloy |& grep -i "error\|failed"
```

### Issue: Metrics present but no per-queue details

**Cause:** Per-object metrics disabled by default (for performance)

**Solution:** Already enabled in rabbitmq.conf with:
```
prometheus.return_per_object_metrics = true
```

If still not working, check RabbitMQ config is mounted:
```bash
docker exec gamebot-rabbitmq cat /etc/rabbitmq/rabbitmq.conf
```

### Issue: High metric cardinality warning

**Cause:** Too many per-object metrics with many queues

**Solution:** Adjust prometheus.relabel rules in config.alloy to be more selective:
```hcl
rule {
  source_labels = ["__name__"]
  regex = "rabbitmq_queue_messages_ready|rabbitmq_queue_messages_unacked|rabbitmq_connections|rabbitmq_consumers"
  action = "keep"
}
```

### Issue: Authentication errors in Alloy logs

**Cause:** Wrong Prometheus instance ID

**Verification:** Same remote_write configuration works for PostgreSQL and Redis, so authentication should be correct.

## Success Criteria Checklist

- [ ] RabbitMQ Prometheus endpoint returns metrics at http://rabbitmq:15692/metrics
- [ ] Alloy logs show successful RabbitMQ scrape target registration
- [ ] No scrape errors in Alloy logs
- [ ] `rabbitmq_up{job="integrations/rabbitmq"}` returns 1 in Grafana Cloud
- [ ] `rabbitmq_queue_messages` shows queue depths
- [ ] `rabbitmq_connections` shows connection count
- [ ] `rabbitmq_consumers` shows consumer count
- [ ] Metrics have correct labels (job, instance)
- [ ] Message rate metrics update after generating RabbitMQ activity

## Next Steps

After Phase 7 verification:
1. Proceed to Phase 8: Grafana Cloud Dashboards
2. Import pre-built RabbitMQ dashboard from grafana.com/orgs/rabbitmq
3. Create custom alerts for queue depth thresholds
4. Configure alert notifications

## Verification Results

*(Document test results here after execution)*
