<!-- markdownlint-disable-file -->

# Task Details: Minimize Docker Port Exposure for Security

## Research Reference

**Source Research**: #file:../research/20251210-test-instance-deployment-issues-research.md

## Phase 1: Remove Infrastructure Ports from Base Configuration

### Task 1.1: Remove postgres port mapping from docker-compose.base.yml

Remove the `ports:` section from the postgres service definition. Services will access PostgreSQL via internal Docker network using `postgres:5432`.

- **Files**:
  - docker-compose.base.yml - Remove lines 27-28 (ports section)
- **Success**:
  - No `ports:` section in postgres service
  - Service still accessible internally via `postgres:5432`
  - Healthcheck continues to function
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 48-65) - Issue 1: Unnecessary port exposure
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Strategy explanation
- **Dependencies**:
  - None

### Task 1.2: Remove rabbitmq data port (5672) from docker-compose.base.yml

Remove only the 5672 port mapping (AMQP protocol) from RabbitMQ. Keep management UI (15672) and Prometheus metrics (15692) ports for now - they will be moved to development overrides in Phase 2.

- **Files**:
  - docker-compose.base.yml - Remove line 50 (5672 port mapping only)
- **Success**:
  - No 5672 port mapping in rabbitmq service
  - Lines 51-52 (15672 and 15692) remain temporarily
  - Service still accessible internally via `rabbitmq:5672`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 48-65) - Infrastructure port exposure issue
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 108-136) - Management UI port analysis
- **Dependencies**:
  - None

### Task 1.3: Remove redis port mapping from docker-compose.base.yml

Remove the `ports:` section from the redis service definition. Services will access Redis via internal Docker network using `redis:6379`.

- **Files**:
  - docker-compose.base.yml - Remove lines 69-70 (ports section)
- **Success**:
  - No `ports:` section in redis service
  - Service still accessible internally via `redis:6379`
  - Healthcheck continues to function
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 48-65) - Infrastructure service exposure
- **Dependencies**:
  - None

### Task 1.4: Remove grafana-alloy OTLP ports from docker-compose.base.yml

Remove OTLP port mappings (4317, 4318) from grafana-alloy service. All services send telemetry to Alloy via internal network using `grafana-alloy:4317` and `grafana-alloy:4318`.

- **Files**:
  - docker-compose.base.yml - Search for grafana-alloy service and remove its ports section
- **Success**:
  - No `ports:` section in grafana-alloy service
  - Services continue sending telemetry via internal network
  - Alloy continues forwarding to Grafana Cloud
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 108-136) - Observability port analysis
- **Dependencies**:
  - None

## Phase 2: Add Development Port Overrides

### Task 2.1: Add frontend port to compose.override.yaml

Add frontend port mapping to development overrides for browser access during development.

- **Files**:
  - compose.override.yaml - Add `ports:` section to frontend service
- **Success**:
  - Frontend accessible at `http://localhost:3000` in development
  - Port configurable via `FRONTEND_HOST_PORT` environment variable
  - Uses format: `"${FRONTEND_HOST_PORT:-3000}:80"`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Development override strategy
- **Dependencies**:
  - Phase 1 completion (base configuration has no ports)

### Task 2.2: Add API port to compose.override.yaml

Add API port mapping to development overrides for direct API testing during development.

- **Files**:
  - compose.override.yaml - Add `ports:` section to api service
- **Success**:
  - API accessible at `http://localhost:8000` in development
  - Port configurable via `API_HOST_PORT` environment variable
  - Uses format: `"${API_HOST_PORT:-8000}:8000"`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Development port requirements
- **Dependencies**:
  - Phase 1 completion

### Task 2.3: Add RabbitMQ management UI port to compose.override.yaml

Add RabbitMQ management UI port (15672) to development overrides for monitoring and debugging.

- **Files**:
  - compose.override.yaml - Add `ports:` section to rabbitmq service (if it exists, otherwise create service override)
  - docker-compose.base.yml - Remove remaining RabbitMQ port mappings (15672, 15692)
- **Success**:
  - RabbitMQ management UI accessible at `http://localhost:15672` in development only
  - Port configurable via `RABBITMQ_MGMT_HOST_PORT` environment variable
  - Prometheus metrics port (15692) not exposed (Alloy scrapes internally)
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 108-136) - Management UI analysis
- **Dependencies**:
  - Phase 1 Task 1.2 completion (base has no RabbitMQ ports)

## Phase 3: Add Test Environment Port Overrides

### Task 3.1: Add frontend and API ports to docker-compose.test.yml

Add frontend and API port mappings to test configuration for test execution and verification.

- **Files**:
  - docker-compose.test.yml - Add service overrides for frontend and api with ports
- **Success**:
  - Frontend accessible during test runs
  - API accessible during test runs
  - No management UI ports exposed in test environment
  - Uses same port environment variables as development
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Test environment requirements
- **Dependencies**:
  - Phase 1 completion (base has no ports)
  - Phase 2 completion (pattern established)

## Phase 4: Update Documentation

### Task 4.1: Update .env.example with port configuration guidance

Add comprehensive documentation about port configuration strategy and `docker exec` usage for infrastructure debugging.

- **Files**:
  - .env.example - Add new section explaining port exposure strategy
- **Success**:
  - Clear explanation of which ports are exposed in which environments
  - `docker exec` examples for postgres, redis, rabbitmq debugging
  - Explanation that observability uses internal network only
  - Port variables documented: API_HOST_PORT, FRONTEND_HOST_PORT, RABBITMQ_MGMT_HOST_PORT
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 138-163) - Documentation requirements
- **Dependencies**:
  - All previous phases complete

### Task 4.2: Verify compose.production.yaml has no port mappings

Verify that production configuration does not expose any ports (reverse proxy handles external access).

- **Files**:
  - compose.production.yaml - Inspect all services
- **Success**:
  - No `ports:` sections in any service
  - Documentation confirms reverse proxy usage
  - Production services communicate only via internal network
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Production security requirements
- **Dependencies**:
  - None (verification only)

## Dependencies

- Docker Compose with multi-file support
- Existing layered compose configuration structure

## Success Criteria

- All infrastructure services accessible via internal Docker network only
- Application services accessible on host in development and test environments
- Production environment exposes zero ports externally
- Documentation provides clear guidance on debugging with `docker exec`
- No port conflicts when running multiple environments
- All tests pass (no regression in functionality)
