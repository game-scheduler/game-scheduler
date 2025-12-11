<!-- markdownlint-disable-file -->

# Release Changes: Grafana Alloy Self-Monitoring

**Related Plan**: 20251210-alloy-self-monitoring-plan.instructions.md
**Implementation Date**: 2025-12-10

## Summary

Enable comprehensive self-monitoring for Grafana Alloy collector to export its own metrics, logs, and traces to Grafana Cloud for operational visibility.

## Changes

### Added

### Modified

- grafana-alloy/config.alloy - Added prometheus.exporter.self component for Alloy internal metrics
- grafana-alloy/config.alloy - Added prometheus.scrape job to collect Alloy metrics at 60s intervals
- grafana-alloy/config.alloy - Added otelcol.receiver.prometheus to convert Alloy metrics to OTLP format
- grafana-alloy/config.alloy - Updated logging block to use JSON format and forward to Loki
- grafana-alloy/config.alloy - Added loki.write component with Grafana Cloud Loki authentication
- docker-compose.base.yml - Added GRAFANA_CLOUD_LOKI_ENDPOINT environment variable for Alloy service
- docker-compose.base.yml - Added GRAFANA_CLOUD_LOKI_INSTANCE_ID environment variable for Alloy service

### Removed

