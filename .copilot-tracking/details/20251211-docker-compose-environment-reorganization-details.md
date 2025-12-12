<!-- markdownlint-disable-file -->

# Task Details: Docker Compose Environment Reorganization

## Research Reference

**Source Research**: #file:../research/20251211-docker-compose-environment-reorganization-research.md

## Phase 1: Merge Base Configuration into compose.yaml

### Task 1.1: Create production-ready compose.yaml by merging docker-compose.base.yml and docker-compose.yml

Merge the shared service definitions from docker-compose.base.yml and the environment-specific configuration from docker-compose.yml into a single, production-ready compose.yaml file. This eliminates the include directive pattern and establishes compose.yaml as the complete base configuration.

- **Files**:
  - docker-compose.base.yml - Source for all service definitions
  - docker-compose.yml - Source for volumes, networks, and any dev-specific overrides
  - compose.yaml - New production-ready base configuration (create)
- **Success**:
  - compose.yaml contains all service definitions from base file
  - compose.yaml includes all necessary volumes and networks
  - compose.yaml has production-appropriate defaults (INFO logging, no port mappings, restart: always)
  - No include directives present in compose.yaml
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 88-121) - Architectural decision on merge vs include pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 206-220) - Migration impact and base file consolidation
- **Dependencies**:
  - None (first task)

### Task 1.2: Remove include directive references from all compose files

After consolidating into compose.yaml, remove all include directive references from remaining compose files since they will use the merge pattern instead.

- **Files**:
  - compose.override.yaml - Remove include directive if present
  - compose.production.yaml - Remove include directive if present
  - compose.testing.yaml - Remove include directive if present
- **Success**:
  - No include directives remain in any compose file
  - Files are pure override files that will merge with compose.yaml
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 88-100) - Why NOT use include directive
- **Dependencies**:
  - Task 1.1 completion (compose.yaml must exist)

## Phase 2: Rename Compose Files to Modern Convention

### Task 2.1: Rename compose files to compose.{env}.yaml pattern

Rename all compose files to follow the modern compose.{env}.yaml naming convention, maintaining git history through git mv commands.

- **Files**:
  - docker-compose.e2e.yml → compose.e2e.yaml
  - docker-compose.integration.yml → compose.int.yaml
  - compose.production.yaml → compose.prod.yaml
  - compose.testing.yaml → compose.staging.yaml
  - compose.override.yaml (keep as-is, already correct)
- **Success**:
  - All files renamed with git history preserved
  - Consistent compose.{env}.yaml naming throughout project
  - No docker-compose.* files remain except those to be deleted
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 105-114) - File naming convention
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 253-260) - Phase 1 rename tasks
- **Dependencies**:
  - Phase 1 completion (base consolidation must be done first)

### Task 2.2: Delete deprecated docker-compose.test.yml file

Remove the deprecated docker-compose.test.yml file which has been superseded by dedicated e2e and integration test configurations.

- **Files**:
  - docker-compose.test.yml - Delete
- **Success**:
  - File removed from repository
  - No references to this file remain in scripts or documentation
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 53-55) - Generic test file identified as deprecated
- **Dependencies**:
  - Task 2.1 completion (rename other test files first)

## Phase 3: Configure Environment-Specific Overrides

### Task 3.1: Configure compose.prod.yaml for production (minimal overrides)

Configure production overrides to be minimal, only setting production-specific restart policies and ensuring no ports are exposed.

- **Files**:
  - compose.prod.yaml - Update with minimal production-specific settings
- **Success**:
  - restart: always set for all production services
  - No port mappings defined (reverse proxy handles access)
  - Production build targets specified if different from base
  - LOG_LEVEL remains at INFO (from base compose.yaml)
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 123-131) - Production usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 224-229) - Production: No ports, WARN logging, restart policies
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 277-279) - compose.prod.yaml configuration task
- **Dependencies**:
  - Phase 2 completion (file must be renamed)

### Task 3.2: Configure compose.staging.yaml for staging environment

