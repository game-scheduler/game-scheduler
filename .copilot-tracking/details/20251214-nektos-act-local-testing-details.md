<!-- markdownlint-disable-file -->

# Task Details: Local GitHub Actions Testing with nektos/act

## Research Reference

**Source Research**: #file:../research/20251214-nektos-act-local-github-actions-research.md

## Phase 1: Install nektos/act in Test Container

### Task 1.1: Add act installation to test.Dockerfile

Add nektos/act binary installation to the test Dockerfile after system dependencies and before uv installation.

- **Files**:
  - `docker/test.Dockerfile` - Add act installation RUN command
- **Success**:
  - ARG ACT_VERSION=0.2.83 defined in Dockerfile
  - RUN command downloads and extracts act binary to /usr/local/bin/
  - Binary permissions set to executable
  - Installation positioned for optimal Docker layer caching
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 44-60) - Dockerfile installation method
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 364-383) - Installation steps with context
- **Dependencies**:
  - curl already available in test container
  - tar already available in test container

### Task 1.2: Rebuild test container with act

Build the updated test container to include act binary.

- **Files**:
  - Run `docker compose build test` command
- **Success**:
  - Test container builds successfully
  - No build errors or warnings
  - Image size increase is reasonable (~7.5MB for act binary)
  - act binary available at `/usr/local/bin/act` when container runs
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 385-392) - Build and verification steps
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Configure Act for Project

### Task 2.1: Create .actrc configuration file

Create project-level act configuration with recommended settings for workflow execution.

- **Files**:
  - `.actrc` - New file in project root
- **Success**:
  - File specifies medium Docker image (catthehacker/ubuntu:act-latest)
  - Enables offline mode for faster iteration
  - References secrets file and environment file
  - Includes bind and reuse flags for performance
  - Enables artifact server with local path
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 190-200) - Configuration file format
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 319-332) - Project-specific configuration
- **Dependencies**:
  - None

### Task 2.2: Create example secrets file template

Create a template secrets file showing required format, with placeholder values.

- **Files**:
  - `.secrets.example` - New template file in project root
- **Success**:
  - File shows format for secrets (KEY=value)
  - Includes placeholders for GITHUB_TOKEN and CODECOV_TOKEN
  - Includes comment explaining to copy to .secrets and fill in values
  - Documents that .secrets is gitignored
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 226-235) - Secrets file format
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 334-337) - Project secrets example
- **Dependencies**:
  - None

### Task 2.3: Create act-specific environment file template

Create template for act-specific environment variables with test service URLs.

- **Files**:
  - `.env.act.example` - New template file in project root
- **Success**:
  - File shows format for environment variables
  - Includes TESTING=true flag
  - Includes database, Redis, and RabbitMQ URLs matching service names
  - Includes comment explaining to copy to .env.act
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 240-247) - Environment variables format
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 339-344) - Project environment example
- **Dependencies**:
  - None

### Task 2.4: Update .gitignore for act files

Add act-related files to .gitignore to prevent committing secrets and local configuration.

- **Files**:
  - `.gitignore` - Add entries for act files
- **Success**:
  - .secrets added to gitignore
  - .env.act added to gitignore
  - .artifacts/ directory added to gitignore
  - Existing .env* pattern already covers .env.act but explicit entry improves clarity
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 399-400) - Files to gitignore
- **Dependencies**:
  - Task 2.2 and 2.3 completion (know which files to ignore)

## Phase 3: Documentation and Testing

### Task 3.1: Create usage documentation

Create comprehensive documentation for using act with this project.

- **Files**:
  - `docs/LOCAL_TESTING_WITH_ACT.md` - New documentation file
- **Success**:
  - Document explains what act is and benefits
  - Includes setup instructions (copy templates, fill in values)
  - Lists common usage commands for project workflows
  - Explains how to run specific jobs (unit-tests, integration-tests)
  - Includes troubleshooting section
  - Documents Docker socket mounting requirement
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 202-221) - Basic usage commands
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 402-418) - Usage patterns
- **Dependencies**:
  - Phase 1 and Phase 2 completion

### Task 3.2: Test act workflow execution

Verify act works correctly by running workflows locally.

- **Files**:
  - No file changes, verification only
- **Success**:
  - `act --version` shows version 0.2.83
  - `act -l` lists workflows successfully
  - Can run unit-tests job: `act -j unit-tests`
  - Medium Docker image pulls successfully on first run
  - Services (postgres, redis, rabbitmq) start correctly
  - Workflow executes without errors
- **Research References**:
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 287-295) - Complete examples
  - #file:../research/20251214-nektos-act-local-github-actions-research.md (Lines 405-408) - First run and testing steps
- **Dependencies**:
  - All Phase 1 and Phase 2 tasks completed
  - Docker socket accessible
  - Secrets and environment files configured

## Dependencies

- Docker must be installed and running on host
- Docker socket must be accessible from test container
- curl and tar available in test container (already present)
- Sufficient disk space for act images (~500MB)

## Success Criteria

- Act binary installed and functional in test container
- Configuration files created and properly formatted
- Secrets and environment templates provided for developers
- .gitignore prevents committing sensitive files
- Documentation enables team members to use act effectively
- At least one successful local workflow execution verified
- Fast iteration on workflow changes without GitHub pushes enabled
