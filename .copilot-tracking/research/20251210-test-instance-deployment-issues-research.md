<!-- markdownlint-disable-file -->
# Task Research Notes: Test Instance Deployment Issues

## Research Executed

### File Analysis
- `docker-compose.base.yml`
  - Infrastructure services (postgres, rabbitmq, redis) expose ports to host
  - Port exposure controlled via environment variables (POSTGRES_HOST_PORT, etc.)
  - All services connected via `app-network` bridge network
- `.env.example`
  - No port configuration variables defined (uses defaults from docker-compose.base.yml)
  - Services communicate internally via service names (postgres:5432, rabbitmq:5672, redis:6379)
- `docker-compose.test.yml`
  - Uses tmpfs volumes for fast ephemeral storage
  - Includes base configuration with all port mappings

### Code Search Results
- Port mappings in docker-compose.base.yml:
  - postgres: `"${POSTGRES_HOST_PORT:-5432}:5432"`
  - rabbitmq: `"${RABBITMQ_HOST_PORT:-5672}:5672"`, `"${RABBITMQ_MGMT_HOST_PORT:-15672}:15672"`, `"${RABBITMQ_PROMETHEUS_PORT:-15692}:15692"`
  - redis: `"${REDIS_HOST_PORT:-6379}:6379"`
  - api: `"${API_HOST_PORT:-8000}:8000"`
  - frontend: `"${FRONTEND_HOST_PORT:-3000}:80"`
  - grafana-alloy: `"${ALLOY_OTLP_GRPC_PORT:-4317}:4317"`, `"${ALLOY_OTLP_HTTP_PORT:-4318}:4318"`

### External Research
- #fetch:https://docs.docker.com/compose/networking/
  - Services on the same Docker network can communicate using service names
  - Port mappings (ports:) expose container ports to the host machine
  - No port mapping needed for inter-container communication on same network
  - Port exposure increases attack surface in production environments
- #githubRepo:"docker/docs" container networking best practices
  - Only expose ports that need to be accessed from outside the Docker network
  - Internal services (databases, message queues) should not expose ports in production
  - Port exposure should be environment-specific (development vs production vs test)

### Project Conventions
- Containerization best practices: `.github/instructions/containerization-docker-best-practices.instructions.md`
  - Security principle: minimize exposed ports to reduce attack surface
  - Network isolation: use Docker networks for inter-service communication
  - Environment-specific configuration: different port strategies for dev/test/prod

## Issues Discovered

### Issue 1: Unnecessary Port Exposure on Infrastructure Services

**Problem**: PostgreSQL, RabbitMQ (5672), and Redis expose ports to the host machine that are not needed for normal operation.

**Impact**:
- Increased attack surface in production/test environments
- Potential port conflicts when running multiple instances (test, dev, production)
- Security risk: databases and message brokers accessible from host without network isolation

**Current Behavior**:
- `postgres` exposes port 5432 to host via `${POSTGRES_HOST_PORT:-5432}:5432`
- `rabbitmq` exposes port 5672 to host via `${RABBITMQ_HOST_PORT:-5672}:5672`
- `redis` exposes port 6379 to host via `${REDIS_HOST_PORT:-6379}:6379`

**Why Ports Are Exposed**:
All application services (bot, api, notification-daemon, status-transition-daemon) connect to infrastructure services using internal Docker network names:
- `postgres:5432` (not `localhost:5432`)
- `rabbitmq:5672` (not `localhost:5672`)
- `redis:6379` (not `localhost:6379`)

**When Port Exposure IS Needed**:
- Development: Management/monitoring UIs (RabbitMQ:15672) for debugging
- Development/Test: Frontend (3000) and API (8000) for direct access
- Never needed in production (reverse proxy handles external access)

**When Port Exposure IS NOT Needed**:
- Infrastructure services (postgres:5432, rabbitmq:5672, redis:6379) - use `docker exec`
- Observability ports (4317, 4318, 15692) - Alloy collects via internal network
- Production: Frontend/API ports - reverse proxy handles external routing
- Production: Management UIs - not needed externally

### Issue 2: Port Configuration Missing from .env.example

**Problem**: Environment variables for controlling port exposure (POSTGRES_HOST_PORT, etc.) are not documented in `.env.example`.

**Impact**:
- Users unaware they can customize ports
- Port conflicts not easily resolvable
- No guidance on which ports are optional vs required

**Current State**:
- Port variables exist in docker-compose.base.yml with defaults
- Not documented in .env.example
- Users must read docker-compose files to discover port configuration options

## Recommended Approach

### Strategy: Minimal Port Exposure with Environment-Specific Overrides

**Base Configuration** (`docker-compose.base.yml`): Remove ALL port mappings
- No ports exposed by default
- Services communicate via internal Docker network
- Maximum security and flexibility

**Development Override** (`compose.override.yaml`): Add useful ports for local development
- Frontend: 3000 (direct browser access)
- API: 8000 (direct API testing)
- RabbitMQ Management UI: 15672 (monitoring/debugging)

**Production Configuration** (`compose.production.yaml`): No ports exposed
- Reverse proxy handles external routing to frontend/API
- No direct port access needed
- Management UIs not exposed externally
### Observability Port Analysis

**Grafana Alloy Architecture**:
- Alloy runs inside the Docker Compose network
- All services send telemetry to Alloy via internal network (grafana-alloy:4317, grafana-alloy:4318)
- RabbitMQ Prometheus metrics scraped internally (rabbitmq:15692)
- Alloy forwards aggregated data to Grafana Cloud
- **No external port exposure needed for observability**

