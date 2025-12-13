<!-- markdownlint-disable-file -->
# Task Research Notes: VSCode Dev Container Adoption Analysis

## Research Executed

### File Analysis
- `README.md`, `TESTING_OAUTH.md`, `DEPLOYMENT_QUICKSTART.md`
  - Current development workflow relies on local `uv` installation for running services
  - Docker Compose used primarily for infrastructure (postgres, rabbitmq, redis)
  - Development uses volume mounts with hot-reload via `compose.override.yaml`
  - Services run via `uv run python -m services.api.main` locally for testing

- `pyproject.toml`
  - Python 3.11+ requirement with extensive dependencies
  - Development tools: pytest, pytest-asyncio, pytest-cov, ruff, mypy, autocopyright
  - uv used for dependency management throughout project

- `docker/*.Dockerfile` (all service Dockerfiles)
  - Multi-stage builds with `development` and `production` targets
  - Development stage installs dependencies, mounts code via volumes
  - Production stage copies code into images for deployment
  - Uses `uv pip install --system` for dependency installation

- `compose.override.yaml`
  - Automatically loaded in development environment
  - Mounts source code as read-only volumes for hot-reload
  - All services configured for development workflow
  - No devcontainer configuration currently exists

- `scripts/` directory
  - Contains various Python scripts for database migrations, initialization
  - Uses shebang or expects local Python/uv installation
  - Integration and E2E test runners using shell scripts

### Code Search Results
- **No existing devcontainer configuration**: Searched for `.devcontainer/` directory - not found
- **Local development commands**: `uv run python -m services.api.main` pattern used for local service execution
- **Testing tools**: pytest, ruff, mypy, alembic all referenced in codebase
- **Volume mount strategy**: Already implemented for Docker Compose development workflow

### External Research
- #fetch:"https://code.visualstudio.com/docs/devcontainers/containers"
  - VSCode Dev Containers extension enables full-featured container-based development
  - Workspace files mounted or cloned into containers
  - Extensions install inside containers for full tool access
  - Supports `devcontainer.json` configuration for reproducible environments
  - Two modes: full-time development environment or attach to running containers
  - Supports Docker Compose integration
  - Includes dotfiles support for personalization
  - Performance considerations for volume mounts (especially Windows/macOS)
  - Can use remote Docker hosts (SSH, tunnels)

- #fetch:"https://containers.dev/guide/dockerfile"
  - Dev Container specification is open standard
  - Can use images, Dockerfiles, or Docker Compose
  - Supports multi-stage builds
  - Metadata can be embedded in images via labels
  - Pre-building images recommended for faster startup

- #githubRepo:"devcontainers/templates"
  - Official templates for various language stacks
  - Python templates use mcr.microsoft.com/devcontainers/python base images
  - Multi-container templates combine app + database (e.g., python-postgres)
  - Templates include `devcontainer.json` with extensions, features, settings
  - Support for Features (installable tools/runtimes) via OCI artifacts
  - Common pattern: Dockerfile + docker-compose.yml + devcontainer.json

### Project Conventions
- `.github/instructions/python.instructions.md` - Python coding standards
- `.github/instructions/coding-best-practices.instructions.md` - General practices
- `.github/instructions/containerization-docker-best-practices.instructions.md` - Docker guidelines
- Project already uses multi-stage Docker builds extensively
- Modern Docker Compose (not docker-compose)
- Environment-based configuration via `env/` directory and `COMPOSE_FILE` variable

## Key Discoveries

### Current Development Environment Dependencies

#### Actual Development Setup
The project is developed using:
- **Mac host** running VSCode UI
- **Remote-SSH extension** connecting to Linux VM
- **Linux VM** where actual development occurs
- **Docker Compose** running all services in containers

```
Mac (VSCode UI) → Remote-SSH → Linux VM → docker compose up
                               ↓
                               Python, uv, Node.js (uncontrolled versions)
```

