# Game Scheduler

A Discord game scheduling system with microservices architecture, featuring
Discord bot with button interactions, web dashboard with OAuth2 authentication,
role-based authorization, multi-channel support, and automated notifications.

## Features

- Discord bot with button interactions for joining/leaving games
- Web dashboard for game creation and management
- Discord OAuth2 authentication with role-based authorization
- Multi-channel support with hierarchical settings inheritance
- Automated notifications before games start
- Display name resolution for guild-specific names
- Pre-populated participants with @mention validation

## Architecture

Microservices architecture with:

- **Discord Bot Service**: Handles Discord Gateway interactions and sends
  notifications to participants
- **Web API Service**: FastAPI REST API for web dashboard and game management
- **Notification Daemon**: Database-backed event-driven scheduler for game
  reminders
- **Status Transition Daemon**: Database-backed event-driven scheduler for game
  status transitions
- **PostgreSQL**: Primary data store with LISTEN/NOTIFY for real-time events
- **RabbitMQ**: Message broker for inter-service communication
- **Redis**: Caching and session storage

### Event-Driven Scheduling System

The system uses a database-backed event-driven architecture for reliable,
scalable scheduling:

#### Game Reminders (Notification Daemon)

1. **Schedule Population**: When games are created or updated, notification
   schedules are stored in the `notification_schedule` table
2. **Event-Driven Wake-ups**: PostgreSQL LISTEN/NOTIFY triggers instant daemon
   wake-ups when schedules change
3. **MIN() Query Pattern**: Daemon queries for the next due notification using
   an optimized O(1) query with partial index
4. **RabbitMQ Events**: When notifications are due, events are published to
   RabbitMQ for the bot service to process

#### Game Status Transitions (Status Transition Daemon)

1. **Schedule Population**: When games are created or scheduled_at updated,
   status transitions are stored in the `game_status_schedule` table
2. **Event-Driven Wake-ups**: PostgreSQL LISTEN/NOTIFY triggers instant daemon
   wake-ups when schedules change
3. **MIN() Query Pattern**: Daemon queries for the next due transition using an
   optimized O(1) query with partial index
4. **Status Updates**: When transitions are due, game status is updated and
   GAME_STARTED events published to RabbitMQ

**Key Features**:

- Unlimited scheduling windows (supports scheduling weeks/months in advance)
- Sub-10 second latency with event-driven wake-ups
- Zero data loss on restarts - all state persisted in database
- Self-healing - single MIN() query resumes processing after restart
- Scalable - O(1) query performance regardless of total scheduled games

## Development Setup

### Quick Start

1. Copy environment template:

```bash
cp .env.example .env
```

2. Update `.env` with your Discord bot credentials

3. Start all services:

```bash
docker compose --env-file .env up
```

The development environment automatically:

- **Mounts your source code** as volumes (no rebuilds needed!)
- **Enables hot-reload** for instant code changes
- **Uses development stages** from Dockerfiles

### Development Workflow

**Prerequisites:**

- Source files must be **world-readable** for volume mounts to work
- Development containers run as non-root user (UID 1000)
- If you encounter permission errors, ensure files have read access:
  ```bash
  chmod -R o+r shared/ services/ frontend/
  ```

**Making code changes:**

1. Edit files in `shared/`, `services/`, or `frontend/src/`
2. Changes appear **instantly** in running containers
3. No rebuild or restart required!

**Python services** (API, bot, daemons) use:

- `uvicorn --reload` (API) or `python -m` (bot, daemons)
- Auto-detects file changes and reloads

**Frontend** uses:

- Vite dev server with hot module replacement
- Changes appear instantly in browser

**When you need to rebuild:**

- Dependency changes (`package.json`, `pyproject.toml`)
- Dockerfile modifications
- New files added that need to be included

```bash
# Rebuild specific service
docker compose build api

# Rebuild all services
docker compose build
```

### Access Services

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672

### Monitoring Services

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f notification-daemon

# Restart specific service
docker compose restart api
```

## Running Services Individually

Start specific services for development:

```bash
# Start infrastructure only
docker compose up -d postgres rabbitmq redis

# Run database migrations
docker compose run --rm api alembic upgrade head

# Start notification daemon
docker compose up -d notification-daemon

# Start API service
docker compose up -d api

# Start Discord bot
docker compose up -d bot
```

## Building Multi-Architecture Images

The project supports building images for both ARM64 (Apple Silicon, AWS
Graviton) and AMD64 (traditional x86) architectures using Docker Bake.

### Production Builds

For production deployments, use the production compose configuration:

```bash
# Build production images
docker compose -f docker-compose.yml -f compose.production.yaml build

# Start production services
docker compose -f docker-compose.yml -f compose.production.yaml up -d
```

Production builds:

- Target `production` stage in Dockerfiles
- Copy all source code into images (no volume mounts)
- Use optimized production commands
- Include restart policies for reliability

### Setup

Create a multi-platform builder (one-time setup):

```bash
# Check existing builders
docker buildx ls

# Create and use multi-platform builder
docker buildx create --use
```

### Building and Pushing Images

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

### Local Development Builds

Development uses `compose.override.yaml` automatically:

```bash
# Development build (single platform, volume mounts)
docker compose build

# Force rebuild after dependency changes
docker compose build --no-cache
```

### Environment Variables

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
├── docker/                     # Dockerfiles for each service
├── alembic/                    # Database migrations
├── docker-compose.base.yml     # Shared service definitions
├── docker-compose.yml          # Development environment
├── docker-compose.integration.yml  # Integration test environment
└── docker-compose.e2e.yml      # E2E test environment
```

## Docker Compose Architecture

The project uses a layered Docker Compose structure to minimize duplication:

- **`docker-compose.base.yml`**: Shared service definitions (images,
  healthchecks, dependencies)
- **`docker-compose.yml`**: Development environment overrides (persistent
  volumes, exposed ports)
- **`docker-compose.integration.yml`**: Integration test environment (postgres,
  rabbitmq, redis only)
- **`docker-compose.e2e.yml`**: E2E test environment (full stack with Discord
  bot)

This design ensures all environments stay in sync while allowing
environment-specific configurations. See [TESTING_E2E.md](TESTING_E2E.md) for
testing details.

## License

Copyright 2025 Bret McKee (bret.mckee@gmail.com)

Game Scheduler is available as open source software, see COPYING.txt for
information on the license.

Please contact the author if you are interested in obtaining it under other
terms.
