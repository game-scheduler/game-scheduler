# Retry Daemon Grafana Dashboard

This dashboard provides comprehensive monitoring for the retry daemon service that processes dead letter queues (DLQs).

## Metrics Overview

### DLQ Depth Over Time
- **Metric**: `retry_dlq_depth`
- **Description**: Current number of messages in each DLQ
- **Alert**: Triggers when depth exceeds 10 messages
- **Use**: Identify accumulating failures or system issues

### Message Processing Rate
- **Metrics**:
  - `retry_messages_processed_total` (rate)
  - `retry_messages_failed_total` (rate)
- **Description**: Messages processed and failed per second
- **Use**: Monitor throughput and failure rates

### Processing Duration
- **Metric**: `retry_processing_duration_bucket`
- **Description**: Time taken to process DLQ (p50, p95, p99)
- **Use**: Identify performance degradation

### Messages by Event Type
- **Metric**: `retry_messages_processed_total` (sum by event_type)
- **Description**: Breakdown of processed messages by event type
- **Use**: Understand which event types are failing most

### Failure Rate by Error Type
- **Metric**: `retry_messages_failed_total` (sum by error_type)
- **Description**: Failures grouped by exception type
- **Alert**: Triggers when failure rate exceeds 0.1/sec
- **Use**: Diagnose root causes of failures

### Service Health Status
- **Metric**: `up{job="retry-daemon"}`
- **Description**: Service up/down status
- **Use**: Quick health check

### Total Messages Processed
- **Metric**: `retry_messages_processed_total` (sum)
- **Description**: Cumulative count of all processed messages
- **Use**: Track overall volume

### Consecutive Failures Alert
- **Metric**: `retry_consecutive_failures`
- **Description**: Number of consecutive processing failures per DLQ
- **Alert**: Triggers when count exceeds 3
- **Use**: Detect persistent issues requiring intervention

## Alert Configuration

### High DLQ Depth
- **Condition**: DLQ depth > 10 messages for 5 minutes
- **Action**: Investigate why messages are accumulating
- **Possible causes**: Bot down, database issues, message format errors

### High Failure Rate
- **Condition**: Failure rate > 0.1 messages/sec for 5 minutes
- **Action**: Check error logs for specific failures
- **Possible causes**: Publisher issues, RabbitMQ connectivity, malformed messages

### Consecutive Processing Failures
- **Condition**: 3+ consecutive failures for any DLQ
- **Action**: Immediate investigation required
- **Possible causes**: RabbitMQ down, authentication failure, network issues

## Dashboard Import

### Option 1: Manual Import
1. Navigate to Grafana UI
2. Click "+" → "Import"
3. Upload `retry-daemon-dashboard.json`
4. Select Prometheus data source
5. Click "Import"

### Option 2: Provisioning
1. Copy `retry-daemon-dashboard.json` to Grafana provisioning directory
2. Add to `dashboards.yml`:
   ```yaml
   - name: 'retry-daemon'
     folder: 'Game Scheduler'
     type: file
     options:
       path: /etc/grafana/provisioning/dashboards/retry-daemon-dashboard.json
   ```

## Metric Labels

All metrics include the following labels where applicable:

- `dlq_name`: Name of the DLQ being processed (`bot_events.dlq`, `notification_queue.dlq`)
- `event_type`: Type of event being processed (`game.created`, `notification.send_dm`, etc.)
- `routing_key`: RabbitMQ routing key used for republishing
- `error_type`: Exception class name for failures

## Troubleshooting

### Dashboard shows no data
- Verify retry-daemon service is running
- Check Prometheus is scraping retry-daemon metrics endpoint
- Verify metric names match (OpenTelemetry exports with underscores, not dots)

### Alerts not firing
- Verify alert rules are saved with dashboard
- Check notification channel configuration
- Verify alert evaluation interval matches dashboard refresh

### High DLQ depth not clearing
- Check retry-daemon logs for errors
- Verify bot service is running and consuming messages
- Inspect DLQ messages for format issues: `rabbitmqadmin get queue=bot_events.dlq count=1`

## Related Documentation

- [Retry Daemon Implementation](../../services/retry/retry_daemon.py)
- [OpenTelemetry Configuration](../config.alloy)
- [RabbitMQ Infrastructure](../../shared/messaging/infrastructure.py)
