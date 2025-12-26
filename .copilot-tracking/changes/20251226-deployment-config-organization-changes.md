<!-- markdownlint-disable-file -->

# Release Changes: Deployment Configuration Organization

**Related Plan**: 20251226-deployment-config-organization-plan.instructions.md
**Implementation Date**: 2025-12-26

## Summary

Reorganizing all deployment configuration files into a single `config/` directory to simplify per-site deployments and enable better separation of code from configuration.

## Changes

### Added

- config/env/ - New directory for environment variable files
- config/rabbitmq/ - New directory for RabbitMQ configuration
- config/grafana-alloy/ - New directory for Grafana Alloy configuration
- config/grafana-alloy/dashboards/ - New directory for Grafana Alloy dashboards
- config/env/env.dev - Moved from env/env.dev
- config/env/env.prod - Moved from env/env.prod
- config/env/env.staging - Moved from env/env.staging
- config/env/env.e2e - Moved from env/env.e2e
- config/env/env.int - Moved from env/env.int
- config/rabbitmq/rabbitmq.conf - Moved from rabbitmq/rabbitmq.conf
- config/grafana-alloy/config.alloy - Moved from grafana-alloy/config.alloy
- config/grafana-alloy/dashboards/ - Moved from grafana-alloy/dashboards/
- config/grafana-alloy/SETUP_GRAFANA_CLOUD.md - Moved from grafana-alloy/SETUP_GRAFANA_CLOUD.md
- docs/grafana-alloy/ - New directory for Grafana Alloy documentation
- docs/grafana-alloy/TESTING_PHASE1.md - Moved from grafana-alloy/TESTING_PHASE1.md
- docs/grafana-alloy/TESTING_PHASE2.md - Moved from grafana-alloy/TESTING_PHASE2.md
- docs/grafana-alloy/TESTING_PHASE3.md - Moved from grafana-alloy/TESTING_PHASE3.md
- docs/grafana-alloy/TESTING_PHASE4.md - Moved from grafana-alloy/TESTING_PHASE4.md
- docs/grafana-alloy/TESTING_PHASE5.md - Moved from grafana-alloy/TESTING_PHASE5.md
- docs/grafana-alloy/TESTING_PHASE6.md - Moved from grafana-alloy/TESTING_PHASE6.md
- docs/grafana-alloy/TESTING_PHASE7.md - Moved from grafana-alloy/TESTING_PHASE7.md

### Modified

### Removed

- env/ - Removed after moving all files to config/env/
- rabbitmq/ - Removed after moving all files to config/rabbitmq/
- grafana-alloy/ - Removed after moving all files to config/grafana-alloy/
