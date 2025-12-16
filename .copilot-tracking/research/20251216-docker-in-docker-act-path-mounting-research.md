<!-- markdownlint-disable-file -->
# Task Research Notes: Docker-in-Docker Path Mounting for Act

## Research Executed

### Commit Analysis
- Commit 367f8302b5b825138cc8bf820f5ee8b3b3ff1b81
  - Solution already implemented and verified working
  - Configuration changes to `.actrc`, `.devcontainer/devcontainer.json`
  - Research notes updated in existing research file

### File Analysis
- `.devcontainer/devcontainer.json`
  - Uses `docker-outside-of-docker` feature (moby: false)
  - Sets `HOST_WORKSPACE_FOLDER` environment variable: `${localWorkspaceFolder}`
  - Includes symlink creation in `postStartCommand`
- `.actrc`
  - Configured with `--directory=${HOST_WORKSPACE_FOLDER}` option
- `docs/LOCAL_TESTING_WITH_ACT.md`
  - Comprehensive usage documentation for act
- `.copilot-tracking/research/20251214-nektos-act-local-github-actions-research.md`
  - Contains detailed solution documentation and verification

### External Research
- #githubRepo:"nektos/act path mapping bind mount"
  - Act spawns Docker containers on the host using host paths
  - `--directory` flag specifies the working directory for workflows
  - Path translation is critical when running act from within a container
- #githubRepo:"microsoft/vscode-dev-containers docker in docker path mapping localWorkspaceFolder HOST_WORKSPACE_FOLDER"
  - Pattern of using `LOCAL_WORKSPACE_FOLDER` environment variable is standard
  - Microsoft recommends symlinks for path consistency in nested containers
  - Docker-from-docker approach requires host path awareness

## Key Discoveries

### Critical Finding: Nested Bind Mount Problem

**Initial assumption was incorrect.** The symlink/environment variable approach (commit 367f8302) solves only the surface problem but fails for the real use case:

1. ✅ Top-level `act` command executes successfully
2. ❌ **Act-spawned containers that attempt bind mounts fail**
3. ❌ **Nested container bind mounts cannot resolve paths**

### Problem Definition

When running `act` from inside a dev container at path `/app`:

**First layer issue (solved by commit 367f8302):**
- Act spawns containers using Docker on host
- Act needs host paths for bind mounts
- Using `--directory=${HOST_WORKSPACE_FOLDER}` helps act itself

**Second layer issue (NOT solved by commit 367f8302):**
- Act-spawned containers run workflows
- Workflows may spawn additional containers with bind mounts
- These nested containers reference paths from their own filesystem
- If workflow references `/app/something`, host Docker daemon cannot find it
- **Symlinks inside dev container are invisible to act-spawned containers**

### Root Cause: Multi-Level Container Nesting

The problem occurs with multi-level container nesting:

```
Layer 1: Host machine
  Path: /home/mckee/src/github.com/game-scheduler
  └─ Docker daemon running here

Layer 2: Dev container
  Path: /app (bind mount from host path above)
  └─ Act command runs here, communicates with Layer 1 Docker daemon

Layer 3: Act job container (spawned by act via host Docker)
  Path: /workspace (bind mount from host path)
  └─ Workflow steps execute here

Layer 4: Workflow-spawned containers (e.g., docker run in workflow)
  Attempted bind mount: /app/something
  ❌ FAILS: Host Docker daemon doesn't have /app path
```

