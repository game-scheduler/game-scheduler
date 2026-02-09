# Development Setup

This guide covers setting up a complete development environment for Game Scheduler, including quick start, development workflow, code quality tools, and local testing.

## Development Container (Recommended)

The project includes a VS Code Dev Container with all tools pre-installed. This is the **recommended** development approach as it provides:

- **Pre-installed tools**: Python 3.13, uv, Node.js 24, Docker CLI, Git
- **Pre-configured**: All Python and frontend dependencies installed
- **Pre-commit hooks**: Automatically installed and ready to use
- **Consistent environment**: Same setup for all developers
- **VS Code integration**: Debugging, linting, and formatting configured

### Using the Dev Container

1. **Prerequisites**:
   - Docker and Docker Compose installed
   - Visual Studio Code with "Dev Containers" extension

2. **Open in container**:

   ```bash
   # Clone and open in VS Code
   git clone <repository-url>
   cd game-scheduler
   code .
   # VS Code will prompt to "Reopen in Container" - click it
   # Or use Command Palette: "Dev Containers: Reopen in Container"
   ```

3. **Automatic setup**:
   - Container builds with all dependencies
   - Pre-commit hooks installed automatically
   - Frontend dependencies installed
   - Ready to develop immediately!

4. **Start infrastructure**:

   ```bash
   # Inside dev container terminal
   docker compose up postgres redis rabbitmq -d
   ```

5. **Run services** (choose one):

   ```bash
   # Option A: Run in containers
   docker compose up api bot notification-daemon status-transition-daemon -d

   # Option B: Run locally in dev container for debugging
   cd services/api && uvicorn main:app --reload
   cd services/bot && python -m bot.main
   cd services/scheduler && python -m notification_daemon_wrapper
   ```

### Dev Container Features

The dev container includes:

- Python 3.13 with all project dependencies (including dev group)
- Node.js 24 with frontend dependencies
- Docker CLI for managing containers
- Git with SSH support
- `act` for local GitHub Actions testing
- Pre-commit hooks configured and installed
- VS Code extensions: Python, Pylance, Ruff, ESLint, Prettier

**All pre-commit hooks work immediately** - no need to run `uv sync` or `npm install` manually!

## Local Development (Without Container)

If you prefer to develop outside the container:

### Prerequisites

- Docker and Docker Compose installed
- Git installed
- Python 3.13+
- Node.js 18+
- `uv` for Python tooling: `pip install uv`

### Initial Setup

1. **Clone the repository**:

```bash
git clone <repository-url>
cd game-scheduler
```

2. **Verify development environment configuration**:

```bash
# Check that .env symlink points to development config
ls -la .env
# Should show: .env -> config/env/env.dev
```

The `.env` symlink is pre-configured to point to `config/env/env.dev`, which contains:

- `COMPOSE_FILE=compose.yaml:compose.override.yaml` - Loads development compose files
- Development-specific configuration (DEBUG logging, all ports exposed)

3. **Update Discord bot credentials** (if needed):

Edit `config/env/env.dev` and add your Discord bot token:

```bash
DISCORD_BOT_TOKEN=your-bot-token-here
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret
```

See [Deployment Guide](../deployment/README.md) for instructions on creating a Discord bot application and obtaining credentials.

4. **Start all services**:

```bash
docker compose up
```

That's it! The development environment will:

- Mount your source code as volumes (no rebuilds needed for code changes)
- Enable hot-reload for instant feedback
- Expose all service ports including management UIs
- Use development stages from Dockerfiles

## Development Environment

### How It Works

The development environment uses Docker Compose with volume mounts for instant code changes:

- **Python services** (API, bot, daemons): Source files mounted from `services/` and `shared/`
  - API uses `uvicorn --reload` for auto-restart on changes
  - Bot and daemons use `python -m` with watch mode

- **Frontend**: Source files mounted from `frontend/src/`
  - Vite dev server with hot module replacement (HMR)
  - Changes appear instantly in browser at http://localhost:3000

- **Infrastructure**: PostgreSQL, RabbitMQ, Redis, Grafana Alloy
  - Persistent data volumes for database and message broker
  - Management UIs exposed for debugging

### File Permissions

Source files must be **world-readable** for volume mounts to work in containers:

