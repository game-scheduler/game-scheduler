<!-- markdownlint-disable-file -->
# Task Research Notes: Docker Compose Environment Reorganization

## Research Executed

### File Analysis
- docker-compose.yml
  - Development environment (default), includes docker-compose.base.yml, defines local volumes/networks
- docker-compose.base.yml
  - Shared service definitions used by all environments via 'include' directive
- docker-compose.test.yml
  - Generic test configuration with profiles for integration/e2e tests
- docker-compose.e2e.yml
  - Dedicated e2e test environment with tmpfs volumes
- docker-compose.integration.yml
  - Dedicated integration test environment with tmpfs volumes
- compose.override.yaml
  - Development overrides (auto-loaded), enables hot-reload with volume mounts
- compose.production.yaml
  - Production overrides (explicit -f flag), production build targets, restart policies
- compose.testing.yaml
  - Testing/staging overrides (explicit -f flag), production builds with INFO logging

### Environment File Analysis
- env/env - Template/example file
- env/env.dev - Development Discord bot credentials
- env/env.prod - Production Discord bot credentials  
- env/env.e2e - E2E test configuration (CONTAINER_PREFIX=gamebot-e2e)
- env/env.integration - Integration test configuration (CONTAINER_PREFIX=gamebot-integration)

### Script Dependencies
- scripts/run-integration-tests.sh
  - Uses: docker-compose.integration.yml with .env.integration
- scripts/run-e2e-tests.sh
  - Uses: docker-compose.e2e.yml with .env.e2e
- DEPLOYMENT_QUICKSTART.md
  - Documents: docker-compose.yml + compose.production.yaml for production

## Key Discoveries

### Current Environment Structure

**Three file categories exist:**
1. **Base files**: docker-compose.base.yml (shared service definitions)
2. **Environment-specific compose files**: docker-compose.yml (dev), docker-compose.{test,e2e,integration}.yml
3. **Override files**: compose.{override,production,testing}.yaml

**Current environments identified:**
- Development (default) - docker-compose.yml + compose.override.yaml (auto)
- Production - docker-compose.yml + compose.production.yaml (explicit)
- Testing/Staging - docker-compose.yml + compose.testing.yaml (explicit)
- E2E tests - docker-compose.e2e.yml + .env.e2e
- Integration tests - docker-compose.integration.yml + .env.integration
- Generic test - docker-compose.test.yml (appears deprecated/superseded)

### Naming Inconsistencies

**Compose files:**
- Mix of `docker-compose.*` and `compose.*` naming
- Test environments use dedicated compose files (docker-compose.{e2e,integration}.yml)
- Non-test environments use override pattern (compose.{production,testing}.yaml)

**Environment files:**
- Located in env/ directory
- Named: env, env.dev, env.prod, env.e2e, env.integration
- No env.staging file exists

### Architectural Patterns

**Two distinct patterns in use:**

1. **Include + Override pattern** (dev/prod/staging):
   - Base file included via 'include' directive
   - Override files modify build targets, volumes, restart policies
   - Development: compose.override.yaml auto-loads, enables hot-reload
   - Production/Staging: Explicit -f flags, production builds

2. **Dedicated compose files** (test environments):
   - Self-contained files that include base
   - Define test-specific services (test containers)
   - Use tmpfs volumes for speed
   - Paired with specific env files

## Recommended Approach

**CORRECTED: Use standard Docker Compose merge pattern, NOT include directive:**

Docker Compose's `include` directive has a critical limitation: services from included files conflict with service overrides in the including file. The Docker documentation states: "Compose reports an error if any resource from `include` conflicts with resources from the included Compose file."

**The correct pattern is the standard merge approach:**
- Base file: `compose.yaml` (production-ready, complete configuration)
- Auto-loaded override: `compose.override.yaml` (development conveniences)
- Explicit overrides: `compose.{env}.yaml` files used with `-f` flag

When using `-f` flag, Docker Compose does NOT auto-load `compose.override.yaml`, so each environment is isolated.

**Consolidate to single naming pattern using modern Docker Compose standards:**

### File Naming Convention
Use `compose.<environment>.yaml` pattern consistently:
- `compose.yaml` - Base configuration (production-ready, complete)
- `compose.override.yaml` - Development overrides (auto-loaded when no -f flag used)
- `compose.prod.yaml` - Production overrides (minimal, explicit -f flag)
- `compose.staging.yaml` - Staging overrides (explicit -f flag)
- `compose.e2e.yaml` - End-to-end test overrides (explicit -f flag)
- `compose.int.yaml` - Integration test overrides (explicit -f flag)

**Key change from current structure**: Eliminate `compose.base.yaml` and `include` directive. The base configuration moves into `compose.yaml` which becomes the production-ready foundation.

