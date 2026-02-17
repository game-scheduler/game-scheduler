<!-- markdownlint-disable-file -->

# Task Details: Discord Webhook Events for Automatic Guild Sync

## Research Reference

**Source Research**: #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md

## Phase 1: Environment and Dependencies Setup

### Task 1.1: Add DISCORD_PUBLIC_KEY environment variable to all env files

Add Discord public key configuration to all environment files for signature validation.

- **Files**:
  - config/env.dev - Development environment variables
  - config/env.int - Integration test environment
  - config/env.e2e - E2E test environment
  - config/env.staging - Staging environment
  - config/env.prod - Production environment
  - config.template/env.template - Template for new deployments
- **Success**:
  - DISCORD_PUBLIC_KEY variable added to all env files
  - Template includes documentation comment
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 357-367) - Environment variable configuration
- **Dependencies**: None

### Task 1.2: Add PyNaCl dependency to pyproject.toml

Install PyNaCl library for Ed25519 signature verification.

- **Files**:
  - pyproject.toml - Python dependencies
- **Success**:
  - PyNaCl>=1.5.0 added to dependencies array
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 369-377) - Dependency specification
- **Dependencies**: Task 1.1 completion

### Task 1.3: Update APIConfig to include discord_public_key

Add discord_public_key field to APIConfig model for runtime access.

- **Files**:
  - services/api/config.py - API configuration model
- **Success**:
  - discord_public_key field added with proper type hints and validation
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 357-367) - Configuration requirements
- **Dependencies**: Task 1.1 completion

## Phase 2: Webhook Signature Validation (TDD)

### Task 2.1: Create validate_discord_webhook dependency stub

Create FastAPI dependency function stub for Discord webhook signature validation.

- **Files**:
  - services/api/dependencies/discord_webhook.py (new file) - Signature validation dependency
- **Success**:
  - Function signature matches validate_discord_webhook(request, x_signature_ed25519, x_signature_timestamp)
  - Raises NotImplementedError
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 118-151) - Signature validation specification
- **Dependencies**: Phase 1 completion

### Task 2.2: Write failing tests for signature validation

Write comprehensive unit tests for Ed25519 signature validation (RED phase).

- **Files**:
  - tests/unit/api/dependencies/test_discord_webhook.py (new file) - Validation tests
- **Success**:
  - Tests expect NotImplementedError
  - Test cases: valid signature, invalid signature, missing headers, malformed signature, wrong public key
  - Tests verify 401 response for invalid signatures
  - Tests verify body extraction for valid signatures
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing strategy
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 118-151) - Validation requirements
- **Dependencies**: Task 2.1 completion

### Task 2.3: Implement Ed25519 signature validation

Implement PyNaCl-based signature verification (GREEN phase).

- **Files**:
  - services/api/dependencies/discord_webhook.py - Implementation of validation logic
- **Success**:
  - PyNaCl VerifyKey validates timestamp + body against signature
  - HTTPException(401) raised for BadSignatureError
  - Returns validated request body bytes
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 118-151) - Implementation example
- **Dependencies**: Task 2.2 completion

### Task 2.4: Update tests to verify actual signature validation

Update tests to verify real validation behavior without NotImplementedError expectations (GREEN phase).

- **Files**:
  - tests/unit/api/dependencies/test_discord_webhook.py - Updated test assertions
- **Success**:
  - Tests generate real Ed25519 signatures using test key pair
  - Assertions verify successful validation returns body
  - Assertions verify invalid signatures raise 401
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing requirements
- **Dependencies**: Task 2.3 completion

### Task 2.5: Refactor validation with comprehensive edge case tests

Refactor implementation and add comprehensive edge case tests (REFACTOR phase).

- **Files**:
  - services/api/dependencies/discord_webhook.py - Refactored validation
  - tests/unit/api/dependencies/test_discord_webhook.py - Additional edge case tests
- **Success**:
  - Code refactored for clarity and maintainability
  - Edge cases: empty body, very large body, expired timestamp, replay attacks
  - Test coverage >95%
  - All tests remain green
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 118-151) - Security considerations
- **Dependencies**: Task 2.4 completion

## Phase 3: Webhook Endpoint Implementation (TDD)

### Task 3.1: Create webhook endpoint stub returning 501

Create Discord webhook endpoint stub in API routes.

- **Files**:
  - services/api/routes/webhooks.py (new file) - Webhook routes