```bash
# If you encounter permission errors
chmod -R o+r shared/ services/ frontend/
```

Development containers run as non-root user (UID 1000) for security.

### Accessing Services

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Grafana**: http://localhost:3001 (admin/admin)

### Monitoring Logs

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f notification-daemon
docker compose logs -f status-transition-daemon

# Restart specific service
docker compose restart api
```

## Development Workflow

### Making Code Changes

1. **Edit files** in `shared/`, `services/`, or `frontend/src/`
2. **Changes appear instantly** in running containers (no rebuild required)
3. **Python services** auto-reload when files change
4. **Frontend** updates immediately with hot module replacement

### When Rebuilds Are Needed

Rebuild only when you change:

- **Dependencies**: `package.json`, `pyproject.toml`
- **Dockerfiles**: Any modifications to build steps
- **New files**: That need to be included in container image

```bash
# Rebuild specific service
docker compose build api

# Rebuild all services
docker compose build

# Force clean rebuild (no cache)
docker compose build --no-cache
```

### Running Specific Services

Start infrastructure and individual services as needed:

```bash
# Start infrastructure only
docker compose up -d postgres rabbitmq redis

# Run database migrations
docker compose run --rm api alembic upgrade head

# Start API service only
docker compose up -d api

# Start Discord bot only
docker compose up -d bot

# Start notification daemon only
docker compose up -d notification-daemon

# Start status transition daemon only
docker compose up -d status-transition-daemon
```

## Pre-commit Hooks

The project uses pre-commit hooks to automatically validate code quality before commits. These hooks are **essential for maintaining project standards**, especially when working with AI-assisted development tools. While AI can generate code quickly, it may not always follow project-specific conventions, complexity limits, or security requirements - even when explicitly instructed. The pre-commit hooks provide automated verification that all code (human or AI-generated) meets the project's quality standards before it enters the repository.

**Key principle**: Trust, but verify. Let AI help you code faster, but rely on automated checks to ensure quality.

### Dev Container Users (Everything Pre-Installed)

If you're using the dev container, **all hooks work immediately** - no additional setup needed! The container includes:

- All Python dependencies installed system-wide
- All frontend dependencies installed in `frontend/node_modules`
- Pre-commit hooks automatically installed on container creation

Just commit normally:

```bash
git add modified_file.py
git commit -m "Your changes"
# All hooks run automatically with full functionality
```

### Local Development Users

Most hooks use **standalone isolated environments** that work immediately without dependencies. Some hooks require full project setup.

#### Quick Start (Works Immediately)

Standalone hooks work right away:

```bash
# Install hooks (one-time setup)
uv tool run pre-commit install

# Run standalone hooks - no dependencies needed!
pre-commit run ruff --all-files      # Python linting (isolated)
pre-commit run prettier --all-files  # Frontend formatting (isolated)
pre-commit run eslint --all-files    # Frontend linting (isolated)
pre-commit run typescript --all-files # TypeScript checking (isolated)
```

#### Standalone Hooks

These hooks work without project dependencies:

- **File cleanup**: Trailing whitespace, end-of-file fixer, line endings
- **Python linting/formatting**: `ruff` (uses official astral-sh/ruff-pre-commit)
- **Frontend formatting**: `prettier` (isolated node environment)
- **Frontend linting**: `eslint` (isolated with TypeScript/React plugins)
- **TypeScript checking**: `typescript` (isolated node environment)
- **Code complexity**: `complexipy`, `lizard` (isolated environments)
- **Duplicate detection**: `jscpd` (isolated node environment)
- **Copyright headers**: `autocopyright` (isolated Python environment)

#### Full Project Setup (For Test Hooks)

Some hooks require the full project environment:

```bash
# Install Python project dependencies (required for Python tests)
uv sync

