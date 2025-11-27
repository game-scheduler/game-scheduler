<!-- markdownlint-disable-file -->

# Task Details: Discord Game Scheduling System

## Research Reference

**Source Research**: #file:../research/20251114-discord-game-scheduling-system-research.md

## Phase 1: Infrastructure Setup

### Task 1.1: Create Docker development environment

Create `docker-compose.yml` with services for bot, api, scheduler, postgres, rabbitmq, redis. Include development volume mounts and environment configuration.

- **Files**:
  - `docker-compose.yml` - Multi-service orchestration
  - `.env.example` - Environment variable template
  - `docker/bot.Dockerfile` - Discord bot service image
  - `docker/api.Dockerfile` - FastAPI service image
  - `docker/scheduler.Dockerfile` - Celery service image
- **Success**:
  - All services start with `docker-compose up`
  - Health checks pass for all services
  - Services can communicate via internal network
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1341-1360) - Deployment architecture
  - #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker guidelines
- **Dependencies**:
  - Docker Engine 24+
  - Docker Compose 2.20+

### Task 1.2: Configure PostgreSQL database with schema

Create SQLAlchemy models for all entities with UTC timestamp handling. Set up Alembic for migrations.

- **Files**:
  - `shared/models/__init__.py` - SQLAlchemy models export
  - `shared/models/user.py` - User model with discordId
  - `shared/models/guild.py` - GuildConfiguration model
  - `shared/models/channel.py` - ChannelConfiguration model
  - `shared/models/game.py` - GameSession model
  - `shared/models/participant.py` - GameParticipant model with nullable userId
  - `alembic/env.py` - Alembic configuration
  - `alembic/versions/001_initial_schema.py` - Initial migration
- **Success**:
  - Database migrations create all tables
  - Foreign key constraints enforced
  - TIMESTAMPTZ columns store UTC correctly
  - Nullable userId constraint works for placeholders
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 856-947) - Database schema design
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1315-1321) - SQLAlchemy configuration
- **Dependencies**:
  - PostgreSQL 15+
  - SQLAlchemy 2.0+
  - Alembic 1.12+

### Task 1.3: Set up RabbitMQ message broker

Configure RabbitMQ with exchanges, queues, and bindings for event-driven communication between services.

- **Files**:
  - `shared/messaging/config.py` - RabbitMQ connection setup
  - `shared/messaging/events.py` - Event schema definitions
  - `shared/messaging/publisher.py` - Event publishing client
  - `shared/messaging/consumer.py` - Event consumption framework
  - `rabbitmq/definitions.json` - Queue and exchange definitions
- **Success**:
  - RabbitMQ accessible at amqp://localhost:5672
  - Events published from one service reach others
  - Dead letter queue configured for failures
  - Management UI accessible at http://localhost:15672
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 61-70) - RabbitMQ capabilities
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1425-1510) - Message flow examples
- **Dependencies**:
  - RabbitMQ 3.12+
  - aio-pika 9.0+ (async Python client)

### Task 1.4: Configure Redis for caching

Set up Redis for session storage, role caching, and display name caching with TTL support.

- **Files**:
  - `shared/cache/client.py` - Redis connection wrapper
  - `shared/cache/keys.py` - Cache key pattern definitions
  - `shared/cache/ttl.py` - TTL configuration constants
- **Success**:
  - Redis accessible at redis://localhost:6379
  - Cache operations complete in < 5ms
  - TTL expiration works correctly
  - Connection pooling configured
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 72-81) - Redis usage
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 199-247) - Display name caching
- **Dependencies**:
  - Redis 7+
  - redis-py 5.0+ with async support

### Task 1.5: Create shared data models package

Build Python package with SQLAlchemy models, Pydantic schemas, and shared utilities accessible to all services.

- **Files**:
  - `shared/setup.py` - Package installation script
  - `shared/models/` - SQLAlchemy ORM models
  - `shared/schemas/` - Pydantic request/response models
  - `shared/utils/timezone.py` - UTC handling utilities
  - `shared/utils/discord.py` - Discord API helpers
- **Success**:
  - Package installable with `pip install -e ./shared`
  - All services can import shared models
  - Type hints work correctly in IDEs
  - No circular dependencies
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 856-947) - Schema definitions
  - #file:../../.github/instructions/python.instructions.md - Python conventions
- **Dependencies**:
  - None (foundational package)

## Phase 2: Discord Bot Service

### Task 2.1: Initialize discord.py bot with Gateway connection

Set up discord.py bot with intents, auto-reconnect, and error handling. Register bot commands and load configuration.

- **Files**:
  - `services/bot/main.py` - Bot entry point
  - `services/bot/bot.py` - Bot class with Gateway setup
  - `services/bot/config.py` - Configuration loading
  - `services/bot/requirements.txt` - Python dependencies
- **Success**:
  - Bot connects to Discord Gateway
  - Bot responds to ready event
  - Auto-reconnect on disconnect
  - Intents configured for guilds, messages, reactions
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 6-19) - Discord API basics
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1361-1389) - Bot service responsibilities
- **Dependencies**:
  - discord.py 2.3+
  - Task 1.5 (shared models)

### Task 2.2: Implement slash commands for game management

Create slash commands: /list-games, /my-games, /config-guild, /config-channel with role-based access control.

- **Files**:
  - `services/bot/commands/__init__.py` - Command registration
  - `services/bot/commands/list_games.py` - List games command
  - `services/bot/commands/my_games.py` - User's games command
  - `services/bot/commands/config_guild.py` - Guild config command (admin)
  - `services/bot/commands/config_channel.py` - Channel config command (admin)
  - `services/bot/commands/decorators.py` - Permission check decorators with `get_permissions()` helper
- **Success**:
  - All commands registered in Discord
  - Commands respond within 3 seconds
  - Admin commands check permissions reliably
  - Error messages display clearly
  - Permission checks handle both Member and interaction contexts
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1361-1389) - Bot command responsibilities
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 103-112) - Role permissions
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 138-145) - Permission checking patterns
- **Dependencies**:
  - Task 2.1 (bot initialization)
  - Task 1.2 (database models)

### Task 2.3: Build game announcement message formatter with buttons

Create message formatter that uses Discord mentions and timestamps, with persistent button views.

- **Files**:
  - `services/bot/formatters/game_message.py` - Message content formatter
  - `services/bot/views/game_view.py` - Button view class
  - `services/bot/utils/discord_format.py` - Discord formatting utilities
- **Success**:
  - Messages use `<@user_id>` mention format
  - Timestamps use `<t:unix:F>` format
  - Buttons persist across bot restarts
  - Buttons show correct enabled/disabled state
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1190-1231) - Discord interaction pattern
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 149-195) - Display name handling
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1037-1072) - Timezone formatting
- **Dependencies**:
  - Task 2.1 (bot initialization)

### Task 2.4: Implement button interaction handlers

Handle INTERACTION_CREATE events for join/leave buttons with deferred responses and RabbitMQ event publishing.

- **Files**:
  - `services/bot/handlers/button_handler.py` - Button interaction dispatcher
  - `services/bot/handlers/join_game.py` - Join button logic
  - `services/bot/handlers/leave_game.py` - Leave button logic
  - `services/bot/handlers/utils.py` - Interaction helpers
- **Success**:
  - Deferred response sent within 3 seconds
  - Validation checks complete before publishing event
  - Events published to RabbitMQ successfully
  - User receives confirmation message
  - Message edited with updated participant list
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1232-1270) - Button implementation
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1425-1477) - Join game message flow
- **Dependencies**:
  - Task 2.3 (message formatter)
  - Task 1.3 (RabbitMQ setup)

### Task 2.5: Set up RabbitMQ event publishing and subscriptions

Configure event publishing for user actions and subscriptions for game updates and notifications.

- **Files**:
  - `services/bot/events/publisher.py` - Event publishing wrapper
  - `services/bot/events/handlers.py` - Event subscription handlers
  - `services/bot/events/schemas.py` - Event payload definitions
- **Success**:
  - Button clicks publish events successfully
  - Bot receives game.updated events
  - Bot receives notification.send_dm events
  - Event processing is idempotent
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1511-1568) - Event schemas
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1361-1389) - Bot communication patterns
- **Dependencies**:
  - Task 1.3 (RabbitMQ setup)
  - Task 2.4 (button handlers)

### Task 2.6: Implement role authorization checks

Build service to check user's Discord roles against configured allowed roles with Redis caching.

- **Files**:
  - `services/bot/auth/role_checker.py` - Role verification service
  - `services/bot/auth/permissions.py` - Permission flag utilities
  - `services/bot/auth/cache.py` - Role caching wrapper
  - `services/bot/commands/decorators.py` - Permission check decorators (uses `get_permissions()` helper)
- **Success**:
  - Roles fetched from Discord API
  - Results cached in Redis with 5-minute TTL
  - Permission checks work reliably for all commands
  - Handles both Member and interaction permission contexts
  - Cache invalidation on critical operations
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 103-123) - Role permissions
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 138-145) - Permission checking patterns
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 821-854) - Role authorization
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 990-1036) - Middleware implementation
- **Dependencies**:
  - Task 1.4 (Redis setup)
  - Task 2.2 (slash commands)

## Phase 3: Web API Service

### Task 3.1: Initialize FastAPI application with middleware

Create FastAPI app with CORS, authentication middleware, error handling, and OpenAPI documentation.

- **Files**:
  - `services/api/main.py` - FastAPI application entry
  - `services/api/app.py` - App factory with middleware
  - `services/api/config.py` - Configuration settings
  - `services/api/middleware/cors.py` - CORS configuration
  - `services/api/middleware/error_handler.py` - Global exception handling
  - `services/api/requirements.txt` - Python dependencies
- **Success**:
  - API accessible at http://localhost:8000
  - OpenAPI docs at /docs
  - CORS configured for frontend origin
  - Validation errors return 422 with details
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 30-39) - FastAPI capabilities
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1390-1424) - Web API responsibilities
- **Dependencies**:
  - FastAPI 0.104+
  - Uvicorn 0.24+ (ASGI server)
  - Task 1.5 (shared models)

### Task 3.2: Implement Discord OAuth2 authentication flow

Build OAuth2 authorization code flow with token exchange, refresh, and user info fetching.

- **Files**:
  - `services/api/auth/oauth2.py` - OAuth2 flow implementation
  - `services/api/auth/tokens.py` - Token management
  - `services/api/auth/discord_client.py` - Discord API client
  - `services/api/routes/auth.py` - Authentication endpoints
  - `services/api/dependencies/auth.py` - Current user dependency
- **Success**:
  - Users can log in via Discord
  - Access tokens stored securely (encrypted)
  - Token refresh works automatically
  - User info and guilds fetched correctly
  - Sessions maintained across requests
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 95-102) - OAuth2 scopes
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 752-795) - OAuth2 implementation
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 796-820) - Token management
- **Dependencies**:
  - Task 3.1 (FastAPI setup)
  - Task 1.4 (Redis for sessions)

### Task 3.3: Create role-based authorization middleware

Build middleware to verify user has required roles for protected endpoints using Discord API.

- **Files**:
  - `services/api/auth/roles.py` - Role verification service
  - `services/api/dependencies/permissions.py` - Permission check dependencies
  - `services/api/middleware/authorization.py` - Auth middleware
- **Success**:
  - Protected endpoints check user roles
  - Guild-specific permissions enforced
  - Channel-specific permissions enforced
  - Cache hit rate > 90% for role checks
  - 403 errors returned for insufficient permissions
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 821-854) - Role authorization
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 990-1036) - Permission checking
- **Dependencies**:
  - Task 3.2 (OAuth2 auth)
  - Task 1.4 (Redis caching)

### Task 3.4: Build guild and channel configuration endpoints

Create CRUD endpoints for guild and channel settings with inheritance preview.

- **Files**:
  - `services/api/routes/guilds.py` - Guild configuration endpoints
  - `services/api/routes/channels.py` - Channel configuration endpoints
  - `services/api/schemas/config.py` - Configuration request/response schemas
  - `services/api/services/config.py` - Configuration business logic
