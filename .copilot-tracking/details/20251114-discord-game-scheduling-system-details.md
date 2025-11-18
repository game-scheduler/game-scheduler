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

## Phase 4: Scheduler Service

### Task 4.1: Set up Celery worker with RabbitMQ broker

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

### Task 4.2: Implement notification check task

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
  - Task 4.1 (Celery setup)
  - Task 1.2 (database models)

### Task 4.3: Build notification delivery task

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
  - Task 4.2 (notification check)
  - Task 1.3 (RabbitMQ)

### Task 4.4: Add game status update tasks

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
  - Task 4.1 (Celery setup)
  - Task 1.2 (database models)

## Phase 5: Web Dashboard Frontend

### Task 5.1: Set up React application with Material-UI

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

### Task 5.2: Implement OAuth2 login flow with redirect handling

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
  - Task 5.1 (React setup)
  - Task 3.2 (API OAuth2 endpoints)

### Task 5.3: Build guild and channel management pages

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
  - Task 5.2 (auth flow)
  - Task 3.4 (config API)

### Task 5.4: Create game management interface

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
  - Task 5.3 (guild pages)
  - Task 3.5 (game API)

### Task 5.5: Implement participant pre-population with validation

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
  - Task 5.4 (game interface)
  - Task 3.5 (game API with validation)

## Phase 6: Integration & Testing

### Task 6.1: Integration tests for inter-service communication

Test event publishing and consumption between services using test containers.

- **Files**:
  - `tests/integration/test_event_flow.py` - Event delivery tests
  - `tests/integration/test_bot_to_api.py` - Bot → API communication
  - `tests/integration/test_scheduler_notifications.py` - Notification flow
  - `tests/integration/conftest.py` - Test fixtures
- **Success**:
  - Events published by one service received by others
  - Database changes propagate correctly
  - Message ordering preserved
  - No data loss under normal conditions
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1425-1510) - Message flows
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1539-1568) - Event schemas
- **Dependencies**:
  - pytest 7.4+
  - testcontainers 3.7+
  - All Phase 1-4 services

### Task 6.2: End-to-end tests for user workflows

Test complete user journeys from login through game creation, joining, and notifications.

- **Files**:
  - `tests/e2e/test_create_and_join.py` - Complete game lifecycle
  - `tests/e2e/test_oauth_flow.py` - Authentication journey
  - `tests/e2e/test_notifications.py` - Notification delivery
  - `tests/e2e/test_settings_inheritance.py` - Configuration hierarchy
- **Success**:
  - User can log in via OAuth2
  - Game creation succeeds with all options
  - Discord button clicks work
  - Notifications sent at correct times
  - Settings inherit correctly
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1425-1538) - Complete flows
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1569-1612) - Success criteria
- **Dependencies**:
  - Playwright or Selenium for browser automation
  - All services running

### Task 6.3: Load testing for concurrent operations

Test system performance under concurrent Discord button clicks and API requests.

- **Files**:
  - `tests/load/test_concurrent_joins.py` - Concurrent button clicks
  - `tests/load/test_api_throughput.py` - API request load
  - `tests/load/test_message_broker.py` - RabbitMQ throughput
- **Success**:
  - 100 concurrent button clicks succeed
  - No duplicate participant records
  - Response times < 3 seconds under load
  - No message loss in RabbitMQ
  - Database connections pooled correctly
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1190-1231) - Button interaction requirements
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 1341-1360) - Scalability architecture
- **Dependencies**:
  - Locust or k6 for load generation
  - Monitoring tools

### Task 6.4: Test display name resolution scenarios

Test display name resolution with various user states and edge cases.

- **Files**:
  - `tests/unit/test_display_name_resolver.py` - Unit tests for resolver
  - `tests/integration/test_display_names.py` - Integration tests with Discord API
- **Success**:
  - Nicknames prioritized over global names
  - Global names used when no nickname
  - Username fallback works
  - Users who left guild show "Unknown User"
  - Cache hit rate > 90%
  - Batch resolution efficient
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 125-148) - User identity strategy
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 196-247) - Resolution service
- **Dependencies**:
  - Task 3.6 (display name service)
  - Mock Discord API responses

### Task 6.5: Test pre-populated participants feature

Test all scenarios for pre-populating participants with validation and error handling.

- **Files**:
  - `tests/unit/test_participant_resolver.py` - Unit tests for resolver
  - `tests/integration/test_participant_validation.py` - Integration tests
  - `tests/e2e/test_participant_prepopulation.py` - E2E validation flows
- **Success**:
  - Valid @mentions resolve correctly
  - Invalid mentions return 422 error
  - Ambiguous mentions show suggestions
  - Placeholder strings accepted
  - Form data preserved on error
  - Disambiguation UI functional
  - Participant count limits work
- **Research References**:
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 313-417) - Pre-population design
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 418-614) - Validation implementation
  - #file:../research/20251114-discord-game-scheduling-system-research.md (Lines 615-750) - Error recovery
- **Dependencies**:
  - Task 3.5 (game API)
  - Task 5.5 (frontend validation)

## Phase 7: Advanced Features

### Task 7.1: Implement waitlist support

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

### Task 7.2: Add game templates for recurring sessions

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
  - Phase 3 and 5 (API and frontend)

### Task 7.3: Build calendar export functionality

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

### Task 7.4: Create statistics dashboard

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

## Dependencies

- Python 3.11+ with type hints and async/await
- PostgreSQL 15+ with TIMESTAMPTZ support
- RabbitMQ 3.12+ for message broker
- Redis 7+ for caching
- Docker and Docker Compose for development
- Discord Application with bot token and OAuth2 client credentials

## Success Criteria

- All microservices start and communicate successfully
- Discord bot posts messages with buttons that work reliably
- Web dashboard authenticates users via Discord OAuth2
- Game creation works with all settings inheritance options
- Display names resolve correctly for all guild contexts
- Pre-populated participants validate with clear error messages
- Notifications send at correct times based on inherited settings
- Button clicks respond within 3 seconds consistently
- Role-based authorization prevents unauthorized actions
- System handles service failures gracefully with message persistence
- Load tests pass with 100+ concurrent users
- All test suites pass (unit, integration, e2e, load)
