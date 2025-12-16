<!-- markdownlint-disable-file -->

# Task Details: Docker-in-Docker Act Path Mounting Fix

## Research Reference

**Source Research**: #file:../research/20251216-docker-in-docker-act-path-mounting-research.md

## Phase 1: Update Dev Container Configuration

### Task 1.1: Update workspace path mapping in devcontainer.json

Change the dev container workspace configuration to use the same path as the host, eliminating the need for path translation.

- **Files**:
  - .devcontainer/devcontainer.json - Update workspaceFolder and workspaceMount
- **Current Values**:
  - `"workspaceFolder": "/app"`
  - `"workspaceMount": "source=${localWorkspaceFolder},target=/app,type=bind,consistency=cached"`
- **New Values**:
  - `"workspaceFolder": "${localWorkspaceFolder}"`
  - `"workspaceMount": "source=${localWorkspaceFolder},target=${localWorkspaceFolder},type=bind,consistency=cached"`
- **Success**:
  - workspaceFolder references ${localWorkspaceFolder}
  - workspaceMount target matches source path
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 234-254) - Required changes section
- **Dependencies**: None

### Task 1.2: Remove HOST_WORKSPACE_FOLDER environment variable

Remove the HOST_WORKSPACE_FOLDER environment variable from remoteEnv as it's no longer needed with path consistency.

- **Files**:
  - .devcontainer/devcontainer.json - Update remoteEnv section
- **Action**: Remove the entire remoteEnv object or change to empty object
- **Success**:
  - remoteEnv section removed or empty
  - No HOST_WORKSPACE_FOLDER variable defined
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 266-278) - Remove HOST_WORKSPACE_FOLDER
- **Dependencies**: None

### Task 1.3: Clean up postStartCommand

Remove the symlink creation and parent directory creation from postStartCommand, keeping only the vscode-server ownership fix.

- **Files**:
  - .devcontainer/devcontainer.json - Simplify postStartCommand
- **Current**: `"sudo chown -R vscode:vscode /home/vscode/.vscode-server 2>/dev/null || true && sudo mkdir -p \"$(dirname \"${HOST_WORKSPACE_FOLDER}\")\" 2>/dev/null || true && sudo ln -sfn /app \"${HOST_WORKSPACE_FOLDER}\" 2>/dev/null || true"`
- **New**: `"sudo chown -R vscode:vscode /home/vscode/.vscode-server 2>/dev/null || true"`
- **Success**:
  - postStartCommand only contains vscode-server ownership command
  - No symlink creation or directory creation commands
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 256-264) - Clean up postStartCommand
- **Dependencies**: None

## Phase 2: Update Act Configuration

### Task 2.1: Remove directory workaround from .actrc

Remove the --directory flag from act configuration as it's no longer needed with path consistency.

- **Files**:
  - .actrc - Remove directory setting
- **Action**: Delete the line `--directory=${HOST_WORKSPACE_FOLDER}`
- **Success**:
  - No --directory flag in .actrc
  - Act will use current working directory by default
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 280-286) - Revert .actrc changes
- **Dependencies**: Task 1.1 completion (workspace path must be updated first)

## Phase 3: Verification

### Task 3.1: Rebuild dev container

Rebuild the dev container to apply the new configuration.

- **Action**: Use VS Code command palette to rebuild dev container
- **Commands**:
  - "Dev Containers: Rebuild Container" or
  - "Dev Containers: Rebuild and Reopen in Container"
- **Success**:
  - Dev container rebuilds successfully
  - Workspace opens at host path inside container
  - No errors during container initialization
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 288-296) - Implementation checklist
- **Dependencies**: Phase 1 and Phase 2 completion

### Task 3.2: Test act with nested bind mounts

Create a test workflow that uses bind mounts and verify it works correctly.

- **Test Workflow**: Create `.github/workflows/test-bind-mount.yml` with a step that:
  1. Creates a test file in the workspace
  2. Spawns a container with bind mount from workspace
  3. Verifies the file is accessible in the spawned container
- **Example**:
  ```yaml
  name: Test Bind Mount
  on: push
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - name: Test nested bind mount
          run: |
            echo "test data" > test.txt
            docker run -v $PWD/test.txt:/data/test.txt:ro alpine cat /data/test.txt
  ```
- **Success**:
  - Act can execute the workflow without errors
  - Nested bind mount works correctly
  - File content is accessible in spawned container
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 188-203) - Example failure scenario and solution
- **Dependencies**: Task 3.1 completion

## Phase 4: Documentation

### Task 4.1: Update act documentation with solution explanation

Update the act documentation to explain the path consistency approach and why it's necessary.

- **Files**:
  - docs/LOCAL_TESTING_WITH_ACT.md - Add section on path consistency
- **Content**: Add explanation of:
  - Why path consistency is needed for nested bind mounts
  - How the solution works
  - Trade-offs and considerations
- **Success**:
  - Documentation includes path consistency explanation
  - Future developers understand why workspace path matches host path
- **Research References**:
  - #file:../research/20251216-docker-in-docker-act-path-mounting-research.md (Lines 288-318) - Why This Works section
- **Dependencies**: Phase 3 verification completion

## Dependencies

- nektos/act installed and configured in dev container
- Docker-outside-of-docker feature enabled
- VS Code Dev Containers extension

## Success Criteria

- All configuration files updated correctly
- Dev container uses host path for workspace
- Act workflows with nested bind mounts execute successfully
- Documentation updated with solution explanation
- No workarounds or path translation needed