- **Success**:
  - GET /api/v1/guilds returns user's guilds
  - GET /api/v1/guilds/{id}/channels returns configured channels
  - POST/PUT endpoints update configurations
  - Responses show inherited vs custom settings
  - Only authorized users can modify settings
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 856-947) - Configuration schema
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 948-989) - Settings inheritance
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1070-1117) - Inheritance implementation
- **Dependencies**:
  - Task 3.3 (authorization)
  - Task 1.2 (database models)

### Task 3.5: Implement game management endpoints

Create endpoints for game CRUD operations with pre-populated participant validation.

- **Files**:
  - `services/api/routes/games.py` - Game management endpoints
  - `services/api/schemas/game.py` - Game request/response schemas
  - `services/api/services/games.py` - Game business logic
  - `services/api/services/participant_resolver.py` - @mention validation service
- **Success**:
  - POST /api/v1/games creates game with validation
  - Invalid @mentions return 422 with suggestions
  - GET /api/v1/games filters by guild/channel
  - PUT /api/v1/games/{id} updates game (host only)
  - DELETE cancels game with notifications
  - Events published to RabbitMQ on changes
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 313-417) - Pre-population feature
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 418-499) - Participant resolution
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 500-614) - Validation and error handling
- **Dependencies**:
  - Task 3.4 (config endpoints)
  - Task 1.3 (RabbitMQ)

### Task 3.6: Build display name resolution service

Implement service to resolve Discord user IDs to guild-specific display names with Redis caching.

- **Files**:
  - `services/api/services/display_names.py` - Display name resolver
  - `services/api/services/discord_api.py` - Discord API wrapper
  - `services/api/utils/cache.py` - Caching utilities
- **Success**:
  - Batch resolution for participant lists
  - Names resolved using nick > global_name > username
  - Results cached with 5-minute TTL
  - Graceful handling of users who left guild
  - API responses include resolved displayName fields
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 125-148) - User identity strategy
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 149-195) - Storage and rendering
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 196-247) - Resolution service
- **Dependencies**:
  - Task 3.5 (game endpoints)
  - Task 1.4 (Redis caching)

### Task 3.7: Implement settings inheritance resolution logic

Build service to resolve game settings using guild → channel → game hierarchy.

- **Files**:
  - `services/api/services/settings_resolver.py` - Settings inheritance logic
  - `services/api/utils/inheritance.py` - Inheritance utilities
- **Success**:
  - Correct settings resolved for each game
  - Inheritance chain visible in responses
  - Default values applied when not specified
  - Override values preserved correctly
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 948-989) - Inheritance hierarchy
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1070-1117) - Resolution service
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1118-1176) - Game creation with inheritance
- **Dependencies**:
  - Task 3.4 (config endpoints)
  - Task 3.5 (game endpoints)

## Phase 4: Web Dashboard Frontend

### Task 4.1: Set up React application with Material-UI

Initialize React app with TypeScript, Material-UI, React Router, and API client configuration.

- **Files**:
  - `frontend/package.json` - Dependencies
  - `frontend/src/index.tsx` - App entry point
  - `frontend/src/App.tsx` - Root component with routing
  - `frontend/src/theme.ts` - Material-UI theme
  - `frontend/src/api/client.ts` - Axios client with auth interceptor
  - `frontend/src/types/` - TypeScript type definitions
- **Success**:
  - App runs at http://localhost:3000
  - Material-UI components render correctly
  - Routing works for all pages
  - API client includes auth headers
  - TypeScript compilation succeeds
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 83-94) - React and Material-UI
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1315-1321) - Frontend stack
- **Dependencies**:
  - React 18+
  - Material-UI 5+
  - TypeScript 5+

### Task 4.2: Implement OAuth2 login flow with redirect handling

Build login page with Discord OAuth2 redirect and callback handling with token storage.

- **Files**:
  - `frontend/src/pages/Login.tsx` - Login page component
  - `frontend/src/pages/AuthCallback.tsx` - OAuth2 callback handler
  - `frontend/src/contexts/AuthContext.tsx` - Authentication state
  - `frontend/src/hooks/useAuth.ts` - Auth hook
  - `frontend/src/utils/auth.ts` - Token storage utilities
- **Success**:
  - "Login with Discord" button redirects correctly
  - Callback page exchanges code for token
  - Token stored securely in localStorage
  - Auth state persists across page refreshes
  - Protected routes redirect to login
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 752-795) - OAuth2 flow
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 796-820) - Token management
- **Dependencies**:
  - Task 4.1 (React setup)
  - Task 3.2 (API OAuth2 endpoints)

### Task 4.3: Build guild and channel management pages

Create pages for viewing and editing guild/channel configurations with inheritance preview.

- **Files**:
  - `frontend/src/pages/GuildSelection.tsx` - Guild list page
  - `frontend/src/pages/GuildDashboard.tsx` - Guild overview page
  - `frontend/src/pages/GuildConfig.tsx` - Guild settings editor
  - `frontend/src/pages/ChannelConfig.tsx` - Channel settings editor
  - `frontend/src/components/InheritancePreview.tsx` - Shows inherited values
- **Success**:
  - Guild list shows user's guilds with bot
  - Configuration forms display current settings
  - Inherited values shown with visual indicators
  - Changes save successfully to API
  - Form validation matches backend rules
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 948-989) - Settings inheritance
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1390-1424) - Web dashboard pages
- **Dependencies**:
  - Task 4.2 (auth flow)
  - Task 3.4 (config API)

### Task 4.4: Create game management interface

Build pages for browsing games, creating games with DateTimePicker, and managing hosted games.

- **Files**:
  - `frontend/src/pages/BrowseGames.tsx` - Game list with filters
  - `frontend/src/pages/CreateGame.tsx` - Game creation form
  - `frontend/src/pages/GameDetails.tsx` - Game details and participant list
  - `frontend/src/pages/MyGames.tsx` - Host's game management
  - `frontend/src/components/GameCard.tsx` - Game display component
  - `frontend/src/components/ParticipantList.tsx` - Participant display
- **Success**:
  - Game list displays with filters
  - DateTimePicker uses browser's timezone
  - Times sent to API as UTC ISO strings
  - Display names rendered for all participants
  - Host can edit/cancel their games
  - Real-time updates when participants join
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1073-1117) - Game creation
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 248-276) - API response pattern
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 277-311) - Frontend rendering
- **Dependencies**:
  - Task 4.3 (guild pages)
  - Task 3.5 (game API)

### Task 4.5: Implement participant pre-population with validation

Add multi-line input for initial participants with validation error display and disambiguation UI.

- **Files**:
  - `frontend/src/components/ParticipantInput.tsx` - Multi-line participant input
  - `frontend/src/components/ValidationErrors.tsx` - Error display with suggestions
  - `frontend/src/components/MentionChip.tsx` - Clickable suggestion chips
  - `frontend/src/utils/validation.ts` - Client-side validation helpers
- **Success**:
  - Input accepts @mentions and plain text
  - Form preserves data on validation error
  - Errors display with disambiguation chips
  - Clicking suggestion replaces invalid mention
  - Successfully resolved participants shown clearly
  - Form re-submits after correction
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 313-417) - Pre-population feature
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 500-614) - Validation error handling
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 615-750) - Frontend error recovery
- **Dependencies**:
  - Task 4.4 (game interface)
  - Task 3.5 (game API with validation)

## Phase 5: Scheduler Service

### Task 5.1: Set up Celery worker with RabbitMQ broker

Configure Celery app with RabbitMQ broker, result backend, and worker pool settings.

- **Files**:
  - `services/scheduler/celery_app.py` - Celery application
  - `services/scheduler/config.py` - Celery configuration
  - `services/scheduler/worker.py` - Worker entry point
  - `services/scheduler/beat.py` - Beat scheduler entry
  - `services/scheduler/requirements.txt` - Python dependencies
- **Success**:
  - Workers start and connect to RabbitMQ
  - Beat scheduler runs periodic tasks
  - Tasks execute reliably with retries
  - Dead letter queue handles failures
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 40-55) - Celery capabilities
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1341-1360) - Scheduler service deployment
- **Dependencies**:
  - Celery 5.3+
  - Task 1.3 (RabbitMQ)
  - Task 1.4 (Redis backend)

### Task 5.2: Implement notification check task

Create periodic task to query upcoming games and schedule notification delivery tasks.

- **Files**:
  - `services/scheduler/tasks/check_notifications.py` - Periodic check task
  - `services/scheduler/tasks/schedule_notification.py` - Per-game notification scheduler
  - `services/scheduler/utils/notification_windows.py` - Time window calculations
- **Success**:
  - Task runs every 5 minutes via Beat
  - Queries games with upcoming scheduled_at times
  - Resolves reminder settings using inheritance
  - Creates notification tasks for each participant
  - Tracks sent notifications to avoid duplicates
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1584) - Notification responsibilities
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1510-1538) - Reminder flow
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 948-989) - Settings inheritance
- **Dependencies**:
  - Task 5.1 (Celery setup)
  - Task 1.2 (database models)

### Task 5.3: Build notification delivery task

Create task to publish notification events to bot service queue for DM delivery.

- **Files**:
  - `services/scheduler/tasks/send_notification.py` - Notification task
  - `services/scheduler/services/notification_service.py` - Notification logic
- **Success**:
  - Events published to notification queue
  - Includes user ID, game details, and timestamp
  - Bot service receives and sends DMs
  - Delivery status tracked in database
  - Failed deliveries retry with exponential backoff
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1510-1538) - Notification message flow
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1539-1568) - Event schemas
- **Dependencies**:
  - Task 5.2 (notification check)
  - Task 1.3 (RabbitMQ)

### Task 5.4: Add game status update tasks

Create tasks to update game status from SCHEDULED → IN_PROGRESS → COMPLETED based on time.

- **Files**:
  - `services/scheduler/tasks/update_game_status.py` - Status update task
  - `services/scheduler/utils/status_transitions.py` - Status state machine
- **Success**:
  - Games marked IN_PROGRESS at start time
  - Games marked COMPLETED after duration
  - Button states updated in Discord messages
  - Status change events published
  - Historical game data preserved
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 856-947) - GameSession status field
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1584) - Status update responsibilities
- **Dependencies**:
  - Task 5.1 (Celery setup)
  - Task 1.2 (database models)

## Phase 6: Refactor Host from Participants

### Task 6.1: Remove host from participants during game creation

Stop adding the game host as a GameParticipant record when creating games.

- **Files**:
  - `services/api/services/games.py` - Remove host from initial participant creation (lines 176-184)
  - `services/api/routes/games.py` - Update join endpoint documentation if needed
  - `tests/services/api/services/test_games.py` - Update game creation tests
  - `tests/services/api/routes/test_games.py` - Update game creation tests
- **Success**:
  - Game creation no longer adds host as GameParticipant
  - Host stored only in GameSession.host_id
  - Participant count excludes host
  - Existing games' hosts removed from participant list via data migration
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1652-1680) - Host field separation requirement
- **Dependencies**:
  - None (straightforward removal)

### Task 6.2: Update API responses to show host separately

Update GameResponse schema and service to return host information separately.

- **Files**:
  - `shared/schemas/game.py` - Add `host` field to GameResponse (ParticipantResponse format)
  - `services/api/services/games.py` - Load host user data for response
  - `services/api/routes/games.py` - Ensure host data included in responses
- **Success**:
  - GameResponse includes `host: ParticipantResponse` field
  - Host information includes discord_id, display_name, resolved_display_name
  - Participant list does not include host
  - All game endpoints return consistent structure
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1652-1680) - Desired API structure
- **Dependencies**:
  - Task 6.1 completion

### Task 6.3: Update database migration for existing data

Create migration to remove any existing host records from game_participants table.

- **Files**:
  - `alembic/versions/YYYYMM01_remove_host_from_participants.py` - Data migration
- **Success**:
  - Migration identifies GameParticipant records where user_id matches GameSession.host_id
  - All such records deleted safely
  - Migration includes rollback logic
  - No data loss for non-host participants
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1652-1680) - Data structure changes
- **Dependencies**:
  - Task 6.1 completion (code change first, then data migration)

### Task 6.4: Update frontend to display host separately

Update game card and details components to show host distinctly.