- **Success**:
  - POST /api/v1/webhooks/discord route created
  - Returns Response(status_code=501)
  - Uses validate_discord_webhook dependency
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 153-225) - Endpoint specification
- **Dependencies**: Phase 2 completion

### Task 3.2: Write failing integration tests for webhook endpoint

Write comprehensive integration tests for webhook endpoint (RED phase).

- **Files**:
  - tests/integration/api/routes/test_webhooks.py (new file) - Webhook integration tests
- **Success**:
  - Tests expect 501 status
  - Test cases: PING validation, APPLICATION_AUTHORIZED event, invalid signature rejection
  - Tests mock RabbitMQ client
  - Tests verify signature validation called
  - Tests use real Discord webhook payload examples
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 60-117) - Webhook event structure
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 390-409) - Integration testing guidance
- **Dependencies**: Task 3.1 completion

### Task 3.3: Implement PING handling (type 0 → 204)

Implement Discord PING validation response (GREEN phase).

- **Files**:
  - services/api/routes/webhooks.py - PING handling logic
- **Success**:
  - Parses validated body as JSON
  - Returns Response(status_code=204) when type==0
  - Sets appropriate Content-Type header
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 60-76) - PING specification
- **Dependencies**: Task 3.2 completion

### Task 3.4: Implement APPLICATION_AUTHORIZED webhook handling with stub sync

Implement APPLICATION_AUTHORIZED event handling with stub sync call (GREEN phase).

- **Files**:
  - services/api/routes/webhooks.py - APPLICATION_AUTHORIZED handling
- **Success**:
  - Checks type==1 and event.type=="APPLICATION_AUTHORIZED"
  - Verifies integration_type==0 (guild install)
  - Logs event receipt
  - Calls stub sync function (initially just logs, no actual sync)
  - Returns 204 for all webhook events
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 78-103) - APPLICATION_AUTHORIZED specification
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 153-225) - Endpoint implementation
- **Dependencies**: Task 3.3 completion

### Task 3.5: Update integration tests and add comprehensive edge cases

Update tests for actual behavior and add edge cases (REFACTOR phase).

- **Files**:
  - tests/integration/api/routes/test_webhooks.py - Updated and expanded tests
- **Success**:
  - Tests verify PING returns 204
  - Tests verify APPLICATION_AUTHORIZED handling
  - Edge cases: missing guild in event, integration_type==1, unknown event types
  - Test idempotency (multiple webhooks for same guild)
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 390-409) - Testing requirements
- **Dependencies**: Task 3.4 completion

## Phase 4: Bot Guild Sync Service (TDD)

### Task 4.1: Create sync_all_bot_guilds stub in guild_service

Create bot-driven guild sync function stub in guild service.

- **Files**:
  - services/api/services/guild_service.py - New sync function stub
- **Success**:
  - Function signature: async def sync_all_bot_guilds(db: AsyncSession, bot_token: str) -> dict
  - Raises NotImplementedError
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Bot sync specification
- **Dependencies**: Phase 3 completion

### Task 4.2: Write tests with real assertions marked as expected failures

Write comprehensive tests for bot guild sync with ACTUAL assertions marked @pytest.mark.xfail (RED phase).

- **Files**:
  - tests/unit/api/services/test_guild_service_bot_sync.py (new file) - Bot sync tests
- **Success**:
  - Tests use @pytest.mark.xfail(reason="Function not yet implemented", strict=True)
  - Tests contain REAL assertions for desired behavior (not expecting NotImplementedError)
  - Test cases: new guild creation, existing guild skip, removed guild marking inactive
  - Tests mock DiscordAPIClient.get_guilds() and get_guild_channels()
  - Tests verify database state after sync
  - Tests verify return values (new_guilds, new_channels counts)
  - Tests run and show as "xfailed" (expected failures)
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Sync logic specification
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing requirements
- **Dependencies**: Task 4.1 completion

### Task 4.3: Implement bot guild sync and remove xfail markers

Implement complete bot guild sync logic and remove @pytest.mark.xfail markers from tests (GREEN phase).

- **Files**:
  - services/api/services/guild_service.py - Complete guild sync implementation
  - tests/unit/api/services/test_guild_service_bot_sync.py - Remove xfail markers only
