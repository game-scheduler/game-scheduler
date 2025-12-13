<!-- markdownlint-disable-file -->

# Release Changes: Minimize Docker Port Exposure for Security

**Related Plan**: 20251210-test-instance-deployment-issues-plan.instructions.md
**Implementation Date**: 2025-12-11

## Summary

Removed unnecessary port mappings from Docker Compose configurations to minimize attack surface and prevent port conflicts when running multiple environments simultaneously. Infrastructure services (postgres, rabbitmq, redis, grafana-alloy) no longer expose ports to host - services communicate via internal Docker network only. Application ports (frontend, API) and management UI ports are now environment-specific.

## Changes

### Added

- DOCKER_PORTS.md - Comprehensive documentation of port exposure strategy, docker exec debugging examples, and observability architecture

### Modified

- docker-compose.base.yml - Removed postgres port mapping (5432) from base configuration
- docker-compose.base.yml - Removed rabbitmq data port mapping (5672) from base configuration
- docker-compose.base.yml - Removed redis port mapping (6379) from base configuration
- docker-compose.base.yml - Removed grafana-alloy OTLP port mappings (4317, 4318) from base configuration
- docker-compose.base.yml - Removed rabbitmq management and Prometheus port mappings (15672, 15692) from base configuration
- docker-compose.base.yml - Removed frontend port mapping (3000) from base configuration
- compose.override.yaml - Added API port mapping (8000) for development environment
- compose.override.yaml - Added RabbitMQ management UI port mapping (15672) for development environment
- docker-compose.test.yml - Added frontend port mapping (3000) for test environment
- docker-compose.test.yml - Added API port mapping (8000) for test environment
- .env.example - Added port configuration variables (API_HOST_PORT, FRONTEND_HOST_PORT, RABBITMQ_MGMT_HOST_PORT) with reference to DOCKER_PORTS.md
- compose.production.yaml - Verified no port mappings exist (production uses reverse proxy for external access)
- DOCKER_PORTS.md - Created comprehensive documentation for port exposure strategy, debugging with docker exec, and observability architecture

**Total Files Affected**: 6

### Files Created (1)

- DOCKER_PORTS.md - Complete port exposure strategy documentation with debugging guide

### Files Modified (5)

- docker-compose.base.yml - Removed all port mappings for infrastructure services (postgres:5432, rabbitmq:5672/15672/15692, redis:6379, grafana-alloy:4317/4318) and application services (frontend:3000, api:8000)
- compose.override.yaml - Added development-specific port mappings for application services (frontend:3000, api:8000) and RabbitMQ management UI (15672)
- docker-compose.test.yml - Added test-specific port mappings for application services only (frontend:3000, api:8000)
- .env.example - Added port configuration variables with reference to DOCKER_PORTS.md documentation
- compose.production.yaml - Verified zero port exposure (reverse proxy handles external routing)ntend:3000, api:8000)
- .env.example - Added comprehensive documentation explaining port exposure strategy across environments, docker exec debugging commands, and observability architecture
- compose.production.yaml - Verified zero port exposure (reverse proxy handles external routing)
- services/bot/events/handlers.py - Added is_host parameter to _send_reminder_dm method to customize host reminder messages
- services/bot/events/handlers.py - Added host notification logic to _handle_game_reminder_due method to send reminders to game hosts

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: 
  - Base configuration now uses internal Docker network (app-network) exclusively for service communication
  - Infrastructure services (postgres, rabbitmq, redis) no longer expose ports to host in any environment
  - Observability services (grafana-alloy) collect telemetry via internal network without port exposure
  - Environment-specific port exposure: development (frontend, API, RabbitMQ UI), test (frontend, API only), production (none)
- **Configuration Updates**: 
  - Added port configuration variables to .env.example: API_HOST_PORT, FRONTEND_HOST_PORT, RABBITMQ_MGMT_HOST_PORT
  - Documented docker exec usage patterns for infrastructure service debugging

### Deployment Notes

**Security Improvements**:
- Minimized attack surface by removing unnecessary port exposure
- Infrastructure services no longer accessible from host (use `docker exec` for debugging)
- Production environment has zero exposed ports (reverse proxy handles routing)

**Port Conflicts Resolution**:
- Multiple environments (dev, test, production) can now run simultaneously without port conflicts
- Each environment exposes only the ports it needs

**Observability**:
- No changes to observability functionality
- Grafana Alloy continues collecting telemetry via internal Docker network
- All metrics, traces, and logs forwarded to Grafana Cloud as before

**Breaking Changes**:
- Direct localhost access to infrastructure services (postgres:5432, rabbitmq:5672, redis:6379) no longer available
- Use `docker exec` commands documented in .env.example for debugging
- RabbitMQ management UI now only available in development environment (http://localhost:15672)

### Removed

