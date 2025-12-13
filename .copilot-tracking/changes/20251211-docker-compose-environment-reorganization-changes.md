<!-- markdownlint-disable-file -->

# Release Changes: Docker Compose Environment Reorganization

**Related Plan**: 20251211-docker-compose-environment-reorganization-plan.instructions.md
**Implementation Date**: 2025-12-12

## Summary

Consolidating Docker Compose files to use modern naming conventions and standard merge behavior, eliminating the include directive and establishing clear environment isolation with consistent configuration patterns across development, production, staging, and testing environments.

## Changes

### Added

- compose.yaml - Production-ready base configuration merging docker-compose.base.yml and docker-compose.yml with production defaults (INFO logging, restart: always, no port mappings)
- compose.e2e.yaml - End-to-end test environment configuration (renamed from docker-compose.e2e.yml)
- compose.int.yaml - Integration test environment configuration (renamed from docker-compose.integration.yml)
- compose.prod.yaml - Production environment overrides (renamed from compose.production.yaml)
- compose.staging.yaml - Staging environment overrides (renamed from compose.testing.yaml)

### Modified

- compose.prod.yaml - Simplified to minimal overrides with only production build targets, LOG_LEVEL INFO inherited from base
- compose.staging.yaml - Updated with DEBUG logging, production builds, restart: always, frontend and API ports exposed
- compose.override.yaml - Updated with DEBUG logging for all services, all infrastructure management ports exposed
- compose.e2e.yaml - Updated with DEBUG logging for all services, no port mappings, infrastructure logging configured
- compose.int.yaml - Updated with DEBUG logging for infrastructure services, no port mappings

### Removed

- docker-compose.e2e.yml - Renamed to compose.e2e.yaml following modern Docker Compose naming conventions
- docker-compose.integration.yml - Renamed to compose.int.yaml following modern Docker Compose naming conventions
- compose.production.yaml - Renamed to compose.prod.yaml following modern Docker Compose naming conventions
- compose.testing.yaml - Renamed to compose.staging.yaml following modern Docker Compose naming conventions
- docker-compose.test.yml - Deleted deprecated test configuration file superseded by dedicated e2e and integration test environments

### Phase 4 Changes - COMPOSE_FILE Configuration

- env/env.staging - Added COMPOSE_FILE=compose.yaml:compose.staging.yaml and CONTAINER_PREFIX=gamebot-staging for staging environment isolation
- env/env.dev - Added COMPOSE_FILE=compose.yaml:compose.override.yaml to explicitly specify development compose files
- env/env.prod - Added COMPOSE_FILE=compose.yaml to specify production base configuration only
- env/env.e2e - Added COMPOSE_FILE=compose.yaml:compose.e2e.yaml for end-to-end test environment
- env/env.int - Added COMPOSE_FILE=compose.yaml:compose.int.yaml for integration test environment

### Phase 5 Changes - Script Updates

- scripts/run-integration-tests.sh - Updated to use --env-file env/env.int and removed explicit -f flags (COMPOSE_FILE variable handles compose file selection)
- scripts/run-e2e-tests.sh - Updated to use --env-file env/env.e2e and removed explicit -f flags, updated file existence checks and source commands to reference env/env.e2e
- scripts/migrate_postgres_15_to_17.sh - Updated documentation reference from docker-compose.base.yml to compose.yaml in rollback instructions

### Phase 6 Changes - Documentation Updates