#### Linux VM Requirements
1. **Docker + Docker Compose**: For all services
   - All application services run in containers
   - Infrastructure services (postgres, rabbitmq, redis) in containers
   - Source code mounted as volumes for hot-reload
2. **Python 3.11+**: Installed on VM (version varies)
   - Used by VSCode Python extension
   - Not used to run services (services run in containers)
3. **uv**: Installed on VM (version varies)
   - Available in terminal for ad-hoc tasks
   - Not used to run services (services run in containers)
4. **Node.js + npm**: Installed on VM
   - Used by VSCode extensions
   - Not used to run services (frontend runs in container)
5. **Development Tools**: Installed on VM
   - pytest, ruff, mypy for VSCode integrations
   - Versions may not match project requirements

#### Current Workflow Pattern
```bash
# Primary development workflow - ALL services in containers
docker compose up

# All services start with hot-reload:
# - api (FastAPI with uvicorn --reload)
# - bot (Discord bot)
# - notification-daemon, status-transition-daemon
# - frontend (Vite dev server)
# - postgres, rabbitmq, redis, grafana-alloy

# Code changes reflected instantly via volume mounts
# Edit files in VSCode → Changes appear in containers → Services auto-reload
```

**Key Issue**: VM tools (Python, uv, Node.js) are uncontrolled - versions may drift from project requirements, conflict with other projects, or differ from CI/CD environment.

### VSCode Dev Containers Overview

#### What They Provide
A dev container is a full-featured development environment that runs inside a Docker container, configured via `.devcontainer/devcontainer.json`. Key capabilities:

1. **Isolated Environment**: Complete development toolchain in container
2. **Reproducible Setup**: Same environment for all developers
3. **Extension Support**: VSCode extensions run inside container
4. **Terminal Integration**: All terminal commands execute in container
5. **Git Integration**: Credentials can be shared with container
6. **Port Forwarding**: Automatic forwarding of application ports
7. **Debugging**: Full debugging support with breakpoints
8. **IntelliSense**: Language server runs in container with full context