Configure staging to match production builds but with DEBUG logging and app-only port exposure for testing.

- **Files**:
  - compose.staging.yaml - Update with staging-specific configuration
- **Success**:
  - LOG_LEVEL: DEBUG for all services (override base INFO setting)
  - Frontend and API ports exposed (no infrastructure ports)
  - Production build targets used (code baked into images)
  - restart: always policy like production
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 133-141) - Staging usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 231-235) - Staging: app ports only
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 279-281) - compose.staging.yaml configuration task
- **Dependencies**:
  - Phase 2 completion (file must be renamed)

### Task 3.3: Configure compose.override.yaml for development

Update development overrides to expose all ports (app + infrastructure) and set DEBUG logging.

- **Files**:
  - compose.override.yaml - Update with complete development configuration
- **Success**:
  - LOG_LEVEL: DEBUG for all services
  - All ports exposed: Frontend (3000), API (8000), Postgres (5432), RabbitMQ (5672, 15672), Redis (6379), Grafana Alloy (12345)
  - Volume mounts enabled for hot-reload
  - Development build targets used where applicable
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 116-122) - Development usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 237-247) - Development port exposure list
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 281-283) - compose.override.yaml configuration task
- **Dependencies**:
  - Phase 2 completion

### Task 3.4: Configure compose.e2e.yaml for end-to-end testing

Configure e2e test overrides with DEBUG logging, no port exposure, and tmpfs volumes for speed.

- **Files**:
  - compose.e2e.yaml - Update with e2e test configuration
- **Success**:
  - LOG_LEVEL: DEBUG for all services
  - No port mappings (tests run inside container network)
  - tmpfs volumes configured for database and cache services
  - E2E test service defined with proper dependencies
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 143-150) - E2E testing usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 283-285) - compose.e2e.yaml configuration task
- **Dependencies**:
  - Phase 2 completion (file must be renamed)

### Task 3.5: Configure compose.int.yaml for integration testing

Configure integration test overrides with DEBUG logging, no port exposure, and tmpfs volumes for speed.

- **Files**:
  - compose.int.yaml - Update with integration test configuration
- **Success**:
  - LOG_LEVEL: DEBUG for all services
  - No port mappings (tests run inside container network)
  - tmpfs volumes configured for database and cache services
  - Integration test service defined with proper dependencies
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 152-159) - Integration testing usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 285-287) - compose.int.yaml configuration task
- **Dependencies**:
  - Phase 2 completion (file must be renamed)

## Phase 4: Configure COMPOSE_FILE in Environment Files

### Task 4.1: Create env/env.staging configuration file

Create a new staging environment configuration file based on production settings but with appropriate test Discord bot credentials and COMPOSE_FILE variable.

- **Files**:
  - env/env.staging - Create new environment file
- **Success**:
  - File created with staging-appropriate Discord bot credentials
  - COMPOSE_FILE=compose.yaml:compose.staging.yaml variable set
  - CONTAINER_PREFIX set to gamebot-staging
  - Database and other infrastructure settings match production pattern
  - File managed in separate git repo (not pushed to main repo)
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 116-121) - Environment file convention
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 189-195) - env/env.staging file location
- **Dependencies**:
  - None (independent of other phases)

### Task 4.2: Add COMPOSE_FILE variable to all environment files

Add COMPOSE_FILE variable to each environment file to specify which compose files should be loaded for that environment.

- **Files**:
  - env/env.dev - Add COMPOSE_FILE=compose.yaml:compose.override.yaml
  - env/env.prod - Add COMPOSE_FILE=compose.yaml
  - env/env.staging - Add COMPOSE_FILE=compose.yaml:compose.staging.yaml (created in Task 4.1)
  - env/env.e2e - Add COMPOSE_FILE=compose.yaml:compose.e2e.yaml
  - env/env.integration - Add COMPOSE_FILE=compose.yaml:compose.int.yaml
  - .env symlink → env/env.dev (verify exists)