- DEPLOYMENT_QUICKSTART.md - Updated all compose file references to use --env-file env/env.prod.local pattern, documented COMPOSE_FILE variable behavior, updated environment configuration sections to reference env/ directory, added environment-specific logging and port exposure documentation
- README.md - Updated development setup to document .env symlink pattern, added COMPOSE_FILE variable explanation, documented all five environments (dev, prod, staging, e2e, int) with their compose file patterns, updated project structure to show env/ directory and compose file organization, replaced docker-compose.base.yml references with modern compose.yaml base configuration
- TESTING_E2E.md - Updated environment file references to env/env.int and env/env.e2e with COMPOSE_FILE variable documentation, updated test execution commands to use --env-file env/env.{environment} pattern, updated CI/CD examples to create env files in env/ directory, updated security notes to reference env/* .gitignore protection
- DOCKER_PORTS.md - Updated base configuration reference from docker-compose.base.yml to compose.yaml, updated test environment references from docker-compose.test.yml to compose.e2e.yaml and compose.int.yaml, updated production reference from compose.production.yaml to compose.prod.yaml, added compose.staging.yaml to See Also section
- grafana-alloy/TESTING_PHASE1.md - Updated prerequisites reference from docker-compose.base.yml to compose.yaml, updated troubleshooting section to reference .env symlink instead of .env being in same directory as docker-compose.yml
- grafana-alloy/TESTING_PHASE2.md - Updated database name reference comment from docker-compose.base.yml to compose.yaml

### Phase 7 Changes - Verification and Cleanup

- .gitignore - Updated Docker section: removed compose.override.yaml and compose.local.yaml patterns (modern compose files should be tracked since they use environment variable references, not hardcoded secrets; only legacy docker-compose.override.yml pattern remains for backwards compatibility)
- .env.integration - Removed from git tracking (file remains locally but is now properly protected by .env* pattern)
- compose.override.yaml - Re-added to git tracking (contains no secrets, only shared development configuration with environment variable references)
- docker-compose.base.yml - Deleted from repository (merged into compose.yaml)
- docker-compose.yml - Deleted from repository (merged into compose.yaml)
- .env.prod symlink - Removed (no longer needed with --env-file env/env.prod pattern)
- .env.staging symlink - Removed (no longer needed with --env-file env/env.staging pattern)
- .env.e2e symlink - Removed (no longer needed with --env-file env/env.e2e pattern)
- .env.int symlink - Removed (no longer needed with --env-file env/env.int pattern)

## Release Summary

**Total Files Affected**: 20

### Files Created (5)

- compose.yaml - Production-ready base configuration consolidating all shared service definitions
- compose.e2e.yaml - End-to-end test environment overrides with DEBUG logging and tmpfs volumes
- compose.int.yaml - Integration test environment overrides with DEBUG logging and tmpfs volumes
- compose.prod.yaml - Minimal production overrides with production build targets
- compose.staging.yaml - Staging environment overrides with DEBUG logging and exposed app ports
- env/env.staging - Staging environment configuration with COMPOSE_FILE and CONTAINER_PREFIX variables

### Files Modified (13)

- compose.override.yaml - Added DEBUG logging and all infrastructure management port mappings for development
- env/env.dev - Added COMPOSE_FILE=compose.yaml:compose.override.yaml
- env/env.prod - Added COMPOSE_FILE=compose.yaml
- env/env.e2e - Added COMPOSE_FILE=compose.yaml:compose.e2e.yaml
- env/env.int - Added COMPOSE_FILE=compose.yaml:compose.int.yaml
- scripts/run-integration-tests.sh - Updated to use --env-file env/env.int pattern
- scripts/run-e2e-tests.sh - Updated to use --env-file env/env.e2e pattern
- scripts/migrate_postgres_15_to_17.sh - Updated compose file references in documentation
- DEPLOYMENT_QUICKSTART.md - Comprehensive update to document new environment patterns
- README.md - Updated development setup and environment documentation
- TESTING_E2E.md - Updated test execution commands and environment references
- DOCKER_PORTS.md - Updated compose file references throughout
- grafana-alloy/TESTING_PHASE1.md - Updated compose file references
- grafana-alloy/TESTING_PHASE2.md - Updated compose file references
- .gitignore - Added compose.override.yaml pattern

### Files Removed (4)

- docker-compose.base.yml - Merged into compose.yaml
- docker-compose.yml - Merged into compose.yaml
- docker-compose.test.yml - Deprecated by compose.e2e.yaml and compose.int.yaml
- .env.integration - Untracked from git (still exists locally, protected by .env* pattern)

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: 
  - Docker Compose file structure completely reorganized
  - COMPOSE_FILE environment variable now controls compose file loading
  - Five distinct environments: development, production, staging, e2e, integration
  - Standard Docker Compose merge pattern replaces include directive pattern
- **Configuration Updates**:
  - All environment files now specify COMPOSE_FILE variable
  - Development uses compose.override.yaml (auto-loaded via COMPOSE_FILE)
  - Production uses compose.yaml only (no overrides)
  - Staging exposes app ports with DEBUG logging
  - Test environments use tmpfs volumes with DEBUG logging

### Deployment Notes

**Breaking Changes**:
- Direct use of `docker compose up` requires `.env` symlink to `env/env.dev` (already in place)
- Production deployments must use `docker compose --env-file env/env.prod.local up -d`
- All environment-specific deployments use single `--env-file` parameter
- Old `docker-compose.base.yml` and `docker-compose.yml` files removed from repository

**Migration Steps**:
1. Ensure `.env` symlink points to `env/env.dev` (already configured)
2. Update any deployment scripts to use `--env-file env/env.{environment}` pattern
3. Verify `COMPOSE_FILE` variable is set in each environment file
4. Test each environment configuration with `docker compose --env-file env/env.{environment} config`

**Environment Usage**:
- **Development**: `docker compose up` (uses .env → env/env.dev)
- **Production**: `docker compose --env-file env/env.prod.local up -d`
- **Staging**: `docker compose --env-file env/env.staging up -d`
- **E2E Tests**: `docker compose --env-file env/env.e2e up --abort-on-container-exit`
- **Integration Tests**: `docker compose --env-file env/env.int run --rm integration-tests`