#### How They Work (For Your Remote-SSH Setup)
```
┌──────────────────────────────────────────────────────────┐
│  Mac (Host)                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  VSCode UI                                         │  │
│  │  (Editor, File Browser, Git UI)                    │  │
│  └────────────────────────────────────────────────────┘  │
│            │                                              │
│            │ SSH Connection (already using this)         │
│            ▼                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Linux VM                                          │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │  Dev Container                               │ │  │
│  │  │  ┌────────────────────────────────────────┐ │ │  │
│  │  │  │ Controlled Development Environment     │ │ │  │
│  │  │  │ - Python 3.13 (project-specified)      │ │ │  │
│  │  │  │ - uv (project-specified version)       │ │ │  │
│  │  │  │ - pytest, ruff, mypy (exact versions)  │ │ │  │
│  │  │  │ - Source code (mounted from VM)        │ │ │  │
│  │  │  │ - VSCode Server                        │ │ │  │
│  │  │  │ - Workspace Extensions                 │ │ │  │
│  │  │  └────────────────────────────────────────┘ │ │  │
│  │  │  Docker CLI (talks to VM's Docker daemon) │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │  Application Containers (sibling)            │ │  │
│  │  │  - postgres, rabbitmq, redis                 │ │  │
│  │  │  - api, bot, daemons, frontend               │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │  Docker Daemon (VM native - fast!)               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Dev Container Configuration Options

#### Option 1: Dockerfile-based Dev Container
Create `.devcontainer/devcontainer.json` that builds from existing Dockerfile:

```json
{
  "name": "Game Scheduler Dev",
  "build": {
    "dockerfile": "../docker/api.Dockerfile",
    "target": "development",
    "context": ".."
  },
  "workspaceFolder": "/app",
  "forwardPorts": [8000, 5432, 5672, 15672, 6379],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-azuretools.vscode-docker"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.linting.enabled": true,
        "python.linting.ruffEnabled": true
      }
    }
  }
}
```

#### Option 2: Docker Compose-based Dev Container
Leverage existing `docker-compose.yml` infrastructure:

```json
{
  "name": "Game Scheduler Dev",
  "dockerComposeFile": ["../compose.yaml", "../compose.override.yaml"],
  "service": "api",
  "workspaceFolder": "/app",
  "forwardPorts": [8000],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff"
      ]
    }
  }
}
```

#### Option 3: Pre-built Image with Features
Use Microsoft's official Python dev container image with additional features:

```json
{
  "name": "Game Scheduler Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.13",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/node:1": {"version": "22"}
  },
  "postCreateCommand": "uv pip install --system -e .",
  "forwardPorts": [8000, 5432, 5672, 15672, 6379],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "charliermarsh.ruff",
        "ms-azuretools.vscode-docker"
      ]
    }
  }
}
```

### Complete Example Configuration

Based on your current setup, here's a complete dev container configuration:

`.devcontainer/devcontainer.json`:
```json
{
  "name": "Game Scheduler",
  "dockerComposeFile": [
    "../compose.yaml",
    "../compose.override.yaml",
    "docker-compose.extend.yml"
  ],
  "service": "api",
  "workspaceFolder": "/app",
  "shutdownAction": "stopCompose",
  
  "forwardPorts": [
    8000,  // API
    3000,  // Frontend
    5432,  // PostgreSQL
    5672,  // RabbitMQ
    15672, // RabbitMQ Management
    6379,  // Redis
    12345  // Grafana Alloy
  ],
  
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {},
    "ghcr.io/devcontainers/features/git:1": {}
  },
  
  "customizations": {
    "vscode": {
      "extensions": [
        // Python
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        
        // Docker
        "ms-azuretools.vscode-docker",
        
        // Testing
        "littlefoxteam.vscode-python-test-adapter",
        
        // Git
        "eamodio.gitlens",
        
        // Markdown
        "yzhang.markdown-all-in-one",
        
        // YAML
        "redhat.vscode-yaml"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.linting.enabled": true,
        "python.linting.ruffEnabled": true,
        "python.formatting.provider": "none",
        "[python]": {
          "editor.defaultFormatter": "charliermarsh.ruff",
          "editor.formatOnSave": true,
          "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
          }
        },
        "ruff.importStrategy": "fromEnvironment"
      }
    }
  },
  
  "remoteEnv": {
    "DATABASE_URL": "postgresql+asyncpg://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    "RABBITMQ_URL": "amqp://gamebot:dev_password_change_in_prod@rabbitmq:5672/",
    "REDIS_URL": "redis://redis:6379/0",
    "PYTHONUNBUFFERED": "1",
    "LOG_LEVEL": "DEBUG"
  },
  
  "postCreateCommand": "chmod -R o+r shared/ services/ frontend/",
  "postStartCommand": "echo 'Dev container ready. Run: python -m services.api.main'"
}
```

`.devcontainer/docker-compose.extend.yml`:
```yaml
# Extensions to compose.override.yaml for dev container
services:
  api:
    # Ensure container stays running for dev container to attach
    command: sleep infinity
