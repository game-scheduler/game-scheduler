---
applyTo: ".copilot-tracking/changes/20251211-docker-compose-environment-reorganization-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Docker Compose Environment Reorganization

## Overview

Consolidate Docker Compose files to use modern naming conventions (`compose.yaml` pattern) and standard merge behavior, eliminating the `include` directive and establishing clear environment isolation with consistent configuration patterns across development, production, staging, and testing environments.

## Objectives

- Migrate from mixed `docker-compose.*` and `compose.*` naming to consistent `compose.{env}.yaml` pattern
- Eliminate `include` directive conflicts by merging base configuration into `compose.yaml`
- Use `COMPOSE_FILE` variable in each env file to specify which compose files to load
- Simplify multi-environment usage to single `--env-file` parameter
- Update all scripts, documentation, and workflows to reference new file structure
- Ensure clean cut-over with no deprecated files remaining

## Research Summary

### Project Files

- docker-compose.base.yml - Shared service definitions using include directive
- docker-compose.yml - Development environment with local volumes/networks
- compose.override.yaml - Development overrides with hot-reload
- compose.production.yaml - Production overrides with restart policies
- compose.testing.yaml - Staging overrides with INFO logging
- docker-compose.e2e.yml - E2E test environment with tmpfs volumes
- docker-compose.integration.yml - Integration test environment
- scripts/run-integration-tests.sh - Integration test execution script
- scripts/run-e2e-tests.sh - E2E test execution script

### External References

- #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 1-330) - Complete environment structure analysis and migration strategy
- #fetch:https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/ - Docker Compose merge behavior documentation
- #fetch:https://docs.docker.com/compose/how-tos/multiple-compose-files/include/#using-overrides-with-included-compose-files - Include directive limitations

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker and container best practices
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding standards

## Implementation Checklist

### [x] Phase 1: Merge Base Configuration into compose.yaml

- [x] Task 1.1: Create production-ready compose.yaml by merging docker-compose.base.yml and docker-compose.yml

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 15-35)

- [x] Task 1.2: Remove include directive references from all compose files
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 37-47)

### [x] Phase 2: Rename Compose Files to Modern Convention

- [x] Task 2.1: Rename compose files to compose.{env}.yaml pattern

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 49-67)

- [x] Task 2.2: Delete deprecated docker-compose.test.yml file
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 69-76)

### [x] Phase 3: Configure Environment-Specific Overrides

- [x] Task 3.1: Configure compose.prod.yaml for production (minimal overrides)

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 78-92)

- [x] Task 3.2: Configure compose.staging.yaml for staging environment

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 94-108)

- [x] Task 3.3: Configure compose.override.yaml for development

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 110-127)

- [x] Task 3.4: Configure compose.e2e.yaml for end-to-end testing

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 129-143)

- [x] Task 3.5: Configure compose.int.yaml for integration testing
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 145-159)

### [x] Phase 4: Configure COMPOSE_FILE in Environment Files

- [x] Task 4.1: Create env/env.staging configuration file

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 161-173)

- [x] Task 4.2: Add COMPOSE_FILE variable to all environment files
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 175-190)

### [ ] Phase 5: Update Scripts

- [ ] Task 5.1: Update scripts/run-integration-tests.sh

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 192-204)

- [ ] Task 5.2: Update scripts/run-e2e-tests.sh

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 206-218)

- [ ] Task 5.3: Audit all other scripts for compose file references
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 220-229)

### [ ] Phase 6: Update Documentation

- [ ] Task 6.1: Update DEPLOYMENT_QUICKSTART.md

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 231-244)

- [ ] Task 6.2: Update README.md

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 246-258)

- [ ] Task 6.3: Update TESTING_E2E.md

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 260-270)

- [ ] Task 6.4: Audit all other documentation files
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 272-281)

### [ ] Phase 7: Verification and Cleanup

- [ ] Task 7.1: Verify .gitignore patterns protect secrets

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 283-293)

- [ ] Task 7.2: Test all environment configurations

  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 295-311)

- [ ] Task 7.3: Remove old compose files
  - Details: .copilot-tracking/details/20251211-docker-compose-environment-reorganization-details.md (Lines 313-324)

## Dependencies

- Docker Compose with merge support (modern Docker Desktop or Docker Engine with Compose v2)
- Existing environment files in env/ directory (env.dev, env.prod, env.e2e, env.integration)
- Access to project documentation and test scripts

## Success Criteria

- All compose files follow `compose.{env}.yaml` naming convention
- `compose.yaml` is complete, production-ready base configuration without include directives
- Each env file contains `COMPOSE_FILE` variable specifying which compose files to load
- Single `--env-file` parameter controls entire environment configuration
- All five environments (dev, prod, staging, e2e, int) clearly defined with appropriate logging and port exposure
- All scripts execute successfully with new `--env-file env/env.{environment}` references
- All documentation updated and accurate
- Integration and E2E tests pass with new configuration
- No deprecated files remain in repository