### Environment File Convention
Use `COMPOSE_FILE` variable within each env file to specify compose files:
- `env/env.dev` - Development (COMPOSE_FILE=compose.yaml:compose.override.yaml)
- `env/env.prod` - Production (COMPOSE_FILE=compose.yaml)
- `env/env.staging` - Staging (COMPOSE_FILE=compose.yaml:compose.staging.yaml)
- `env/env.e2e` - End-to-end testing (COMPOSE_FILE=compose.yaml:compose.e2e.yaml)
- `env/env.integration` - Integration testing (COMPOSE_FILE=compose.yaml:compose.int.yaml)
- `.env` - Symlink to env/env.dev for default development usage

### Usage Patterns

**Development (default):**
```bash
docker compose up
# Auto-loads: .env symlink (→ env/env.dev)
# env.dev sets: COMPOSE_FILE=compose.yaml:compose.override.yaml
# LOG_LEVEL: DEBUG (from compose.override.yaml)
# Exposes all ports including infrastructure management ports
# Enables hot-reload via volume mounts
```

**Production:**
```bash
docker compose --env-file env/env.prod up -d
# env.prod sets: COMPOSE_FILE=compose.yaml
# LOG_LEVEL: INFO (production default in compose.yaml)
# No ports exposed (reverse proxy handles external access)
# restart: always policy
```

**Staging:**
```bash
docker compose --env-file env/env.staging up -d
# env.staging sets: COMPOSE_FILE=compose.yaml:compose.staging.yaml
# LOG_LEVEL: DEBUG (from compose.staging.yaml for troubleshooting)
# Exposes app ports only (frontend, API) for testing
# restart: always policy
```

**E2E Testing:**
```bash
docker compose --env-file env/env.e2e up --abort-on-container-exit
# env.e2e sets: COMPOSE_FILE=compose.yaml:compose.e2e.yaml
# LOG_LEVEL: DEBUG (from compose.e2e.yaml)
# No ports exposed (tests run inside container network)
# tmpfs volumes for speed
```

**Integration Testing:**
```bash
docker compose --env-file env/env.integration run --rm integration-tests
# env.integration sets: COMPOSE_FILE=compose.yaml:compose.int.yaml
# LOG_LEVEL: DEBUG (from compose.int.yaml)
# No ports exposed (tests run inside container network)
# tmpfs volumes for speed
```

## Recommended Approach

**Consolidate to single naming pattern using modern Docker Compose standards.**

### File Structure After Migration

```
compose.yaml              (base/production - consolidates docker-compose.base.yml + docker-compose.yml)
compose.override.yaml     (dev overrides - existing file, adds debug logging + port exposure)
compose.prod.yaml         (production overrides - was compose.production.yaml, minimal changes)
compose.staging.yaml      (staging overrides - was compose.testing.yaml, DEBUG logging + app ports)
compose.e2e.yaml          (e2e test overrides - was docker-compose.e2e.yml, adds test service)
compose.int.yaml          (integration test overrides - was docker-compose.integration.yml, adds test service)

.env                      (symlink → env/env.dev for default dev usage)

env/
  env                     (template/example - managed in separate git repo)
  env.dev                 (development - sets COMPOSE_FILE=compose.yaml:compose.override.yaml)
  env.prod                (production - sets COMPOSE_FILE=compose.yaml)
  env.staging             (staging - sets COMPOSE_FILE=compose.yaml:compose.staging.yaml)
  env.e2e                 (e2e test - sets COMPOSE_FILE=compose.yaml:compose.e2e.yaml)
  env.integration         (integration test - sets COMPOSE_FILE=compose.yaml:compose.int.yaml)
```

**Note**: The env/ directory is managed in a separate git repository and never pushed to the main repo. The .gitignore patterns `.env*` and `env/*` ensure secrets remain protected.

### Key Architectural Decision: Merge vs Include

**Why NOT use `include` directive:**
- Docker Compose's `include` directive causes conflicts when trying to override services from the included file
- Error message: "services.{name} conflicts with imported resource"
- This prevents overriding LOG_LEVEL, ports, or any other service-level settings
- See: https://docs.docker.com/compose/how-tos/multiple-compose-files/include/#using-overrides-with-included-compose-files

**Why USE standard merge pattern:**
- When using `-f` flag, Docker Compose only loads specified files (compose.override.yaml is NOT auto-loaded)
- Services merge naturally across multiple files specified with `-f` flags
- Environment variables in later files override earlier files
- Ports, volumes, and other sequences are merged intelligently
- This is the standard Docker Compose pattern documented for production use
- See: https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/

**Migration Impact:**
- Current `docker-compose.base.yml` must be merged into `compose.yaml` 
- Current `docker-compose.yml` must also be merged into `compose.yaml`
- Test files that used `include` must be converted to pure override files
- Result: `compose.yaml` becomes complete, production-ready base configuration

## Implementation Guidance

### User Decisions

