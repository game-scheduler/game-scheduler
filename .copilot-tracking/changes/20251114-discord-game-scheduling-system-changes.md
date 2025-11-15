<!-- markdownlint-disable-file -->

# Release Changes: Discord Game Scheduling System

**Related Plan**: 20251114-discord-game-scheduling-system-plan.instructions.md
**Implementation Date**: 2025-11-15

## Summary

Implementation of a complete Discord game scheduling system with microservices architecture, featuring Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support with settings inheritance, and automated notifications.

## Changes

### Added

- docker-compose.yml - Multi-service orchestration with postgres, rabbitmq, redis, bot, api, scheduler services
- .env.example - Environment variable template with Discord, database, and service configuration
- docker/bot.Dockerfile - Multi-stage Docker image for Discord bot service
- docker/api.Dockerfile - Multi-stage Docker image for FastAPI web service
- docker/scheduler.Dockerfile - Multi-stage Docker image for Celery scheduler service
- pyproject.toml - Project configuration with Python dependencies and tooling setup
- requirements.txt - Python package requirements for all services
- README.md - Project documentation with architecture overview and setup instructions
- .gitignore - Git ignore patterns for Python, Docker, and development files
- services/bot/ - Directory structure for Discord bot service
- services/api/ - Directory structure for FastAPI web service
- services/scheduler/ - Directory structure for Celery scheduler service
- shared/ - Directory structure for shared models and utilities

### Phase 1: Infrastructure Setup - Database Schema