# Install frontend dependencies (required for frontend tests)
cd frontend && npm install
```

#### System-Dependent Hooks

These require project setup:

| Hook                      | Requires                     | Purpose                                        |
| ------------------------- | ---------------------------- | ---------------------------------------------- |
| `mypy`                    | `uv sync`                    | Python type checking with project dependencies |
| `python-compile`          | `uv sync`                    | Python compilation validation                  |
| `pytest-coverage`         | `uv sync`                    | Python unit tests with coverage                |
| `diff-coverage`           | `uv sync`                    | Python diff coverage check                     |
| `frontend-build`          | `cd frontend && npm install` | Frontend build validation                      |
| `vitest-coverage`         | `cd frontend && npm install` | Frontend unit tests with coverage              |
| `diff-coverage-frontend`  | `cd frontend && npm install` | Frontend diff coverage check                   |
| `ci-cd-workflow` (manual) | Docker                       | Run GitHub Actions locally with `act`          |

### Normal Usage

```bash
# Just commit normally - all hooks run automatically
git add modified_file.py
git commit -m "Your commit message"
# Pre-commit runs all checks + tests for modified files automatically
# Commit succeeds if all checks pass, fails otherwise
```

What runs automatically on every commit:

- All standalone hooks (linting, formatting, type checking, complexity)
- System-dependent hooks (tests for new/modified files only)
  - **Dev container**: All system hooks work (dependencies pre-installed)
  - **Local dev**: Only works after `uv sync` and `npm install`

### Manual Test Execution

```bash
# Run ALL unit tests (comprehensive validation)
pre-commit run pytest-all --hook-stage manual

# Run ALL frontend tests
pre-commit run vitest-all --hook-stage manual

# Run CI/CD workflow locally (same as GitHub Actions, requires Docker)
pre-commit run ci-cd-workflow --hook-stage manual

# Run all hooks on all files
pre-commit run --all-files
```

### Emergency Skip (Use Sparingly)

The project enforces a quality check override policy through a git wrapper that prevents accidental bypasses. Direct use of `--no-verify` or `SKIP=` environment variables will be blocked with an error message.

**Policy Enforcement:**

- `git commit --no-verify` → Blocked with error
- `SKIP=hook git commit` → Blocked with error
- See [.github/instructions/quality-check-overrides.instructions.md](../../.github/instructions/quality-check-overrides.instructions.md) for the complete policy

**Important:** If you have a legitimate need to bypass quality checks (rare cases like urgent production hotfixes), contact the project maintainer for guidance on approved bypass mechanisms. Bypasses require explicit approval and documentation of the reason.

**Note:** Even if you bypass hooks locally, all validations still run in the GitHub Actions CI/CD pipeline.

### Architecture Notes

- **Official repositories**: Ruff uses `github.com/astral-sh/ruff-pre-commit` for automatic updates
- **Isolated environments**: Most tools use `language: python` or `language: node` with `additional_dependencies`
- **Cached environments**: Pre-commit caches isolated environments in `~/.cache/pre-commit/`
- **System hooks**: Complex tools requiring full project context use `language: system`

**Performance expectations:**

- Most commits: 15-45 seconds (depending on files changed)
- Tests run ONLY on new/modified files for efficiency
- Full test suite still runs in CI/CD for comprehensive validation

## Code Quality Standards

The project enforces comprehensive code quality standards through automated linting and testing.

### Python Linting (Ruff)

Ruff enforces 33 rule categories covering security, correctness, performance, and style:

**Security & Correctness:**

- **S** (flake8-bandit): Security vulnerability detection (SQL injection, subprocess security, hardcoded secrets)
- **ASYNC** (flake8-async): Async/await best practices
- **FAST** (FastAPI): FastAPI-specific patterns (Annotated dependencies)

**Code Quality & Maintainability:**

- **E/W** (pycodestyle): PEP 8 style enforcement
- **F** (Pyflakes): Logical errors and undefined names
- **N** (pep8-naming): Naming convention enforcement
- **B** (flake8-bugbear): Common bug patterns
- **C4** (flake8-comprehensions): List/dict comprehension improvements
- **UP** (pyupgrade): Modern Python 3.13+ syntax
- **RET** (flake8-return): Return statement optimization
- **SIM** (flake8-simplify): Code simplification opportunities
- **TC** (flake8-type-checking): TYPE_CHECKING import optimization
- **PLE/PLW/PLC** (Pylint): Pylint error/warning/convention checks
- **ERA** (eradicate): Commented-out code detection
- **A** (flake8-builtins): Builtin shadowing prevention
- **DTZ** (flake8-datetimez): Timezone-aware datetime usage
- **ICN** (flake8-import-conventions): Import convention enforcement
- **PT** (flake8-pytest-style): Pytest best practices

**Performance:**

- **PERF** (Perflint): Performance anti-patterns
- **G004** (flake8-logging-format): Lazy logging (no f-strings in logging)

**Polish & Documentation:**

- **T20** (flake8-print): No print statements in production code (use logging)
- **EM** (flake8-errmsg): Exception message extraction
- **G/LOG** (flake8-logging-format): Logging best practices
- **ANN** (flake8-annotations): Comprehensive type annotations
- **ARG** (flake8-unused-arguments): Unused argument detection
- **RUF** (Ruff-specific): Ruff's own code quality rules

### Code Complexity Limits

- **Cyclomatic complexity**: Max 10 per function (C901)
- **Statement count**: Max 50 per function (PLR0915)
- **Overall complexity**: Max 15 (complexipy)

### Running Linting Locally

```bash
# Check all Python files (uses pyproject.toml configuration)
uv run ruff check .