**Management UI Ports**:
- RabbitMQ Management UI (15672): Useful for development debugging only
- Should be in development override, not base configuration
- Not needed in production or test environments
- Forces best practice of using `docker exec` for infrastructure access

### Keep Management/Monitoring Ports

**Ports to Keep Exposed** (useful in all environments):
- RabbitMQ Management UI: `15672` (useful for monitoring)
- RabbitMQ Prometheus metrics: `15692` (needed for Grafana Alloy)
- Grafana Alloy OTLP endpoints: `4317`, `4318` (needed for observability)

**Rationale**:
- Management UIs are secured by authentication
- Monitoring ports are needed for observability stack
### Documentation Updates

Update `.env.example`:
```bash
# Application Ports (exposed in development and test, not in production)
# Production uses reverse proxy for external access
API_HOST_PORT=8000
FRONTEND_HOST_PORT=3000

# Management UI Ports (development only)
# Note: Only exposed via compose.override.yaml for local development
# Production and test environments use 'docker exec' for debugging
RABBITMQ_MGMT_HOST_PORT=15672

# Note: Infrastructure service ports are NOT exposed
# Use 'docker exec' to access them for debugging:
#   docker exec -it gamebot-postgres psql -U gamebot -d game_scheduler
#   docker exec -it gamebot-redis redis-cli
#   docker exec -it gamebot-rabbitmq rabbitmqctl status
#
# Note: Observability ports are NOT exposed externally
# Grafana Alloy collects metrics/traces via internal Docker network
# Services connect to grafana-alloy:4317 (gRPC) and grafana-alloy:4318 (HTTP)
``` docker exec -it gamebot-redis redis-cli
#   docker exec -it gamebot-rabbitmq rabbitmqctl status
```

## Implementation Guidance

### Objectives
### Key Tasks

1. **Update docker-compose.base.yml**:
   - Remove ALL `ports:` sections from all services
   - Infrastructure services: postgres, rabbitmq, redis
   - Application services: api, frontend
   - Observability services: grafana-alloy
   - Services communicate only via internal network

2. **Update compose.override.yaml** (development):
   - Add frontend port mapping: `"${FRONTEND_HOST_PORT:-3000}:80"`
   - Add api port mapping: `"${API_HOST_PORT:-8000}:8000"`
   - Add rabbitmq management port: `"${RABBITMQ_MGMT_HOST_PORT:-15672}:15672"`

3. **Update docker-compose.test.yml** (test environments):
   - Add frontend port mapping: `"${FRONTEND_HOST_PORT:-3000}:80"`
   - Add api port mapping: `"${API_HOST_PORT:-8000}:8000"`
   - No management UI ports

4. **Verify compose.production.yaml**:
   - Should have NO port mappings
   - Reverse proxy handles external routing

5. **Update .env.example**:
   - Document that ports are environment-specific
   - Explain observability uses internal network only
   - Add `docker exec` examples for debugging

6. **Update documentation**:
### Success Criteria
- Base configuration exposes zero ports
- Development exposes: frontend (3000), api (8000), rabbitmq management (15672)
- Test exposes: frontend (3000), api (8000) only
- Production exposes: zero ports (reverse proxy handles routing)
- No observability ports exposed (internal collection by Alloy)
- Documentation clearly explains architecture and `docker exec` usage
- No port conflicts when running multiple environments simultaneously
- No regression in functionality (all services communicate via internal network)
   - Add section on using `docker exec` for infrastructure service access
   - Update troubleshooting guides to use `docker exec` instead of localhost connections
   - Document that no infrastructure ports are exposed by design
### Dependencies
- Docker Compose with multi-file support (already in use)
- Existing layered compose configuration structure

### Success Criteria
- Test environments expose no infrastructure ports by default
- Development environment exposes all ports for debugging
- Production environment exposes only application and monitoring ports
- Clear documentation about port configuration options
- No regression in functionality (services communicate via internal network)

### Success Criteria
- No infrastructure ports exposed in any environment
- Only application ports (8000, 3000) and monitoring ports (15672, 15692, 4317, 4318) exposed
- Documentation clearly explains `docker exec` usage for debugging
- No port conflicts when running multiple instances simultaneously
- No regression in functionality (services communicate via internal network)
- Docker Compose Networking: https://docs.docker.com/compose/networking/
- Project containerization standards: `.github/instructions/containerization-docker-best-practices.instructions.md`
- Current base configuration: `docker-compose.base.yml` (Lines 15-70)
- Development overrides: `compose.override.yaml`
- Test configuration: `docker-compose.test.yml`

### Issue 3: Game Host Not Receiving Notifications

**Problem**: Game reminders are sent only to participants, but the game host does not receive notification reminders even though they are hosting the game.

**Impact**:
- Game hosts may forget about games they are hosting
- No reminder when they need to prepare or show up
- Asymmetric experience: participants get reminders, host doesn't
- Particularly problematic for games where host has setup responsibilities

**Current Behavior**:
```python
# services/bot/events/handlers.py _handle_game_reminder_due()
# Filters to real participants only
real_participants = [p for p in game.participants if p.user_id and p.user]

# Sends reminders to confirmed participants
for participant in confirmed_participants:
    await self._send_reminder_dm(...)

# Sends reminders to waitlist participants  
for participant in overflow_participants:
    await self._send_reminder_dm(...)