- **Files**:
  - `frontend/src/types/index.ts` - Update Game type with separate host field
  - `frontend/src/components/GameCard.tsx` - Show host badge separate from participants
  - `frontend/src/pages/GameDetails.tsx` - Display host info prominently
  - `frontend/src/components/ParticipantList.tsx` - Ensure host not in list
- **Success**:
  - Game cards show "Host: @username" separately
  - Participant list excludes host
  - Participant count accurate (doesn't include host)
  - Host can be distinguished visually from regular participants
  - Host information visible on game details page
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1652-1680) - UI requirements
- **Dependencies**:
  - Task 6.2 completion (API changes first)

## Dependencies

- Python 3.11+ with type hints and async/await
- PostgreSQL 15+ with TIMESTAMPTZ support
- RabbitMQ 3.12+ for message broker
- Redis 7+ for caching
- Docker and Docker Compose for development
- Discord Application with bot token and OAuth2 client credentials

## Success Criteria

## Phase 7: Min Players Field Implementation

### Task 7.1: Add min_players field to GameSession model

Add `min_players` integer field to GameSession with default value of 1 and appropriate constraints.

- **Files**:
  - `shared/models/game.py` - Add min_players field to GameSession model
  - `alembic/versions/YYYYMMDD_add_min_players_field.py` - Create Alembic migration (new file)
- **Success**:
  - min_players column exists in database with NOT NULL constraint
  - Default value is 1 for all new games
  - Existing games updated to have min_players=1
  - Migration is reversible (downgrade removes column)
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1715-1745) - Min players requirement details
- **Dependencies**:
  - Task 1.2 completion (database setup)

### Task 7.2: Update schemas to include min_players

Add min_players field to request and response schemas with proper validation.

- **Files**:
  - `shared/schemas/game.py` - Add min_players to CreateGameRequest (optional, default 1)
  - `shared/schemas/game.py` - Add min_players to UpdateGameRequest (optional)
  - `shared/schemas/game.py` - Add min_players to GameResponse
- **Success**:
  - min_players accepts integer input in create/update requests
  - min_players defaults to 1 if not provided
  - min_players appears in all game responses
  - Validation errors clear if invalid values provided
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1740-1745) - Validation rules
- **Dependencies**:
  - Task 7.1 completion (model field exists)

### Task 7.3: Implement validation and service logic

Add validation to ensure min_players ≤ max_players and update service methods.

- **Files**:
  - `services/api/routes/games.py` - Add min_players validation to POST/PUT endpoints
  - `services/api/services/games.py` - Update create_game() to accept and store min_players
  - `services/api/services/games.py` - Update update_game() to accept and store min_players
- **Success**:
  - Validation rejects min_players > max_players with 422 error
  - Validation rejects min_players < 1 with 422 error
  - Service methods properly store min_players in database
  - Error messages are clear and actionable
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1738-1745) - Validation rules
- **Dependencies**:
  - Task 7.2 completion (schemas updated)

### Task 7.4: Update frontend to handle min_players

Add min_players input to game creation form and display in participant count format.

- **Files**:
  - `frontend/src/types/index.ts` - Add minPlayers to Game interface
  - `frontend/src/pages/CreateGame.tsx` - Add input field for min_players (optional, default 1)
  - `frontend/src/components/GameCard.tsx` - Display participant count as "X/min-max" format
  - `frontend/src/components/ParticipantDisplay.tsx` - Show min-max format in all places
- **Success**:
  - Game creation form includes min_players field (optional, defaults to 1)
  - Game cards show "X/1-5" format instead of just "X/5"
  - Validation prevents min > max in form before submission
  - API validation errors displayed clearly to user
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1725-1730) - Display format
- **Dependencies**:
  - Task 7.3 completion (API validation working)

## Phase 8: Description and Signup Instructions Fields

### Task 8.1: Add description and signup_instructions fields to GameSession model

- **Files**:
  - `shared/models/game.py` - Add description (TEXT, nullable) and signup_instructions (TEXT, nullable) fields
  - `alembic/versions/YYYYMMDD_add_description_signup_instructions.py` - Create Alembic migration (new file)
- **Success**:
  - Both columns exist in database as TEXT type with nullable constraint
  - Existing games have NULL values for both fields
  - Migration is reversible (downgrade removes both columns)
  - No default values (NULL allowed)
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1763-1810) - Description and signup instructions requirement
- **Dependencies**:
  - Task 1.2 completion (database setup)

### Task 8.2: Update schemas to include description and signup_instructions

Add both fields to request and response schemas with length validation.

- **Files**:
  - `shared/schemas/game.py` - Add description to CreateGameRequest (optional, max 4000 chars)
  - `shared/schemas/game.py` - Add signup_instructions to CreateGameRequest (optional, max 1000 chars)
  - `shared/schemas/game.py` - Add description to UpdateGameRequest (optional)
  - `shared/schemas/game.py` - Add signup_instructions to UpdateGameRequest (optional)
  - `shared/schemas/game.py` - Add both fields to GameResponse
- **Success**:
  - Both fields accept text input in create/update requests
  - Validation enforces max length constraints
  - Both fields appear in all game responses (may be null)
  - Clear validation errors if length limits exceeded
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1800-1805) - Validation rules
- **Dependencies**:
  - Task 8.1 completion (model fields exist)

### Task 8.3: Update service and bot logic to handle new fields

Update game creation, updates, and Discord message formatting to include new fields.

- **Files**:
  - `services/api/services/games.py` - Update create_game() to accept and store both fields
  - `services/api/services/games.py` - Update update_game() to accept and store both fields
  - `services/bot/formatters/game_message.py` - Include truncated description in Discord messages
- **Success**:
  - Service methods properly store both fields in database
  - Discord messages show first 100 chars of description with "..." if longer
  - Both fields handled correctly in all game operations
  - NULL values handled gracefully (don't break formatting)
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1795-1800) - Display guidelines
- **Dependencies**:
  - Task 8.2 completion (schemas updated)

### Task 8.4: Update frontend to display and edit new fields

Add description and signup_instructions to game creation form and display components.

- **Files**:
  - `frontend/src/types/index.ts` - Add description and signupInstructions to Game interface
  - `frontend/src/pages/CreateGame.tsx` - Add textarea fields for both (optional)
  - `frontend/src/components/GameCard.tsx` - Display truncated description (first 200 chars)
  - `frontend/src/pages/GameDetails.tsx` - Display full description and signup instructions
  - `frontend/src/components/GameCard.tsx` - Show signup instructions near participant count
- **Success**:
  - Game creation form includes both fields with appropriate textarea inputs
  - Game cards show truncated description with "Read more..." if truncated
  - Detail page shows full description and signup instructions
  - Signup instructions appear near Join/Leave buttons
  - Markdown rendering supported for description field
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1795-1800) - Display guidelines
- **Dependencies**:
  - Task 8.3 completion (API returns new fields)

## Phase 9: Bot Managers Role List

### Task 9.1: Add botManagerRoleIds field to GuildConfiguration model

Add `botManagerRoleIds` JSON array field to GuildConfiguration for managing game moderation permissions.

- **Files**:
  - `shared/models/guild.py` - Add botManagerRoleIds (JSON array, nullable) field
  - `alembic/versions/YYYYMMDD_add_bot_manager_roles.py` - Create Alembic migration (new file)
- **Success**:
  - bot_manager_role_ids column exists in database as JSON type with nullable constraint
  - Existing guilds have NULL values for this field
  - JSON array can store multiple Discord role IDs (snowflake strings)
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1833-1900) - Bot Managers requirement
- **Dependencies**:
  - Task 1.2 completion (database setup)

### Task 9.2: Update schemas and permissions middleware

Add botManagerRoleIds to guild schemas and create permission check helpers.

- **Files**:
  - `shared/schemas/guild.py` - Add botManagerRoleIds to GuildConfigUpdateRequest (optional)
  - `shared/schemas/guild.py` - Add botManagerRoleIds to GuildConfigResponse
  - `services/api/middleware/permissions.py` - Add has_bot_manager_permission() helper
  - `services/api/middleware/permissions.py` - Add can_manage_game() authorization function
- **Success**:
  - Guild configuration accepts botManagerRoleIds in update requests
  - Guild responses include botManagerRoleIds (may be null)
  - Permission helpers correctly identify Bot Manager role membership
  - Authorization checks distinguish between host, Bot Manager, and admin
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1860-1880) - Authorization logic
- **Dependencies**:
  - Task 9.1 completion (model field exists)

### Task 9.3: Implement Bot Manager authorization in game routes

Update game edit/delete endpoints to check Bot Manager permissions.

- **Files**:
  - `services/api/routes/games.py` - Update PUT /games/{id} to check Bot Manager roles
  - `services/api/routes/games.py` - Update DELETE /games/{id} to check Bot Manager roles
  - `services/api/services/games.py` - Add authorization checks in update_game() and delete_game()
- **Success**:
  - Bot Managers can edit any game in their guild
  - Bot Managers can delete any game in their guild
  - Hosts retain ability to manage their own games
  - Guild admins (MANAGE_GUILD) retain full permissions
  - Clear 403 error if user lacks permissions
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1860-1880) - Authorization logic
- **Dependencies**:
  - Task 9.2 completion (permission helpers exist)

### Task 9.4: Update bot commands and frontend for Bot Manager configuration

Add Bot Manager role management to Discord bot commands and web dashboard.

- **Files**:
  - `services/bot/commands/config_guild.py` - Add bot_managers parameter to guild config command
  - `frontend/src/pages/GuildConfig.tsx` - Add UI for selecting Bot Manager roles
  - `frontend/src/components/RoleSelector.tsx` - Reusable role selection component
- **Success**:
  - Guild admins can configure Bot Manager roles via Discord bot
  - Guild admins can configure Bot Manager roles via web dashboard
  - Multiple roles can be selected/deselected
  - Changes persist to database and take effect immediately
  - Clear indication of which roles have Bot Manager permissions
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1850-1860) - Configuration requirements
- **Dependencies**:
  - Task 9.3 completion (authorization logic working)
- Bot Manager roles can be configured by guild admins
- Bot Managers have permission to edit/delete any game in their guild
- Authorization correctly distinguishes between hosts, Bot Managers, and admins
- Permission checks cached and performant

## Phase 10: Notify Roles Field

### Task 10.1: Add notifyRoleIds field to GameSession model

Add `notifyRoleIds` JSON array field to GameSession for role-based notifications.

- **Files**:
  - `shared/models/game.py` - Add notifyRoleIds (JSON array, nullable) field
  - `alembic/versions/YYYYMMDD_add_notify_roles.py` - Create Alembic migration (new file)
- **Success**:
  - notify_role_ids column exists in database as JSON type with nullable constraint
  - Existing games have NULL or empty array values for this field
  - Migration is reversible (downgrade removes column)
  - JSON array can store multiple Discord role IDs (snowflake strings)
- **Research References**:
- **Dependencies**:
  - Task 1.2 completion (database setup)

### Task 10.2: Update schemas to include notifyRoleIds

Add notifyRoleIds to game schemas with validation.

- **Files**:
  - `shared/schemas/game.py` - Add notifyRoleIds to CreateGameRequest (optional, max 10 items)
  - `shared/schemas/game.py` - Add notifyRoleIds to UpdateGameRequest (optional, max 10 items)
  - `shared/schemas/game.py` - Add notifyRoleIds to GameResponse
- **Success**:
  - Game creation accepts notifyRoleIds in request body
  - Game updates accept notifyRoleIds in request body
  - API responses include notifyRoleIds (may be null or empty array)
  - Pydantic validation enforces max 10 roles
  - Role IDs validated as valid snowflake format
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 2000-2010) - Validation rules
- **Dependencies**:
  - Task 10.1 completion (model field exists)

### Task 10.3: Implement role mention formatting in bot announcements

Update Discord message formatting to include role mentions when game is created.

- **Files**:
  - `services/bot/formatters/game_message.py` - Add role mention formatting at top of message
  - `services/bot/events/game_events.py` - Ensure role mentions included in game_created handler
  - `services/api/services/games.py` - Pass notifyRoleIds when publishing game.created events