**1. Port Exposure Strategy:**
- **Production**: No ports exposed (uses reverse proxy on same Docker network)
- **Staging**: Frontend and API only (no infrastructure/management ports)
- **E2E/Integration**: No ports exposed (tests run inside containers)
- **Development**: Expose everything (all application and management ports)

**2. Log Levels:**
- **Production**: INFO (via compose.yaml defaults)
- **Staging**: DEBUG (via compose.staging.yaml override for troubleshooting)
- **E2E**: DEBUG (via compose.e2e.yaml override)
- **Integration**: DEBUG (via compose.int.yaml override)
- **Development**: DEBUG (via compose.override.yaml override)
- **Development**: DEBUG

**3. Staging Configuration:**
- Use production build targets (code baked into images)
- Apply INFO logging for better debugging
- Expose only frontend and API ports (no management UIs)
- Use restart: always policy like production

**4. Migration Strategy:**
- Clean cut-over (no backwards compatibility period)
- Update all scripts and documentation immediately
- Remove deprecated files in same commit

### Implementation Tasks

**Phase 1: Rename and restructure compose files**
- Rename docker-compose.base.yml → compose.base.yaml
- Rename docker-compose.yml → compose.yaml
- Rename docker-compose.e2e.yml → compose.e2e.yaml
- Rename docker-compose.integration.yml → compose.int.yaml
- Rename compose.production.yaml → compose.prod.yaml
- Rename compose.testing.yaml → compose.staging.yaml
- Delete docker-compose.test.yml (deprecated)
- Update all 'include' directives to reference compose.base.yaml

**Phase 2: Configure COMPOSE_FILE in environment files**
- Note: .env files are stored in env/ directory (separate git repo, not pushed to main repo)
- .env symlink already exists (points to env/env.dev) ✓
- Add COMPOSE_FILE=compose.yaml:compose.override.yaml to env/env.dev
- Add COMPOSE_FILE=compose.yaml to env/env.prod
- Add COMPOSE_FILE=compose.yaml:compose.staging.yaml to env/env.staging (create file first)
- Add COMPOSE_FILE=compose.yaml:compose.e2e.yaml to env/env.e2e
- Add COMPOSE_FILE=compose.yaml:compose.int.yaml to env/env.integration
- Keep env/env as template/example file
- .gitignore already correctly ignores .env* and env/* patterns (secrets managed in separate repo)

**Phase 3: Update compose file configurations**
- compose.prod.yaml: WARN logging, production builds, restart: always, NO port mappings
- compose.staging.yaml: INFO logging, production builds, restart: always, frontend + API ports only
- compose.e2e.yaml: Remove port mappings, set DEBUG logging
- compose.int.yaml: Remove port mappings, set DEBUG logging
- compose.override.yaml: Add all management ports, set DEBUG logging

**Phase 4: Update scripts**
- scripts/run-integration-tests.sh: Update to use --env-file env/env.integration
- scripts/run-e2e-tests.sh: Update to use --env-file env/env.e2e
- Verify all other scripts in scripts/ directory

**Phase 5: Update documentation**
- DEPLOYMENT_QUICKSTART.md: Update all compose file references
- README.md: Update development and deployment instructions
- TESTING_E2E.md: Update test execution commands
- Any other documentation referencing compose files

**Phase 6: Verify .gitignore**
- Confirm `.env*` and `env/` patterns remain in .gitignore (secrets managed in separate repo)
- Keep `compose.override.yaml` ignored (per existing pattern)
- No changes needed to .gitignore
### Port Exposure Summary

**Development (all ports):**
- Frontend: 3000
- API: 8000
- Postgres: 5432
- RabbitMQ Data: 5672
- RabbitMQ Management: 15672
- Redis: 6379
- Grafana Alloy: 12345

**Production (none):**
- No ports exposed to host
- Services accessed via reverse proxy on Docker network

**Staging (app only):**
- Frontend: configured port (via env var)
- API: configured port (via env var)
- No infrastructure/management ports

**E2E/Integration (none):**
- All tests run inside containers
### Dependencies Identified
- Update scripts: run-integration-tests.sh, run-e2e-tests.sh
- Update documentation: DEPLOYMENT_QUICKSTART.md, README.md, TESTING_E2E.md
- Update CI/CD workflows if any exist (.github/workflows/)
- Create env/env.staging and add COMPOSE_FILE variables to all env files
- Verify .gitignore patterns remain protective of secrets
- Update any hardcoded references in source code to use --env-file env/env.{environment}

### Success Criteria
- All five environments clearly defined with consistent naming
- COMPOSE_FILE variable in each env file specifies which compose files to use
- Single --env-file parameter controls entire environment configuration
- Clear documentation of when to use each environment
- Scripts updated and functional
- Clean cut-over with no deprecated files remaining
- All tests pass with new configuration
