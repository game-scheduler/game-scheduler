<!-- markdownlint-disable-file -->

# Release Changes: OpenTelemetry Observability Implementation

**Related Plan**: 20251206-opentelemetry-observability-plan.instructions.md
**Implementation Date**: 2025-12-07

## Summary

Implementation of comprehensive distributed tracing, metrics collection, and log
aggregation using OpenTelemetry with Grafana Cloud as the observability backend.

## Changes

### Added

- grafana-alloy/SETUP_GRAFANA_CLOUD.md - Comprehensive instructions for Grafana
  Cloud account setup and credential collection
- grafana-alloy/config.alloy - OpenTelemetry Collector configuration with OTLP
  receiver and HTTP exporter to Grafana Cloud
- grafana-alloy/TESTING_PHASE1.md - Step-by-step testing guide for Phase 1 Alloy
  connection verification
- grafana-alloy/TESTING_PHASE2.md - Step-by-step testing guide for Phase 2
  PostgreSQL metrics verification

### Modified

- docker-compose.base.yml - Added grafana-alloy service for OpenTelemetry
  collection; updated environment variables to pass all three instance IDs;
  Added PostgreSQL environment variables (POSTGRES_USER, POSTGRES_PASSWORD,
  POSTGRES_DB) to Alloy service for PostgreSQL exporter connection
- .env.example - Added Grafana Cloud configuration variables with all three
  instance IDs (OTLP, Prometheus, Loki) and comprehensive documentation
- RUNTIME_CONFIG.md - Added comprehensive OpenTelemetry configuration
  documentation with all three instance IDs
- grafana-alloy/config.alloy - Fixed Alloy configuration syntax: unquoted header
  keys with trailing comma, removed send_batch_size to use defaults; Updated to
  use otelcol.exporter.otlp (gRPC) with otelcol.auth.basic per Grafana Cloud
  documentation, targeting Tempo endpoint directly; Added PostgreSQL metrics
  collection with prometheus.exporter.postgres using format() function for DSN
  construction, discovery.relabel, prometheus.relabel for metric filtering, and
  prometheus.scrape with 60s interval; Added prometheus.remote_write to send
  infrastructure metrics to Grafana Cloud Mimir with Prometheus-specific
  instance ID
- grafana-alloy/SETUP_GRAFANA_CLOUD.md - Added Step 3.5 for Loki instance ID
  collection
- .copilot-tracking/plans/20251206-opentelemetry-observability-plan.instructions.md -
  Marked Phase 1 tasks as complete; Marked Phase 2 tasks as complete

### Removed

- N/A - No postgres-exporter service found to remove (Task 2.4 verification
  confirmed no redundant service exists)
