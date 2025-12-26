# Phase 6 Testing: Daemon Services Instrumentation Verification

## Overview

Verify that notification-daemon and status-transition-daemon generate traces with proper span attributes and inherit context from RabbitMQ messages.

## Prerequisites

- Phase 5 completed (bot service instrumented)
- Notification-daemon and status-transition-daemon rebuilt and restarted
- Docker containers running
- Grafana Cloud access

## Test Procedure

### Step 1: Rebuild and Restart Daemons

```bash
# Rebuild daemon containers
docker compose build notification-daemon status-transition-daemon

# Restart daemons
docker compose up -d notification-daemon status-transition-daemon
```

### Step 2: Verify OpenTelemetry Initialization

Check daemon logs for initialization messages:

```bash
# Notification daemon logs
docker logs gamebot-notification-daemon 2>&1 | grep "OpenTelemetry"

# Expected output:
# OpenTelemetry tracing initialized: service.name=notification-daemon
# OpenTelemetry metrics initialized: service.name=notification-daemon
# OpenTelemetry logging initialized: service.name=notification-daemon

# Status transition daemon logs
docker logs gamebot-status-transition-daemon 2>&1 | grep "OpenTelemetry"

# Expected output:
# OpenTelemetry tracing initialized: service.name=status-transition-daemon
# OpenTelemetry metrics initialized: service.name=status-transition-daemon
# OpenTelemetry logging initialized: service.name=status-transition-daemon
```

### Step 3: Test Notification Daemon Scheduled Task

Trigger a game reminder notification:

1. Create a game via bot with a reminder scheduled (or use existing game with upcoming notification)
2. Wait for notification time to arrive (or update database to make notification due now)
3. Check notification daemon logs for processing:

```bash
docker logs gamebot-notification-daemon --tail 20
# Look for: "Processed scheduled item <uuid> for NotificationSchedule"
```

### Step 4: Verify Notification Daemon Traces in Grafana Cloud

1. Navigate to Grafana Cloud → Explore → Tempo
2. Query for notification-daemon traces:
   ```
   {service.name="notification-daemon"}
   ```
3. Find trace for scheduled notification processing
4. Verify span structure:
   - Root span: `scheduled.NotificationSchedule`
   - Span attributes should include:
     - `scheduler.job_id` (notification schedule UUID)
     - `scheduler.model` = "NotificationSchedule"
     - `scheduler.time_field` = "notification_time"
5. Check for child spans:
   - RabbitMQ publish span (from aio-pika instrumentation)
   - Database query spans (from asyncpg/SQLAlchemy instrumentation)

### Step 5: Test Status Transition Daemon Scheduled Task

Trigger a status transition:

1. Create a game with automatic status transition scheduled (e.g., SCHEDULED → ACTIVE at start time)
2. Wait for transition time (or update database to make it due now)
3. Check status transition daemon logs:

```bash
docker logs gamebot-status-transition-daemon --tail 20
# Look for: "Processed scheduled item <uuid> for GameStatusSchedule"
```

### Step 6: Verify Status Transition Daemon Traces

1. In Grafana Cloud → Explore → Tempo
2. Query for status-transition-daemon traces:
   ```
   {service.name="status-transition-daemon"}
   ```
3. Find trace for status transition processing
4. Verify span structure:
   - Root span: `scheduled.GameStatusSchedule`
   - Span attributes should include:
     - `scheduler.job_id` (status schedule UUID)
     - `scheduler.model` = "GameStatusSchedule"
     - `scheduler.time_field` = "transition_time"
5. Check for child spans:
   - RabbitMQ publish span
   - Database query spans

### Step 7: Test RabbitMQ Context Propagation (End-to-End Trace)

Test complete trace from bot → daemon → bot:

1. Use bot command to create game with notification
2. Wait for notification daemon to process scheduled notification
3. Verify bot receives and handles the notification event
4. In Grafana Cloud → Explore → Tempo, search for the originating trace ID
5. Verify trace continuity:
   ```
   bot-service: discord.on_interaction (game creation)
     └─ api-service: POST /api/games
       └─ postgres: INSERT game
       └─ postgres: INSERT notification_schedule
     └─ notification-daemon: scheduled.NotificationSchedule (when time arrives)
       └─ rabbitmq: publish notification event
         └─ bot-service: process notification event
           └─ discord: send reminder message
   ```

**Note**: The scheduled task creates a NEW root span (no upstream context), but the RabbitMQ message publish/consume should maintain trace context through message properties.

### Step 8: Test DLQ Processing Traces (Optional)

If DLQ processing is enabled and there are messages in DLQ:

