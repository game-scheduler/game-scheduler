---
applyTo: ".copilot-tracking/changes/20251210-alloy-self-monitoring-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Grafana Alloy Self-Monitoring

## Overview

Enable comprehensive self-monitoring for Grafana Alloy collector to export its own metrics, logs, and traces to Grafana Cloud for operational visibility.

## Objectives

- Export Alloy internal metrics to Grafana Cloud Mimir
- Forward Alloy logs to Grafana Cloud Loki
- Enable Alloy trace sampling to Grafana Cloud Tempo
- Maintain minimal resource overhead (<5% CPU, <20MB memory)
- Provide operational visibility for collector health monitoring

## Research Summary

### Project Files

- `grafana-alloy/config.alloy` - Current Alloy configuration with application and infrastructure monitoring
- `docker-compose.base.yml` - Alloy service configuration with environment variables

### External References

- #file:../research/20251210-alloy-self-monitoring-research.md - Comprehensive self-monitoring implementation research
- #fetch:https://grafana.com/docs/alloy/latest/collect/metamonitoring/ - Official Alloy self-monitoring documentation
- #githubRepo:"grafana/alloy self monitoring internal metrics" - Self-monitoring component implementation patterns

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker configuration best practices

## Implementation Checklist

### [x] Phase 1: Add Alloy Metrics Self-Monitoring

- [x] Task 1.1: Add prometheus.exporter.self component
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 18-29)

- [x] Task 1.2: Configure prometheus.scrape for Alloy metrics
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 31-43)

- [x] Task 1.3: Add otelcol.receiver.prometheus for metrics conversion
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 45-57)

### [x] Phase 2: Enable Alloy Logs Export

- [x] Task 2.1: Configure logging block for Loki export
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 61-74)

- [x] Task 2.2: Add loki.write component for Grafana Cloud
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 76-91)

- [x] Task 2.3: Add Loki environment variables to docker-compose
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 93-105)

### [ ] Phase 3: Enable Alloy Trace Sampling

- [ ] Task 3.1: Add tracing block with sampling configuration
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 109-121)

### [ ] Phase 4: Documentation and Validation

- [ ] Task 4.1: Update Alloy configuration comments
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 125-135)

- [ ] Task 4.2: Document required environment variables
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 137-150)

- [ ] Task 4.3: Verify Alloy self-monitoring in Grafana Cloud
  - Details: .copilot-tracking/details/20251210-alloy-self-monitoring-details.md (Lines 152-165)

## Dependencies

- Grafana Cloud account with OTLP Gateway and Loki endpoints configured
- Existing Grafana Alloy deployment (already present in docker-compose.base.yml)
- Environment variables for OTLP and Loki authentication (partially present)

## Success Criteria

- Alloy metrics visible in Grafana Cloud Mimir with service.name="alloy"
- Alloy logs flowing to Grafana Cloud Loki with structured JSON format
- Alloy traces appearing in Grafana Cloud Tempo at 10% sampling rate
- No performance degradation to existing monitoring pipelines
- Resource overhead remains below 5% CPU and 20MB memory
- Configuration changes documented with clear architecture comments
