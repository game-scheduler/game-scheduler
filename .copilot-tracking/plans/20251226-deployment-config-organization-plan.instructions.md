---
applyTo: ".copilot-tracking/changes/20251226-deployment-config-organization-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Deployment Configuration Organization

## Overview

Reorganize all deployment configuration files into a single `config/` directory to simplify per-site deployments and enable better separation of code from configuration.

## Objectives

- Consolidate all deployment-specific config (env files, RabbitMQ, Grafana Alloy) into a single `config/` directory
- Update all Docker Compose files and scripts to reference new config paths
- Enable per-site customization via separate config repository pattern
- Maintain full compatibility with existing deployment workflows

## Research Summary

### Project Files

- compose.yaml - Current Docker Compose base configuration with volume mounts
- compose.override.yaml - Development environment overrides with hot-reload
- compose.prod.yaml - Production environment overrides
- compose.staging.yaml - Staging environment overrides
- env/ - Environment variable files for all environments
- rabbitmq/ - RabbitMQ configuration files
- grafana-alloy/ - Grafana Alloy configuration and dashboards

### External References

- #file:../research/20251226-deployment-config-organization-research.md - Complete research on config directory patterns
- #githubRepo:"traefik/traefik deployment config organization" - Config directory and layering patterns
- #githubRepo:"netbox-community/netbox deployment config organization" - Code/config separation patterns
- #githubRepo:"home-assistant/core deployment config organization" - Config directory and volume mounting
- #fetch:https://12factor.net/config - Twelve-Factor App config principles
- #fetch:https://docs.docker.com/compose/production/ - Docker Compose production best practices

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker and Compose conventions

## Implementation Checklist

### [x] Phase 1: Create Config Directory Structure

- [x] Task 1.1: Create config directory hierarchy
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 20-30)

- [x] Task 1.2: Move environment files
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 32-42)

- [x] Task 1.3: Move RabbitMQ configuration
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 44-54)

- [x] Task 1.4: Move Grafana Alloy configuration
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 56-66)

### [ ] Phase 2: Update Docker Compose Files

- [ ] Task 2.1: Update compose.yaml volume mounts
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 68-78)

- [ ] Task 2.2: Update compose.override.yaml volume mounts
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 80-90)

- [ ] Task 2.3: Update environment-specific compose files
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 92-102)

### [ ] Phase 3: Update Scripts and Documentation

- [ ] Task 3.1: Update scripts with config file references
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 104-114)

- [ ] Task 3.2: Update deployment documentation
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 116-126)

- [ ] Task 3.3: Update .gitignore if needed
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 128-138)

### [ ] Phase 4: Testing and Validation

- [ ] Task 4.1: Test development environment
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 140-150)

- [ ] Task 4.2: Test staging environment
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 152-162)

- [ ] Task 4.3: Test production environment configuration
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 164-174)

### [ ] Phase 5: Documentation and Templates

- [ ] Task 5.1: Create per-site deployment template documentation
  - Details: .copilot-tracking/details/20251226-deployment-config-organization-details.md (Lines 176-186)

## Dependencies

- Docker and Docker Compose
- Git (for moving files with history preservation)

## Success Criteria

- All deployment config files are in `config/` directory
- All Docker Compose files reference new config paths correctly
- All environments (dev, staging, prod) work with new structure
- Documentation accurately reflects new configuration organization
- Per-site deployment pattern is documented and ready for use
