<!-- markdownlint-disable-file -->
# Task Research Notes: RabbitMQ Runtime Configuration

## Problem Statement

Current implementation bakes RabbitMQ credentials into container image during build using multi-stage Dockerfile with password hashing and template substitution. This requires different container images for different environments (dev, test, prod), which is not ideal for deployment flexibility.

**Goal**: Enable runtime configuration using environment variables so the same container image can be used across all environments.

## Research Executed

### File Analysis
- docker/rabbitmq.Dockerfile
  - Multi-stage build that generates password hash at build time using `rabbitmqctl hash_password`
  - Uses `envsubst` to substitute credentials into definitions.json.template
  - Bakes final definitions.json into image at /etc/rabbitmq/definitions.json
  - Requires different builds for different environments
- rabbitmq/definitions.json.template
  - Contains placeholder ${RABBITMQ_USER} and ${RABBITMQ_PASSWORD_HASH}
  - Template processed at BUILD time, not RUNTIME
  - Includes user creation, exchanges, queues, and bindings
- docker-compose.base.yml
  - Passes build args for credentials to Dockerfile
  - Same credentials used as runtime environment variables (redundant)
- shared/messaging/publisher.py and consumer.py
  - Application code already declares exchanges and queues when connecting
  - Uses idempotent operations (declare operations don't fail if already exists)
- docker/init-entrypoint.sh
  - Currently only handles database migrations
  - Could be expanded to handle all infrastructure initialization

### External Research

#### #fetch:https://www.rabbitmq.com/docs/configure
**Key findings on environment variable support**:
- Modern RabbitMQ supports environment variable interpolation in `rabbitmq.conf`
- Syntax: `setting_name = $(ENVIRONMENT_VARIABLE)`
- Example: `default_user = $(SEED_USERNAME)` and `default_pass = $(SEED_USER_PASSWORD)`

**Built-in environment variables for user creation**:
- `RABBITMQ_DEFAULT_USER` - Creates default user on first boot
- `RABBITMQ_DEFAULT_PASS` - Sets password for default user
- Documentation notes these are "meant for development and CI" but they work in production
- Higher priority than config file settings
- RabbitMQ automatically creates user on first boot if database is uninitialized

#### #fetch:https://www.rabbitmq.com/docs/definitions
**Key findings on definition import**:
- Definitions can be imported from local filesystem or HTTPS URL at boot time
- Configuration: `definitions.import_backend = local_filesystem` and `definitions.local.path = /path/to/defs.json`
- **CRITICAL**: Definitions in file will NOT overwrite existing objects (idempotent)
- On blank node, importing definitions SKIPS creating default virtual host and user
- Definition files can include users with password hashes, but this requires build-time hashing

**Definition file structure for infrastructure**:
```json
{
  "exchanges": [...],
  "queues": [...],
  "bindings": [...]
}
```

#### #githubRepo:"docker-library/rabbitmq docker-entrypoint.sh"
**Official Docker image patterns**:
- Official image uses `RABBITMQ_DEFAULT_USER` and `RABBITMQ_DEFAULT_PASS` environment variables
- Does NOT use definitions file for user creation
- Relies on RabbitMQ's built-in environment variable support
- Entrypoint checks for deprecated environment variables and exits if found
- Simple approach: let RabbitMQ handle user creation, not definitions file

## Key Discoveries

### Discovery 1: RabbitMQ Built-in Environment Variables

RabbitMQ provides **RABBITMQ_DEFAULT_USER** and **RABBITMQ_DEFAULT_PASS** that:
- Create default user on first boot if database is uninitialized
- Work without any configuration file changes
- Can be set at container runtime (no build-time processing)
- Are simpler than definitions file approach
- Follow the pattern used by official RabbitMQ Docker image

### Discovery 2: Application Code Already Creates Infrastructure

Current codebase already declares exchanges and queues:
- `shared/messaging/publisher.py`: Declares exchange on connect
- `shared/messaging/sync_publisher.py`: Declares exchange on connect
- `shared/messaging/consumer.py`: Declares both exchange and queue on connect
- All operations are idempotent (safe to call multiple times)

However, having infrastructure pre-created before services start provides:
- No race conditions during startup
- Clear visibility of message topology
- Validation that infrastructure is ready before services start

### Discovery 3: Init Container Architecture Pattern

Current init container:
- Runs database migrations before application services start
- Uses `depends_on` with health checks to ensure proper ordering
- Runs once (`restart: "no"`)
- Perfect pattern for all infrastructure initialization

**Architectural insight**: Expanding init container from "database initialization" to "infrastructure initialization" provides:
- Centralized initialization logic
- Single place to validate environment is ready
- Consistent with existing patterns
- Clean separation: init creates, applications use

## Recommended Approach

**Use Hybrid Approach: Environment Variables + Init Container Infrastructure Setup**

### Architecture

**RabbitMQ Container**:
- Use official `rabbitmq:4.2-management-alpine` image (no custom Dockerfile)
- User credentials provided via `RABBITMQ_DEFAULT_USER` and `RABBITMQ_DEFAULT_PASS` at runtime
- Same container image for all environments

**Init Container** (expanded scope):
- Run database migrations (existing functionality)
- Create RabbitMQ exchanges, queues, and bindings
- Validate infrastructure is ready
- Runs once before application services start

**Application Services**:
- Connect to pre-existing infrastructure
- No need to declare queues/exchanges during startup
- Cleaner, faster startup

### Rationale

1. **No build-time credentials** - User credentials provided via environment variables
2. **Same image for all environments** - Official RabbitMQ image with runtime configuration
3. **Centralized initialization** - All infrastructure setup in one place (init container)
4. **Consistent architecture** - Matches existing database migration pattern
5. **Clear separation** - Init creates, applications use
6. **No race conditions** - Infrastructure exists before services start
7. **Explicit topology** - All queues, exchanges, bindings defined declaratively in code

## Implementation Guidance

### Phase 1: Switch to Official RabbitMQ Image

**Objectives**:
- Use official rabbitmq:4.2-management-alpine image
- Pass credentials via environment variables at runtime
- Remove build-time credential processing

**Key Tasks**:

1. Update docker-compose.base.yml rabbitmq service:
   ```yaml
   rabbitmq:
     image: rabbitmq:4.2-management-alpine
     container_name: ${CONTAINER_PREFIX:-gamebot}-rabbitmq
     restart: ${RESTART_POLICY:-unless-stopped}
     environment:
       RABBITMQ_DEFAULT_USER: ${RABBITMQ_DEFAULT_USER}
       RABBITMQ_DEFAULT_PASS: ${RABBITMQ_DEFAULT_PASS}
     # ... rest of config unchanged
   ```
   - Remove entire `build` section
   - Keep all other settings (ports, volumes, healthcheck, networks)

2. Remove files:
   - `docker/rabbitmq.Dockerfile`
   - `rabbitmq/definitions.json.template`
   - `rabbitmq/definitions.json` (generated file, if exists)

3. Update rabbitmq/rabbitmq.conf:
   - Remove `load_definitions = /etc/rabbitmq/definitions.json` line
   - Keep `management_agent.disable_metrics_collector = true`

**Success Criteria**:
- RabbitMQ starts with runtime-provided credentials
- Management UI accessible at localhost:15672 with provided credentials
- Same image works in all environments
- No build-time credential processing

### Phase 2: Expand Init Container for RabbitMQ Infrastructure

**Objectives**:
- Rename/repurpose init container from "database migration" to "infrastructure initialization"
- Create RabbitMQ exchanges, queues, and bindings before application services start
- Maintain idempotent operations

**Key Tasks**:

1. Create `scripts/init_rabbitmq.py`:
   ```python
   #!/usr/bin/env python3
   """Initialize RabbitMQ infrastructure."""
   import os
   import sys
   import time
   import pika
   
   def wait_for_rabbitmq(rabbitmq_url, max_retries=30):
       """Wait for RabbitMQ to be ready."""
       # Connection retry logic
       pass
   
   def create_infrastructure(rabbitmq_url):
       """Create exchanges, queues, and bindings."""
       connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
       channel = connection.channel()
       
       # Declare exchanges
       channel.exchange_declare(
           exchange='game_scheduler',
           exchange_type='topic',
           durable=True
       )
       channel.exchange_declare(
           exchange='game_scheduler.dlx',
           exchange_type='topic',
           durable=True
       )
       
       # Declare queues with DLX configuration
       queues = ['bot_events', 'api_events', 'scheduler_events', 'notification_queue']
       for queue_name in queues:
           channel.queue_declare(
               queue=queue_name,
               durable=True,
               arguments={
                   'x-dead-letter-exchange': 'game_scheduler.dlx',
                   'x-message-ttl': 86400000
               }
           )
       
       # Declare DLQ
       channel.queue_declare(queue='DLQ', durable=True)
       
       # Create bindings (routing keys)
       # ... bind queues to exchanges
       
       connection.close()
   
   if __name__ == '__main__':
       rabbitmq_url = os.getenv('RABBITMQ_URL')
       wait_for_rabbitmq(rabbitmq_url)
       create_infrastructure(rabbitmq_url)
       print("RabbitMQ infrastructure initialized successfully")
   ```

2. Update docker/init-entrypoint.sh:
   ```bash
   #!/bin/bash
   set -e
   
   echo "Starting infrastructure initialization..."
   
   # Wait for PostgreSQL
   echo "Waiting for PostgreSQL..."
   python3 -c "import time; ..." # existing wait logic
   
   # Run database migrations
   echo "Running database migrations..."
   alembic upgrade head
   
   # Wait for RabbitMQ
   echo "Waiting for RabbitMQ..."
   python3 scripts/init_rabbitmq.py
   
   echo "Infrastructure initialization complete"
   ```

3. Update docker/init.Dockerfile:
   - Ensure `pika` library is installed (probably already is via pyproject.toml)
   - Copy `scripts/init_rabbitmq.py` into image

4. Update docker-compose.base.yml init service:
   ```yaml
   init:
     # ... existing config
     environment:
       DATABASE_URL: ${DATABASE_URL}
       RABBITMQ_URL: ${RABBITMQ_URL}  # ADD THIS
       # ... other env vars
     depends_on:
       postgres:
         condition: service_healthy
       rabbitmq:  # ADD THIS
         condition: service_healthy
   ```

**Success Criteria**:
- Init container successfully creates all RabbitMQ infrastructure
- Infrastructure creation is idempotent (safe to rerun)
- Application services find infrastructure ready when they start
- Integration tests pass without modifications
- Clear separation: init creates, applications use

### Phase 3: Simplify Application Code (Optional)

Once init container creates infrastructure, application code no longer needs to declare queues/exchanges:

- Remove exchange/queue declarations from `shared/messaging/publisher.py`
- Remove exchange/queue declarations from `shared/messaging/consumer.py`
- Keep connection logic only
- Results in simpler, faster service startup

**Note**: This phase is optional and can be done later. Keeping declarations doesn't hurt (they're idempotent) but removing them makes the code cleaner.

## Dependencies

- Official RabbitMQ Docker image: `rabbitmq:4.2-management-alpine`
- Python `pika` library (already in project)
- Environment variables for credentials (already in compose files)
- No additional dependencies required

## Success Criteria

- ✅ Same RabbitMQ container image used in all environments
- ✅ Credentials provided at runtime via environment variables
- ✅ No build-time credential processing
- ✅ RabbitMQ starts successfully with provided credentials
- ✅ Init container creates all infrastructure before services start
- ✅ All integration tests pass
- ✅ Simplified deployment process
- ✅ Clear architecture: init creates, applications use
