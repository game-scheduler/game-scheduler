# Game Scheduler

A Discord game scheduling system with microservices architecture, featuring Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support, and automated notifications.

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

- **Discord Bot Service**: Handles Discord Gateway interactions
- **Web API Service**: FastAPI REST API for web dashboard
- **Scheduler Service**: Celery workers for background jobs and notifications
- **PostgreSQL**: Primary data store
- **RabbitMQ**: Message broker for inter-service communication
- **Redis**: Caching and session storage

## Development Setup

1. Copy environment template:

```bash
cp .env.example .env
```

2. Update `.env` with your Discord bot credentials

3. Start all services:

```bash
docker compose --env-file .env up
```

4. Access services:

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RabbitMQ Management: http://localhost:15672

## Building Multi-Architecture Images

The project supports building images for both ARM64 (Apple Silicon, AWS Graviton) and AMD64 (traditional x86) architectures using Docker Bake.

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

For local development (single platform, no push):

```bash
# Regular docker compose build (single platform)
docker compose --env-file .env build

# Build for specific platform
docker compose --env-file .env build --build-arg BUILDPLATFORM=linux/amd64
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
│   └── scheduler/              # Celery scheduler service
├── shared/                     # Shared models and utilities
├── docker/                     # Dockerfiles for each service
├── docker-compose.base.yml     # Shared service definitions
├── docker-compose.yml          # Development environment
├── docker-compose.integration.yml  # Integration test environment
└── docker-compose.e2e.yml      # E2E test environment
```

## Docker Compose Architecture

The project uses a layered Docker Compose structure to minimize duplication:

- **`docker-compose.base.yml`**: Shared service definitions (images, healthchecks, dependencies)
- **`docker-compose.yml`**: Development environment overrides (persistent volumes, exposed ports)
- **`docker-compose.integration.yml`**: Integration test environment (postgres, rabbitmq, redis only)
- **`docker-compose.e2e.yml`**: E2E test environment (full stack with Discord bot)

This design ensures all environments stay in sync while allowing environment-specific configurations. See [TESTING_E2E.md](TESTING_E2E.md) for testing details.

## License

Copyright 2025 Bret McKee (bret.mckee@gmail.com)

Game Scheduler is available as open source software, see COPYING.txt for
information on the license. 

Please contact the author if you are interested in obtaining it under other
terms.