# Host (game.host.discord_id) is NOT included in notification loop
```

**Analysis**:
- Game host is stored separately in `GameSession.host_id` (separate from participants)
- Notification logic only iterates through `game.participants` list
- Host is not in participants list (removed in Phase 6 refactor)
- Host receives no DM reminder at scheduled times

**Desired Behavior**:
- Game host should receive the same reminder DMs as confirmed participants
- Host notification should include their role (e.g., "Reminder: You are hosting...")
- Host should receive reminder even if there are no other participants
- Consistent with user expectation that creator gets notified about their event

**Implementation Approach**:
```python
# After sending to confirmed participants, also send to host
if game.host and game.host.discord_id:
    try:
        await self._send_reminder_dm(
            user_discord_id=game.host.discord_id,
            game_title=game.title,
            game_time_unix=game_time_unix,
            reminder_minutes=reminder_event.reminder_minutes,
            is_waitlist=False,
            is_host=True,  # New parameter to customize message
        )
    except Exception as e:
        logger.error(f"Failed to send reminder to host {game.host.discord_id}: {e}")
```

**Files Affected**:
- `services/bot/events/handlers.py` - `_handle_game_reminder_due()` method
- `services/bot/events/handlers.py` - `_send_reminder_dm()` method (add is_host parameter)

### Issue 4: Notify Roles Not Mentioned in Initial Game Announcement

**Problem**: When a game is created with `notify_role_ids`, the role mentions might not be triggering Discord notifications as expected.

**Impact**:
- Role-based notifications feature may not be working fully
- Users who want to be pinged about specific game types might miss announcements
- Reduced engagement for games that rely on role-based notifications

**Current Behavior**:
```python
# services/bot/formatters/game_message.py format_game_announcement()
# Role mentions are formatted in message content
content = None
if notify_role_ids:
    role_mentions = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])
    content = role_mentions

return content, embed, view

# services/bot/events/handlers.py _create_game_announcement()
return format_game_announcement(
    game_id=str(game.id),
    notify_role_ids=game.notify_role_ids or [],  # Passed correctly
    # ...
)
```

**Analysis**:
- `notify_role_ids` field exists in database (`GameSession.notify_role_ids`)
- Frontend allows setting notify roles during game creation
- Bot formatter has code to format role mentions
- Role mentions should appear above embed in message content
- Discord format: `<@&role_id>` triggers notification for users with that role

**Verification Needed**:
- Check if role IDs are actually being stored in database
- Verify `game.notify_role_ids` is populated when message is created
- Confirm role mentions are appearing in Discord message content
- Test that users with mentioned roles receive Discord notifications
- Verify role IDs are valid snowflake strings

**Potential Issues**:
- notify_role_ids not being loaded from database with game object
- notify_role_ids being None/empty when it should have values
- Role IDs format incorrect or invalid
- Discord message content not being sent properly
- Permissions issue preventing bot from mentioning roles

**Files to Check**:
- `services/bot/events/handlers.py` - `_handle_game_created()` method
- `services/bot/events/handlers.py` - `_get_game_with_participants()` query
- `services/bot/formatters/game_message.py` - `format_game_announcement()` function
- `shared/models/game.py` - `GameSession.notify_role_ids` field
- Database: Check actual stored values in game_sessions table

## Additional Issues To Be Added

*Note: User may have more issues to document. This research file will be updated as additional issues are identified.*

### Issue 5: Unused Environment Variables

**Problem**: Several environment variables are defined in `.env.example` and `env/` files but are not actually used by any application code or Docker configurations, creating maintenance burden and confusion.

**Impact**:
- Confusion about which environment variables are actually required
- Maintenance overhead keeping unused variables in sync across files
- Potential security concerns if sensitive unused values are left in files
- Larger environment files with unnecessary documentation

**Identified Unused Variables**:

1. **`DISCORD_REDIRECT_URI`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`, all environment files
   - Passed to bot service in: `compose.yaml` (`DISCORD_REDIRECT_URI: ${DISCORD_REDIRECT_URI:-}`)
   - Used in code: **NO** - No Python code references this variable
   - OAuth redirect URI is constructed by API service using `API_URL` instead
   - Previous research (`20251130-oauth-redirect-uri-configuration-research.md`) confirmed it's unused
   - **Status**: UNUSED - Safe to remove from all locations

2. **`API_HOST`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`
   - Used in code: `services/api/config.py` loads `API_HOST` environment variable
   - Used in production: `services/api/main.py` passes to `uvicorn.Config(host=config.api_host)`
   - Used in development: `compose.override.yaml` hardcodes `--host 0.0.0.0` in command override
   - **Status**: USED IN PRODUCTION - Used when running via `python -m services.api.main`
   - **Action**: KEEP - Required for production uvicorn startup

3. **`API_PORT`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`
   - Used in code: `services/api/config.py` loads `API_PORT` environment variable
   - Used in production: `services/api/main.py` passes to `uvicorn.Config(port=config.api_port)`
   - Used in development: `compose.override.yaml` hardcodes `--port 8000` in command override
   - **Status**: USED IN PRODUCTION - Used when running via `python -m services.api.main`
   - **Action**: KEEP - Required for production uvicorn startup

4. **`POSTGRES_LOG_LEVEL`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`
   - Used in compose: `compose.yaml` postgres service command uses `${POSTGRES_LOG_LEVEL:-info}`
   - **Status**: USED - PostgreSQL container startup uses this for logging configuration
   - **Action**: KEEP

5. **`RABBITMQ_LOG_LEVEL`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`
   - Used in compose: `compose.yaml` rabbitmq service uses `${RABBITMQ_LOG_LEVEL:-info}`
   - **Status**: USED - RabbitMQ container startup uses this for logging configuration
   - **Action**: KEEP

