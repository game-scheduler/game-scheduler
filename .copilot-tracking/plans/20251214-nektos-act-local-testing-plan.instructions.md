---
applyTo: ".copilot-tracking/changes/20251214-nektos-act-local-testing-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Local GitHub Actions Testing with nektos/act

## Overview

Enable local testing of GitHub Actions workflows using nektos/act to catch issues before pushing to GitHub and reduce CI/CD iteration time.

## Objectives

- Install nektos/act binary in test container for consistent development environment
- Configure act with project-specific settings for optimal workflow execution
- Provide secrets and environment management for local testing
- Document usage patterns for team members
- Enable fast iteration on workflow changes without GitHub pushes

## Research Summary

### Project Files

- `docker/test.Dockerfile` - Test container definition, will add act installation
- `.github/workflows/ci-cd.yml` - CI/CD workflow with unit tests, integration tests, linting, frontend tests
- `.gitignore` - Needs updates to exclude secrets and act-specific files

### External References

- #file:../research/20251214-nektos-act-local-github-actions-research.md - Comprehensive nektos/act installation and configuration research
- #githubRepo:"nektos/act installation configuration docker setup" - Implementation patterns and Docker integration methods
- #fetch:https://nektosact.com/installation/index.html - Official installation documentation
- #fetch:https://nektosact.com/usage/index.html - Usage patterns and best practices

### Standards References

- #file:../../.github/copilot-instructions.md - Project coding standards and conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices for image building

## Implementation Checklist

### [ ] Phase 1: Install nektos/act in Test Container

- [ ] Task 1.1: Add act installation to test.Dockerfile
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 13-32)

- [ ] Task 1.2: Rebuild test container with act
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 34-46)

### [ ] Phase 2: Configure Act for Project

- [ ] Task 2.1: Create .actrc configuration file
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 48-67)

- [ ] Task 2.2: Create example secrets file template
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 69-82)

- [ ] Task 2.3: Create act-specific environment file template
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 84-97)

- [ ] Task 2.4: Update .gitignore for act files
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 99-110)

### [ ] Phase 3: Documentation and Testing

- [ ] Task 3.1: Create usage documentation
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 112-130)

- [ ] Task 3.2: Test act workflow execution
  - Details: .copilot-tracking/details/20251214-nektos-act-local-testing-details.md (Lines 132-149)

## Dependencies

- Docker must be installed and running
- curl and tar available in test container (already present)
- Docker socket access for spawning test containers
- Medium disk space (~500MB for act Docker images)

## Success Criteria

- `act` binary installed and accessible at `/usr/local/bin/act` in test container
- `.actrc` configuration file present with project-specific settings
- Example secrets and environment templates created
- `.gitignore` updated to exclude sensitive act files
- Documentation created with usage patterns and examples
- Successfully run at least one workflow locally using act
- Team members can iterate on workflows without pushing to GitHub