- **Success**:
  - Role mentions appear at top of game announcement messages
  - Multiple roles mentioned with space separation: `<@&role1> <@&role2>`
  - Users with mentioned roles receive Discord notification
  - Messages without notifyRoleIds don't include mentions (graceful handling)
  - Role mentions don't break message formatting
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1965-1990) - Discord message format
- **Dependencies**:
  - Task 10.2 completion (schemas updated)

### Task 10.4: Update frontend for role selection

Add role selection UI to game creation form.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Add role multi-select component
  - `frontend/src/components/RoleSelector.tsx` - Create reusable role selector (if not exists)
  - `frontend/src/api/client.ts` - Add endpoint to fetch guild roles
  - `services/api/routes/guilds.py` - Add GET /guilds/{id}/roles endpoint
- **Success**:
  - Game creation form shows role selection dropdown
  - Dropdown populated with guild roles (excluding @everyone and managed roles)
  - Multiple roles can be selected
  - Selected roles displayed with role name and color indicator
  - Role selection optional (can create game without notifications)
  - Selected roles submitted as notifyRoleIds array to API
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1990-2000) - Frontend role selection
- **Dependencies**:
  - Task 10.3 completion (backend handling works)

### Task 10.5: Fix compile errors

Resolve any TypeScript compilation errors and Python type checking issues across the codebase.

- **Files**:
  - All files with compile/type errors (to be identified)
- **Success**:
  - `npm run build` completes without errors in frontend
  - `mypy` type checking passes on Python services
  - No TypeScript errors in VS Code
  - All imports resolve correctly
  - Type annotations are accurate and complete
- **Research References**:
  - Project error logs and compiler output
- **Dependencies**:
  - All previous phase implementations

## Phase 11: Bug Fixes

### Task 11.1: Fix missing default values for min/max players in create game form

The create game form does not automatically populate default values for min_players and max_players fields, requiring users to manually enter values every time. Add default values to improve user experience.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Add default values to form state
  - `frontend/src/components/GameForm.tsx` - Set default values if component exists
- **Success**:
  - Create game form shows default min_players value (e.g., 2)
  - Create game form shows default max_players value (e.g., 8)
  - Users can still modify the default values
  - Form validation still enforces min <= max constraint
  - Default values consistent with backend GameSession model defaults
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 713-785) - Min/Max players implementation
  - #file:../../shared/models/game.py - Check model default values
- **Dependencies**:
  - Phase 7 completion (min_players field implementation)

### Task 11.2: Fix game time default value to use current time

The create game form does not automatically populate the game time field with the current time, leaving it empty or with an outdated default. Set the default to current time for better user experience.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Add current time as default value
  - `frontend/src/components/GameForm.tsx` - Initialize time picker with current time if component exists
- **Success**:
  - Create game form shows current date/time as default when opened
  - Time field properly formatted for datetime-local input or date picker component
  - Users can still modify the default time
  - Timezone handling consistent with user's selected timezone or UTC
  - Default updates if user stays on page and creates multiple games
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 488-512) - Game management interface
  - #file:../../shared/utils/timezone.py - Timezone handling utilities
- **Dependencies**:
  - Phase 4 completion (frontend game management)

### Task 11.3: Auto-select channel when only one is available

When a guild has only one configured channel, the channel selector requires manual selection. Automatically select the channel to improve user experience and reduce unnecessary clicks.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Add auto-select logic for single channel
  - `frontend/src/components/ChannelSelector.tsx` - Handle single option auto-select if component exists
- **Success**:
  - Channel automatically selected when guild has exactly one channel
  - Channel selector still displayed (not hidden) for user awareness
  - User can still change selection if needed
  - Auto-select triggers on initial load and when guild changes
  - Does not auto-select when multiple channels available
  - Does not auto-select when zero channels available (shows appropriate message)
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 465-486) - Guild and channel management
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 488-512) - Game management interface
- **Dependencies**:
  - Phase 4 completion (frontend game management)

### Task 11.4: Move Scheduled Time field to top of game display and edit pages

The Scheduled Time field is currently positioned lower in the game information layout, making it harder for users to quickly identify when a game is scheduled. Move this critical field to a more prominent position at the top of both game display and edit pages.

- **Files**:
  - `frontend/src/pages/GameDetails.tsx` - Reorder display to show scheduled time at top
  - `frontend/src/pages/EditGame.tsx` - Reorder form fields to show scheduled time at top
  - `frontend/src/components/GameCard.tsx` - Adjust game card layout if needed
- **Success**:
  - Scheduled time appears as first or second field in game details view
  - Scheduled time appears near top of edit game form
  - Field remains visually prominent (large font, bold, or highlighted)
  - Time display includes timezone information for clarity
  - Changes do not break existing layout or responsive design
  - All existing functionality preserved
- **Research References**:
  - #file:../../frontend/src/pages/GameDetails.tsx - Current game details layout
  - #file:../../frontend/src/pages/EditGame.tsx - Current edit form layout
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 488-512) - Game management interface
- **Dependencies**:
  - Phase 4 completion (frontend game management)

### Task 11.5: Move Channel field under Scheduled Time field on game display and edit pages

The Channel field should be positioned directly under the Scheduled Time field to provide clear context about where and when the game will take place. This logical grouping improves information hierarchy.

- **Files**:
  - `frontend/src/pages/GameDetails.tsx` - Position channel field under scheduled time
  - `frontend/src/pages/EditGame.tsx` - Position channel selector under time picker
  - `frontend/src/components/GameCard.tsx` - Adjust game card layout if needed
- **Success**:
  - Channel field appears immediately after Scheduled Time field in game details
  - Channel selector appears immediately after time picker in edit form
  - Visual grouping indicates these fields are primary game logistics
  - Clear separation from other game details (description, rules, etc.)
  - Responsive layout maintained on all screen sizes
  - All existing functionality preserved
- **Research References**:
  - #file:../../frontend/src/pages/GameDetails.tsx - Current game details layout
  - #file:../../frontend/src/pages/EditGame.tsx - Current edit form layout
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 488-512) - Game management interface
- **Dependencies**:
  - Task 11.4 completion (Scheduled Time field moved to top)

### Task 11.6: Move reminder box directly below scheduled time box

The Reminder Times field should be positioned immediately after the Scheduled Time field to create a logical grouping of time-related settings. This improves the user experience by keeping all time-related configuration together.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Reorder form fields to place reminder input after time picker
  - `frontend/src/pages/EditGame.tsx` - Reorder form fields to place reminder input after time picker
  - `frontend/src/pages/GameDetails.tsx` - Reorder display fields to place reminders after scheduled time
- **Success**:
  - Reminder Times field appears immediately after Scheduled Time field in create game form
  - Reminder Times field appears immediately after Scheduled Time field in edit game form
  - Reminders display appears immediately after Scheduled Time display in game details page
  - Visual grouping clearly indicates these fields are related to timing
  - All existing functionality preserved (validation, helper text, default values)
  - Responsive layout maintained on all screen sizes
  - No changes to underlying data flow or API interactions
- **Research References**:
  - #file:../../frontend/src/pages/CreateGame.tsx (Lines 1-426) - Current create game form layout
  - #file:../../frontend/src/pages/EditGame.tsx (Lines 1-321) - Current edit game form layout
  - #file:../../frontend/src/pages/GameDetails.tsx - Current game details display layout
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 488-512) - Game management interface patterns
- **Dependencies**:
  - Task 11.4 completion (Scheduled Time moved to top)
  - Task 11.5 completion (Channel field positioned under Scheduled Time)

### Task 11.7: Fix all unit test and lint messages for Python and TypeScript

Ensure all Python and TypeScript code passes linting and all unit tests are passing. Fix any errors, warnings, or failures that appear when running pytest, ruff, mypy for Python, and eslint, tsc for TypeScript.

- **Files**:
  - `services/**/*.py` - Fix Python linting issues
  - `shared/**/*.py` - Fix shared Python module issues
  - `tests/**/*.py` - Fix test failures and test file linting
  - `frontend/src/**/*.ts` - Fix TypeScript linting issues
  - `frontend/src/**/*.tsx` - Fix React component linting and type issues
  - `pyproject.toml` - Adjust ruff/mypy configuration if needed
  - `frontend/.eslintrc.cjs` - Adjust ESLint configuration if needed
- **Success**:
  - `uv run ruff check .` passes with 0 errors
  - `uv run mypy .` passes with 0 errors
  - `uv run pytest tests/` runs with all tests passing
  - `cd frontend && npm run lint` passes with 0 errors and 0 warnings
  - `cd frontend && npm run build` completes successfully with no TypeScript errors
  - `cd frontend && npm run test` runs with all tests passing
  - All code follows project conventions and style guidelines
- **Research References**:
  - #file:../../.github/instructions/python.instructions.md - Python coding standards
  - #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript standards
  - #file:../../pyproject.toml - Python tooling configuration
  - #file:../../frontend/package.json - Frontend tooling scripts
- **Dependencies**:
  - All previous phases with code changes

### Task 11.8: Install eslint and prettier and fix any issues found

Install ESLint and Prettier with the recommended configuration for React and TypeScript, configure them with appropriate rules, and fix all linting and formatting issues they identify in the frontend codebase.

- **Files**:
  - `frontend/package.json` - Add ESLint and related plugins as dev dependencies
  - `frontend/.eslintrc.cjs` - Create or update ESLint configuration
  - `frontend/src/**/*.ts` - Fix ESLint errors in TypeScript files
  - `frontend/src/**/*.tsx` - Fix ESLint errors in React component files
  - `frontend/.eslintignore` - Configure files to exclude from linting
  - `frontend/vite.config.ts` - Ensure ESLint plugin integration if needed
- **Success**:
  - ESLint installed with appropriate plugins (@typescript-eslint, eslint-plugin-react, eslint-plugin-react-hooks)
  - ESLint configuration file created with recommended rules for React and TypeScript
  - `cd frontend && npm run lint` command available in package.json scripts
  - `cd frontend && npm run lint` passes with 0 errors and 0 warnings
  - All code follows ESLint configured style guidelines
  - No ESLint rules disabled without justification
  - Configuration aligns with project conventions from #file:../../.github/instructions/reactjs.instructions.md
- **Research References**:
  - #file:../../.github/instructions/reactjs.instructions.md - React and linting best practices
  - #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript standards
  - #file:../../frontend/package.json - Frontend tooling scripts
  - #fetch:https://eslint.org/docs/latest/use/getting-started - ESLint setup guide
  - #fetch:https://typescript-eslint.io/getting-started - TypeScript ESLint setup
- **Dependencies**:
  - Phase 4 completion (frontend implementation)

### Task 11.9: Display min players and max players on the same line

The Min Players and Max Players fields should be displayed side-by-side on the same line rather than stacked vertically. This creates a more compact layout and visually reinforces that these are related range values.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Update form layout to display min/max players horizontally
  - `frontend/src/pages/EditGame.tsx` - Update form layout to display min/max players horizontally
- **Success**:
  - Min Players and Max Players fields appear side-by-side on the same line in create game form
  - Min Players and Max Players fields appear side-by-side on the same line in edit game form
  - Fields maintain proper spacing and alignment
  - Both fields remain fully functional with proper validation
  - Responsive layout works on mobile devices (fields may stack on small screens)
  - Helper text displays appropriately for both fields
  - All existing functionality preserved (validation, default values, constraints)
- **Research References**:
  - #file:../../frontend/src/pages/CreateGame.tsx (Lines 1-426) - Current create game form layout
  - #file:../../frontend/src/pages/EditGame.tsx (Lines 1-321) - Current edit game form layout
  - #file:../../.github/instructions/reactjs.instructions.md - React and Material-UI best practices
- **Dependencies**:
  - Phase 4 completion (frontend game management)

### Task 11.10: Remove the rules field everywhere

