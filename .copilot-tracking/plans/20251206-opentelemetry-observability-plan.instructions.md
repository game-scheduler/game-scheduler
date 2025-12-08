---
applyTo: ".copilot-tracking/changes/20251206-opentelemetry-observability-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: OpenTelemetry Observability Implementation

## Overview

Implement comprehensive distributed tracing, metrics collection, and log
aggregation using OpenTelemetry with Grafana Cloud as the observability backend.

## Objectives

- Enable distributed tracing across all Python microservices
- Collect infrastructure metrics from PostgreSQL and Redis
- Aggregate structured logs with trace correlation
- Deploy Grafana Alloy as OpenTelemetry collector
- Configure Grafana Cloud free tier for observability data

## Research Summary

### Project Files

- `docker-compose.base.yml` - Service inventory and configuration
- `pyproject.toml` - Python dependencies for instrumentation
- `services/api/app.py` - FastAPI service startup
- `services/bot/main.py` - Discord bot startup
- `services/scheduler/notification_daemon.py` - Notification daemon startup
- `services/scheduler/status_transition_daemon.py` - Status daemon startup

### External References

- #file:../research/20251206-opentelemetry-compatibility-research.md -
  Comprehensive OpenTelemetry implementation research
- #githubRepo:"open-telemetry/opentelemetry-python tracing fastapi" - Python
  instrumentation patterns
- #fetch:https://opentelemetry.io/docs/languages/python/libraries/ - Official
  Python instrumentation libraries

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding
  conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md -
  Docker configuration best practices

## Implementation Checklist

### [x] Phase 1: Grafana Alloy Deployment

- [x] Task 1.1: Create Grafana Cloud account and obtain credentials

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 15-35)

- [x] Task 1.2: Create Alloy configuration file

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 37-75)

- [x] Task 1.3: Add Grafana Alloy service to docker-compose

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 77-100)

- [x] Task 1.4: Configure environment variables

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 102-125)

- [x] Task 1.5: Test Alloy connection to Grafana Cloud
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 127-145)

### [x] Phase 2: PostgreSQL Metrics Collection

- [x] Task 2.1: Configure PostgreSQL exporter in Alloy

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 147-180)

- [x] Task 2.2: Configure Prometheus remote write

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 182-205)

- [x] Task 2.3: Verify PostgreSQL metrics in Grafana Cloud

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 207-225)

- [x] Task 2.4: Remove redundant postgres-exporter service
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 227-240)

### [ ] Phase 3: Redis Metrics Collection

- [ ] Task 3.1: Configure Redis exporter scraping in Alloy

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 242-270)

- [ ] Task 3.2: Verify Redis metrics in Grafana Cloud
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 272-285)

### [ ] Phase 4: API Service Instrumentation

- [ ] Task 4.1: Add OpenTelemetry Python packages

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 287-310)

- [ ] Task 4.2: Create shared telemetry initialization module

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 312-360)

- [ ] Task 4.3: Instrument API service startup

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 362-390)

- [ ] Task 4.4: Configure API service environment variables

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 392-410)

- [ ] Task 4.5: Verify API traces, metrics, and logs
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 412-435)

### [ ] Phase 5: Bot Service Instrumentation

- [ ] Task 5.1: Instrument bot service startup

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 437-465)

- [ ] Task 5.2: Add manual spans for Discord event handlers

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 467-505)

- [ ] Task 5.3: Configure bot service environment variables

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 507-525)

- [ ] Task 5.4: Verify bot traces
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 527-545)

### [ ] Phase 6: Daemon Services Instrumentation

- [ ] Task 6.1: Instrument notification daemon

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 547-585)

- [ ] Task 6.2: Instrument status transition daemon

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 587-625)

- [ ] Task 6.3: Configure daemon environment variables

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 627-650)

- [ ] Task 6.4: Verify daemon traces and message context propagation
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 652-675)

### [ ] Phase 7: Grafana Cloud Dashboards

- [ ] Task 7.1: Import pre-built PostgreSQL dashboard

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 677-695)

- [ ] Task 7.2: Import pre-built Redis dashboard

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 697-715)

- [ ] Task 7.3: Create custom service overview dashboard

  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 717-750)

- [ ] Task 7.4: Configure alerting rules
  - Details:
    .copilot-tracking/details/20251206-opentelemetry-observability-details.md
    (Lines 752-780)

## Dependencies

- Grafana Cloud free tier account
- OpenTelemetry Collector Contrib (Grafana Alloy)
- OpenTelemetry Python instrumentation libraries
- Existing PostgreSQL, Redis, and RabbitMQ services

## Success Criteria

- API requests generate complete trace spans from HTTP ingress to database
  queries
- Bot commands create trace spans with Discord event context
- Scheduled daemon tasks create root spans with proper attributes
- RabbitMQ message context propagates from publishers to consumers
- PostgreSQL and Redis metrics visible in Grafana Cloud Mimir
- Structured logs with trace correlation available in Grafana Cloud Loki
- All services remain within Grafana Cloud free tier limits (50GB traces, 50GB
  logs, 10k metric series)
- No critical performance degradation (<5% latency increase)