- **Success**:
  - COMPOSE_FILE variable set in all environment files
  - Each environment explicitly declares which compose files it uses
  - Development works with default `docker compose up` using .env symlink
  - Other environments work with `docker compose --env-file env/env.{environment}` syntax
  - .gitignore patterns protect secrets (.env* and env/* already ignored)
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 116-121) - Environment file convention with COMPOSE_FILE
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 262-271) - Phase 2 COMPOSE_FILE configuration tasks
- **Dependencies**:
  - Task 4.1 completion (env/env.staging must exist)

## Phase 5: Update Scripts

### Task 5.1: Update scripts/run-integration-tests.sh

Update integration test script to use new environment file path with --env-file parameter.

- **Files**:
  - scripts/run-integration-tests.sh - Update env file references
- **Success**:
  - Script uses `docker compose --env-file env/env.integration` syntax
  - No explicit -f flags needed (COMPOSE_FILE in env handles it)
  - Script executes successfully with new configuration
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 29-31) - Current script usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 289-291) - Phase 4 script update tasks
- **Dependencies**:
  - Phase 2 completion (files must be renamed)
  - Phase 4 completion (COMPOSE_FILE variables must be set)

### Task 5.2: Update scripts/run-e2e-tests.sh

Update e2e test script to use new environment file path with --env-file parameter.

- **Files**:
  - scripts/run-e2e-tests.sh - Update env file references
- **Success**:
  - Script uses `docker compose --env-file env/env.e2e` syntax
  - No explicit -f flags needed (COMPOSE_FILE in env handles it)
  - Script executes successfully with new configuration
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 32-34) - Current script usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 291-293) - Phase 4 script update tasks
- **Dependencies**:
  - Phase 2 completion (files must be renamed)
  - Phase 4 completion (COMPOSE_FILE variables must be set)

### Task 5.3: Audit all other scripts for compose file references

Search all scripts in scripts/ directory for any hardcoded references to old compose file names or env file paths and update them.

- **Files**:
  - scripts/*.sh - Audit all shell scripts
  - scripts/*.py - Audit all Python scripts
- **Success**:
  - All references use `--env-file env/env.{environment}` pattern
  - No explicit -f flags used (COMPOSE_FILE variable handles it)
  - No broken references remain
  - All scripts execute successfully
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 293-295) - Phase 4 script verification task
- **Dependencies**:
  - Phase 2 completion (files must be renamed)
  - Phase 4 completion (COMPOSE_FILE variables must be set)

## Phase 6: Update Documentation

### Task 6.1: Update DEPLOYMENT_QUICKSTART.md

Update deployment documentation to reflect new COMPOSE_FILE variable approach and simplified usage patterns.

- **Files**:
  - DEPLOYMENT_QUICKSTART.md - Update all compose file references and usage examples
- **Success**:
  - All references to docker-compose.yml updated to compose.yaml
  - Production deployment uses: `docker compose --env-file env/env.prod up -d`
  - Staging deployment uses: `docker compose --env-file env/env.staging up -d`
  - Clear explanation of COMPOSE_FILE variable and how it controls compose file loading
  - Documentation shows single --env-file parameter controls entire environment
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 35-37) - Current documentation references
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 123-159) - All environment usage patterns
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 297-299) - Phase 5 documentation update tasks
- **Dependencies**:
  - Phases 1-4 completion (all file operations must be done)

### Task 6.2: Update README.md

Update main README to reflect new COMPOSE_FILE variable approach and simplified environment usage.

- **Files**:
  - README.md - Update development setup and compose file references
- **Success**:
  - Development setup uses default `docker compose up` (uses .env symlink → env/env.dev)
  - Clear explanation of COMPOSE_FILE variable in each env file
  - Documents single --env-file parameter pattern for all environments
  - File structure and environment patterns clearly explained
  - Links to detailed documentation updated
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 116-122) - Development usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 299-301) - Phase 5 README update task
- **Dependencies**:
  - Phases 1-4 completion

### Task 6.3: Update TESTING_E2E.md

Update e2e testing documentation to reflect new COMPOSE_FILE variable approach and simplified execution.

- **Files**:
  - TESTING_E2E.md - Update test execution commands and file references
- **Success**:
  - All references to docker-compose.e2e.yml updated to compose.e2e.yaml
  - Test execution uses: `docker compose --env-file env/env.e2e up --abort-on-container-exit`
  - Documents how COMPOSE_FILE variable in env.e2e specifies compose files
  - Clear explanation of test environment configuration
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 143-150) - E2E testing usage pattern
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 301-303) - Phase 5 TESTING_E2E update task
- **Dependencies**:
  - Phases 1-4 completion)

### Task 6.4: Audit all other documentation files

Search all documentation files for references to old compose file names and update them systematically.

- **Files**:
  - *.md - All markdown files in project root
  - docs/*.md - Any documentation in docs directory
- **Success**:
  - All references to docker-compose.* files updated
  - All usage examples reflect new file structure
  - No broken references remain
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 303-305) - Phase 5 documentation audit task
- **Dependencies**:
  - Phases 1-4 completion

## Phase 7: Verification and Cleanup

### Task 7.1: Verify .gitignore patterns protect secrets

Confirm that .gitignore patterns correctly protect all environment files and prevent secrets from being committed.

- **Files**:
  - .gitignore - Verify patterns
- **Success**:
  - Pattern `.env*` present and functional
  - Pattern `env/*` or `env/` present and functional
  - compose.override.yaml ignored (if desired for local dev customization)
  - Test by checking git status shows no env files
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 189-195) - Environment file security note
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 307-311) - Phase 6 .gitignore verification task
- **Dependencies**:
  - Phase 4 completion (symlinks must exist for testing)

### Task 7.2: Test all environment configurations

Validate that each environment can start successfully using COMPOSE_FILE variable approach.

- **Files**:
  - N/A (testing phase)
- **Success**:
  - Development: `docker compose up` works (uses .env symlink, COMPOSE_FILE loads compose.yaml:compose.override.yaml)
  - Production: `docker compose --env-file env/env.prod config` validates (COMPOSE_FILE=compose.yaml)
  - Staging: `docker compose --env-file env/env.staging config` validates (COMPOSE_FILE=compose.yaml:compose.staging.yaml)
  - E2E: `docker compose --env-file env/env.e2e config` validates (COMPOSE_FILE=compose.yaml:compose.e2e.yaml)
  - Integration: `docker compose --env-file env/env.integration config` validates (COMPOSE_FILE=compose.yaml:compose.int.yaml)
  - Verify COMPOSE_FILE variable is respected in each environment
  - Port exposure matches expectations per environment
  - Log levels correct per environment
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 116-159) - All environment usage patterns
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 237-253) - Port exposure summary
- **Dependencies**:
  - All previous phases complete

### Task 7.3: Remove old compose files

Delete the original docker-compose.* files that have been replaced by the new structure.

- **Files**:
  - docker-compose.base.yml - Delete (merged into compose.yaml)
  - docker-compose.yml - Delete (merged into compose.yaml)
  - docker-compose.e2e.yml - Delete if not already renamed
  - docker-compose.integration.yml - Delete if not already renamed
  - compose.production.yaml - Delete if not already renamed
  - compose.testing.yaml - Delete if not already renamed
- **Success**:
  - All old files removed from repository
  - Only new compose.{env}.yaml files remain
  - Git history preserved for renamed files
  - No broken references in any code or documentation
- **Research References**:
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 253-260) - Phase 1 file operations
  - #file:../research/20251211-docker-compose-environment-reorganization-research.md (Lines 227-229) - Migration strategy (clean cut-over)
- **Dependencies**:
  - All previous phases complete and tested

## Dependencies

- Docker Compose v2 with merge support
- Git for preserving file history during renames

## Success Criteria

- All compose files follow modern naming convention
- Environment isolation proven through testing
- All scripts and documentation updated and functional
- No deprecated files remain
- Integration and E2E tests pass with new configuration