- **Success**:
  - Fetches bot guilds using bot token
  - Queries existing guild IDs from database
  - Creates GuildConfiguration for new guilds only (sets is_active=True)
  - Fetches channels for each new guild
  - Creates ChannelConfiguration for text/voice/announcement channels (types 0, 2, 5)
  - Creates default GameTemplate for each new guild (is_default=True)
  - Marks guilds as inactive if bot no longer present (optional)
  - Returns count of new guilds and new channels created
  - Commits transaction with proper error handling
  - Logs sync results
  - Remove @pytest.mark.xfail markers from all tests (DO NOT modify test assertions)
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Complete sync implementation
- **Dependencies**: Task 4.2 completion

### Task 4.4: Refactor and add comprehensive edge case tests

Refactor implementation for quality and add comprehensive edge case tests (REFACTOR phase).

- **Files**:
  - services/api/services/guild_service.py - Refactored implementation
  - tests/unit/api/services/test_guild_service_bot_sync.py - Additional edge case tests
- **Success**:
  - Refactor implementation for clarity and maintainability
  - Add edge case tests: empty guild list, Discord API errors, database constraint violations
  - Add tests verifying idempotency (safe to run multiple times)
  - Tests verify new guild/channel/template creation
  - Tests verify existing guilds unchanged
  - Test coverage >95%
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing strategy
- **Dependencies**: Task 4.3 completion

## Phase 5: Move Sync Logic to Bot Service (Architecture Refactoring)

### Task 5.1: Move sync_all_bot_guilds() from API to bot service

Move sync_all_bot_guilds() from API service to new bot service module without behavioral changes.

- **Files**:
  - services/bot/guild_sync.py (new file) - Guild sync logic relocated from API service
  - services/api/services/guild_service.py - Remove sync_all_bot_guilds() function
- **Success**:
  - services/bot/guild_sync.py created with async def sync_all_bot_guilds(discord_client: DiscordAPIClient, db: AsyncSession) -> None
  - Function implementation moved from services/api/services/guild_service.py
  - Uses bot token from bot service config
  - Handles RLS context setup for service users
  - Creates missing guilds/channels/default templates
  - Logs sync results
  - Original function removed from API service
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 611-626) - Bot service implementation
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 587-600) - Architecture rationale
- **Dependencies**: Phase 4 completion

### Task 5.2: Move and update unit tests to bot service

Relocate unit tests from API service to bot service with updated imports and structure.

- **Files**:
  - tests/unit/services/bot/test_guild_sync.py (new file) - Relocated tests
  - tests/unit/services/api/services/test_guild_service_bot_sync.py - Remove file after content moved
- **Success**:
  - Tests moved from tests/unit/services/api/services/test_guild_service_bot_sync.py
  - Import paths updated to reference services/bot/guild_sync.py
  - Fixture references updated for bot service context
  - Old test file removed
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 656-657) - Test relocation
- **Dependencies**: Task 5.1 completion

### Task 5.3: Verify all tests pass after relocation

Run comprehensive test suite to verify code and test relocation was successful.

- **Files**:
  - (Verification only - no file changes)
- **Success**:
  - uv run pytest tests/unit/services/bot/test_guild_sync.py passes
  - uv run pytest tests/integration/ passes
  - uv run pytest tests/e2e/ passes
  - No import errors or broken references
  - All existing functionality preserved
- **Research References**:
  - None - verification step
- **Dependencies**: Task 5.2 completion

### Task 5.4: Add guild sync to bot service startup

Add automatic guild sync to bot service startup lifecycle.

- **Files**:
  - services/bot/app.py - Add sync_all_bot_guilds() call to bot startup/lifespan
- **Success**:
  - Bot service lifespan function calls sync_all_bot_guilds() on startup
  - Uses bot service's discord_client and database session
  - Logs sync results
  - Handles errors gracefully (logs but doesn't fail startup)
  - Sync completes before bot starts processing RabbitMQ messages
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 628-641) - Startup sync implementation
- **Dependencies**: Task 5.3 completion

### Task 5.5: Add E2E ordered test for bot startup sync verification using pytest-order

Create ordered test using pytest-order plugin to verify bot startup sync works, avoiding session-scoped fixture event loop issues.

- **Files**:
  - pyproject.toml - Add pytest-order>=1.4.0 to dev dependencies
  - tests/e2e/test_00_bot_startup_sync.py - Create ordered test with @pytest.mark.order(0)
  - tests/e2e/conftest.py - Add cleanup_startup_sync_guilds fixture