The rules field is no longer needed and should be completely removed from the entire system including database, API, bot, and frontend.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Remove rules field from form and form data interface
  - `frontend/src/pages/EditGame.tsx` - Remove rules field from form and form data interface
  - `frontend/src/pages/GameDetails.tsx` - Remove rules display if present
  - `frontend/src/components/GameCard.tsx` - Remove rules display if present
  - `frontend/src/types/index.ts` - Remove rules field from GameSession type
  - `shared/models/game.py` - Remove rules column from GameSession model
  - `shared/schemas/game.py` - Remove rules field from all game schemas
  - `services/api/routes/games.py` - Remove rules field handling from create/update endpoints
  - `services/api/routes/channels.py` - Remove rules field from channel configuration if present
  - `services/api/routes/guilds.py` - Remove rules field from guild configuration if present
  - `services/bot/formatters/game_message.py` - Remove rules from message formatting
  - `services/bot/commands/*.py` - Remove rules field from bot commands
  - `alembic/versions/` - Create new migration to drop rules column from game_sessions table
  - `tests/**/*.py` - Update all tests to remove rules field references
- **Success**:
  - Rules column removed from game_sessions table via Alembic migration
  - Rules field removed from all SQLAlchemy models
  - Rules field removed from all Pydantic schemas
  - Rules field removed from all API endpoints (create, update, retrieve)
  - Rules field removed from all frontend components and types
  - Rules field removed from Discord bot message formatting
  - All tests pass without rules field
  - No references to "rules" field remain in codebase (except migration history)
  - Database migration runs successfully without errors
  - Existing deployments can migrate smoothly with downgrade capability
- **Research References**:
  - #file:../../frontend/src/pages/CreateGame.tsx (Lines 1-426) - Current create game form with rules field
  - #file:../../frontend/src/pages/EditGame.tsx (Lines 1-321) - Current edit game form with rules field
  - #file:../../shared/models/game.py - GameSession model with rules column
  - #file:../../shared/schemas/game.py - Game schemas with rules field
  - #file:../../services/api/routes/games.py - API endpoints handling rules
- **Dependencies**:
  - Phase 1 completion (database setup)
  - Phase 2 completion (bot service)
  - Phase 3 completion (API endpoints)
  - Phase 4 completion (frontend game management)

### Task 11.11: Fix API crash when specifying an @user

The API crashes when a user attempts to create a game with an @mention in the initial_participants field. Investigate and fix the crash to ensure proper error handling and validation.

- **Files**:
  - `services/api/services/participant_resolver.py` - Fix exception handling in resolve_initial_participants
  - `services/api/routes/games.py` - Ensure proper error handling in create_game endpoint
  - `services/api/services/games.py` - Validate participant resolver error handling
  - `tests/services/api/services/test_participant_resolver.py` - Add test for crash scenario
  - `tests/services/api/routes/test_games.py` - Add integration test for @mention error handling
- **Success**:
  - API does not crash when processing @mentions
  - Invalid @mentions return proper 422 error with disambiguation details
  - Valid @mentions are processed correctly
  - Exception handling catches all potential errors from Discord API
  - Logs provide clear information for debugging mention resolution failures
  - Tests cover crash scenario and verify proper error responses
  - No unhandled exceptions in participant resolution flow
- **Research References**:
  - #file:../../services/api/services/participant_resolver.py (Lines 1-213) - Current participant resolver implementation
  - #file:../../services/api/routes/games.py (Lines 48-92) - Create game endpoint with validation
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 514-538) - Pre-populated participants feature
- **Dependencies**:
  - Phase 3 completion (API endpoints)
  - Phase 4 completion (frontend game management with pre-populated participants)

## Phase 12: Advanced Features

### Task 12.1: Implement waitlist support

Add waitlist functionality when games reach maxPlayers capacity.

- **Files**:
  - Database migration for waitlist status
  - `services/api/services/waitlist.py` - Waitlist management
  - `services/bot/handlers/join_waitlist.py` - Waitlist button
  - `frontend/src/components/WaitlistDisplay.tsx` - Waitlist UI
- **Success**:
  - Full games show "Join Waitlist" button
  - Waitlist participants notified when slot opens
  - Automatic promotion when participant drops
  - Waitlist visible in game details
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1612) - Advanced features list
- **Dependencies**:
  - All Phase 2-5 services

### Task 12.2: Change pre-filled participant ordering to use explicit position

Replace timestamp-based ordering of pre-populated and placeholder participants with an explicit integer position field. This enables proper reordering when participant list editing is implemented in future tasks.

- **Files**:
  - Database migration - Add `pre_filled_position` nullable integer field to `game_participants` table
  - `shared/models/participant.py` - Add `pre_filled_position` field to GameParticipant model
  - `shared/schemas/participant.py` - Update schemas to include pre_filled_position
  - `services/api/services/game_service.py` - Update pre-population logic to assign sequential positions
  - `services/api/routes/games.py` - Ensure position values are set during game creation
  - `services/bot/formatters/game_announcer.py` - Sort participants by position when is_pre_populated=True
  - `frontend/src/components/ParticipantList.tsx` - Use position for sorting pre-filled participants
- **Success**:
  - Pre-populated and placeholder participants have explicit position integers
  - Participants sorted by position (ascending) when displayed
  - Regular (non-pre-filled) participants sorted by joined_at timestamp as before
  - Position field nullable (NULL for regular participants who join via button)
  - Migration preserves existing data by calculating positions from joined_at for pre-populated entries
  - API validation ensures positions are sequential starting from 1 for pre-filled participants
  - Frontend displays participants in correct order regardless of join time
- **Research References**:
  - #file:../../shared/models/participant.py (Lines 1-70) - Current participant model structure
  - #file:../../services/api/services/game_service.py - Game creation with pre-population logic
  - #file:../../frontend/src/components/ParticipantList.tsx - Current participant display logic
- **Dependencies**:
  - Task 4.5 completion (pre-population feature)
  - Database migration capability

### Task 12.3: Fix default_rules related problem in bot

Remove or update references to the deprecated `default_rules` field from bot commands and configuration logic, as this field was removed from guild and channel configurations in migration 008.

- **Files**:
  - `services/bot/commands/config.py` - Update config commands to remove default_rules parameter
  - `services/bot/handlers/config_handler.py` - Remove default_rules handling logic if present
- **Success**:
  - Bot config commands no longer reference default_rules
  - No errors when running /config-guild or /config-channel commands
  - Configuration help text updated to reflect removal
  - All bot tests pass without default_rules references
- **Research References**:
  - #file:../changes/20251114-discord-game-scheduling-system-changes.md (Lines 6758-6791) - Migration 008 removal of default_rules
  - #file:../../services/bot/commands/config.py - Current config command implementation
- **Dependencies**:
  - Migration 008 completion (default_rules removal)

### Task 12.4: Refactor Create/Edit Game Pages with Shared Form Component

Refactor CreateGame and EditGame pages to eliminate code duplication by extracting common form logic into a shared GameForm component. Add editable participant management with real-time validation to both create and edit workflows.

- **Files**:

  - `frontend/src/components/GameForm.tsx` - New shared form component (extract from CreateGame/EditGame)
  - `frontend/src/components/EditableParticipantList.tsx` - New editable participant component
  - `frontend/src/pages/CreateGame.tsx` - Refactor to use GameForm component
  - `frontend/src/pages/EditGame.tsx` - Refactor to use GameForm component
  - `services/api/routes/guilds.py` - Add mention validation endpoint
  - `services/api/routes/games.py` - Update game save to handle participant deletes and reordering
  - `services/bot/handlers/game_handler.py` - Update Discord message when participants are removed

- **Implementation Details**:

  **1. Shared GameForm Component:**

  - Extract all form fields from CreateGame.tsx and EditGame.tsx into GameForm.tsx
  - Props interface:
    ```typescript
    interface GameFormProps {
      mode: "create" | "edit";
      initialData?: Partial<GameSession>;
      guildId: string;
      onSubmit: (formData: GameFormData) => Promise<void>;
      onCancel: () => void;
    }
    ```
  - Include all existing form fields: title, description, signupInstructions, scheduledAt, channelId, minPlayers, maxPlayers, reminderMinutes
  - Add EditableParticipantList component below form fields (before submit buttons)
  - Title prop for header: "Create Game" vs "Edit Game" passed from parent pages
  - Form validation logic remains in component
  - LocalizationProvider wrapper stays in component

  **2. EditableParticipantList Component:**

  - Accept free-form text input for @mentions (any format: @username, <@123>, plain text)
  - Dynamic participant fields with "Add Participant" button
  - Each participant row shows:
    - Text input field for mention/name
    - Validation status indicator (loading spinner, green check, red X)
    - Up/Down arrow buttons for reordering
    - Delete button (X icon)
  - Props interface:

    ```typescript
    interface EditableParticipantListProps {
      participants: ParticipantInput[];
      guildId: string;
      onChange: (participants: ParticipantInput[]) => void;
    }

    interface ParticipantInput {
      id: string; // temp client ID
      mention: string;
      isValid: boolean | null; // null = not validated yet
      validationError?: string;
      preFillPosition: number; // auto-calculated by order
    }
    ```

  - Real-time validation with 500ms debounce per field
  - Shows validation state inline (not blocking, just visual feedback)
  - Empty state: "No pre-populated participants (users can join via Discord button)"
  - Reordering updates preFillPosition automatically (1-based index)

  **3. Validation Endpoint (Backend):**

  - New endpoint: `POST /api/v1/guilds/{guildId}/validate-mention`
  - Request body: `{ "mention": "@username" }`
  - Response: `{ "valid": true }` or `{ "valid": false, "error": "User not found in guild" }`
  - Does NOT resolve/return user details (validation only)
  - Actual resolution happens during game save
  - Bot service checks if mention exists in guild members
  - Handles all formats: @username, <@123456789>, plain text
  - Rate limiting: 10 requests per second per user

  **4. Game Save with Participants:**

  - Update `POST /api/v1/games` and `PATCH /api/v1/games/{gameId}` endpoints
  - Accept participants array in request body:
    ```json
    {
      "title": "D&D Session",
      "participants": [
        { "mention": "@player1", "preFillPosition": 1 },
        { "mention": "<@123456>", "preFillPosition": 2 }
      ]
    }
    ```
  - Backend resolves mentions to user_id or stores as display_name placeholders
  - For edit: detect removed participants and publish `participant.removed` events
  - Update pre_filled_position based on array order
  - Validate no duplicate user_ids in final participant list

  **5. Discord Message Updates:**

  - When participant removed via web: publish `participant.removed` event to RabbitMQ
  - Bot subscribes to event and updates Discord message to reflect current state
  - Removed user receives DM notification: "You were removed from [Game Title] on [Date]"
  - Message always shows current participant list (auto-updates on any change)

  **6. Page Refactoring:**

  - CreateGame.tsx becomes thin wrapper:
    - Fetches guild channels
    - Passes mode='create', no initialData
    - Handles submit by calling POST /api/v1/games
    - Empty participants array by default
  - EditGame.tsx becomes thin wrapper:
    - Fetches game and channels
    - Passes mode='edit', initialData=game
    - Handles submit by calling PATCH /api/v1/games/{gameId}
    - Loads existing participants from game.participants

- **Component Structure Examples**:

  ```tsx
  // CreateGame.tsx
  export const CreateGame: FC = () => {
    const [channels, setChannels] = useState<Channel[]>([]);

    const handleSubmit = async (formData: GameFormData) => {
      await apiClient.post("/api/v1/games", formData);
      navigate("/games");
    };

    return (
      <Container maxWidth="md">
        <GameForm
          mode="create"
          guildId={guildId}
          channels={channels}
          onSubmit={handleSubmit}
          onCancel={() => navigate("/games")}
        />
      </Container>
    );
  };

  // EditableParticipantList component structure
  <Box sx={{ mb: 3 }}>
    <Typography variant="h6" gutterBottom>
      Pre-populate Participants (Optional)
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
      Add Discord users who should be included automatically. Use @mentions or
      user names. Others can join via Discord button.
    </Typography>

    {participants.map((p, index) => (
      <Box
        key={p.id}
        sx={{ display: "flex", gap: 1, mb: 1, alignItems: "center" }}
      >
        <TextField
          value={p.mention}
          onChange={(e) => handleMentionChange(p.id, e.target.value)}
          placeholder="@username or Discord user"
          error={p.isValid === false}
          helperText={p.validationError}
          InputProps={{
            endAdornment:
              p.isValid === null ? (
                <CircularProgress size={20} />
              ) : p.isValid ? (
                <CheckCircleIcon color="success" />
              ) : (
                <ErrorIcon color="error" />
              ),
          }}
        />
        <IconButton onClick={() => moveUp(index)} disabled={index === 0}>
          <ArrowUpIcon />
        </IconButton>
        <IconButton
          onClick={() => moveDown(index)}
          disabled={index === participants.length - 1}
        >
          <ArrowDownIcon />
        </IconButton>
        <IconButton onClick={() => remove(p.id)}>
          <DeleteIcon />
        </IconButton>
      </Box>
    ))}

    <Button onClick={addParticipant} startIcon={<AddIcon />}>
      Add Participant
    </Button>
  </Box>;
  ```

