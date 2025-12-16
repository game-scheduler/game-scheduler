---
applyTo: ".copilot-tracking/changes/20251216-docker-in-docker-act-path-mounting-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Docker-in-Docker Act Path Mounting Fix

## Overview

Fix the incomplete Docker-in-Docker path mounting solution by implementing path consistency approach for nested container bind mounts in act workflows.

## Objectives

- Replace incomplete symlink/environment variable workaround with path consistency approach
- Enable nested bind mounts in act-spawned workflow containers
- Simplify dev container configuration by removing unnecessary path translation
- Ensure act workflows with Docker bind mounts work correctly from dev container

## Research Summary

### Project Files

- .devcontainer/devcontainer.json - Dev container configuration with incorrect workspace path mapping
- .actrc - Act configuration with workaround directory setting
- docs/LOCAL_TESTING_WITH_ACT.md - Act usage documentation

### External References

- #file:../research/20251216-docker-in-docker-act-path-mounting-research.md - Complete problem analysis and solution documentation
- #githubRepo:"nektos/act path mapping bind mount" - Act container spawning behavior with host paths
- #githubRepo:"microsoft/vscode-dev-containers docker in docker path mapping" - VSCode dev container path handling patterns

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker configuration best practices

## Implementation Checklist

### [x] Phase 1: Update Dev Container Configuration

- [x] Task 1.1: Update workspace path mapping in devcontainer.json
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 11-28)

- [x] Task 1.2: Remove HOST_WORKSPACE_FOLDER environment variable
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 30-40)

- [x] Task 1.3: Clean up postStartCommand
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 42-54)

### [x] Phase 2: Update Act Configuration

- [x] Task 2.1: Remove directory workaround from .actrc
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 58-70)

### [x] Phase 3: Verification

- [x] Task 3.1: Rebuild dev container
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 74-84)

- [x] Task 3.2: Test act with nested bind mounts
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 86-104)

### [x] Phase 4: Documentation

- [x] Task 4.1: Update act documentation with solution explanation
  - Details: .copilot-tracking/details/20251216-docker-in-docker-act-path-mounting-details.md (Lines 108-118)

## Dependencies

- nektos/act installed and configured
- Docker-outside-of-docker feature in dev container
- VS Code Dev Containers extension

## Success Criteria

- Dev container workspace path matches host path exactly
- Act can spawn containers that successfully use nested bind mounts
- No path translation workarounds needed
- Act workflows with Docker operations execute successfully
- Documentation explains the path consistency approach