6. **`REDIS_LOG_LEVEL`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`
   - Used in compose: `compose.yaml` redis service command uses `${REDIS_LOG_LEVEL:-notice}`
   - **Status**: USED - Redis container startup uses this for logging configuration
   - **Action**: KEEP

7. **`NGINX_LOG_LEVEL`**:
   - Defined in: `.env.example`, `env/env.dev`, `env/env.prod`
   - Used in compose: `compose.yaml` frontend service environment passes `NGINX_LOG_LEVEL`
   - Used in entrypoint: `docker/frontend-entrypoint.sh` substitutes into nginx config
   - Used in config: `docker/frontend-nginx.conf` uses `${NGINX_LOG_LEVEL}`
   - **Status**: USED - Nginx logging configuration uses this at runtime
   - **Action**: KEEP

**Analysis Summary**:

**Variables to REMOVE**:
- `DISCORD_REDIRECT_URI` - Completely unused, OAuth redirect URI constructed from API_URL instead

**Variables to KEEP** (actively used):
- `API_HOST` - Used by production API startup (services/api/main.py via uvicorn.Config)
- `API_PORT` - Used by production API startup (services/api/main.py via uvicorn.Config)
- `POSTGRES_LOG_LEVEL` - PostgreSQL logging configuration
- `RABBITMQ_LOG_LEVEL` - RabbitMQ logging configuration
- `REDIS_LOG_LEVEL` - Redis logging configuration
- `NGINX_LOG_LEVEL` - Nginx logging configuration
- `API_URL` - Frontend runtime configuration for API endpoint
- `FRONTEND_URL` - API CORS configuration

**Note on API_HOST and API_PORT**:
- Development override (`compose.override.yaml`) hardcodes uvicorn command with `--host 0.0.0.0 --port 8000`
- Production container uses `python -m services.api.main` which reads from config
- Tests verify these values are used correctly in uvicorn.Config
- These variables ARE used, just not in development mode

**Files Affected**:
- `.env.example` - Remove `DISCORD_REDIRECT_URI`
- `env/env.dev` - Remove `DISCORD_REDIRECT_URI`
- `env/env.prod` - Remove `DISCORD_REDIRECT_URI`
- `env/env.staging` - Remove `DISCORD_REDIRECT_URI`
- `env/env.int` - Remove `DISCORD_REDIRECT_URI`
- `env/env.e2e` - Remove `DISCORD_REDIRECT_URI`
- `compose.yaml` - Remove `DISCORD_REDIRECT_URI` from bot service environment section
- `DEPLOYMENT_QUICKSTART.md` - Remove reference to `DISCORD_REDIRECT_URI`

**Verification Needed**:
- Verify OAuth flow works without `DISCORD_REDIRECT_URI` environment variable (already confirmed in `20251130-oauth-redirect-uri-configuration-research.md`)
- Test bot service starts correctly without the unused environment variable

**Implementation Approach**:
1. Remove `DISCORD_REDIRECT_URI` from all environment files (`.env.example`, `env/env.*`)
2. Remove `DISCORD_REDIRECT_URI: ${DISCORD_REDIRECT_URI:-}` from bot service in `compose.yaml`
3. Remove documentation reference in `DEPLOYMENT_QUICKSTART.md`
4. Run OAuth flow test to confirm functionality unchanged
5. Verify all services start correctly in development and production modes

### Issue 6: Missing Game Completion Status Schedule Entries

**Problem**: The system only creates ONE `game_status_schedule` entry per game (SCHEDULED → IN_PROGRESS). It never creates a SECOND entry for the IN_PROGRESS → COMPLETED transition. This means NO games automatically transition to COMPLETED status, regardless of whether they have `expected_duration_minutes` set.

**Impact**:
- ALL games stay IN_PROGRESS forever (no automatic completion for any game)
- Historical game data completely inaccurate (all past games appear ongoing)
- Discord messages never update to show COMPLETED status
- Game lists cluttered with hundreds of "in progress" games
- No game completion notifications are ever sent
- Database query confirmed: All games only have `target_status=IN_PROGRESS` schedule entries

**Current Behavior** (Verified via database inspection):
```sql
SELECT gs.id, gs.title, gs.status, gs.expected_duration_minutes, 
       gss.target_status, gss.transition_time, gss.executed 
FROM game_sessions gs 
LEFT JOIN game_status_schedule gss ON gs.id = gss.game_id;

-- Result: ALL games only have ONE schedule entry with target_status='IN_PROGRESS'
-- NO games have a second entry with target_status='COMPLETED'
```

```python
# services/api/services/games.py - create_game() method (lines 240-249)
# Only creates SCHEDULED → IN_PROGRESS transition
if game.status == game_model.GameStatus.SCHEDULED.value:
    status_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,  # ← Only IN_PROGRESS!
        transition_time=game.scheduled_at,
        executed=False,
    )
    self.db.add(status_schedule)
    # MISSING: No code to create COMPLETED transition schedule!