- **Success**:

  - CreateGame.tsx and EditGame.tsx are <100 lines each (thin wrappers)
  - All form logic consolidated in GameForm.tsx component
  - GameForm component created with mode prop (create/edit)
  - EditableParticipantList component created (standalone)
  - Backend validation endpoint implemented
  - No code duplication between create and edit pages
  - Consistent UX across both workflows
  - TypeScript compilation successful
  - All form functionality preserved

- **Research References**:

  - #file:../../frontend/src/pages/CreateGame.tsx (Lines 1-145) - Refactored implementation
  - #file:../../frontend/src/pages/EditGame.tsx (Lines 1-115) - Refactored implementation
  - #file:../../frontend/src/components/GameForm.tsx (Lines 1-334) - Shared form component
  - #file:../../frontend/src/components/EditableParticipantList.tsx (Lines 1-180) - Participant editor
  - #file:../../frontend/src/components/ParticipantList.tsx (Lines 1-97) - Read-only participant display pattern
  - #file:../../frontend/src/types/index.ts (Lines 34-70) - GameSession and Participant interfaces
  - #file:../../shared/models/participant.py (Lines 1-57) - Participant model with pre_filled_position
  - #file:../../services/api/routes/games.py - Game CRUD endpoints to extend
  - #file:../../services/api/routes/guilds.py - Added validation endpoint
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 450-510) - Participant management patterns

- **Dependencies**:
  - Task 4.4 completion (game management interface)
  - Task 6.4 completion (ParticipantList component)
  - RabbitMQ events infrastructure (Task 1.3)
  - Discord bot message formatting (Task 2.3)

### Task 12.5: Integrate EditableParticipantList into GameForm Component

Integrate the EditableParticipantList component into GameForm for inline participant management during game creation and editing.

- **Files**:

  - `frontend/src/components/GameForm.tsx` - Add EditableParticipantList integration
  - `frontend/src/pages/CreateGame.tsx` - Update to handle participant data in submission
  - `frontend/src/pages/EditGame.tsx` - Update to load and handle existing participants
  - `services/api/routes/games.py` - Update POST/PUT endpoints to process participants array
  - `services/api/services/games.py` - Add participant processing logic
  - `services/bot/handlers/game_handler.py` - Handle participant.removed events
  - `shared/messaging/events.py` - Add ParticipantRemovedEvent if needed

- **Implementation Details**:

  **1. Add EditableParticipantList to GameForm:**

  - Import EditableParticipantList component
  - Add participants state management to GameForm
  - Place EditableParticipantList below form fields, before submit buttons
  - Pass participants array and onChange handler
  - Include participants in form submission data

  **2. Update CreateGame page:**

  - Initialize empty participants array in form submission
  - Map ParticipantInput to API format (mention + preFillPosition)
  - Send participants array in POST /api/v1/games payload
  - Filter out empty mentions before submission

  **3. Update EditGame page:**

  - Load existing participants from game data
  - Convert to ParticipantInput format with validation state
  - Detect removed participants by comparing before/after
  - Send updated participants array in PUT /api/v1/games/{id} payload

  **4. Backend participant processing:**

  - Accept participants array in game create/update requests
  - Resolve @mentions to user_id or store as display_name placeholders
  - Create GameParticipant records with pre_filled_position
  - For updates: detect removed participants and publish events
  - Validate no duplicate user_ids in participant list
  - Return error if mention resolution fails

  **5. Discord message updates on participant removal:**

  - Bot subscribes to participant.removed events from RabbitMQ
  - Update game announcement message with current participant list
  - Send DM to removed user: "You were removed from [Game Title] on [Date]"
  - Handle DM failures gracefully (user may have DMs disabled)

  **6. Validation improvements:**

  - Enhance /api/v1/guilds/{guildId}/validate-mention endpoint
  - Actually query Discord API to verify user exists in guild
  - Parse mention formats: @username, <@123456>, plain text
  - Return helpful error messages for invalid mentions

- **Success**:

  - EditableParticipantList visible in both create and edit game forms
  - Participants can be added in create mode (starts empty)
  - Participants can be added/removed/reordered in edit mode
  - Real-time validation provides visual feedback (500ms debounce)
  - Validation errors displayed inline per field
  - Up/down arrows reorder participants correctly
  - Delete button removes any participant type (pre-filled or joined)
  - Pre-fill positions auto-calculated from list order
  - Form submission includes participants array with positions
  - Backend validates mentions don't duplicate existing joined users
  - Removed participants trigger Discord message update
  - Removed users receive DM notification
  - Discord message always shows current participant state
  - Consistent behavior across create and edit workflows

- **Research References**:

  - #file:../../frontend/src/components/GameForm.tsx (Lines 1-334) - Form component to modify
  - #file:../../frontend/src/components/EditableParticipantList.tsx (Lines 1-180) - Component to integrate
  - #file:../../services/api/routes/games.py - Game endpoints to extend
  - #file:../../services/api/services/games.py - Game service to extend
  - #file:../../services/bot/handlers/game_handler.py - Discord message update logic
  - #file:../../shared/messaging/events.py - Event definitions
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 450-510) - Participant management patterns

- **Dependencies**:
  - Task 12.4 completion (GameForm and EditableParticipantList components)
  - RabbitMQ events infrastructure (Task 1.3)
  - Discord bot message formatting (Task 2.3)

### Task 12.6: Replace adaptive backoff with Redis-based rate limiting

Simplify message update throttling by replacing in-memory state tracking with Redis cache.

- **Files**:
  - `services/bot/handlers/game_handler.py` - Replace adaptive backoff logic
  - `shared/cache/client.py` - Ensure Redis client supports key operations
- **Success**:
  - Redis key existence check with 1.5s TTL for rate limiting
  - Instant updates when idle, throttled when busy
  - Simpler code without in-memory state tracking
  - Multi-instance ready
- **Research References**:
  - #file:../research/20251122-redis-rate-limiting-research.md - Redis rate limiting patterns
- **Dependencies**:
  - Task 1.4 (Redis configuration)
  - Task 2.4 (Button interaction handlers)

### Task 12.7: Change "Pre-Populated" to "Added by host" on web pages and messages

Update terminology across all user-facing interfaces for better clarity.

- **Files**:
  - `frontend/src/components/EditableParticipantList.tsx` - Update UI labels
  - `frontend/src/components/ParticipantList.tsx` - Update display text
  - `frontend/src/pages/GameDetails.tsx` - Update participant section labels
  - `services/bot/formatters/game_formatter.py` - Update Discord message text
- **Success**:
  - All instances of "Pre-Populated" changed to "Added by host"
  - Consistent terminology across frontend and Discord messages
  - Clear distinction between host-added and user-joined participants
- **Research References**:
  - #file:../../frontend/src/components/EditableParticipantList.tsx - Component with pre-populated text
  - #file:../../services/bot/formatters/game_formatter.py - Discord message formatting
- **Dependencies**:
  - Task 4.4 (Game management interface)
  - Task 2.3 (Game announcement message formatter)

### Task 12.8: Change "Guild" to "Server" on web pages and messages

Update user-facing terminology to match Discord's user interface language.

- **Files**:
  - `frontend/src/pages/GuildList.tsx` - Update page title and labels
  - `frontend/src/pages/GuildSettings.tsx` - Update page title and headings
  - `frontend/src/components/GuildSelector.tsx` - Update dropdown labels
  - `frontend/src/components/ChannelSettings.tsx` - Update references to guild
  - `services/bot/commands/*.py` - Update command descriptions and responses
  - `services/bot/formatters/*.py` - Update message text
- **Success**:
  - All user-facing "Guild" text changed to "Server"
  - Internal code and database models still use "guild" for API consistency
  - Discord bot messages use "Server" terminology
  - Navigation and page titles updated
- **Research References**:
  - #file:../../frontend/src/pages/GuildList.tsx - Guild list page
  - #file:../../services/bot/commands/ - Bot command files
- **Dependencies**:
  - Task 4.3 (Guild and channel management pages)
  - Task 2.2 (Slash commands)

### Task 12.9: Send notification of waitlist clearing

Notify users when they are promoted from the overflow/waitlist to confirmed participants.

- **Files**:
  - `services/api/services/games.py` - Add promotion detection in update_game() method
  - `services/bot/events/handlers.py` - Handle waitlist promotion notification via existing NOTIFICATION_SEND_DM event
- **Implementation Approach**:
  - In `games.py` `update_game()` method, after updating game state:
    - Fetch current participant lists before and after updates
    - Compare overflow → confirmed transitions using participant sorting
    - For each promoted user, publish `NOTIFICATION_SEND_DM` event with promotion message
  - Promotion occurs when:
    - A confirmed player is removed (via `removed_participant_ids`)
    - Host increases `max_players`
    - Host reorders participants (via `participants` field updates)
  - Use existing `_handle_send_notification()` in handlers.py (no new event type needed)
  - Message format: "✅ Good news! A spot opened up in **{game_title}** scheduled for <t:{timestamp}:F>. You've been moved from the waitlist to confirmed participants!"
- **Success**:
  - User receives DM when promoted from waitlist to confirmed
  - DM includes game title, scheduled time, and confirmation message
  - Notification sent for all three trigger scenarios
  - Discord message updated immediately via existing `_publish_game_updated()`
  - No duplicate notifications (track promotions during single update)
  - Handles edge cases (user DMs disabled via discord.Forbidden)
  - Works with both Discord users and placeholder participants
- **Research References**:
  - #file:../../services/bot/events/handlers.py (Lines 334-368) - Existing notification handler pattern
  - #file:../../services/api/services/games.py (Lines 370-460) - update_game() method
  - #file:../../shared/messaging/events.py (Lines 100-110) - NotificationSendDMEvent structure
  - #file:../../shared/utils/participant_sorting.py - Participant ordering logic
- **Dependencies**:
  - Task 12.1 (Waitlist support)
  - Task 2.5 (RabbitMQ event system)
  - Existing notification infrastructure (NotificationSendDMEvent)

### Task 12.10: Fix participant count to include placeholder participants

Update the participant_count calculation to include both Discord-linked users and placeholder participants added by the host.

- **Files**:
  - `services/api/routes/games.py` - Update `_build_game_response()` to count all participants
  - `shared/schemas/game.py` - Update GameResponse documentation if needed
- **Problem**:
  - Currently `participant_count = sum(1 for p in game.participants if p.user_id is not None)` only counts Discord users
  - This excludes placeholder participants (those added by host without Discord accounts)
  - Results in confusing display where participant list shows more players than the count indicates
  - "My Games" screen shows incorrect player counts in GameCard
- **Solution**:
  - Change calculation to: `participant_count = len(game.participants)`
  - This counts all participants regardless of user_id status
  - Matches the actual visible participant list in game details
  - Provides accurate count for "X/min-max" display on game cards
- **Success**:
  - participant_count includes both Discord users and placeholder participants
  - GameCard on "My Games" page displays correct total participant count
  - Count matches number of participants shown in game details view
  - Min-max display (e.g., "5/4-8") accurately reflects all confirmed players
- **Research References**:
  - #file:../../services/api/routes/games.py (Lines 270-290) - Current \_build_game_response() implementation
  - #file:../../frontend/src/components/GameCard.tsx (Lines 1-100) - GameCard display logic
  - #file:../../frontend/src/pages/MyGames.tsx (Lines 1-150) - My Games page
- **Dependencies**:
  - Task 12.2 (Pre-filled participant positioning) - placeholder participants exist

### Task 12.11: Add play time field for expected game duration

Add an optional field to track how long the host expects the game session to run.