# Auto-fix issues where possible
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check specific rule category
uv run ruff check --select S,ASYNC,FAST .
```

**Note:** All linting rules are enforced in CI/CD and pre-commit hooks. The project maintains a zero-violation baseline for all enabled rules.

### Frontend Linting

- **ESLint**: TypeScript and React best practices
- **Prettier**: Consistent code formatting
- **TypeScript**: Strict type checking

```bash
cd frontend

# Run ESLint
npm run lint

# Auto-fix ESLint issues
npm run lint:fix

# Format with Prettier
npm run format

# Type check
npm run type-check
```

## Testing

The project includes comprehensive testing at multiple levels:

- **Unit Tests**: Fast, isolated component tests
- **Integration Tests**: Service integration with database/message broker
- **End-to-End Tests**: Full system tests with Discord bot interactions

See [TESTING.md](TESTING.md) for comprehensive testing documentation.

### Quick Test Commands

```bash
# Run Python unit tests
pre-commit run pytest-all --hook-stage manual

# Run frontend unit tests
pre-commit run vitest-all --hook-stage manual

# Run integration tests
scripts/run-integration-tests.sh

# Run E2E tests
scripts/run-e2e-tests.sh

# Run with coverage
scripts/coverage-report.sh
```

## Environment Configuration

### Environment Files

Configuration is managed through environment files in `config/env/`:

- **`config/env/env.dev`**: Development (volume mounts, DEBUG logging, all ports exposed)
- **`config/env/env.prod`**: Production (production builds, INFO logging, no port mappings)
- **`config/env/env.staging`**: Staging (production builds with DEBUG logging, app ports exposed)
- **`config/env/env.int`**: Integration tests
- **`config/env/env.e2e`**: End-to-end tests

Each environment file contains a `COMPOSE_FILE` variable specifying which compose files to merge.

### Switching Environments

```bash
# Use production configuration
docker compose --env-file config/env/env.prod up

# Use staging configuration
docker compose --env-file config/env/env.staging up

# Development uses .env symlink automatically (no --env-file needed)
docker compose up
```

### Docker Compose Files

- **`compose.yaml`**: Production-ready base configuration
- **`compose.override.yaml`**: Development overrides (auto-loaded via .env symlink)
- **`compose.prod.yaml`**: Production overrides (minimal)
- **`compose.staging.yaml`**: Staging overrides (DEBUG logging, app ports)
- **`compose.int.yaml`**: Integration test overrides
- **`compose.e2e.yaml`**: E2E test overrides

## Building for Production

### Production Builds

For production deployments, use the production environment file:

```bash
# Build production images
docker compose --env-file config/env/env.prod build

# Start production services
docker compose --env-file config/env/env.prod up -d
```

Production builds:

- Target `production` stage in Dockerfiles
- Copy all source code into images (no volume mounts)
- Use optimized production commands
- Include restart policies for reliability

### Multi-Architecture Builds

The project supports building images for both ARM64 (Apple Silicon, AWS Graviton) and AMD64 (traditional x86) architectures using Docker Bake.

#### Setup

Create a multi-platform builder (one-time setup):

```bash
# Check existing builders
docker buildx ls

# Create and use multi-platform builder
docker buildx create --use
```

#### Building and Pushing Images

Build for multiple architectures and push to registry:

```bash
# Build all services for both architectures and push
docker buildx bake --push

