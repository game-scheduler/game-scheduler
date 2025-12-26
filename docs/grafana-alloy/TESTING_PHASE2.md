# Phase 2 Testing: PostgreSQL Metrics Verification

This guide walks through verifying PostgreSQL metrics are successfully flowing
from Alloy to Grafana Cloud Mimir.

## Prerequisites

- Phase 1 completed (Alloy connected to Grafana Cloud)
- PostgreSQL database running and accessible
- Environment variables configured in `.env`:
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
  - `POSTGRES_DB`
  - `GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID`
  - `GRAFANA_CLOUD_PROMETHEUS_ENDPOINT`
  - `GRAFANA_CLOUD_API_KEY`

## Step 1: Restart Alloy with New Configuration

Restart the Alloy service to pick up the PostgreSQL exporter configuration:

```bash
docker compose restart grafana-alloy
```

## Step 2: Check Alloy Logs for PostgreSQL Connection

Verify that Alloy successfully connected to PostgreSQL:

```bash
docker logs gamebot-grafana-alloy --tail 50
```

**Expected output:**

- No authentication errors
- No connection errors to PostgreSQL
- Log entries showing prometheus.exporter.postgres started
- Log entries showing prometheus.scrape started for
  integrations/postgres_exporter

**If you see errors:**

- Verify database credentials in `.env` match PostgreSQL service
- Verify database name is correct (should be `game_scheduler` based on
  compose.yaml)
- Check PostgreSQL container is running: `docker ps | grep postgres`

## Step 3: Wait for Initial Scrape

The PostgreSQL exporter is configured to scrape every 60 seconds. Wait at least
60 seconds after Alloy restart before proceeding.

```bash
sleep 60
```

## Step 4: Verify Metrics in Grafana Cloud

### 4.1 Navigate to Grafana Cloud

1. Go to your Grafana Cloud instance
2. Navigate to **Explore** (compass icon in left sidebar)
3. Select **Mimir** (or **Prometheus**) as the data source

### 4.2 Query Basic PostgreSQL Metrics

Run these queries to verify metrics are arriving:

**Query 1: PostgreSQL Exporter Health**

```promql
pg_up
```

**Expected:** Should return `1` (PostgreSQL exporter is running)

**Query 2: Database Connection Count**

```promql
pg_stat_database_numbackends
```

**Expected:** Should return connection counts for each database (including
`game_scheduler`)

**Query 3: Database Statistics**

```promql
pg_stat_database_xact_commit
```

**Expected:** Should return transaction commit counts

**Query 4: Check Labels**

```promql
pg_up{job="integrations/postgres_exporter", instance="postgres"}
```

**Expected:** Should return `1` with correct labels

### 4.3 Verify Metric Filtering

Attempt to query a metric that should be filtered out:

```promql
pg_stat_ssl_compression
```

**Expected:** Should return no data (metric filtered by prometheus.relabel)

Verify a metric that should be kept:

```promql
pg_stat_activity_count
```

**Expected:** Should return data (metric matches filter regex)

## Step 5: Check Alloy Prometheus Remote Write

Verify Alloy is successfully sending metrics to Mimir:

```bash
docker logs gamebot-grafana-alloy --tail 100 | grep -i "prometheus\|remote_write\|mimir"
```

**Expected:**

- No "401 Unauthorized" errors
- No "connection refused" errors
- Log entries showing successful metric export

**If you see "401 Unauthorized":**

- Verify `GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID` is correct (should be 7-digit
  number)
- Verify it's the **Prometheus instance ID**, NOT the OTLP/Tempo instance ID
- Check `GRAFANA_CLOUD_API_KEY` is correct (format: `glc_xxxxx...`)

## Step 6: Verify in Docker Logs (Optional)

Check that the PostgreSQL exporter component is working:

```bash
docker exec gamebot-grafana-alloy alloy-cli components list 2>/dev/null || echo "Alloy CLI not available"
```

## Step 7: Create a Test Dashboard (Optional)

Create a simple dashboard in Grafana Cloud to visualize metrics:

1. Go to **Dashboards** → **New** → **New Dashboard**
2. Add a panel with this query:
   ```promql
   rate(pg_stat_database_xact_commit{datname="game_scheduler"}[5m])
   ```
3. Set panel title to "Game Scheduler Transaction Rate"
4. Save the dashboard

## Success Criteria

- ✅ Alloy logs show no PostgreSQL connection errors
- ✅ Alloy logs show no authentication errors to Grafana Cloud Prometheus
  endpoint
- ✅ Query `pg_up` returns `1`
- ✅ Query `pg_stat_database_numbackends` returns connection counts
- ✅ Metrics have correct labels: `job="integrations/postgres_exporter"`,
  `instance="postgres"`
- ✅ Filtered metrics (not matching regex) return no data
- ✅ Metrics appear in Grafana Cloud within ~60 seconds of Alloy restart

## Troubleshooting

### Problem: No metrics appearing in Grafana Cloud

**Solution 1:** Check Alloy is scraping PostgreSQL

```bash
docker logs gamebot-grafana-alloy | grep "postgres_exporter"
```

**Solution 2:** Verify PostgreSQL connection string

```bash
docker exec gamebot-grafana-alloy env | grep POSTGRES
```

**Solution 3:** Manually test PostgreSQL connection

```bash
docker exec gamebot-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"
```

### Problem: 401 Unauthorized to Prometheus endpoint

**Solution:** Verify you're using the correct Prometheus instance ID:

1. Go to Grafana Cloud Portal
2. Navigate to **Connections** → **Prometheus**
3. Copy the **Instance ID** (7-digit number)
4. Update `GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID` in `.env`
5. Restart Alloy: `docker compose restart grafana-alloy`

### Problem: Metrics appearing but missing expected labels

**Solution:** Check discovery.relabel configuration in
`grafana-alloy/config.alloy`:

- Verify `target_label = "job"` is set to `"integrations/postgres_exporter"`
- Verify `target_label = "instance"` is set to `"postgres"`

## Next Steps

After successful verification:

- Proceed to **Phase 3: Redis Metrics Collection**
- Import pre-built PostgreSQL dashboard from Grafana dashboard library
- Configure alerting rules for PostgreSQL metrics (e.g., connection count,
  deadlocks)