- **Files**:
  - `shared/models/game.py` - Add `expected_duration_minutes` integer field to GameSession model
  - `alembic/versions/` - Create migration for new field
  - `shared/schemas/game.py` - Add field to GameCreate, GameUpdate, GameResponse schemas
  - `services/api/routes/games.py` - Update \_build_game_response() to include duration
  - `services/bot/formatters/game_message.py` - Display duration in Discord embed
  - `frontend/src/types/index.ts` - Add expected_duration_minutes to GameSession interface
  - `frontend/src/components/GameForm.tsx` - Add duration input on same line as reminder times
  - `frontend/src/components/GameCard.tsx` - Display duration in game summary
  - `frontend/src/pages/GameDetails.tsx` - Display duration in game details view
- **Implementation Details**:
  - Database: Add nullable `expected_duration_minutes INTEGER` column to game_sessions table
  - Backend validation: Accept positive integers (15, 30, 60, 90, 120, 180, 240, 300, 360+ minutes)
  - Frontend input: Number input with common presets (30min, 1hr, 2hr, 3hr, 4hr, 6hr) or custom
  - Display format: "2h 30m" for values, "Duration: X hours Y minutes" in descriptions
  - GameForm layout: Place duration input on same horizontal line as Reminder times field
  - GameCard display: Show "Duration: Xh Ym" below "When" and "Players" info
  - Discord message: Add to embed fields as "Expected Duration: Xh Ym" (only if set)
  - Handle null/empty values gracefully (field is optional)
- **Success**:
  - expected_duration_minutes field stored in database (nullable)
  - Migration applies cleanly without errors
  - Create/edit forms show duration input on same line as reminder times
  - Duration appears on My Games cards when set
  - Duration displayed in game details page
  - Discord announcements show duration in embed when set
  - Format displays as human-readable (e.g., "2h 30m" not "150 minutes")
  - Validation prevents negative or invalid values
  - Field remains optional (can be null/unset)
- **Research References**:
  - #file:../../shared/models/game.py - GameSession model structure
  - #file:../../shared/schemas/game.py - Game schemas
  - #file:../../services/bot/formatters/game_message.py - Discord message formatting
  - #file:../../frontend/src/components/GameCard.tsx - Game summary display
  - #file:../../frontend/src/components/GameForm.tsx - Form layout patterns
- **Dependencies**:
  - Phase 3 (Web API Service) - API endpoints exist
  - Phase 4 (Web Dashboard Frontend) - Frontend components exist
  - Task 12.4 (GameForm refactor) - Shared form component available

### Task 12.12: Rename "Allowed Host Role IDs" to "Host Roles" on server configuration

Simplify the label on server configuration screens for better user experience.

- **Files**:
  - `frontend/src/pages/GuildConfig.tsx` - Update server configuration form label
  - `frontend/src/pages/ChannelConfig.tsx` - Update channel configuration form label
- **Implementation Details**:
  - GuildConfig: Change label from "Allowed Host Role IDs" to "Host Roles"
  - ChannelConfig: Change label from "Allowed Host Role IDs (override)" to "Host Roles (override)"
  - Keep helper text unchanged (still explains role IDs and inheritance)
  - No backend changes needed - this is purely a UI label update
  - Maintain same functionality and validation
- **Success**:
  - Server configuration page shows "Host Roles" label
  - Channel configuration page shows "Host Roles (override)" label
  - Helper text remains informative and accurate
  - All existing functionality works unchanged
- **Research References**:
  - #file:../../frontend/src/pages/GuildConfig.tsx (Lines 182-186) - Current label implementation
  - #file:../../frontend/src/pages/ChannelConfig.tsx (Lines 215-219) - Current channel override label
- **Dependencies**:
  - Phase 4 (Web Dashboard Frontend) - Configuration pages exist

### Task 12.13: Convert role ID fields to multi-select dropdowns with actual server roles

Replace text input fields for role IDs with user-friendly multi-select dropdowns showing actual role names from the server.

- **Files**:
  - `frontend/src/pages/GuildConfig.tsx` - Replace Host Roles and Bot Manager Roles text inputs with Autocomplete
  - `frontend/src/pages/ChannelConfig.tsx` - Replace Host Roles (override) text input with Autocomplete
- **Implementation Details**:
  - Fetch available roles on page load using existing `GET /api/v1/guilds/{guild_id}/roles` endpoint
  - Replace TextField components with Material-UI Autocomplete components (multiple selection enabled)
  - Display role names in dropdown, but store role IDs in form state
  - Show selected roles as chips with role names (not IDs)
  - Sort roles by position (API already returns sorted by position)
  - Handle loading states while fetching roles
  - Maintain backward compatibility with existing comma-separated role ID storage format
  - Convert between array of role IDs and comma-separated string format for API
  - Show helpful placeholder text (e.g., "Select roles that can host games")
  - Allow searching/filtering roles by name in dropdown
  - Display role color indicator if available
- **Success**:
  - Server configuration page shows multi-select dropdown for Host Roles
  - Server configuration page shows multi-select dropdown for Bot Manager Roles
  - Channel configuration page shows multi-select dropdown for Host Roles (override)
  - Users can select multiple roles from dropdown showing role names
  - Selected roles display as chips with role names
  - Role IDs correctly saved to backend in comma-separated format
  - Existing role ID configurations load and display correctly as selected role names
  - Dropdown allows searching/filtering by role name
  - Empty selection allowed (inherits from defaults or allows all users)
- **Research References**:
  - #file:../../services/api/routes/guilds.py (Lines 288-350) - Existing list_guild_roles endpoint
  - #file:../../frontend/src/pages/GuildConfig.tsx (Lines 182-192) - Current role ID text inputs
  - #file:../../frontend/src/pages/ChannelConfig.tsx (Lines 215-220) - Current channel role ID override
- **Dependencies**:
  - Existing /guilds/{guild_id}/roles endpoint functional
  - Material-UI Autocomplete component available

### Task 12.14: Upgrade Docker Compose for multi-architecture builds

Configure Docker Compose and Dockerfiles to support building images for both ARM64 and AMD64 architectures using Docker Bake, enabling deployment across different hardware platforms (e.g., Apple Silicon Macs, AWS Graviton, traditional x86 servers). Add image tagging with environment variable-based registry URL prefix and tag configuration.

- **Files**:
  - docker-compose.yml - Add x-bake configuration, tags, and image naming
  - docker/api.Dockerfile - Verify multi-arch base image compatibility
  - docker/bot.Dockerfile - Verify multi-arch base image compatibility
  - docker/scheduler.Dockerfile - Verify multi-arch base image compatibility
  - docker/frontend.Dockerfile - Verify multi-arch base image compatibility
  - .env.example - Document IMAGE_REGISTRY and IMAGE_TAG variables
  - .env - Add IMAGE_REGISTRY and IMAGE_TAG variables (not committed to git)
  - README.md - Document docker buildx bake workflow
- **Implementation**:

  - Add `x-bake` section to each custom service's build configuration with platforms list:
    ```yaml
    api:
      container_name: game-scheduler-api
      image: ${IMAGE_REGISTRY:-}game-scheduler-api:${IMAGE_TAG:-latest}
      build:
        context: .
        dockerfile: docker/api.Dockerfile
        tags:
          - ${IMAGE_REGISTRY:-}game-scheduler-api:${IMAGE_TAG:-latest}
        x-bake:
          platforms:
            - linux/amd64
            - linux/arm64
    ```
  - Add same x-bake configuration to bot, scheduler, and frontend services
  - Ensure `image:` and `tags:` fields use same naming pattern with environment variables
  - Create IMAGE_REGISTRY environment variable with default value "172-16-1-24.xip.boneheads.us:5050/"
  - Create IMAGE_TAG environment variable with default value "latest"
  - Verify all base images (python:3.11-slim, node:18-alpine, nginx:alpine) support both architectures (they do)
  - Verify all dependencies in Dockerfiles are architecture-agnostic
  - Document Docker Bake workflow in .env.example:

    ```bash
    # Docker registry URL prefix (include trailing slash)
    # Examples: 172-16-1-24.xip.boneheads.us:5050/, docker.io/myorg/, empty for local
    IMAGE_REGISTRY=172-16-1-24.xip.boneheads.us:5050/

    # Image tag for built containers (default: latest)
    # Examples: latest, v1.0.0, dev, staging
    IMAGE_TAG=latest
    ```

  - Document build commands in README.md:

    ```bash
    # Create buildx builder if needed (one-time setup)
    docker buildx ls  # Check existing builders
    docker buildx create --use  # Create multi-platform builder

    # Build for multiple architectures and push to registry
    docker buildx bake --push

    # Build specific service(s)
    docker buildx bake --push api bot

    # Build with custom registry and tag
    IMAGE_REGISTRY=myregistry.com/ IMAGE_TAG=v1.2.3 docker buildx bake --push

    # Build without pushing (local only, single platform)
    docker compose build

    # Build for local use with specific platform
    docker compose build --build-arg BUILDPLATFORM=linux/amd64
    ```

- **Success**:
  - x-bake configuration added to all custom services (api, bot, scheduler, frontend)
  - `docker buildx bake --push` successfully builds and pushes multi-arch images
  - Images contain both linux/amd64 and linux/arm64 manifests in registry
  - Environment variables control registry prefix and image tags
  - Build commands documented in README.md
  - .env.example includes all necessary variables with examples
  - Regular `docker compose build` still works for local single-platform builds
- **Research References**:
  - #fetch:https://medium.com/womenintechnology/multi-architecture-builds-are-possible-with-docker-compose-kind-of-2a4e8d166c56 - Docker Bake with docker-compose.yml
  - #fetch:https://docs.docker.com/build/bake/ - Docker Bake reference documentation
  - #file:../../docker-compose.yml - Current compose configuration
  - #file:../../docker/api.Dockerfile - API service Dockerfile
  - #file:../../docker/bot.Dockerfile - Bot service Dockerfile
  - #file:../../docker/scheduler.Dockerfile - Scheduler service Dockerfile
  - #file:../../docker/frontend.Dockerfile - Frontend service Dockerfile
- **Dependencies**:
  - Docker Desktop or Docker Engine with BuildKit support
  - docker buildx CLI plugin (included with modern Docker installations)
  - Multi-platform builder created via `docker buildx create --use`
  - Authentication to target container registry (e.g., `docker login`)
- **Success**:
  - docker-compose.yml includes platform specifications for all services
  - Custom service builds explicitly declare support for linux/amd64 and linux/arm64
  - Each custom service has image field with ${IMAGE_REGISTRY:-} prefix and ${IMAGE_TAG:-latest} variable
  - IMAGE_REGISTRY environment variable documented in .env.example with default value
  - IMAGE_TAG environment variable documented in .env.example
  - Images built with registry prefix: `172-16-1-24.xip.boneheads.us:5050/game-scheduler-api:latest`
  - Images can be built with custom tags: `IMAGE_TAG=v1.0.0 docker-compose build`
  - Images can be built without registry prefix by setting IMAGE_REGISTRY to empty string
  - Default registry prefix "172-16-1-24.xip.boneheads.us:5050/" used when IMAGE_REGISTRY not specified
  - Images can be built successfully on both ARM64 and AMD64 hosts
  - All services start and run correctly on both architectures
  - No architecture-specific dependencies cause build failures
  - BuildKit multi-platform build process documented
  - Tagged images can be pushed to registry: `docker-compose push`
- **Research References**:
  - #file:../../docker-compose.yml (Lines 1-164) - Current compose configuration
  - #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices
  - #fetch:https://docs.docker.com/build/building/multi-platform/ - Docker multi-platform builds
  - #fetch:https://docs.docker.com/compose/compose-file/build/#platforms - Compose platform specification
- **Dependencies**:
  - Docker Buildx enabled (included in Docker Desktop and modern Docker Engine)
  - Base images support target architectures (Python 3.11, Node 18, Nginx are multi-arch)
  - No architecture-specific Python or Node packages in dependencies

### Task 12.15: Fix bot manager role changes not saving in API responses

Fix missing bot_manager_role_ids field in API response construction, causing bot manager role selections to appear lost after saving.

