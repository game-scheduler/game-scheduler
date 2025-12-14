<!-- markdownlint-disable-file -->
# Task Research Notes: Local GitHub Actions Testing with nektos/act

## Research Executed

### External Research
- #fetch:https://github.com/nektos/act
  - Official repository for nektos/act
  - Latest version: v0.2.83 (released 2 weeks ago)
  - 67.6k stars, actively maintained
  - MIT licensed
- #fetch:https://nektosact.com/installation/index.html
  - Official installation documentation
  - Multiple installation methods available
- #fetch:https://nektosact.com/usage/index.html
  - Comprehensive usage documentation
  - Configuration and workflow execution patterns
- #githubRepo:"nektos/act installation configuration docker setup"
  - Implementation patterns and examples
  - Docker container integration methods
  - Configuration file formats

### Project Analysis
- Current CI/CD workflow: `.github/workflows/ci-cd.yml`
  - Unit tests (Python 3.11, 3.12)
  - Integration tests with PostgreSQL, Redis, RabbitMQ services
  - Linting with ruff and mypy
  - Frontend tests with Node.js
  - Docker image building and publishing
- Environment: Debian GNU/Linux 13 (trixie) in dev container
- Docker available: version 29.1.3
- Sufficient disk space: 417G available

## Key Discoveries

### What is nektos/act

nektos/act is a tool that allows you to run GitHub Actions locally using Docker. It reads workflows from `.github/workflows/` and executes them in containers that mirror the GitHub Actions environment.

**Core Benefits:**
- **Fast Feedback Loop**: Test workflow changes locally without committing/pushing
- **Cost Savings**: Reduce GitHub Actions minutes consumption
- **Offline Development**: Work on workflows without network connectivity (with cached images)
- **Local Task Runner**: Use GitHub Actions as a Make replacement

### Installation Methods

#### 1. Dockerfile Installation (Recommended for Build Containers)
Add to your Dockerfile to install the latest version:

```dockerfile
# Install nektos/act for local GitHub Actions testing
ARG ACT_VERSION=0.2.83
RUN curl -L "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_x86_64.tar.gz" \
    | tar xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/act
```

**Benefits:**
- Consistent version across all development environments
- No manual installation needed by developers
- Version controlled via Dockerfile
- Works in CI/CD pipelines

**Best Practices:**
- Use ARG for version to make updates easy
- Pin to specific version for reproducibility
- Verify checksum for security (optional but recommended)
- Install early in Dockerfile for layer caching

**With Checksum Verification:**
```dockerfile
# Install nektos/act with checksum verification
ARG ACT_VERSION=0.2.83
ARG ACT_CHECKSUM=ed37d29fc117b3075cf586bb9323ec6c16320a5a3c5c0df9f1859d271d303f0d
RUN curl -L "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_x86_64.tar.gz" -o /tmp/act.tar.gz \
    && echo "${ACT_CHECKSUM}  /tmp/act.tar.gz" | sha256sum -c - \
    && tar xzf /tmp/act.tar.gz -C /usr/local/bin/ \
    && rm /tmp/act.tar.gz \
    && chmod +x /usr/local/bin/act
```

#### 2. Bash Script (Standalone Linux Installation)
```bash
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

This installs the latest release to `/usr/local/bin/act`.

#### 3. Manual Download
Download pre-built binaries from: https://github.com/nektos/act/releases/latest

For Linux x86_64:
```bash
cd /tmp
wget https://github.com/nektos/act/releases/latest/download/act_Linux_x86_64.tar.gz
tar xzf act_Linux_x86_64.tar.gz
sudo mv act /usr/local/bin/
chmod +x /usr/local/bin/act
```

#### 4. Build from Source
```bash
git clone https://github.com/nektos/act.git
cd act/
make build
# OR
go build -ldflags "-X main.version=$(git describe --tags --dirty --always | sed -e 's/^v//')" -o dist/local/act main.go
```

### Prerequisites

**Required:**
- Docker Engine API compatible host (Docker Desktop, Docker Engine)
- Sufficient disk space for images (varies by image size choice)

**Operating Systems:**
- Linux: Install Docker Engine
- macOS: Install Docker Desktop
- Windows: Install Docker Desktop

**Important Notes:**
- Podman is not officially supported (may work but not guaranteed)
- Docker daemon must be running
- User must have Docker permissions

### Running Act Inside a Container

When installing act in a Docker container (like the test.Dockerfile approach), there are important considerations:

**Docker Socket Access:**
Act needs access to the Docker daemon to spawn test containers. You must mount the Docker socket:

```bash
# Using docker compose
docker compose run --rm -v /var/run/docker.sock:/var/run/docker.sock test bash

# Or add to compose file
services:
  test:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

**Volume Mounting:**
The workspace needs to be available to containers spawned by act:

```bash
# Ensure workspace is mounted and bind option is used
act --bind
```

**Network Considerations:**
- Service containers spawned by act will be in their own network
- They can communicate with each other via service names
- Host network may be needed for some scenarios: `act --container-daemon-socket=-`