# Build specific service(s)
docker buildx bake --push api bot

# Build with custom registry and tag
IMAGE_REGISTRY=myregistry.com/ IMAGE_TAG=v1.2.3 docker buildx bake --push

# Build without registry prefix (empty string)
IMAGE_REGISTRY= IMAGE_TAG=dev docker buildx bake --push
```

#### Environment Variables

Configure in `.env` file:

- `IMAGE_REGISTRY`: Docker registry URL prefix (include trailing slash)
  - Default: `172-16-1-24.xip.boneheads.us:5050/`
  - Examples: `docker.io/myorg/`, empty for local
- `IMAGE_TAG`: Image tag for built containers
  - Default: `latest`
  - Examples: `v1.0.0`, `dev`, `staging`

## Project Structure

```
.
├── services/
│   ├── bot/                    # Discord bot service
│   ├── api/                    # FastAPI web service
│   └── scheduler/              # Event-driven scheduling daemons
│       ├── generic_scheduler_daemon.py     # Generic parameterized scheduler daemon
│       ├── notification_daemon_wrapper.py  # Game reminder scheduler wrapper
│       ├── status_transition_daemon_wrapper.py  # Game status transition scheduler wrapper
│       ├── event_builders.py               # Event builder functions
│       └── postgres_listener.py            # PostgreSQL LISTEN/NOTIFY client
├── shared/                     # Shared models and utilities
│   └── models/
│       ├── notification_schedule.py        # Notification schedule model
│       └── game_status_schedule.py         # Status schedule model
├── frontend/                   # React + TypeScript web dashboard
│   ├── src/                    # Frontend source code
│   └── vite.config.ts          # Vite build configuration
├── docker/                     # Dockerfiles for each service
├── alembic/                    # Database migrations
├── config/
│   └── env/                    # Environment configurations
│       ├── env.dev             # Development (COMPOSE_FILE=compose.yaml:compose.override.yaml)
│       ├── env.prod            # Production (COMPOSE_FILE=compose.yaml)
│       ├── env.staging         # Staging (COMPOSE_FILE=compose.yaml:compose.staging.yaml)
│       ├── env.e2e             # E2E tests (COMPOSE_FILE=compose.yaml:compose.e2e.yaml)
│       └── env.int             # Integration tests (COMPOSE_FILE=compose.yaml:compose.int.yaml)
├── compose.yaml                # Base configuration (production-ready)
├── compose.override.yaml       # Development overrides (auto-loaded via .env symlink)
├── compose.prod.yaml           # Production overrides (minimal)
├── compose.staging.yaml        # Staging overrides (DEBUG logging, app ports)
├── compose.int.yaml            # Integration test overrides
└── compose.e2e.yaml            # E2E test overrides
```

## Troubleshooting

### Permission Errors

If you see permission errors when running containers:

```bash
# Make source files world-readable
chmod -R o+r shared/ services/ frontend/
```

### Port Conflicts

If ports are already in use:

1. Check what's using the port: `lsof -i :3000`
2. Stop conflicting services
3. Or modify port mappings in `compose.override.yaml`

### Container Won't Start

Check logs for errors:

```bash
docker compose logs <service-name>
```

Common issues:

- Missing environment variables (check `config/env/env.dev`)
- Database not ready (wait for postgres container to be healthy)
- Dependency changes (rebuild container)

### Database Migrations

If database schema is out of date:

```bash
# Run migrations
docker compose run --rm api alembic upgrade head

# Create new migration (after model changes)
docker compose run --rm api alembic revision --autogenerate -m "description"
```

### Clear Development Data

Reset database and caches:

```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Restart fresh
docker compose up
```

## Next Steps

- Review [architecture.md](architecture.md) for system design
- Read [TESTING.md](TESTING.md) for testing strategies
- See [database.md](database.md) for database schema
- Check [oauth-flow.md](oauth-flow.md) for authentication
- Review [transaction-management.md](transaction-management.md) for service patterns

## Additional Resources

- [Root README](../../README.md) - Project overview
- [Deployment Guide](../deployment/README.md) - Production deployment
- [Developer Gateway](README.md) - All developer documentation