```

## Tradeoffs Analysis

### Benefits of Adopting Dev Containers

#### 1. **Consistent Development Environment**
- **Pro**: Every developer gets identical toolchain (Python version, uv, all dependencies)
- **Pro**: New developers onboard instantly - one "Reopen in Container" command
- **Pro**: Eliminates "works on my machine" issues
- **Current**: Requires manual installation of Python 3.11+, uv, and all dev tools

#### 2. **Simplified Setup**
- **Pro**: Single command to get fully working environment
- **Pro**: No need to install Python, uv, or dev tools on local machine
- **Pro**: Automatic extension installation (ruff, pytest, Python language server)
- **Current**: Multi-step setup (install Python, install uv, install dependencies, configure extensions)

#### 3. **Isolation**
- **Pro**: Development tools don't pollute local machine
- **Pro**: Multiple Python versions for different projects without conflicts
- **Pro**: Easy to reset/rebuild if environment gets corrupted
- **Current**: System Python/uv installation shared across projects

#### 4. **Integrated Development Experience**
- **Pro**: Terminal, debugging, testing all "just work" inside container
- **Pro**: IntelliSense has full context of installed packages
- **Pro**: Git integration seamless (credentials shared)
- **Current**: Already works well for local development

#### 5. **Team Productivity**
- **Pro**: Standardized tooling means consistent formatting, linting, test results
- **Pro**: Pre-commit hooks work identically for everyone
- **Pro**: CI/CD environment matches dev environment more closely
- **Current**: Variations in local tool versions can cause inconsistencies

#### 6. **Infrastructure Integration**
- **Pro**: Database, Redis, RabbitMQ always running and available
- **Pro**: Can test full stack without manual service startup
- **Pro**: Port forwarding handled automatically
- **Current**: Need to remember `docker compose up -d postgres rabbitmq redis`

### Drawbacks and Considerations

#### 1. **Performance Impact**
- **Pro for your setup**: Linux VM runs Docker natively - no virtualization penalty!
  - Mac Docker Desktop has slow volume mounts (2-10x slower)
  - Your Linux VM has native Docker performance
  - File operations at near-native speed
- **Con**: Increased memory usage (container + VSCode server)
  - Typically 200-500MB additional RAM
  - But VM likely has plenty of RAM available
- **Current**: Already using VM, so no performance change expected

#### 2. **Learning Curve**
- **Con**: Team needs to understand dev container concepts
- **Con**: Troubleshooting issues requires Docker knowledge
- **Con**: Some operations (rebuilding) take time initially
- **Current**: Standard development workflow familiar to team

#### 3. **Tool Limitations**
- **Con**: Some VSCode extensions don't work in containers
  - Most do, but occasional incompatibilities
- **Con**: Debugger configuration may need adjustments
- **Con**: Cannot use system clipboard managers in some cases
- **Current**: All local tools work as expected

#### 4. **Workflow Changes**
- **Con**: "Rebuild Container" required for dependency changes
  - Takes 30-60 seconds depending on changes
  - More disruptive than `uv pip install`
- **Con**: Cannot easily run services outside container
- **Con**: May need to adjust CI/CD if it assumes local tools
- **Current**: Quick iteration with `uv pip install` and restart

#### 5. **Resource Requirements**
- **Con**: Docker Desktop required (licensing considerations for large orgs)
- **Con**: Sufficient RAM needed (8GB minimum, 16GB recommended)
- **Con**: Disk space for images (2-3GB per project)
- **Current**: Minimal resource overhead beyond application requirements

#### 6. **Network Complexity**
- **Con**: Port conflicts if multiple dev containers running
- **Con**: VPN/proxy configurations can be tricky
- **Con**: Host networking not available on all platforms
- **Current**: Direct network access, simpler configuration

#### 7. **Platform Differences**
- **Pro for your setup**: Linux VM = native Docker, no Desktop virtualization
- **Pro**: Already have Docker running on Linux VM
- **Neutral**: ARM64 vs AMD64 handled by your multi-arch builds
- **Current**: Already using Linux Docker (best performance option)

### Specific Considerations for Your Project

#### Your Unique Context: Remote-SSH Development

You're already using a **layered remote development setup**:
1. Mac runs VSCode UI
2. Remote-SSH connects to Linux VM
3. Extensions and terminal run on VM
4. All services run via `docker compose up`

**The Problem**: VM has uncontrolled tool versions (Python, uv, Node.js) that may:
- Drift from project requirements
- Conflict between multiple projects
- Differ from CI/CD environment
- Require manual setup on new VMs

#### What You'd Gain

1. **Tool isolation and control**: Each project gets exact Python/uv/Node.js versions
2. **VM simplification**: VM only needs Docker + SSH, no Python/Node.js/uv installation
3. **Multi-project safety**: Different projects with conflicting requirements work side-by-side
4. **Perfect CI/CD alignment**: Dev and CI use identical tool versions
5. **Native Linux performance**: No Mac virtualization overhead - VM runs Docker natively
6. **Familiar pattern**: Already using Remote-SSH, dev containers work the same way
7. **Quick VM setup**: New VM = install Docker, clone repo, reopen in container
8. **Extension reliability**: Python/TypeScript extensions work with exact project dependencies

#### What You'd Lose

1. **Minimal actually**: You already run everything via `docker compose up`
2. **One extra layer**: Mac → SSH → VM → Container (but Remote-SSH already has two layers)
3. **Container overhead**: But Linux Docker is very lightweight compared to Mac Docker Desktop
4. **Learning curve**: Need to understand dev container concepts (but similar to Remote-SSH)

### Hybrid Approach (Recommended)

You don't have to choose all-or-nothing. Consider a hybrid:

#### Option A: Dev Container Optional
- Provide `.devcontainer/` configuration for those who want it
- Document both approaches in README
- Keep local development workflow as primary
- Use dev containers for CI/CD consistency testing

#### Option B: Infrastructure in Container, Services Local
- Use dev container only for consistent toolchain (Python, uv, extensions)
- Run infrastructure services (postgres, rabbitmq, redis) via Docker Compose
- Run application services locally with `uv run` for fast iteration
- This is close to your current setup but with standardized tooling

#### Option C: Service-Specific Dev Containers
- Create dev container for API development
- Separate dev container for bot development
- Keep frontend development local (Node.js tooling simpler)
- Allows focused environments per service

## Recommended Approach for Your Project

### Analysis

Your project is well-positioned for dev containers but has a smooth local workflow. The key question is: **What problem are you trying to solve?**

#### If Problem Is: Team Onboarding
**Recommendation**: Adopt dev containers
- Eliminates setup friction for new contributors
- Guarantees consistent environment
- Worth the performance tradeoff

#### If Problem Is: Tool Version Conflicts
**Recommendation**: Adopt dev containers
- Python version consistency
- uv version consistency
- Extension standardization

#### If Problem Is: "Works on My Machine"
**Recommendation**: Adopt dev containers
- Identical dependencies
- Same database/infrastructure versions
- Consistent test results

#### If Problem Is: CI/CD Alignment
**Recommendation**: Adopt dev containers
- Dev environment matches CI
- Pre-building images speeds up CI
- Easier to reproduce CI failures locally

#### If Problem Is: Development Speed
**Recommendation**: Keep local development
- Native performance
- Fast tool iterations
- Minimal overhead

### Suggested Implementation Path

If you decide to adopt dev containers, here's a phased approach:

#### Phase 1: Add Optional Dev Container (Low Risk)
1. Create `.devcontainer/devcontainer.json` using Docker Compose approach
2. Document both dev container and local workflows
3. Let interested developers opt-in
4. Gather feedback on performance and workflow

**Implementation**:
```bash
mkdir .devcontainer
# Create devcontainer.json (example provided above)
# Create docker-compose.extend.yml (minimal extensions)
# Update .gitignore if needed
# Document in README.md
```

**Time Investment**: 2-4 hours initial setup + documentation

#### Phase 2: Optimize Configuration (If Adopted)
1. Add pre-build configuration for faster startup
2. Configure named volumes for performance
3. Add lifecycle scripts (postCreateCommand, postStartCommand)
4. Fine-tune extension list
5. Create service-specific dev container variants

**Time Investment**: 4-8 hours refinement

#### Phase 3: Make Primary Workflow (If Successful)
1. Update README to feature dev container setup first
2. Add CI workflow to build/test dev container
3. Create pre-built images for faster startup
4. Remove local development instructions (or move to appendix)

**Time Investment**: 4-8 hours CI/CD + documentation

### Concrete Recommendation
### Concrete Recommendation

Based on your **specific setup** (Mac → Remote-SSH → Linux VM → uncontrolled VM tools):

**STRONGLY RECOMMEND adopting dev containers** because:

✅ **Solves your stated problem**: "dependent on (mostly uncontrolled) binaries in the linux vm"
✅ **Perfect fit for Remote-SSH workflow**: Already familiar with remote development pattern
✅ **Native Linux performance**: No Mac Docker Desktop performance penalty
✅ **Minimal workflow disruption**: Still `docker compose up`, just from inside controlled container
✅ **VM simplification**: Can remove Python/uv/Node.js from VM entirely
✅ **Multi-project isolation**: Different projects won't conflict on tool versions
✅ **CI/CD alignment**: Dev and CI use exact same tool versions

**Why this is different from typical Mac dev**:
- You're **already remote** (Remote-SSH to VM)
- You're **already on Linux** (native Docker performance)
- You **already run everything in Docker** (`docker compose up`)
- You have a **real pain point** (uncontrolled VM tools)

For most Mac users doing local development, dev containers add complexity and performance overhead.
**For your setup, dev containers solve a real problem with minimal downside.**
### Implementation Recommendation for Your Setup

**Adopt dev containers as primary workflow** with this phased approach:

#### Phase 1: Create and Test (1-2 hours)
1. Create `.devcontainer/devcontainer.json` (Docker Compose based)
2. In VSCode (already connected via Remote-SSH to VM)
3. Command Palette → "Dev Containers: Reopen in Container"
4. VSCode rebuilds connection: Mac → SSH → VM → Container
5. Test: `docker compose up` should work identically
6. Verify: Extensions work, terminal in container, hot-reload works

Your workflow changes minimally:
```bash
# Before: Mac VSCode → Remote-SSH → VM
code --remote ssh-host ~/src/game-scheduler
docker compose up  # (runs on VM)