1. Add messages to DLQ (or wait for 15 minutes for automatic DLQ check)
2. Check daemon logs for DLQ processing:
   ```bash
   docker logs gamebot-notification-daemon 2>&1 | grep "DLQ"
   # Look for: "Processing N messages from DLQ"
   ```
3. In Grafana Cloud → Tempo, find DLQ processing span:
   ```
   {service.name="notification-daemon" span.name="scheduled.process_dlq"}
   ```
4. Verify span attributes:
   - `scheduler.model` = "NotificationSchedule"
   - `scheduler.dlq_check_interval` = 900

### Step 9: Verify Logs with Trace Correlation

Check that daemon logs include trace IDs:

1. In Grafana Cloud → Explore → Loki
2. Query daemon logs:
   ```
   {service_name="notification-daemon"} | json
   ```
3. Verify log entries include `trace_id` and `span_id` fields
4. Click on a log entry and "Show in Tempo" to jump to the trace

## Success Criteria

- ✅ Both daemons log OpenTelemetry initialization (traces, metrics, logs)
- ✅ Scheduled tasks create root spans with correct name pattern (`scheduled.<ModelName>`)
- ✅ Span attributes include `scheduler.job_id`, `scheduler.model`, `scheduler.time_field`
- ✅ Child spans visible for database queries and RabbitMQ publish
- ✅ DLQ processing creates span with correct attributes (if applicable)
- ✅ Logs include trace context (trace_id, span_id)
- ✅ RabbitMQ message context propagates from publisher to consumer (aio-pika instrumentation handles this)

## Troubleshooting

### Daemon Not Starting

**Symptom**: Container exits immediately after start

**Check**:
```bash
docker logs gamebot-notification-daemon
```

**Common causes**:
- Import error (missing telemetry module)
- Environment variables not set
- Database connection failure

**Solution**: Review logs for specific error, ensure all dependencies installed

### No Traces Appearing

**Symptom**: Daemons run but no traces in Grafana Cloud

**Check**:
1. Verify OTEL environment variables are set:
   ```bash
   docker exec gamebot-notification-daemon env | grep OTEL
   ```
2. Check Alloy is receiving data:
   ```bash
   docker logs gamebot-grafana-alloy --tail 50 | grep -i "notification-daemon\|status-transition"
   ```
3. Test OTLP endpoint manually

**Solution**: Ensure containers can reach `grafana-alloy:4318`

### Traces Not Linking Through RabbitMQ

**Symptom**: Daemon and bot traces exist but are disconnected

**Cause**: aio-pika instrumentation may not be propagating context correctly

**Check**: Verify `opentelemetry-instrumentation-aio-pika` is installed:
```bash
docker exec gamebot-notification-daemon pip list | grep aio-pika
```

**Solution**: Ensure instrumentation is installed and imported by telemetry initialization

### Container Rebuild Required

**Symptom**: Code changes not reflected

**Reminder**: Docker images copy code during build, not at runtime

**Solution**:
```bash
docker compose build notification-daemon
docker compose up -d notification-daemon
```

## Expected Trace Examples

### Notification Daemon Scheduled Task

```
Trace ID: 1a2b3c4d5e6f7g8h9i0j
Service: notification-daemon
Root Span: scheduled.NotificationSchedule
  Attributes:
    - scheduler.job_id: "550e8400-e29b-41d4-a716-446655440000"
    - scheduler.model: "NotificationSchedule"
    - scheduler.time_field: "notification_time"
  Child Spans:
    - pg.query: SELECT * FROM notification_schedule...
    - rabbitmq.publish: notification_event
```

### Status Transition Daemon Scheduled Task

```
Trace ID: 9i8h7g6f5e4d3c2b1a0j
Service: status-transition-daemon
Root Span: scheduled.GameStatusSchedule
  Attributes:
    - scheduler.job_id: "660e9500-f39c-52e5-b827-557766551111"
    - scheduler.model: "GameStatusSchedule"
    - scheduler.time_field: "transition_time"
  Child Spans:
    - pg.query: SELECT * FROM game_status_schedule...
    - rabbitmq.publish: status_transition_event
```

## Verification Results

**Date**: ___________
**Tester**: ___________

- [ ] Notification daemon initialization logged
- [ ] Status transition daemon initialization logged
- [ ] Scheduled task traces visible in Tempo
- [ ] Span attributes correct
- [ ] Child spans present (database, RabbitMQ)
- [ ] DLQ processing traces visible (if applicable)
- [ ] Logs include trace context
- [ ] RabbitMQ context propagation working

**Notes**:

---

## Next Steps

After Phase 6 verification:
- Phase 7: Create Grafana Cloud dashboards
- Set up alerting rules
- Document operational procedures