```

**Root Cause Analysis**:
1. `create_game()` creates single schedule entry: `target_status=IN_PROGRESS`, `transition_time=scheduled_at`
2. At scheduled time: Status transition daemon processes entry, game transitions to IN_PROGRESS
3. **No code exists** to create a second schedule entry for COMPLETED transition
4. Game stays IN_PROGRESS forever
5. No completion notification ever created in database

**Game Creation Flow** (Actual):
1. User creates game with `scheduled_at` and optional `expected_duration_minutes`
2. **One** `game_status_schedule` entry created: `target_status=IN_PROGRESS`
3. At scheduled time: Game transitions to IN_PROGRESS
4. **Zero** further status transitions scheduled
5. Game remains IN_PROGRESS indefinitely (verified in production database)

**Desired Behavior**:
- System should create TWO status schedule entries at game creation
- First entry: SCHEDULED → IN_PROGRESS at `scheduled_at` time
- Second entry: IN_PROGRESS → COMPLETED at `scheduled_at + expected_duration_minutes`
- Games with `expected_duration_minutes=NULL` should use default duration (e.g., 60 minutes)
- Both status transitions should trigger Discord message updates

**Implementation Solution**:

**Primary Fix: Create COMPLETED Schedule Entry at Game Creation**
```python
# services/api/services/games.py - Modify create_game() method (after line 249)
# After creating IN_PROGRESS schedule, also create COMPLETED schedule

# Populate status transition schedule for SCHEDULED games
if game.status == game_model.GameStatus.SCHEDULED.value:
    # Create IN_PROGRESS transition (existing code)
    status_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=game.scheduled_at,
        executed=False,
    )
    self.db.add(status_schedule)
    
    # NEW: Create COMPLETED transition
    DEFAULT_GAME_DURATION_MINUTES = 60  # Default to 1 hour
    duration_minutes = expected_duration_minutes or DEFAULT_GAME_DURATION_MINUTES
    completion_time = game.scheduled_at + timedelta(minutes=duration_minutes)
    
    completion_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=completion_time,
        executed=False,
    )
    self.db.add(completion_schedule)
```

**Secondary Fix: Update Schedule Logic in update_game() Method**
```python
# services/api/services/games.py - Modify update_game() method (around lines 556-591)
# Currently only handles IN_PROGRESS schedule, needs to handle COMPLETED schedule too

if status_schedule_needs_update:
    # Get ALL existing status schedules
    status_schedule_result = await self.db.execute(
        select(game_status_schedule_model.GameStatusSchedule).where(
            game_status_schedule_model.GameStatusSchedule.game_id == game.id
        )
    )
    status_schedules = status_schedule_result.scalars().all()
    
    if game.status == game_model.GameStatus.SCHEDULED.value:
        # Find or create IN_PROGRESS schedule
        in_progress_schedule = next(
            (s for s in status_schedules if s.target_status == "IN_PROGRESS"), None
        )
        if in_progress_schedule:
            in_progress_schedule.transition_time = game.scheduled_at
            in_progress_schedule.executed = False
        else:
            # Create new IN_PROGRESS schedule (existing code)
            ...
        
        # Find or create COMPLETED schedule
        completed_schedule = next(
            (s for s in status_schedules if s.target_status == "COMPLETED"), None
        )
        DEFAULT_GAME_DURATION_MINUTES = 60
        duration_minutes = game.expected_duration_minutes or DEFAULT_GAME_DURATION_MINUTES
        completion_time = game.scheduled_at + timedelta(minutes=duration_minutes)
        
        if completed_schedule:
            completed_schedule.transition_time = completion_time
            completed_schedule.executed = False
        else:
            # Create new COMPLETED schedule
            ...
    else:
        # Game not SCHEDULED - delete all schedules
        for schedule in status_schedules:
            await self.db.delete(schedule)
```

**Files Requiring Changes**:
1. **`services/api/services/games.py`**:
   - `create_game()` method (line ~240-249): Add COMPLETED schedule creation
   - `update_game()` method (line ~556-591): Handle both IN_PROGRESS and COMPLETED schedules
   
2. **Configuration** (new constant):
   - Add `DEFAULT_GAME_DURATION_MINUTES = 60` constant
   - Could be in `shared/models/game.py` or separate config file

3. **Database Migration** (cleanup existing data):
   - Create migration to add missing COMPLETED schedules to existing IN_PROGRESS games
   - Calculate completion time as `scheduled_at + expected_duration_minutes` (or default)

**Testing Requirements**:
- Test game creation creates TWO schedule entries
- Test games with explicit `expected_duration_minutes` use that value
- Test games without duration use default (60 minutes)
- Test update_game() maintains both schedule entries correctly
- Test status transition daemon processes COMPLETED transitions
- Test Discord messages update when game reaches COMPLETED status
- Test that completion notifications are created and sent

**Migration Strategy for Existing Games**:
```sql
-- Find all IN_PROGRESS games without COMPLETED schedule
INSERT INTO game_status_schedule (id, game_id, target_status, transition_time, executed)
SELECT 
    gen_random_uuid(),
    gs.id,
    'COMPLETED',
    gs.scheduled_at + INTERVAL '60 minutes',  -- Default duration
    FALSE
