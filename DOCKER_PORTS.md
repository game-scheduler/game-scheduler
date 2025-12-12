# Docker Port Exposure Strategy

This document explains the port exposure strategy used in this project to minimize security risks and prevent port conflicts when running multiple environments simultaneously.

## Overview

Services communicate via the internal Docker network (`app-network`) by default. Port exposure to the host is environment-specific and follows the principle of least privilege.

## Port Exposure by Environment

### Base Configuration (`docker-compose.base.yml`)

**NO ports exposed to host**

- Infrastructure services (postgres, rabbitmq, redis) expose no ports
- Observability services (grafana-alloy) expose no ports
- All services communicate via internal Docker network

### Development (`compose.override.yaml`)

**Application ports + management UI**

- Frontend: `localhost:3000` (configurable via `FRONTEND_HOST_PORT`)
- API: `localhost:8000` (configurable via `API_HOST_PORT`)
- RabbitMQ Management UI: `localhost:15672` (configurable via `RABBITMQ_MGMT_HOST_PORT`)

### Test (`docker-compose.test.yml`)

**Application ports only**

- Frontend: `localhost:3000` (configurable via `FRONTEND_HOST_PORT`)
- API: `localhost:8000` (configurable via `API_HOST_PORT`)

### Production (`compose.production.yaml`)

**NO ports exposed to host**

- Reverse proxy handles external routing
- Maximum security with minimal attack surface

## Debugging Infrastructure Services

Infrastructure service ports (postgres, redis, rabbitmq data) are NOT exposed to the host in any environment. This improves security and prevents port conflicts.

### PostgreSQL

```bash
# Access psql CLI
docker exec -it gamebot-postgres psql -U gamebot -d game_scheduler

# Run SQL query
docker exec -it gamebot-postgres psql -U gamebot -d game_scheduler -c "SELECT * FROM games LIMIT 5;"

# Database backup
docker exec gamebot-postgres pg_dump -U gamebot game_scheduler > backup.sql
```

### Redis

```bash
# Access redis-cli
docker exec -it gamebot-redis redis-cli

# Check specific key
docker exec -it gamebot-redis redis-cli GET some_key

# Monitor commands
docker exec -it gamebot-redis redis-cli MONITOR
```

### RabbitMQ

#### CLI Management

```bash
# Check status
docker exec -it gamebot-rabbitmq rabbitmqctl status

# List queues
docker exec -it gamebot-rabbitmq rabbitmqctl list_queues

# List exchanges
docker exec -it gamebot-rabbitmq rabbitmqctl list_exchanges

# List connections
docker exec -it gamebot-rabbitmq rabbitmqctl list_connections
```

#### Management UI (Development Only)

Access http://localhost:15672 in browser

- **Username**: Value of `RABBITMQ_DEFAULT_USER` (default: `gamebot`)
- **Password**: Value of `RABBITMQ_DEFAULT_PASS` (default: `dev_password_change_in_prod`)

## Observability Architecture

### Grafana Alloy (OpenTelemetry Collector)

Services send telemetry to Grafana Alloy via internal Docker network:

- **OTLP gRPC**: `grafana-alloy:4317`
- **OTLP HTTP**: `grafana-alloy:4318`

Alloy forwards telemetry to Grafana Cloud. No external port exposure is needed.

### RabbitMQ Prometheus Metrics

Alloy scrapes RabbitMQ Prometheus metrics internally from `rabbitmq:15692`. The metrics port is not exposed to the host.

## Benefits

### Security

- Minimized attack surface (infrastructure services not accessible from host)
- Production environment has zero exposed ports
- Reduced risk of unauthorized access

### Port Conflicts

- Multiple environments (dev, test, production) can run simultaneously
- No conflicts between environments
- Each environment exposes only the ports it needs

### Debugging

- `docker exec` provides secure, direct access to infrastructure services
- No need to expose ports for debugging
- Management UIs available in development when needed

## Configuration Variables

Define these in your `.env` file to customize port mappings:

| Variable | Default | Environments | Description |
|----------|---------|--------------|-------------|
| `API_HOST_PORT` | `8000` | dev, test | API port on host |
| `FRONTEND_HOST_PORT` | `3000` | dev, test | Frontend port on host |
| `RABBITMQ_MGMT_HOST_PORT` | `15672` | dev only | RabbitMQ management UI port |

## Migration Notes

If you previously accessed infrastructure services directly via localhost:

- **PostgreSQL** (`localhost:5432`) → Use `docker exec -it gamebot-postgres psql -U gamebot -d game_scheduler`
- **Redis** (`localhost:6379`) → Use `docker exec -it gamebot-redis redis-cli`
- **RabbitMQ** (`localhost:5672`) → Services use `rabbitmq:5672` internally
- **RabbitMQ Management** (`localhost:15672`) → Still available in development mode only

## See Also

- [RUNTIME_CONFIG.md](RUNTIME_CONFIG.md) - Runtime configuration options
- [DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md) - Deployment instructions
- [docker-compose.base.yml](docker-compose.base.yml) - Base service definitions
- [compose.override.yaml](compose.override.yaml) - Development overrides
