---
applyTo: ".copilot-tracking/changes/20260204-autocopyright-official-repository-migration-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Autocopyright Official Repository Migration

## Overview

Migrate autocopyright from local pre-commit hooks to the official Argmaster/autocopyright repository for improved maintainability and automatic version updates.

## Objectives

- Replace local autocopyright hooks with official repository configuration
- Remove obsolete scripts/add-copyright wrapper script
- Enable automatic version management via pre-commit autoupdate
- Maintain existing copyright header functionality for Python and TypeScript files

## Research Summary

### Project Files

- .pre-commit-config.yaml (Lines 27-46) - Current local autocopyright hooks configuration
- scripts/add-copyright - Obsolete bash wrapper from pre-20260128 implementation
- templates/mit-template.jinja2 - Jinja2 template for copyright headers (compatible)

### External References

- #file:../research/20260204-autocopyright-precommit-direct-integration-research.md - Complete migration analysis
- #fetch:https://github.com/Argmaster/autocopyright - Official repository and documentation
- #githubRepo:"Argmaster/autocopyright README pre-commit" - Official pre-commit configuration examples

### Standards References

- #file:../../.github/instructions/github-actions-ci-cd-best-practices.instructions.md - Pre-commit hook best practices
- #file:../research/20260128-precommit-standalone-configuration-research.md - Previous standalone configuration migration context

## Implementation Checklist

### [x] Phase 1: Update Pre-commit Configuration

- [x] Task 1.1: Replace local autocopyright hooks with official repository
  - Details: .copilot-tracking/details/20260204-autocopyright-official-repository-migration-details.md (Lines 15-45)

- [x] Task 1.2: Verify hook configuration syntax and file patterns
  - Details: .copilot-tracking/details/20260204-autocopyright-official-repository-migration-details.md (Lines 47-65)

### [x] Phase 2: Remove Obsolete Files

- [x] Task 2.1: Delete scripts/add-copyright wrapper script
  - Details: .copilot-tracking/details/20260204-autocopyright-official-repository-migration-details.md (Lines 67-80)

### [x] Phase 3: Testing and Validation

- [x] Task 3.1: Test Python copyright hook execution
  - Details: .copilot-tracking/details/20260204-autocopyright-official-repository-migration-details.md (Lines 82-95)

- [x] Task 3.2: Test TypeScript copyright hook execution
  - Details: .copilot-tracking/details/20260204-autocopyright-official-repository-migration-details.md (Lines 97-110)

- [x] Task 3.3: Verify pre-commit autoupdate functionality
  - Details: .copilot-tracking/details/20260204-autocopyright-official-repository-migration-details.md (Lines 112-125)

## Dependencies

- pre-commit framework installed
- templates/mit-template.jinja2 template file
- pyproject.toml for template variable substitution

## Success Criteria

- Official Argmaster/autocopyright repository configured with v1.1.0
- Both Python and TypeScript hooks execute successfully
- Copyright headers maintained correctly on all files
- scripts/add-copyright removed from repository
- pre-commit autoupdate recognizes and can update autocopyright version
- No local dependencies or additional_dependencies required
