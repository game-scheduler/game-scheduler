<!-- markdownlint-disable-file -->

# Release Changes: Docker-in-Docker Act Path Mounting Fix

**Related Plan**: 20251216-docker-in-docker-act-path-mounting-plan.instructions.md
**Implementation Date**: 2025-12-16

## Summary

Fixed Docker-in-Docker path mounting for nektos/act by implementing a path consistency approach. The dev container workspace path now matches the host path exactly using `${localWorkspaceFolder}`, enabling nested container bind mounts to work correctly without workarounds. Simplified CI/CD workflows by removing matrix strategies and updating to Python 3.13.

## Changes

### Added

- .copilot-tracking/changes/20251216-docker-in-docker-act-path-mounting-changes.md - This change tracking file

### Modified

- .devcontainer/devcontainer.json - Updated workspace path to use ${localWorkspaceFolder} for path consistency, removed HOST_WORKSPACE_FOLDER environment variable, simplified postStartCommand
- .actrc - Removed --directory workaround flag since act now uses current directory correctly
- .github/workflows/ci-cd.yml - Removed matrix strategies from unit-tests and integration-tests, updated to Python 3.13
- docs/LOCAL_TESTING_WITH_ACT.md - Added path consistency approach section, troubleshooting for chdir errors and port conflicts, container reuse notes
- .copilot-tracking/plans/20251216-docker-in-docker-act-path-mounting-plan.instructions.md - Marked all phases complete

### Removed

None

## Release Summary

**Total Files Affected**: 6

### Files Created (1)

- .copilot-tracking/changes/20251216-docker-in-docker-act-path-mounting-changes.md - Change tracking documentation

### Files Modified (5)

- .devcontainer/devcontainer.json - Implemented path consistency by setting workspaceFolder and workspaceMount to ${localWorkspaceFolder}, removed remoteEnv with HOST_WORKSPACE_FOLDER, cleaned up postStartCommand symlink workarounds
- .actrc - Removed --directory=${HOST_WORKSPACE_FOLDER} flag as it's no longer needed with path consistency
- .github/workflows/ci-cd.yml - Simplified workflows by removing python-version matrix from unit-tests and integration-tests jobs, updated to single Python 3.13 version
- docs/LOCAL_TESTING_WITH_ACT.md - Documented path consistency solution, added troubleshooting sections for chdir errors and port conflicts, noted container reuse limitations with matrix jobs
- .copilot-tracking/plans/20251216-docker-in-docker-act-path-mounting-plan.instructions.md - Updated all phase checkboxes to complete

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: Dev container now uses path consistency approach (workspace path matches host path), eliminating need for symlinks and path translation
- **Configuration Updates**: Removed HOST_WORKSPACE_FOLDER environment variable, simplified act configuration, updated CI/CD to Python 3.13

### Testing Performed

- ✅ Dev container rebuild with path consistency configuration
- ✅ Workspace path verification (pwd shows /home/mckee/src/github.com/game-scheduler)
- ✅ Act workflow execution with nested bind mounts (file and directory)
- ✅ Nested Docker containers successfully resolved workspace paths
- ✅ All act jobs passing: lint, frontend-test, unit-tests, integration-tests
- ✅ Environment cleanup (removed 22 stopped containers)

### Key Findings

- Matrix jobs with --reuse flag cause container naming conflicts - removed matrix strategies for local testing
- Root-owned files from previous act runs caused "chdir" errors - resolved with docker system prune
- Path consistency approach eliminates need for special workarounds (symlinks, environment variables, --directory flag)
- Solution is simpler and more maintainable than previous approach

### Deployment Notes

Developers must rebuild their dev containers to apply the path consistency changes. Run "Dev Containers: Rebuild Container" from VS Code Command Palette. After rebuild, workspace path inside container will match host path instead of /app.
