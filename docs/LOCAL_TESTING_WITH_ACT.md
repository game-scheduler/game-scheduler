# Local GitHub Actions Testing with nektos/act

## Overview

This project uses [nektos/act](https://nektosact.com/) to run GitHub Actions workflows locally. This enables faster iteration on CI/CD changes without pushing to GitHub and waiting for remote runners.

### Benefits

- **Faster feedback loop**: Test workflow changes in seconds, not minutes
- **Cost savings**: Reduce GitHub Actions minutes usage
- **Offline development**: Work on workflows without internet connectivity
- **Easier debugging**: Direct access to containers and logs
- **Pre-commit validation**: Catch issues before pushing to GitHub

## Prerequisites

- Docker installed and running
- Docker socket accessible (`/var/run/docker.sock`)
- `act` binary installed (included in dev container)
- Sufficient disk space (~500MB for Docker images)

## Initial Setup

### 1. Configure Secrets

Copy the secrets template and fill in your values:

```bash
cp .secrets.example .secrets
```

Edit `.secrets` and replace placeholders:

```
GITHUB_TOKEN=your_actual_github_token_here
CODECOV_TOKEN=your_actual_codecov_token_here
```

**Note**: `.secrets` is gitignored and will not be committed.

### 2. Configure Environment Variables

Copy the environment template (optional, has sensible defaults):

```bash
cp .env.act.example .env.act
```

The default values match the service container names used in CI:

```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/test_db
REDIS_URL=redis://redis:6379
RABBITMQ_URL=amqp://test:test@rabbitmq:5672/
```

**Note**: `.env.act` is gitignored and will not be committed.

## Usage

### List Available Workflows and Jobs

See all workflows and jobs that can be run:

```bash
act -l
```

This shows the CI/CD pipeline jobs:
- `unit-tests` - Run unit tests (multiple Python versions)
- `integration-tests` - Run integration tests with service containers
- `e2e-tests` - Run end-to-end tests
- `build` - Build Docker images
- `deploy-*` - Deployment jobs (staging, production)

### Run Specific Jobs

#### Unit Tests

Run unit tests (fastest, no external services):

```bash
act -j unit-tests
```

This runs the unit test suite across all Python versions defined in the matrix.

#### Integration Tests

Run integration tests (requires service containers):

```bash
act -j integration-tests
```

This starts PostgreSQL, Redis, and RabbitMQ containers, runs database migrations, and executes integration tests.

#### End-to-End Tests

Run full end-to-end tests:

```bash
act -j e2e-tests
```

### Run Specific Events

Run all jobs triggered by a push event:

```bash
act push
```

Run all jobs triggered by a pull request:

```bash
act pull_request
```

### Run with Specific Matrix Values

Test a specific Python version:

```bash
act -j unit-tests --matrix python-version:3.11
```

### Dry Run

See what would run without actually executing:

```bash
act -j unit-tests -n
```

### Verbose Output

Enable detailed logging for troubleshooting:

```bash
act -j unit-tests -v
```

## Configuration

Project-level configuration is stored in `.actrc`:

- **Docker image**: Uses `catthehacker/ubuntu:act-latest` (medium size)
- **Offline mode**: Caches actions and images for faster iteration
- **Container reuse**: Reuses containers between runs for speed (note: may conflict with matrix jobs)
- **Bind mount**: Mounts workspace directly for immediate file access
- **Artifacts**: Stores artifacts in `.artifacts/` directory

### Path Consistency Approach

This project uses a **path consistency approach** for Docker-in-Docker scenarios (act running inside a dev container):

1. **Dev Container Configuration**: The dev container workspace path matches the host path exactly using `${localWorkspaceFolder}` in `.devcontainer/devcontainer.json`
2. **Act Configuration**: Act uses the default current directory (no `--directory` flag needed)
3. **Nested Bind Mounts**: Workflows can create their own bind mounts (e.g., for integration test services) and the host Docker daemon correctly resolves the paths

This approach eliminates the need for special workarounds like:
- Environment variables for path translation (`HOST_WORKSPACE_FOLDER`)
- Symlinks to map container paths to host paths
- Custom `--directory` flags in act configuration

**Benefits**:
- Simpler configuration with fewer special cases
- Nested containers can bind mount workspace paths correctly
- Integration tests with service containers work seamlessly
- No path translation needed between layers

## Troubleshooting

### Docker Socket Permission Denied

Ensure Docker socket is accessible:

```bash
ls -la /var/run/docker.sock
```

If needed, add your user to the `docker` group:

```bash
sudo usermod -aG docker $USER
```

Then log out and back in.

### Workflow Fails with "command not found"

The workflow may require tools not present in the act Docker image. Options:

1. Use a larger image: Edit `.actrc` and change to `catthehacker/ubuntu:full-latest`
2. Install tools in workflow: Add installation steps to the workflow
3. Use a custom Docker image with required tools pre-installed

### Service Containers Not Starting

Check that services are defined correctly in the workflow. Act supports the same service container syntax as GitHub Actions.

View service logs:

```bash
docker logs <container_name>
```

### Act Image Pull Fails

If offline or behind a firewall, pre-pull the image:

```bash
docker pull catthehacker/ubuntu:act-latest
```

### Secrets Not Available

Ensure `.secrets` file exists and is formatted correctly:

```bash
cat .secrets
```

Format should be `KEY=value` with one secret per line.

### Environment Variables Not Working

Ensure `.env.act` file exists if referenced in `.actrc`:

```bash
cat .env.act
```

Or remove `--env-file=.env.act` from `.actrc` if not needed.

### "chdir to cwd failed" Errors

If you see errors like "chdir to cwd: failed: no such file or directory", this is typically caused by:

1. **Root-owned files in workspace**: Previous act runs may have created root-owned files that interfere with Docker exec operations
   - **Solution**: Clean up and restart: `docker system prune -a`, then rebuild dev container

2. **Matrix jobs with container reuse**: The `--reuse` flag can cause issues with matrix strategies creating multiple containers
   - **Solution**: Remove matrix strategies from workflows or don't use `--reuse` with matrix jobs

### Port Conflicts with Service Containers

Integration tests may fail if service containers can't bind to required ports:

```bash
docker ps -a | grep -E 'postgres|redis|rabbitmq'
```

Stop and remove conflicting containers:

```bash
docker stop <container_id>
docker rm <container_id>
```

Or clean up all stopped containers:

```bash
docker container prune -f
```

## Performance Tips

### Container Reuse

The `--reuse` flag (enabled in `.actrc`) keeps containers running between executions, significantly speeding up subsequent runs.

**Note**: Container reuse can cause issues with matrix strategy jobs (jobs that run multiple times with different parameters). If you experience container naming conflicts or reuse problems, either:
- Remove the `--reuse` flag from `.actrc` temporarily
- Simplify workflows to avoid matrix strategies during local testing

### Offline Mode

The `--action-offline-mode` flag (enabled in `.actrc`) uses cached actions instead of pulling fresh copies on every run.

### Bind Mounting

The `--bind` flag (enabled in `.actrc`) mounts the workspace directly instead of copying, making file changes immediately available.

### Artifacts

Artifacts are stored locally in `.artifacts/` directory. This avoids the overhead of uploading to GitHub's artifact storage.

## Limitations

### Differences from GitHub Actions

Act runs workflows in Docker containers on your local machine, which has some differences from GitHub's hosted runners:

- **Hardware**: Different CPU, memory, and disk performance
- **Services**: Service containers use local Docker networking
- **Secrets**: Loaded from local `.secrets` file, not GitHub Secrets
- **Permissions**: May differ based on local Docker configuration
- **External services**: Can't access GitHub-hosted resources without proper tokens

### Unsupported Features

Some GitHub Actions features are not supported or work differently:

- Artifacts upload/download (stored locally instead)
- OIDC token generation
- GitHub environment protection rules
- Some GitHub context variables

## Best Practices

### Test Before Pushing

Run workflows locally before committing changes:

```bash
act -j unit-tests -j integration-tests
```

This catches syntax errors and common issues early.

### Use Dry Run for Quick Validation

Validate workflow syntax without full execution:

```bash
act -n
```

### Clean Up Periodically

Remove old containers and images to free disk space:

```bash
docker system prune -a
```

### Keep Secrets Secure

Never commit `.secrets` or `.env.act` files. They are gitignored, but double-check before committing.

## Further Reading

- [nektos/act Documentation](https://nektosact.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Act GitHub Repository](https://github.com/nektos/act)

## Support

If you encounter issues not covered in this documentation:

1. Check the [act troubleshooting guide](https://nektosact.com/usage/index.html#troubleshooting)
2. Review [act GitHub issues](https://github.com/nektos/act/issues)
3. Ask the team in the project chat/channel