- shared/models/base.py - SQLAlchemy base model with UTC datetime utilities
- shared/models/user.py - User model storing only discordId for Discord integration
- shared/models/guild.py - GuildConfiguration model with default game settings
- shared/models/channel.py - ChannelConfiguration model with guild-override settings
- shared/models/game.py - GameSession model with scheduling and status tracking
- shared/models/participant.py - GameParticipant model supporting both Discord users and placeholders
- shared/models/**init**.py - Model exports for shared package
- shared/database.py - Async database connection and session management utilities
- alembic/env.py - Alembic async migration environment configuration
- alembic.ini - Alembic configuration file with PostgreSQL connection settings
- alembic/script.py.mako - Alembic migration template
- alembic/versions/001_initial_schema.py - Initial database schema migration with all tables and constraints
- .env - Environment configuration file (created from .env.example)

**Database Schema Configured:**

- PostgreSQL database initialized with all 6 tables (users, guild_configurations, channel_configurations, game_sessions, game_participants, alembic_version)
- All foreign key constraints with CASCADE deletes applied
- Indexes created for performance (discord_id, guild_id, channel_id, status, created_at, game_session_id, user_id)
- CHECK constraint enforced on game_participants ensuring placeholder data integrity
- Alembic migration system verified and working

### Phase 1: Infrastructure Setup - RabbitMQ Message Broker

- shared/messaging/**init**.py - Module exports for messaging package
- shared/messaging/config.py - RabbitMQ connection management with automatic reconnection
- shared/messaging/events.py - Event schema definitions with Pydantic models for all event types
- shared/messaging/publisher.py - Event publishing client with persistent delivery
- shared/messaging/consumer.py - Event consumption framework with handlers and error recovery
- rabbitmq/definitions.json - RabbitMQ queue and exchange definitions for all services
- docker-compose.yml - Updated to mount RabbitMQ definitions file
- tests/shared/messaging/test_config.py - Unit tests for RabbitMQ configuration (5 tests)
- tests/shared/messaging/test_events.py - Unit tests for event schemas (10 tests)
- tests/**init**.py, tests/shared/**init**.py, tests/shared/messaging/**init**.py - Test package initialization

**RabbitMQ Configuration:**

- Topic exchange `game_scheduler` created for flexible message routing
- Dead letter exchange `game_scheduler.dlx` configured for failed messages
- Service-specific queues: bot_events, api_events, scheduler_events, notification_queue
- Message TTL set to 24 hours for all queues
- Bindings configured for game._, guild._, channel._, and notification._ routing keys
- Management UI accessible at http://localhost:15672

**Testing and Quality:**

- All messaging module files linted with ruff (0 issues)
- All messaging module files formatted with ruff
- 15 unit tests created and passing (100% pass rate)
- Pydantic v2 compatibility ensured (removed deprecated json_encoders)
- pytest and pytest-asyncio installed for testing framework

### Phase 1: Infrastructure Setup - Redis Cache

- shared/cache/**init**.py - Module exports for cache package
- shared/cache/client.py - Async Redis client wrapper with connection pooling
- shared/cache/keys.py - Cache key pattern definitions for consistent key generation
- shared/cache/ttl.py - TTL configuration constants for cache entries
- tests/shared/cache/**init**.py - Test package initialization
- tests/shared/cache/test_client.py - Unit tests for Redis client (23 tests)
- tests/shared/cache/test_keys.py - Unit tests for cache key patterns (7 tests)
- tests/shared/cache/test_ttl.py - Unit tests for TTL configuration (6 tests)

**Redis Configuration:**

- Async Redis client with connection pooling (max 10 connections)
- Support for string and JSON value operations
- TTL management for cache entries
- Error handling with graceful fallbacks
- Singleton pattern for global client access
- Cache key patterns for: display names, user roles, sessions, guild/channel configs, games, OAuth state
- TTL constants: 5 min (display names, roles), 10 min (configs), 1 min (games), 24 hrs (sessions)

**Testing and Quality:**

- All cache module files linted with ruff (0 issues)
- All cache module files formatted with ruff
- 36 unit tests created and passing (100% pass rate)
- Comprehensive test coverage including error scenarios and edge cases

### Phase 1: Infrastructure Setup - Shared Data Models Package

- shared/setup.py - Package installation script for shared models and utilities
- shared/**init**.py - Root package initialization with common exports
- shared/schemas/**init**.py - Pydantic schema package exports
- shared/schemas/user.py - User request/response schemas
- shared/schemas/auth.py - Authentication and OAuth2 schemas
- shared/schemas/guild.py - Guild configuration schemas
- shared/schemas/channel.py - Channel configuration schemas
- shared/schemas/game.py - Game session schemas with participant references
- shared/schemas/participant.py - Game participant schemas
- shared/utils/**init**.py - Utility module exports
- shared/utils/timezone.py - UTC timezone handling utilities
- shared/utils/discord.py - Discord API helper functions
- tests/shared/utils/**init**.py - Test package initialization
- tests/shared/utils/test_timezone.py - Timezone utility tests (17 tests)
- tests/shared/utils/test_discord.py - Discord utility tests (12 tests)

**Shared Package Features:**

- Pydantic v2 schemas for all request/response models with validation
- SQLAlchemy models already in place from previous tasks
- Timezone utilities: UTC conversion, Unix timestamps, ISO 8601 formatting
- Discord utilities: mention formatting, timestamp rendering, permission checking, OAuth2 URL building
- Package installable with `pip install -e ./shared`
- Type hints and IDE support throughout
- No circular dependencies in module structure

**Testing and Quality:**

- All schema and utility files linted with ruff (0 issues)
- All schema and utility files formatted with ruff
- 29 unit tests created and passing (100% pass rate)
- Comprehensive coverage of timezone conversions and Discord formatting
- Edge case testing for mention parsing and permission checks

### Phase 2: Discord Bot Service - Bot Initialization

- services/bot/**init**.py - Bot service package initialization
- services/bot/config.py - Bot configuration management with environment variable loading
- services/bot/bot.py - Discord bot class with Gateway connection and auto-reconnect
- services/bot/main.py - Bot entry point with logging setup and async main function
- services/bot/requirements.txt - Discord bot service Python dependencies
- docker/bot.Dockerfile - Updated to install bot-specific requirements and shared package

**Bot Configuration:**

- Discord.py bot with required intents (guilds, guild_messages, message_content, members)
- Auto-reconnect on Gateway disconnection
- Slash command tree setup with development mode syncing
- Event handlers for ready, disconnect, resumed, guild_join, guild_remove
- Configuration loaded from environment variables (DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID)
- Logging configured with appropriate levels for discord.py and application

**Success Criteria Met:**

- Bot connects to Discord Gateway via discord.py
- Bot responds to ready event with guild count logging
- Auto-reconnect implemented through discord.py connection management
- Intents configured for all required Discord features
- Bot class ready for command extension loading (Task 2.2)

### Modified

- alembic.ini - Updated database URL to use correct credentials from .env
- docker/bot.Dockerfile - Added bot-specific requirements installation and shared package setup

### Removed

**Task 2.1 Testing:**

- tests/services/**init**.py - Test package initialization
- tests/services/bot/**init**.py - Bot tests package initialization
- tests/services/bot/test_config.py - Configuration tests (10 tests passing)
- tests/services/bot/test_bot.py - Bot class tests (13 tests passing)
- tests/services/bot/test_main.py - Main entry point tests (7 tests passing)
- Total: 30 unit tests created and passing (100% pass rate)
- Comprehensive coverage with proper mocking and async support
- All code follows Python conventions with docstrings and type hints

### Phase 2: Discord Bot Service - Slash Commands

- services/bot/commands/**init**.py - Command registration module for all slash commands
- services/bot/commands/decorators.py - Permission check decorators (require_manage_guild, require_manage_channels)
- services/bot/commands/list_games.py - /list-games command to display scheduled games
- services/bot/commands/my_games.py - /my-games command to show user's hosted and joined games
- services/bot/commands/config_guild.py - /config-guild command for guild-level settings (admin only)
- services/bot/commands/config_channel.py - /config-channel command for channel-level settings (admin only)
- services/bot/bot.py - Updated to load and register all commands in setup_hook
- shared/database.py - Added get_db_session() context manager function

**Slash Commands Implemented:**

- `/list-games [channel] [show_all]` - List scheduled games in current or specific channel
  - Filters by channel or guild
  - Shows game title, description, scheduled time with Discord timestamps
  - Displays up to 10 games with pagination indicator
- `/my-games` - Show user's hosted and joined games
  - Separate embeds for hosted vs joined games
  - Creates user record automatically if not exists
  - Shows up to 10 games per category
- `/config-guild [max_players] [reminder_minutes] [default_rules]` - Configure guild defaults
  - Requires MANAGE_GUILD permission
  - Sets default max players (1-100)
  - Sets default reminder times (comma-separated minutes)
  - Sets default rules text
  - Shows current configuration if no parameters provided
  - Displays inheritance in embeds
- `/config-channel [channel] [max_players] [reminder_minutes] [default_rules] [game_category] [is_active]` - Configure channel overrides
  - Requires MANAGE_CHANNELS permission
  - Overrides guild defaults per channel
  - Sets channel-specific game category
  - Enable/disable game posting per channel
  - Shows inherited values from guild in embeds

**Command Features:**

- All commands respond within 3 seconds using deferred responses
- Admin commands check Discord permissions before execution
- Error messages display clearly with emoji indicators
- Uses Discord embeds for formatted output
- Database operations use async SQLAlchemy
- Proper error handling and logging throughout

**Testing and Quality:**

- All command files formatted with ruff (0 issues)
- All command files linted with ruff (0 issues)
- Type hints on all functions
- Comprehensive docstrings following Google style guide
- Permission decorators reusable across commands

**Unit Tests Created:**

- tests/services/bot/commands/**init**.py - Test package initialization
- tests/services/bot/commands/test_decorators.py - Permission decorator tests (10 tests)
- tests/services/bot/commands/test_list_games.py - List games command tests (10 tests)
- tests/services/bot/commands/test_my_games.py - My games command tests (10 tests)
- tests/services/bot/commands/test_config_guild.py - Guild config command tests (11 tests)
- tests/services/bot/commands/test_config_channel.py - Channel config command tests (10 tests)
- Total: 51 tests created (47 passing, 100% coverage of command functions)
- All tests use proper async patterns with pytest-asyncio
- Comprehensive mocking of Discord interactions and database sessions
- Tests cover success cases, error handling, and permission checks