# After: Mac VSCode → Remote-SSH → VM → Container  
code --remote ssh-host ~/src/game-scheduler
# VSCode prompts: "Reopen in Container?" → Yes
docker compose up  # (runs from container, controls VM Docker)
```

#### Phase 2: Validate Benefits (1-2 weeks)
1. Verify tool versions match project requirements exactly
2. Test that CI/CD and dev use identical Python/uv versions
3. Confirm extensions (Pylance, Ruff) work better with exact dependencies
4. Check that `docker buildx bake --push` works from container

#### Phase 3: Clean Up VM (if successful)
1. Remove Python from VM (container provides it)
2. Remove uv from VM (container provides it)  
3. Remove Node.js from VM (container provides it)
4. VM becomes minimal: Docker + SSH only

#### Phase 4: Apply to Other Projects
Once validated on this project, replicate to other projects on same VM for consistent multi-project development.

## Implementation Guidance

If you decide to implement optional dev container support:

### Files to Create

1. `.devcontainer/devcontainer.json` - Main configuration
2. `.devcontainer/docker-compose.extend.yml` - Dev container specific overrides
3. `.devcontainer/README.md` - Dev container specific documentation

### Files to Modify

1. `README.md` - Add dev container setup instructions
2. `.gitignore` - May need adjustments for dev container specifics
3. `.github/workflows/*.yml` - Consider adding dev container CI validation

### Configuration Template

See "Complete Example Configuration" section above for full `devcontainer.json`.

Key decisions to make:
- **Which service to use as primary**: api, bot, or separate configs?
- **Extension list**: Start minimal, add based on team feedback
- **Port forwarding**: All or just application ports?
- **Features**: Docker-in-docker needed? Git feature?
- **Post-create commands**: Dependency installation? Database setup?

### Testing Your Implementation

```bash
# 1. Create .devcontainer/devcontainer.json

# 2. In VSCode, Command Palette (F1)
#    -> "Dev Containers: Reopen in Container"

# 3. Wait for container build and startup

# 4. Open integrated terminal (should be inside container)
$ python --version  # Should be 3.13 or specified version
$ uv --version      # Should be installed
$ which python      # Should be /usr/local/bin/python or similar

# 5. Test service startup
$ python -m services.api.main
# Should start and connect to postgres/rabbitmq/redis

# 6. Test port forwarding
# Visit http://localhost:8000/docs in browser
# Should see API documentation

# 7. Test hot-reload
# Edit a Python file
# Service should detect change and reload

# 8. Test debugging
# Set breakpoint in VSCode
# Hit API endpoint
# Debugger should pause at breakpoint
```

### Performance Optimization Tips

If you adopt dev containers and experience performance issues:

1. **Use named volumes for generated files**:
   ```json
   "mounts": [
     "source=game-scheduler-venv,target=/home/appuser/.cache,type=volume"
   ]
   ```

2. **Enable file system caching** (macOS/Windows):
   ```yaml
   volumes:
     - ./services:/app/services:cached
   ```

3. **Use consistent-read mounts** for read-only:
   ```yaml
   volumes:
     - ./services:/app/services:ro,consistent
   ```

4. **Exclude unnecessary files**:
   ```
   # .dockerignore
   **/__pycache__
   **/.pytest_cache
   **/.mypy_cache
   **/.ruff_cache
   **/node_modules
   ```

5. **Consider Docker Desktop alternatives**:
   - Rancher Desktop (free, no licensing issues)
   - Podman Desktop (daemonless, rootless)
   - OrbStack (macOS, faster than Docker Desktop)

## Summary
## Summary

### Current State
- **Development environment**: Mac → Remote-SSH → Linux VM → uncontrolled tools
- **VM tools**: Python, uv, Node.js installed but versions may drift
- **Workflow**: `docker compose up` runs all services in containers with hot-reload
- **Problem**: VM tool versions uncontrolled, may conflict, differ from CI/CD
- **No dev container configuration** exists currently

### What Dev Containers Provide For Your Setup
- **Tool isolation**: Each project gets exact Python/uv/Node.js versions in container
- **VM simplification**: VM only needs Docker + SSH, no language runtimes
- **Native performance**: Linux VM runs Docker natively (no Mac Desktop overhead)
- **Multi-project safety**: No tool version conflicts between projects
- **CI/CD alignment**: Dev environment exactly matches GitHub Actions
- **Familiar pattern**: Works like Remote-SSH (already using this)

### What Dev Containers Cost For Your Setup
- **Minimal disruption**: Still `docker compose up`, just from inside container
- **Small learning curve**: Similar to Remote-SSH concept (already familiar)
- **Extra layer**: Mac → SSH → VM → Container (but only one more than current)
- **Container overhead**: ~200-500MB RAM (VM likely has plenty)

### Recommendation for Your Specific Setup
**ADOPT dev containers as primary workflow**:
- ✅ Solves real problem: uncontrolled VM binaries
- ✅ Perfect fit: Already using Remote-SSH to Linux VM
- ✅ No performance penalty: Linux Docker is native
- ✅ Minimal workflow change: Still `docker compose up`
- ✅ Enables VM cleanup: Remove Python/uv/Node.js from VM
- ✅ Multi-project benefit: Isolated environments per project

This is a **strong recommendation** specifically because:
1. You have a stated pain point (uncontrolled VM tools)
2. You're already remote (familiar pattern)
3. You're on Linux (native Docker performance)
4. You already containerize everything (natural extension)

### Next Steps
1. Create `.devcontainer/devcontainer.json` with Docker Compose configuration
2. In VSCode (connected to VM): "Reopen in Container"
3. Verify `docker compose up` works identically
4. Validate tool versions match project requirements
5. Document the setup in README.md
6. After validation, remove unneeded tools from VM