FROM game_sessions gs
WHERE gs.status = 'IN_PROGRESS'
AND NOT EXISTS (
    SELECT 1 FROM game_status_schedule gss 
    WHERE gss.game_id = gs.id AND gss.target_status = 'COMPLETED'
);
```

### Issue 7: Init Service Has No Observability

**Problem**: The init service (`scripts/init_rabbitmq.py` and `docker/init-entrypoint.sh`) does not initialize OpenTelemetry instrumentation, so it produces no traces or logs to the observability stack.

**Impact**:
- No visibility into init service execution in Grafana Cloud
- Cannot trace database migrations or RabbitMQ initialization failures
- Difficult to debug deployment issues during initialization phase
- No metrics for init service duration or success/failure rates
- Init process is "black box" with only console output

**Current Behavior**:
```python
# scripts/init_rabbitmq.py - No telemetry initialization
def main() -> None:
    """Main initialization entry point."""
    print("=== RabbitMQ Infrastructure Initialization ===")
    # ... initialization logic ...
    # No init_telemetry() call
    # No OpenTelemetry spans or metrics
```

```bash
# docker/init-entrypoint.sh - No telemetry
echo "Running database migrations..."
alembic upgrade head
echo "✓ Migrations complete"
# No tracing or observability
```

**Analysis**:
- All other services initialize telemetry:
  - `services/api/app.py`: `init_telemetry("api-service")`
  - `services/bot/main.py`: `init_telemetry("bot-service")`
  - `services/scheduler/notification_daemon_wrapper.py`: `init_telemetry("notification-daemon")`
  - `services/scheduler/status_transition_daemon_wrapper.py`: `init_telemetry("status-transition-daemon")`
  - `services/retry/retry_daemon_wrapper.py`: `init_telemetry("retry-daemon")`
- Init service runs critical startup tasks:
  - Database migrations via `alembic upgrade head`
  - RabbitMQ infrastructure setup (exchanges, queues, bindings)
  - Schema verification
- Init service is short-lived (runs once at startup), but still valuable to trace
- Init failures block entire application startup

**Desired Behavior**:
- Init service should initialize OpenTelemetry with service name `"init-service"`
- Database migration steps should be traced with spans
- RabbitMQ infrastructure creation should be traced
- Console output should continue (for Docker logs) but also send to observability
- Init service duration and success metrics should be recorded

**Implementation Approach**:
```python
# scripts/init_rabbitmq.py - Add telemetry initialization
import logging
from shared.telemetry import init_telemetry
from opentelemetry import trace

def main() -> None:
    """Main initialization entry point."""
    # Initialize telemetry first
    init_telemetry("init-service")
    
    tracer = trace.get_tracer(__name__)
    
    print("=== RabbitMQ Infrastructure Initialization ===")
    
    with tracer.start_as_current_span("init.rabbitmq") as span:
        rabbitmq_url = os.getenv("RABBITMQ_URL")
        if not rabbitmq_url:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "RABBITMQ_URL not set"))
            print("✗ RABBITMQ_URL environment variable not set")
            sys.exit(1)
        
        print("Waiting for RabbitMQ...")
        wait_for_rabbitmq(rabbitmq_url)
        
        print("Creating RabbitMQ infrastructure...")
        try:
            create_infrastructure(rabbitmq_url)
            span.set_status(trace.Status(trace.StatusCode.OK))
            print("✓ RabbitMQ infrastructure initialized successfully")
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            print(f"✗ Failed to initialize RabbitMQ infrastructure: {e}")
            sys.exit(1)
```

```bash
# docker/init-entrypoint.sh - Add telemetry for migrations
echo "Running database migrations..."
# Wrap alembic command with telemetry span
PYTHONPATH=/app python3 -c "
from shared.telemetry import init_telemetry
from opentelemetry import trace
import subprocess
import sys

init_telemetry('init-service')
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span('init.database_migration') as span:
    result = subprocess.run(['alembic', 'upgrade', 'head'], capture_output=True)
    if result.returncode != 0:
        span.set_status(trace.Status(trace.StatusCode.ERROR, 'Migration failed'))
        span.record_exception(Exception(result.stderr.decode()))
        sys.exit(result.returncode)
    span.set_status(trace.Status(trace.StatusCode.OK))
"
echo "✓ Migrations complete"
```

**Files Affected**:
- `scripts/init_rabbitmq.py` - Add `init_telemetry()` call and span wrapping
- `docker/init-entrypoint.sh` - Add telemetry wrapper for alembic migrations
- `docker/init.Dockerfile` - Ensure OpenTelemetry packages installed (likely already via shared dependencies)

**Benefits**:
- Complete observability across all application services
- Trace init failures to specific step (migrations vs RabbitMQ setup)
- Monitor init service duration trends over time
- Correlate init issues with downstream service startup problems
- Visibility into cold-start behavior during deployments

### Issue 8: Infrastructure Metrics Missing service.name and Logs Not Collected

**Problem**: Infrastructure services (postgres, rabbitmq, redis) send metrics to Grafana Cloud but without `service.name` attributes, and their logs are not collected at all. Docker logs also have no rotation limits.

**Impact**:
- Infrastructure metrics lack `service.name` resource attribute (only have `job` and `instance` labels)
- Cannot filter/group infrastructure metrics by service in Grafana dashboards
- Inconsistent with application services which all have `service.name` from OpenTelemetry
- No centralized log aggregation for infrastructure services
- Docker logs grow unbounded, consuming disk space indefinitely
- Difficult to correlate infrastructure issues with application telemetry

**Current Behavior**:
```alloy
// grafana-alloy/config.alloy - Infrastructure metrics bypass OTEL processing
prometheus.scrape "integrations_postgres_exporter" {
  targets         = discovery.relabel.integrations_postgres_exporter.output
  forward_to      = [prometheus.remote_write.grafana_cloud_mimir.receiver]  // Direct to Mimir
  // No OTEL processor - no service.name attribute added
}