- **Files**:
  - services/api/routes/guilds.py - Add bot_manager_role_ids to all GuildConfigResponse constructions
- **Implementation**:
  - Update list_guilds endpoint (around line 52) to include bot_manager_role_ids in response
  - Update get_guild endpoint (around line 117) to include bot_manager_role_ids in response
  - Update create_guild_config endpoint (around line 171) to include bot_manager_role_ids in response
  - Update update_guild_config endpoint (around line 210) to include bot_manager_role_ids in response
  - Ensure field is populated from guild_config.bot_manager_role_ids model attribute
- **Success**:
  - Bot manager role selections save correctly and persist
  - Guild configuration API responses include bot_manager_role_ids field
  - Frontend displays selected bot manager roles after page refresh
  - No data loss when updating guild configuration
- **Research References**:
  - #file:../../services/api/routes/guilds.py (Lines 1-220) - Guild API routes missing field in responses
  - #file:../../shared/schemas/guild.py (Lines 36-50) - GuildConfigResponse schema includes bot_manager_role_ids
  - #file:../../frontend/src/pages/GuildConfig.tsx (Lines 185-195) - Frontend expects bot_manager_role_ids in response
- **Dependencies**:
  - Phase 9 completion (bot_manager_role_ids field exists in model and schema)

### Task 12.16: Fix notifications not being sent to game participants

Diagnose and fix the notification system to ensure game reminders are sent to participants via Discord DMs at the configured reminder times.

- **Files**:
  - services/scheduler/beat.py - Verify Celery beat is running
  - services/scheduler/celery_app.py - Verify beat_schedule configuration
  - services/scheduler/tasks/check_notifications.py - Check notification scheduling logic
  - services/scheduler/tasks/send_notification.py - Verify notification sending task
  - services/scheduler/services/notification_service.py - Verify event publishing
  - services/bot/events/handlers.py - Verify \_handle_send_notification implementation
  - shared/messaging/events.py - Verify NotificationSendDMEvent definition
  - docker-compose.yml - Verify scheduler service configuration
- **Implementation**:
  - Add comprehensive logging to track notification flow from scheduling to delivery
  - Verify scheduler service container is running in docker-compose
  - Check Celery beat logs to confirm periodic task execution
  - Verify check_notifications task is finding games in the time window
  - Verify notification events are being published to RabbitMQ exchange
  - Check bot service logs for notification event consumption
  - Verify bot can send DMs (user has DMs enabled, bot has permissions)
  - Test with a game scheduled 15 minutes in the future
  - Add debug logging at each step: task scheduling, event publishing, event consumption, DM sending
  - Check Redis cache for notification_sent keys to verify deduplication isn't blocking sends
  - Verify RabbitMQ queue bindings for notification.send_dm events
- **Success**:
  - Scheduler service runs and executes check_notifications task every 5 minutes
  - Notifications are scheduled for games within the reminder time windows
  - Notification events are published to RabbitMQ successfully
  - Bot service consumes notification events from RabbitMQ
  - Discord DMs are sent to participants at correct reminder times
  - End-to-end test: Create game, wait for reminder time, receive DM
  - Logs show complete flow: schedule → publish → consume → send
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1198-1244) - Notification system architecture
  - #file:../../services/scheduler/celery_app.py (Lines 28-35) - Beat schedule configuration
  - #file:../../services/scheduler/tasks/check_notifications.py (Lines 1-164) - Notification checking logic
  - #file:../../services/bot/events/handlers.py (Lines 308-339) - Notification DM handler
- **Dependencies**:
  - Phase 6 completion (notification scheduling system)
  - Phase 2 completion (bot event handlers)
  - Docker compose services running (scheduler, bot, rabbitmq, redis)

## Phase 13: Remove Async Operations from Scheduler Service

### Task 13.1: Add synchronous database session factory

Add synchronous SQLAlchemy session factory to shared/database.py for scheduler service use.

- **Files**:
  - shared/database.py - Add create_engine() and sync session factory
  - pyproject.toml - Add psycopg2-binary dependency
- **Implementation**:
  - Add `create_engine()` alongside existing `create_async_engine()`
  - Create `sync_sessionmaker` using `sessionmaker()` (not `async_sessionmaker`)
  - Add `get_sync_db_session()` context manager function
  - Keep async versions for API and Bot services unchanged
  - Use postgresql+psycopg2:// connection string for sync engine
  - Configure same pooling settings as async engine
- **Success**:
  - get_sync_db_session() context manager works correctly
  - Synchronous Session can execute queries
  - Both sync and async sessions coexist without conflicts
  - psycopg2-binary installed in dependencies
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 148-169) - Synchronous database alternative
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 251-277) - Migration strategy Phase 1
- **Dependencies**:
  - None - foundational change

### Task 13.2: Create synchronous RabbitMQ publisher

Create synchronous EventPublisher using pika library for scheduler service messaging.

- **Files**:
  - shared/messaging/sync_publisher.py - New synchronous publisher
  - pyproject.toml - Verify pika dependency exists
- **Implementation**:
  - Create SyncEventPublisher class using pika (not aio_pika)
  - Implement connect(), publish(), and close() methods (sync, no await)
  - Use same exchange configuration as async EventPublisher
  - Support same routing keys and message formats
  - Add proper connection error handling and retries
  - Keep async EventPublisher for API and Bot services
- **Success**:
  - SyncEventPublisher connects to RabbitMQ successfully
  - Messages published to correct exchanges and routing keys
  - Bot service receives messages from sync publisher
  - Connection lifecycle managed correctly (connect/close)
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 171-195) - Synchronous messaging alternative
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 279-290) - Migration strategy Phase 2
- **Dependencies**:
  - Task 13.1 completion not required (independent)

### Task 13.3: Convert check_notifications task to synchronous

Remove async/await from check_notifications task and use synchronous database/messaging.

- **Files**:
  - services/scheduler/tasks/check_notifications.py - Convert to sync
- **Implementation**:
  - Remove event loop wrapper pattern from task entry point
  - Change task function from async def to def
  - Remove all await keywords from function calls
  - Replace async with context manager with regular with
  - Use get_sync_db_session() instead of get_db_session()
  - Use SyncEventPublisher instead of EventPublisher
  - Remove asyncio imports
  - Update all helper functions to be synchronous
  - Change AsyncSession type hints to Session
- **Success**:
  - Task executes without event loop errors
  - Database queries return correct results
  - Notification events published successfully
  - No async/await keywords remain in file
  - Task execution time unchanged or improved
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 197-219) - Celery task pattern changes
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 304-348) - Before/after example
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 292-302) - Migration strategy Phase 3
- **Dependencies**:
  - Task 13.1 (sync database session)
  - Task 13.2 (sync publisher)

### Task 13.4: Convert update_game_status task to synchronous

Remove async/await from update_game_status task and use synchronous database/messaging.

- **Files**:
  - services/scheduler/tasks/update_game_status.py - Convert to sync
- **Implementation**:
  - Remove event loop wrapper pattern
  - Convert all async functions to synchronous
  - Replace await with direct function calls
  - Use get_sync_db_session() for database operations
  - Use SyncEventPublisher for event publishing
  - Update type hints from AsyncSession to Session
  - Remove asyncio imports
- **Success**:
  - Task executes without event loop errors
  - Game status updates correctly in database
  - Status change events published successfully
  - No async/await keywords remain
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 15-30) - Current anti-pattern
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 292-302) - Migration strategy Phase 3
- **Dependencies**:
  - Task 13.1 (sync database session)
  - Task 13.2 (sync publisher)

### Task 13.5: Convert send_notification task to synchronous

Remove async/await from send_notification task and use synchronous database/messaging.

- **Files**:
  - services/scheduler/tasks/send_notification.py - Convert to sync
- **Implementation**:
  - Remove event loop wrapper pattern
  - Convert task function to synchronous
  - Use get_sync_db_session() for database lookups
  - Call synchronous NotificationService.send_game_reminder()
  - Remove all await keywords
  - Update type hints to use Session
  - Keep retry logic intact
- **Success**:
  - Task executes without event loop errors
  - Database queries work correctly
  - Notification service called successfully
  - Retry logic still functions
  - No async/await keywords remain
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 32-43) - Current async pattern
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 292-302) - Migration strategy Phase 3
- **Dependencies**:
  - Task 13.1 (sync database session)
  - Task 13.6 (sync NotificationService)

### Task 13.6: Convert NotificationService to synchronous

Convert NotificationService.send_game_reminder() method to synchronous implementation.

- **Files**:
  - services/scheduler/services/notification_service.py - Convert to sync
- **Implementation**:
  - Change send_game_reminder() from async def to def
  - Remove await keywords
  - Use SyncEventPublisher instead of EventPublisher
  - Simplify connection lifecycle (connect/publish/close)
  - Update any type hints
  - Remove asyncio imports
- **Success**:
  - send_game_reminder() executes synchronously
  - Events published to RabbitMQ successfully
  - Bot service receives and processes events
  - Connection management works correctly
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 45-57) - Current async service
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 304-306) - Migration strategy Phase 4
- **Dependencies**:
  - Task 13.2 (sync publisher)

### Task 13.7: Update dependencies and test scheduler service

Update pyproject.toml dependencies and run comprehensive tests to verify synchronous refactor.

- **Files**:
  - pyproject.toml - Update dependencies
  - tests/services/scheduler/ - All scheduler tests
  - docker-compose.yml - Verify scheduler service config
- **Implementation**:
  - Ensure psycopg2-binary is in dependencies
  - Ensure pika is in dependencies
  - Keep asyncpg and aio_pika for other services
  - Run pytest tests/services/scheduler/ -v
  - Test check_notifications task end-to-end
  - Test update_game_status task
  - Test send_notification task
  - Monitor logs for event loop errors
  - Verify task execution times are similar or better
  - Check RabbitMQ message delivery
- **Success**:
  - All scheduler unit tests pass
  - Integration tests pass
  - No event loop warnings or errors in logs
  - Tasks execute successfully in Docker environment
  - Notification flow works end-to-end
  - No async/await keywords in services/scheduler/ directory
  - Code complexity reduced (fewer lines, simpler patterns)
- **Research References**:
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 308-320) - Migration strategy Phase 5
  - #file:../research/20251126-scheduler-async-removal-research.md (Lines 322-368) - Success criteria and testing
- **Dependencies**:
  - All Phase 13 tasks complete

## Phase 14: Additional Functionality

### Task 14.1: Add game templates for recurring sessions

Create template system for games that repeat weekly/monthly with same settings.

- **Files**:
  - Database migration for templates
  - `services/api/routes/templates.py` - Template CRUD
  - `services/api/services/template_service.py` - Template logic
  - `frontend/src/pages/Templates.tsx` - Template management UI
- **Success**:
  - Hosts can save game as template
  - Templates include all settings and rules
  - New games created from templates
  - Templates editable and deletable
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1612) - Advanced features list
- **Dependencies**:
  - Phase 3 and 4 (API and frontend)

### Task 14.2: Build calendar export functionality

Generate iCal format calendar files for users to import into their calendar apps.

- **Files**:
  - `services/api/services/calendar_export.py` - iCal generation
  - `services/api/routes/export.py` - Export endpoints
  - `frontend/src/components/ExportButton.tsx` - Export UI
- **Success**:
  - Users can export their joined games
  - iCal files import successfully into Google/Outlook
  - Timezones handled correctly
  - Updates reflected in calendar
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1612) - Advanced features list
- **Dependencies**:
  - icalendar Python library
  - Task 3.5 (game API)

### Task 14.3: Create statistics dashboard

Build dashboard showing game history, participation rates, and trends per guild/channel.

- **Files**:
  - `services/api/services/statistics.py` - Stats aggregation
  - `services/api/routes/stats.py` - Statistics endpoints
  - `frontend/src/pages/Statistics.tsx` - Dashboard page
  - `frontend/src/components/Charts.tsx` - Chart components
- **Success**:
  - Dashboard shows games per month
  - Participation rates calculated
  - Popular times and channels identified
  - Host statistics displayed
  - Charts render responsively
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1612) - Advanced features list
- **Dependencies**:
  - Chart library (recharts or chart.js)
  - Task 3.5 (game API)