**Permissions:**
The container user needs permission to access Docker socket:

```dockerfile
# Add user to docker group (if using non-root user)
RUN addgroup --system docker || true \
    && usermod -aG docker testuser || true
```

**Alternative: Docker-in-Docker (DinD):**
If socket mounting is not feasible, use Docker-in-Docker, but this is more complex and resource-intensive.

### Docker Image Selection

On first run, act prompts for image size selection:

**Large Image (~17GB download + 53.1GB storage)**
- Snapshots of GitHub Hosted Runners
- Most compatible with all actions
- Requires 75GB free disk space
- Image: `catthehacker/ubuntu:full-latest`

**Medium Image (~500MB)**
- Recommended for most users
- Includes necessary tools to bootstrap actions
- Compatible with most actions
- Image: `catthehacker/ubuntu:act-latest`

**Micro Image (<200MB)**
- Contains only NodeJS
- Doesn't work with all actions
- Minimal footprint
- Image: `node:16-bullseye-slim`

### Configuration File (.actrc)

Act reads configuration from `.actrc` files in order:
1. XDG spec location (`~/.config/act/actrc`)
2. Home directory (`~/.actrc`)
3. Current directory (`./.actrc`)

**Format:** One argument per line, no comments

```
--container-architecture=linux/amd64
--action-offline-mode
--secret-file=.secrets
--env-file=.env
--artifact-server-path=$PWD/.artifacts
```

### Basic Usage Commands

```bash
# Run default event (push) for all workflows
act

# Run specific event
act pull_request
act schedule
act workflow_dispatch

# List workflows for an event
act -l pull_request

# Run specific workflow
act -W '.github/workflows/ci-cd.yml'

# Run specific job
act -j 'unit-tests'

# Run with verbose logging
act -v

# Dry run to see what would execute
act -n

# Use specific Docker image
act -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

### Secrets Management

**Interactive (Secure):**
```bash
act -s MY_SECRET
# Prompts for secure input
```

**From Environment:**
```bash
act -s MY_SECRET=value
# OR check env variable
act -s MY_SECRET
```

**From File:**
```bash
act --secret-file .secrets
```

**Secrets File Format (.secrets):**
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
DOCKER_USERNAME=myuser
DOCKER_PASSWORD=mypass
DATABASE_URL=postgresql://localhost/db
```

### Environment Variables

**From File:**
```bash
act --env-file .env
```

**From Command Line:**
```bash
act --env KEY=value
```

**Special Variable:**
- `ACT=true` is automatically set in all act runs
- Use to skip steps: `if: ${{ !env.ACT }}`

### Working with Services

Act supports GitHub Actions services (like PostgreSQL, Redis, RabbitMQ). Services are automatically started as containers.

**Current Project Services:**
```yaml
services:
  postgres:
    image: postgres:17-alpine
  redis:
    image: redis:7.4-alpine
  rabbitmq:
    image: rabbitmq:4.2-management-alpine
```

Act will create a Docker network and start these service containers automatically.

### Common Options

```bash
# Bind working directory to job container
act --bind

# Reuse containers between runs (faster)
act --reuse

# Use privileged mode
act --privileged

# Specify container architecture
act --container-architecture=linux/amd64

# Enable artifact server
act --artifact-server-path $PWD/.artifacts

# Matrix filtering
act --matrix os:ubuntu-latest --matrix python-version:3.11

# Event payload file
act push -e event.json
```

### Action Offline Mode

Speeds up execution by using cached actions and images:

```bash
act --action-offline-mode
```

**Benefits:**
- Stops pulling existing images
- Works offline after first online run
- Avoids rate limits
- No unnecessary timeouts

### Debugging Workflows

```bash
# Verbose output
act -v

# Very verbose (includes Docker API calls)
act -vv

# Show secrets in logs (WARNING: insecure)
act --insecure-secrets

# Shell into container after failure
act --container-options "--rm=false"
# Then: docker exec -it <container-name> bash
```

### Complete Examples

#### Example 1: Run Unit Tests Locally
```bash
# Run just the unit-tests job
act -j unit-tests -s CODECOV_TOKEN
```

#### Example 2: Run Integration Tests with Services
```bash
# Run integration tests with all services
act -j integration-tests \
  --secret-file .secrets \
  --env-file .env
```

#### Example 3: Test Specific Workflow
```bash
# Test only the CI/CD workflow
act push -W .github/workflows/ci-cd.yml -v
```

#### Example 4: Offline Development
```bash
# After first run, work offline
act --action-offline-mode --reuse
```

### Project-Specific Configuration

For this project, create `.actrc`:

```
# Use medium image for balance
-P ubuntu-latest=catthehacker/ubuntu:act-latest

# Enable offline mode for faster iteration
--action-offline-mode

# Load secrets from file
--secret-file=.secrets

# Load environment from file
--env-file=.env

# Bind working directory
--bind

# Reuse containers
--reuse

# Enable artifacts
--artifact-server-path=$PWD/.artifacts
```