- **Success**:
  - pytest-order plugin added to development dependencies
  - test_00_bot_startup_sync.py created with @pytest.mark.order(0) ensuring it runs first
  - Test waits for bot startup sync to complete (asyncio.sleep(2))
  - Verifies test guilds (111, 222) were created with channels and templates
  - cleanup_startup_sync_guilds fixture (scope="function", autouse=True) added to conftest.py
  - Cleanup runs after each test to delete startup-created data for hermetic execution
  - Deletes GameTemplate, ChannelConfiguration, GuildConfiguration in correct order
  - pytest-order executes after pytest-randomly, preserving order markers
  - E2E tests pass without duplicate key violations or event loop scope errors
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 801-931) - pytest-order solution for random test ordering
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 807-821) - Problem analysis (session fixture + pytest-randomly conflict)
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 823-842) - pytest-order and pytest-randomly compatibility research
- **Dependencies**: Task 5.4 completion

### Task 5.6: Verify all tests pass with startup sync

Run comprehensive test suite to verify bot startup sync works correctly with E2E fixture.

- **Files**:
  - (Verification only - no file changes)
- **Success**:
  - uv run pytest tests/unit/services/bot/test_guild_sync.py passes
  - uv run pytest tests/integration/ passes
  - uv run pytest tests/e2e/ passes
  - Bot startup sync creates guilds without errors
  - E2E fixture cleanup works correctly
  - No test failures or duplicate key violations
  - All existing functionality preserved
- **Research References**:
  - None - verification step
- **Dependencies**: Task 5.5 completion

### Task 5.7: Add GUILD_SYNC_REQUESTED event type

Add new event type for guild synchronization requests to shared messaging module.

- **Files**:
  - shared/messaging/events.py - Add GUILD_SYNC_REQUESTED = 11 to EventType enum
- **Success**:
  - EventType.GUILD_SYNC_REQUESTED = 11 added to enum
  - Event type documented with comment explaining bot guild sync purpose
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 602-609) - Event type specification
- **Dependencies**: Task 5.6 completion

### Task 5.8: Add bot event handler for webhook-triggered guild sync

Create RabbitMQ event handler in bot service to process GUILD_SYNC_REQUESTED events from webhook.

- **Files**:
  - services/bot/events/handlers.py - Add handle_guild_sync_requested handler
- **Success**:
  - async def handle_guild_sync_requested(event: Event) added
  - Handler creates database session and calls sync_all_bot_guilds()
  - Proper error handling and logging
  - Handler registered in EventHandlers.**init**() with self.\_handlers[EventType.GUILD_SYNC_REQUESTED]
  - Processes webhook-triggered sync requests (separate from startup sync)
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 643-654) - Bot handler implementation
- **Dependencies**: Task 5.7 completion

## Phase 6: RabbitMQ Integration for Webhook

### Task 6.1: Update webhook endpoint to publish GUILD_SYNC_REQUESTED event

Connect webhook endpoint to bot sync logic via RabbitMQ event.

- **Files**:
  - services/api/routes/webhooks.py - RabbitMQ event publishing
- **Success**:
  - Injects EventPublisher dependency
  - Publishes Event(event_type=EventType.GUILD_SYNC_REQUESTED, data={}) on APPLICATION_AUTHORIZED
  - Logs event publication
  - Handles RabbitMQ errors gracefully (still returns 204)
  - Bot service handler (Task 5.4) processes the event
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 227-261) - RabbitMQ architecture
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 153-225) - Webhook implementation
- **Dependencies**: Phase 5 completion

### Task 6.2: Add integration tests for RabbitMQ event publishing

Add tests verifying RabbitMQ event publication from webhook endpoint.

- **Files**:
  - tests/integration/api/routes/test_webhooks.py - RabbitMQ integration tests
- **Success**:
  - Tests mock EventPublisher
  - Tests verify publish() called with Event(event_type=EventType.GUILD_SYNC_REQUESTED, data={})
  - Tests verify webhook succeeds even if RabbitMQ fails
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 390-409) - Integration testing
- **Dependencies**: Task 6.1 completion

## Phase 7: Lazy Channel Loading (TDD)

### Task 7.1: Create refresh_guild_channels function stub

Create channel refresh function stub in guild service.

- **Files**:
  - services/api/services/guild_service.py - Channel refresh stub
- **Success**:
  - Function signature: async def refresh_guild_channels(db: AsyncSession, guild_id: int, bot_token: str) -> list
  - Raises NotImplementedError
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - Lazy loading specification
- **Dependencies**: Phase 6 completion

### Task 7.2: Write tests with real assertions marked as expected failures