prometheus.scrape "integrations_rabbitmq" {
  targets = [{
    __address__ = "rabbitmq:15692",
    job         = "integrations/rabbitmq",
    instance    = "rabbitmq",
  }]
  forward_to = [prometheus.remote_write.grafana_cloud_mimir.receiver]  // Direct to Mimir
  // Only job and instance labels, no service.name
}
```

```bash
# Docker logs have no rotation limits
$ docker inspect gamebot-postgres | grep -A 5 "LogConfig"
"LogConfig": {
    "Type": "json-file",
    "Config": {}  # No max-size, max-file, or other limits
}
```

```yaml
# compose.yaml - No logging configuration for infrastructure services
services:
  postgres:
    image: postgres:17-alpine
    # ... no logging: section
    
  rabbitmq:
    image: rabbitmq:4.2-management-alpine
    # ... no logging: section
    
  redis:
    image: redis:7.4-alpine
    # ... no logging: section
    
  grafana-alloy:
    image: grafana/alloy:latest
    # ... no logging: section
```

**Analysis**:
- Infrastructure metrics currently go: Prometheus scraper → Direct to Mimir (bypasses OTEL)
- Application metrics go: OTEL SDK → OTLP receiver → Batch processor → Mimir (with service.name)
- Alloy self-monitoring goes: Prometheus → `otelcol.receiver.prometheus` → OTLP exporter (gets service.name)
- Infrastructure services need to route through OTEL processor to get resource attributes
- Docker logs have no rotation → unbounded disk growth on long-running deployments
- Infrastructure logs contain critical debugging information but aren't centralized:
  - PostgreSQL: query logs, connection errors, replication issues
  - RabbitMQ: queue depths, message delivery failures, connection tracking
  - Redis: cache hit/miss rates, memory usage, eviction events
  - Grafana Alloy: pipeline processing, scrape errors, delivery failures

**Desired Behavior**:
1. **OTEL Resource Attributes**: Infrastructure metrics should have `service.name` attribute
2. **Docker Log Rotation**: All services should have max-size and max-file limits
3. **Log Aggregation**: Infrastructure logs should be collected and sent to Grafana Cloud
4. **Unified Observability**: Consistent resource attributes across all services

**Implementation Solutions**:

**Solution 1: Add service.name to Infrastructure Metrics via OTEL Processor**
```alloy
// grafana-alloy/config.alloy - Route infrastructure metrics through OTEL

// Convert Prometheus metrics to OTEL format with resource attributes
otelcol.receiver.prometheus "postgres_metrics" {
  output {
    metrics = [otelcol.processor.resource.add_service_name_postgres.input]
  }
}

otelcol.processor.resource "add_service_name_postgres" {
  attributes {
    insert {
      key   = "service.name"
      value = "postgres"
    }
  }
  output {
    metrics = [otelcol.processor.batch.default.input]
  }
}

// Update postgres scrape to send to OTEL instead of direct Mimir
prometheus.scrape "integrations_postgres_exporter" {
  targets         = discovery.relabel.integrations_postgres_exporter.output
  forward_to      = [otelcol.receiver.prometheus.postgres_metrics.receiver]  // Changed!
  job_name        = "integrations/postgres_exporter"
  scrape_interval = "60s"
}

// Similar for redis and rabbitmq...
```

**Solution 2: Docker Logging Driver with Rotation (Immediate Fix)**
```yaml
# compose.yaml - Add to all services
services:
  postgres:
    image: postgres:17-alpine
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service,environment"
    labels:
      service: "postgres"
      environment: "${ENVIRONMENT:-production}"
```

**Solution 3: Grafana Alloy Docker Log Collection**
```yaml
# grafana-alloy/config.alloy - Add Docker log collection
loki.source.docker "infrastructure_logs" {
  host = "unix:///var/run/docker.sock"
  targets = [
    {
      __meta_docker_container_name = "gamebot-postgres",
      job = "postgres",
    },
    {
      __meta_docker_container_name = "gamebot-rabbitmq",
      job = "rabbitmq",
    },
    {
      __meta_docker_container_name = "gamebot-redis",
      job = "redis",
    },
  ]
  forward_to = [loki.write.grafana_cloud.receiver]
  relabel_rules = loki.relabel.docker_logs.rules
}

loki.relabel "docker_logs" {
  rule {
    source_labels = ["__meta_docker_container_name"]
    target_label  = "container"
  }
  rule {
    source_labels = ["__meta_docker_container_label_service"]
    target_label  = "service"
  }
}
```

```yaml
# compose.yaml - Mount Docker socket for Alloy
  grafana-alloy:
    image: grafana/alloy:latest
    volumes:
      - ./grafana-alloy/config.alloy:/etc/alloy/config.alloy:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro  # NEW
```

**Recommendation: Phased Approach**
1. **Phase 1**: Add service.name to infrastructure metrics (Solution 1) - improves filtering/grouping
2. **Phase 2**: Add Docker log rotation to all services (Solution 2) - prevents disk exhaustion
3. **Phase 3**: Configure Grafana Alloy to collect Docker logs (Solution 3) - centralizes logs

**Detailed Implementation**:

**Phase 1: Add service.name to Infrastructure Metrics**
```alloy
// grafana-alloy/config.alloy - Add OTEL processors for each infrastructure service

// PostgreSQL metrics with service.name
otelcol.receiver.prometheus "postgres_metrics" {
  output {
    metrics = [otelcol.processor.resource.add_service_name_postgres.input]
  }
}