Create `.secrets` file:
```
GITHUB_TOKEN=<your-github-token>
CODECOV_TOKEN=<your-codecov-token>
```

Create `.env` file for test environment:
```
TESTING=true
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/test_db
REDIS_URL=redis://redis:6379
RABBITMQ_URL=amqp://test:test@rabbitmq:5672/
```

### Limitations and Considerations

**Known Limitations:**
1. Not all GitHub Actions features are supported
2. Some actions may behave differently than on GitHub
3. Service containers networking may differ slightly
4. GitHub-specific features (OIDC, environments) have limited support
5. Matrix strategies work but with some limitations

**Service Container Considerations:**
- Services use Docker networking
- Port mappings may differ from GitHub
- Health checks are supported
- Service discovery works via container names

**Performance Considerations:**
- First run downloads images (can be large)
- Subsequent runs are much faster with caching
- `--reuse` flag significantly speeds up iteration
- Offline mode eliminates network delays

### Troubleshooting

**Problem: Cannot pull Docker images**
```bash
# Check Docker daemon
docker ps

# Check network connectivity
docker pull ubuntu:latest

# Use offline mode after first successful run
act --action-offline-mode
```

**Problem: Services not connecting**
```bash
# Check service container logs
docker logs <service-container-name>

# Verify network
docker network ls
docker network inspect act-<workflow>-<job>
```

**Problem: Insufficient permissions**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

**Problem: Out of disk space**
```bash
# Clean up old containers and images
docker system prune -a

# Use smaller image size
act -P ubuntu-latest=node:16-bullseye-slim
```

## Recommended Approach

For this game-scheduler project using a build container, the recommended approach is:

1. **Add act to the test.Dockerfile** (consistent across all developers)
2. **Use medium-sized Docker image** (good balance of compatibility and size)
3. **Create `.actrc` configuration file** with common options
4. **Create `.secrets` file** for sensitive data (add to .gitignore)
5. **Create test-specific `.env` file** for environment variables
6. **Use `--reuse` and `--action-offline-mode`** for fast iteration

### Installation Steps

#### Step 1: Modify docker/test.Dockerfile

Add these lines after system dependencies installation:

```dockerfile
# Install nektos/act for local GitHub Actions testing
ARG ACT_VERSION=0.2.83
RUN curl -L "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_x86_64.tar.gz" \
    | tar xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/act
```

Full context for placement (after system dependencies, before uv installation):

```dockerfile
# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install nektos/act for local GitHub Actions testing
ARG ACT_VERSION=0.2.83
RUN curl -L "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_x86_64.tar.gz" \
    | tar xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/act

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv
```

#### Step 2: Configure act in the Container

```bash
# 1. Build the updated test container
docker compose build test

# 2. Run bash in the container
docker compose run --rm test bash

# 3. Inside the container, verify installation
act --version

# 4. Create .actrc configuration (in the container or mount from host)
cat > .actrc << 'CONFIG'
-P ubuntu-latest=catthehacker/ubuntu:act-latest
--action-offline-mode
--secret-file=.secrets
--env-file=.env.act
--bind
--reuse
--artifact-server-path=$PWD/.artifacts
CONFIG

# 5. Create secrets file (add to .gitignore!)
cat > .secrets << 'SECRETS'
GITHUB_TOKEN=<your-token>
CODECOV_TOKEN=<optional>
SECRETS

# 6. Create act-specific env file
cat > .env.act << 'ENVFILE'
TESTING=true
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/test_db
REDIS_URL=redis://redis:6379
RABBITMQ_URL=amqp://test:test@rabbitmq:5672/
ENVFILE

# 7. Add to .gitignore
echo ".secrets" >> .gitignore
echo ".env.act" >> .gitignore

# 8. First run (downloads images)
act -l

# 9. Run specific job
act -j unit-tests
```

### Usage Patterns

```bash
# Quick iteration on unit tests
act -j unit-tests

# Test integration with services
act -j integration-tests

# Test entire workflow
act push

# Test before pushing
act pull_request

# Dry run to verify
act -n -j unit-tests

# Debug failing step
act -j integration-tests -v
```

## Implementation Guidance

- **Objectives**: Enable local testing of GitHub Actions workflows to catch issues before pushing to GitHub
- **Key Tasks**:
  1. Modify `docker/test.Dockerfile` to install nektos/act binary
  2. Rebuild test container with act included
  3. Configure .actrc for project-specific settings
  4. Set up secrets and environment files
  5. Test workflow execution locally within container
  6. Document usage for team members
- **Dependencies**: 
  - Docker must be installed and running
  - Build container must have curl and tar available (already present in test.Dockerfile)
  - Docker socket must be accessible from container for act to spawn test containers
- **Success Criteria**:
  - `act` binary is available in test container at `/usr/local/bin/act`
  - Can run workflows locally with `act` command from inside container
  - Unit tests execute successfully via act
  - Integration tests run with service containers
  - Secrets and environment variables properly configured
  - Team can iterate on workflow changes without pushing to GitHub
  - Container image size increase is minimal (~7.5MB for act binary)