Write comprehensive tests for channel refresh with ACTUAL assertions marked @pytest.mark.xfail (RED phase).

- **Files**:
  - tests/unit/api/services/test_guild_service_channel_refresh.py (new file) - Channel refresh tests
- **Success**:
  - Tests use @pytest.mark.xfail(reason="Function not yet implemented", strict=True)
  - Tests contain REAL assertions for desired behavior (not expecting NotImplementedError)
  - Test cases: new channel creation, deleted channel marking inactive, reactivated channel
  - Tests mock Discord API channel fetch
  - Tests verify database state after refresh
  - Tests run and show as "xfailed" (expected failures)
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - Channel refresh logic
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing requirements
- **Dependencies**: Task 7.1 completion

### Task 7.3: Implement channel refresh and remove xfail markers

Implement complete channel refresh logic and remove @pytest.mark.xfail markers from tests (GREEN phase).

- **Files**:
  - services/api/services/guild_service.py - Channel refresh implementation
  - services/api/routes/guilds.py - Update channels endpoint with refresh parameter
  - tests/unit/api/services/test_guild_service_channel_refresh.py - Remove xfail markers only
- **Success**:
  - Fetches channels from Discord for specified guild
  - Creates new ChannelConfiguration records
  - Marks deleted channels as inactive
  - Reactivates previously inactive channels that reappear
  - Returns updated channel list
  - Adds refresh: bool = Query(False) parameter to GET /guilds/{guild_id}/channels
  - Calls refresh_guild_channels() when refresh=true
  - Maintains backward compatibility (refresh=false uses cached channels)
  - Remove @pytest.mark.xfail markers from all tests (DO NOT modify test assertions)
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - Implementation details and API endpoint
- **Dependencies**: Task 7.2 completion

### Task 7.4: Refactor and add comprehensive edge case tests

Refactor implementation for quality and add comprehensive edge case tests (REFACTOR phase).

- **Files**:
  - services/api/services/guild_service.py - Refactored implementation
  - tests/unit/api/services/test_guild_service_channel_refresh.py - Additional edge case tests
  - tests/integration/api/routes/test_guilds.py - Endpoint integration tests
- **Success**:
  - Refactor implementation for clarity and maintainability
  - Add edge case tests: Discord API errors, non-existent guilds, channel type filtering
  - Add integration tests for endpoint with refresh parameter
  - Tests verify channel addition, deletion, and reactivation
  - Tests verify endpoint backward compatibility
  - Test coverage >95%
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing strategy
- **Dependencies**: Task 7.3 completion
- **Success**:
  - Tests verify channel refresh updates database
  - Tests verify refresh=false uses cached channels
  - Edge cases: Discord API errors, no channels in guild, all channels deleted
  - Test coverage >95%
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing strategy
- **Dependencies**: Task 7.4 completion

## Phase 8: Manual Discord Portal Configuration

### Task 8.1: Document webhook configuration steps in deployment docs

Create documentation for webhook configuration in Discord Developer Portal.

- **Files**:
  - docs/deployment/discord-webhook-setup.md (new file) - Webhook configuration guide
- **Success**:
  - Step-by-step instructions for portal configuration
  - Public key location documentation
  - Endpoint URL format specification
  - Environment variable setup
  - Troubleshooting common issues
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 452-483) - Manual configuration steps
- **Dependencies**: Phase 7 completion

### Task 8.2: Create testing checklist for webhook validation

Create comprehensive testing checklist for webhook validation.

- **Files**:
  - docs/deployment/discord-webhook-setup.md - Testing section
- **Success**:
  - PING validation test steps
  - APPLICATION_AUTHORIZED event test steps
  - Signature validation verification
  - Guild sync verification steps
  - Rollback procedures
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 390-409) - Manual testing guidance
- **Dependencies**: Task 8.1 completion

## Dependencies

- PyNaCl >= 1.5.0
- Existing DiscordAPIClient
- RabbitMQ infrastructure
- Database models: GuildConfiguration, ChannelConfiguration, GameTemplate
- Discord Developer Portal access

## Success Criteria

- All phases completed with comprehensive TDD coverage
- Webhook signature validation working (401 for invalid signatures)
- PING validation responds 204
- APPLICATION_AUTHORIZED creates guilds automatically
- Bot sync function works without user authentication
- Channel refresh updates database on demand
- Test coverage >90% for all new code
- Documentation complete for deployment