otelcol.processor.resource "add_service_name_postgres" {
  attributes {
    insert {
      key   = "service.name"
      value = "postgres"
    }
  }
  output {
    metrics = [otelcol.processor.batch.default.input]
  }
}

prometheus.scrape "integrations_postgres_exporter" {
  targets         = discovery.relabel.integrations_postgres_exporter.output
  forward_to      = [otelcol.receiver.prometheus.postgres_metrics.receiver]  // NEW: Route through OTEL
  job_name        = "integrations/postgres_exporter"
  scrape_interval = "60s"
}

// Redis metrics with service.name
otelcol.receiver.prometheus "redis_metrics" {
  output {
    metrics = [otelcol.processor.resource.add_service_name_redis.input]
  }
}

otelcol.processor.resource "add_service_name_redis" {
  attributes {
    insert {
      key   = "service.name"
      value = "redis"
    }
  }
  output {
    metrics = [otelcol.processor.batch.default.input]
  }
}

prometheus.scrape "integrations_redis_exporter" {
  targets         = prometheus.exporter.redis.integrations_redis_exporter.targets
  forward_to      = [otelcol.receiver.prometheus.redis_metrics.receiver]  // NEW: Route through OTEL
  job_name        = "integrations/redis_exporter"
  scrape_interval = "60s"
}

// RabbitMQ metrics with service.name
otelcol.receiver.prometheus "rabbitmq_metrics" {
  output {
    metrics = [otelcol.processor.resource.add_service_name_rabbitmq.input]
  }
}

otelcol.processor.resource "add_service_name_rabbitmq" {
  attributes {
    insert {
      key   = "service.name"
      value = "rabbitmq"
    }
  }
  output {
    metrics = [otelcol.processor.batch.default.input]
  }
}

prometheus.scrape "integrations_rabbitmq" {
  targets = [{
    __address__ = "rabbitmq:15692",
    job         = "integrations/rabbitmq",
    instance    = "rabbitmq",
  }]
  forward_to      = [otelcol.receiver.prometheus.rabbitmq_metrics.receiver]  // NEW: Route through OTEL
  scrape_interval = "60s"
}

// Remove prometheus.remote_write since all metrics now go through OTLP
// DELETE: prometheus.remote_write "grafana_cloud_mimir" { ... }
```

**Phase 2: Docker Log Rotation (Quick Win)**
```yaml
# Create x-logging-default YAML anchor in compose.yaml
x-logging-default: &logging-default
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
    compress: "true"
    labels: "service,environment"

services:
  postgres:
    logging: *logging-default
    labels:
      service: "postgres"
      environment: "${ENVIRONMENT:-production}"
      
  rabbitmq:
    logging: *logging-default
    labels:
      service: "rabbitmq"
      environment: "${ENVIRONMENT:-production}"
      
  redis:
    logging: *logging-default
    labels:
      service: "redis"
      environment: "${ENVIRONMENT:-production}"
      
  grafana-alloy:
    logging: *logging-default
    labels:
      service: "grafana-alloy"
      environment: "${ENVIRONMENT:-production}"
```

**Phase 3: Grafana Alloy Log Collection**
```alloy
// grafana-alloy/config.alloy - Add Docker log collection
loki.source.docker "containers" {
  host             = "unix:///var/run/docker.sock"
  targets          = discovery.docker.containers.targets
  forward_to       = [loki.process.add_static_labels.receiver]
  refresh_interval = "5s"
}

discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"
  
  filter {
    name   = "label"
    values = ["service"]  // Only collect containers with 'service' label
  }
}

loki.process "add_static_labels" {
  forward_to = [loki.write.grafana_cloud_loki.receiver]
  
  stage.docker {}  // Parse Docker JSON logs
  
  stage.labels {
    values = {
      service     = "",  // From Docker label
      environment = "",  // From Docker label
      container   = "",  // From Docker metadata
    }
  }
}
```

```yaml
# compose.yaml - Mount Docker socket for Alloy
  grafana-alloy:
    image: grafana/alloy:latest
    volumes:
      - ./grafana-alloy/config.alloy:/etc/alloy/config.alloy:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    user: "${ALLOY_USER_ID:-0}"  // May need root for socket access
```

**Files Affected**:
- `grafana-alloy/config.alloy` - Add OTEL resource processors and route metrics through OTLP
- `compose.yaml` - Add logging configuration and labels to all services
- `.env.example` - Document ENVIRONMENT variable for log labels
- Documentation - Explain unified observability architecture

**Testing Requirements**:
- Verify infrastructure metrics have `service.name` attribute in Grafana Cloud
- Test filtering metrics by service.name in Grafana dashboards
- Verify log files rotate when size limit reached
- Verify old log files are compressed
- Test log collection in Grafana Alloy
- Confirm infrastructure logs appear in Grafana Cloud Loki
- Test log queries filtering by service label
- Verify no disk space exhaustion after extended runtime

**Benefits**:
- **Consistent Resource Attributes**: All services (application + infrastructure) have `service.name`
- **Improved Dashboards**: Can filter/group infrastructure metrics by service
- **Prevents Disk Exhaustion**: Log rotation prevents unbounded disk usage
- **Centralized Logs**: All logs (application + infrastructure) in Grafana Cloud
- **Unified Observability**: Correlate infrastructure and application telemetry
- **Searchable Infrastructure Logs**: Query PostgreSQL/RabbitMQ/Redis logs with LogQL
- **Historical Analysis**: Track infrastructure behavior trends over time