**The critical insight:**
- **ALL bind mount requests ultimately go to the host Docker daemon**
- Symlinks in Layer 2 (dev container) don't help Layer 4 containers
- Layer 4 containers inherit working directory `/workspace` from Layer 3
- If Layer 4 tries `docker run -v /workspace/data:/data`, it fails
- Host Docker daemon looks for `/workspace/data` on host (doesn't exist)

**Example failure:**
```bash
# In workflow step (Layer 3):
- name: Run tests in container
  run: |
    docker run -v $PWD/testdata:/data test-image
    # $PWD is /workspace, but host doesn't have /workspace
```

### Previous Solution Attempt (INCOMPLETE)

An earlier attempt (commit 367f8302) tried using environment variables and symlinks:

#### Part 1: Environment Variable (Insufficient)

In `.devcontainer/devcontainer.json`:
```json
{
  "remoteEnv": {
    "HOST_WORKSPACE_FOLDER": "${localWorkspaceFolder}"
  }
}
```

#### Part 2: Act Configuration (Insufficient)

In `.actrc`:
```
--directory=${HOST_WORKSPACE_FOLDER}
```

#### Part 3: Symlink Creation (Insufficient)

In `.devcontainer/devcontainer.json` `postStartCommand`:
```bash
sudo mkdir -p "$(dirname "${HOST_WORKSPACE_FOLDER}")" 2>/dev/null || true && \
sudo ln -sfn /app "${HOST_WORKSPACE_FOLDER}" 2>/dev/null || true
```

**Why this approach fails:**
- Works for top-level `act` command execution
- Breaks when act-spawned containers try to do their own bind mounts
- Symlinks only exist in dev container, not visible to act-spawned containers
- Nested bind mounts reference container paths that don't exist on host

### Implementation Details

**Current `.devcontainer/devcontainer.json` Configuration:**
```json
{
  "name": "Game Scheduler Development",
  "workspaceFolder": "/app",
  "workspaceMount": "source=${localWorkspaceFolder},target=/app,type=bind,consistency=cached",
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {
      "moby": false
    }
  },
  "postStartCommand": "sudo chown -R vscode:vscode /home/vscode/.vscode-server 2>/dev/null || true && sudo mkdir -p \"$(dirname \"${HOST_WORKSPACE_FOLDER}\")\" 2>/dev/null || true && sudo ln -sfn /app \"${HOST_WORKSPACE_FOLDER}\" 2>/dev/null || true",
  "remoteEnv": {
    "HOST_WORKSPACE_FOLDER": "${localWorkspaceFolder}"
  }
}
```

**Current `.actrc` Configuration:**
```
# Use medium-sized Docker image
-P ubuntu-latest=catthehacker/ubuntu:act-latest

# Enable offline mode for faster iteration
--action-offline-mode

# Load secrets from file
--secret-file=.secrets

# Load environment variables from file
--env-file=.env.act

# Bind working directory to job container
--bind

# Reuse containers between runs
--reuse

# Enable artifact server
--artifact-server-path=.artifacts

# Use host workspace folder for proper path mapping (fixes nested container issues)
--directory=${HOST_WORKSPACE_FOLDER}
```

### How It Works (Step-by-Step)

1. **Dev container starts**: VS Code reads `${localWorkspaceFolder}` (host path) and sets `HOST_WORKSPACE_FOLDER`
2. **Workspace mount**: Host path bound to `/app` inside container
3. **Symlink creation**: `postStartCommand` creates symlink from host path to `/app`
4. **Act execution**: User runs `act` command inside dev container
5. **Act reads config**: Expands `${HOST_WORKSPACE_FOLDER}` to actual host path
6. **Container spawn**: Act tells host Docker daemon to create containers with bind mounts using host path
7. **Success**: Bind mounts work because Docker daemon can resolve the host path

### Verification Status

❌ **Previous approach from commit 367f8302 incomplete:**
- `act` command itself runs successfully
- Workflows fail when they attempt nested bind mounts
- Need to implement path consistency approach instead

## Technical Background

### Docker-Outside-of-Docker Pattern

The dev container uses `docker-outside-of-docker` feature:
```json
"ghcr.io/devcontainers/features/docker-outside-of-docker:1": {
  "moby": false
}
```

This pattern:
- Mounts host's Docker socket into dev container
- Docker CLI commands in container communicate with host daemon
- All containers are siblings on the host (not nested)
- Requires host path awareness for bind mounts

### Alternative: Docker-in-Docker

An alternative approach is true Docker-in-Docker (DinD), which:
- Runs separate Docker daemon inside container
- Allows using container paths for bind mounts
- Has performance penalty due to nested virtualization
- More complex setup and resource overhead

The docker-outside-of-docker approach is preferred for:
- Better performance (no nested virtualization)
- Simpler configuration
- Container reuse across dev container restarts
- Shared Docker image cache with host

### Path Translation Considerations

**Why symlinks work:**
1. Symlink exists only inside dev container filesystem
2. When act spawns containers with host paths, those containers don't see the symlink
3. Containers see the actual host path mounted to their specified mount point
4. Dev container can reference either path, both resolve to same content

**Path resolution flow:**
```
Inside dev container:
  /app -> actual mount point
  /home/mckee/src/github.com/game-scheduler -> symlink to /app

On host:
  /home/mckee/src/github.com/game-scheduler -> actual directory

Act-spawned container:
  Bind mount: /home/mckee/src/github.com/game-scheduler (host) -> /workspace (container)
```

### Act Workflow Execution Model

When act runs a workflow:
1. Parses workflow YAML and evaluates expressions
2. Creates job container with specified image
3. Sets up bind mounts for workspace and actions
4. Copies required files and sets environment
5. Executes workflow steps inside job container
6. Spawns additional containers for actions (action-based steps)

All container operations go through host Docker daemon, requiring host paths for bind mounts.

## Best Practices

### Environment Variable Pattern

Using environment variables for host paths is a standard pattern:
- Recommended by Microsoft VSCode Dev Containers documentation
- Used across Microsoft's official dev container templates
- Enables consistent behavior across different host platforms

**Standard variable names:**
- `LOCAL_WORKSPACE_FOLDER`: Common in Microsoft examples
- `HOST_WORKSPACE_FOLDER`: Used in this project (more explicit)

Both are valid; consistency within project is what matters.

### Symlink Strategy

Creating symlinks on container startup:
- Makes both paths valid references
- Simplifies scripts (no path translation logic needed)
- Transparent to users and tools
- Safe because symlink only exists in container

**Safety considerations:**
- Use `sudo` carefully (only for symlink creation)
- Create parent directories first to avoid failures
- Use `-f` flag to handle existing symlinks gracefully
- Redirect errors with `2>/dev/null || true` for resilience

### Configuration Management

Keep path-related configuration in one place:
- `.devcontainer/devcontainer.json`: Source of truth for environment variables
- `.actrc`: References environment variables (no hardcoded paths)
- Documentation: Explains the why and how

## Related Patterns

### Compose File Integration

In `compose.yaml` and `compose.override.yaml`:
```yaml
services:
  rabbitmq:
    volumes:
      - ${HOST_WORKSPACE_FOLDER:-.}/rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
```

The `${HOST_WORKSPACE_FOLDER:-.}` pattern:
- Uses `HOST_WORKSPACE_FOLDER` if set (inside dev container)
- Falls back to `.` (current directory) if not set (direct docker compose)
- Ensures consistent behavior in both environments

### Cross-Platform Compatibility

Path handling considerations:
- **Linux/macOS**: Paths use forward slashes, case-sensitive
- **Windows**: Paths may use backslashes, case-insensitive, drive letters
- **WSL**: Windows paths translated to `/mnt/c/...` style

The solution works across platforms because:
- `${localWorkspaceFolder}` is normalized by VS Code
- Symlink creation handles any path format
- Act uses normalized paths internally

## ISSUE WITH PREVIOUS SOLUTION

❌ **THE SYMLINK/ENVIRONMENT VARIABLE APPROACH DOES NOT FULLY WORK**

### Why the Previous Solution Fails

The symlink and `--directory` approach from commit 367f8302 only partially solves the problem:

1. ✅ **Act itself runs** - The `act` command can spawn job containers
2. ❌ **Nested bind mounts fail** - When act-spawned containers try to do their own bind mounts (common in workflows), they fail

**Root cause:** When a container spawned by act tries to bind mount a path, it uses paths **relative to its own container filesystem**. If that container references `/app` or any path that doesn't exist on the host, the bind mount fails because all bind mounts ultimately go through the host Docker daemon.

**Example failure scenario:**
```
Host: /home/mckee/src/github.com/game-scheduler
Dev Container: /app (mounted from host path)
  └─ Act spawns Container A: working directory is /workspace (bound from /app)
     └─ Container A tries to mount /app/something -> FAILS (host doesn't have /app)
```

## Correct Solution: Path Consistency

### The Right Approach

**Use the SAME path inside the dev container as exists on the host.**

Instead of:
- Host: `/home/mckee/src/github.com/game-scheduler`
- Dev Container: `/app` ❌

Do this:
- Host: `/home/mckee/src/github.com/game-scheduler`
- Dev Container: `/home/mckee/src/github.com/game-scheduler` ✅

### Why This Works

With consistent paths, the entire nesting chain works:

```
Layer 1: Host machine
  Path: /home/mckee/src/github.com/game-scheduler
  └─ Docker daemon sees this path

Layer 2: Dev container
  Path: /home/mckee/src/github.com/game-scheduler (same as host!)
  └─ Act command runs here

Layer 3: Act job container
  Working dir: /home/mckee/src/github.com/game-scheduler
  └─ Bound from host with same path

Layer 4: Workflow-spawned containers
  Bind mount: /home/mckee/src/github.com/game-scheduler/data
  ✅ SUCCESS: Host Docker daemon CAN resolve this path
```

**The magic:**
- Every layer references the same absolute path
- No path translation needed at any level
- Host Docker daemon can always resolve paths
- Works for unlimited nesting depth

### Required Changes

**1. Update `.devcontainer/devcontainer.json`:**

Current (incorrect):
```json
{
  "workspaceFolder": "/app",
  "workspaceMount": "source=${localWorkspaceFolder},target=/app,type=bind,consistency=cached"
}
```

Change to (correct):
```json
{
  "workspaceFolder": "${localWorkspaceFolder}",
  "workspaceMount": "source=${localWorkspaceFolder},target=${localWorkspaceFolder},type=bind,consistency=cached"
}
```

**2. Clean up `postStartCommand`:**

Current (with workaround):
```json
{
  "postStartCommand": "sudo chown -R vscode:vscode /home/vscode/.vscode-server 2>/dev/null || true && sudo mkdir -p \"$(dirname \"${HOST_WORKSPACE_FOLDER}\")\" 2>/dev/null || true && sudo ln -sfn /app \"${HOST_WORKSPACE_FOLDER}\" 2>/dev/null || true"
}
```

Change to (simplified):
```json
{
  "postStartCommand": "sudo chown -R vscode:vscode /home/vscode/.vscode-server 2>/dev/null || true"
}
```

**3. Remove `HOST_WORKSPACE_FOLDER` from `remoteEnv`:**

Current (unnecessary):
```json
{
  "remoteEnv": {
    "HOST_WORKSPACE_FOLDER": "${localWorkspaceFolder}"
  }
}
```

Change to (remove entirely or empty object):
```json
{
  "remoteEnv": {}
}
```

**4. Revert `.actrc` changes:**

Current (with workaround):
```
--directory=${HOST_WORKSPACE_FOLDER}
```

Change to (remove this line completely)

### Why This Works

When the dev container path matches the host path:
1. Act spawns containers with bind mounts using container paths
2. Those paths are valid on the host (same paths exist there)
3. Nested containers can freely use bind mounts without path translation
4. No special configuration or environment variables needed

### Implementation Checklist

- [ ] Update `workspaceFolder` in `.devcontainer/devcontainer.json` to `${localWorkspaceFolder}`
- [ ] Update `workspaceMount` in `.devcontainer/devcontainer.json` to use `${localWorkspaceFolder}` as target
- [ ] Remove `HOST_WORKSPACE_FOLDER` from `remoteEnv` section
- [ ] Remove symlink creation from `postStartCommand`
- [ ] Remove `--directory=${HOST_WORKSPACE_FOLDER}` line from `.actrc`
- [ ] Rebuild dev container
- [ ] Test act with workflows that use bind mounts

### Trade-offs and Considerations

**Pros:**
- Simple and robust - no special configuration needed
- Works for any level of container nesting
- No path translation logic required
- Bind mounts "just work" at any nesting level

**Cons:**
- Dev container path matches host path (may be long or unusual)
- Less control over where workspace appears in container
- Path may differ across development machines with different home directories

**Mitigation:**
- This is the standard approach used by many projects with similar requirements
- VS Code handles the path consistently across the project
- Tools and scripts work the same way regardless of path

## References

### Documentation
- [nektos/act Usage Guide](https://nektosact.com/usage/index.html)
- [VSCode Dev Containers: Docker from Docker](https://github.com/microsoft/vscode-dev-containers/tree/main/containers/docker-from-docker)
- [Act Configuration Options](https://nektosact.com/usage/index.html)

### Key Files
- `.devcontainer/devcontainer.json` - Dev container configuration
- `.actrc` - Act configuration file
- `docs/LOCAL_TESTING_WITH_ACT.md` - Usage documentation
- `.copilot-tracking/research/20251214-nektos-act-local-github-actions-research.md` - Detailed research

### Related Commits
- 367f8302b5b825138cc8bf820f5ee8b3b3ff1b81 - **INCOMPLETE SOLUTION** - Configure act for dev container path mapping (needs to be reverted)
  - Added `--directory=${HOST_WORKSPACE_FOLDER}` to `.actrc`
  - Added `HOST_WORKSPACE_FOLDER` to `remoteEnv`
  - Added symlink creation to `postStartCommand`
  - Works for basic act commands but fails for nested bind mounts
