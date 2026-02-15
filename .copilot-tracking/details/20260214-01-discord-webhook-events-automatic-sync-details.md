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

### Task 4.2: Write failing tests for bot guild sync

Write comprehensive tests for bot guild sync (RED phase).

- **Files**:
  - tests/unit/api/services/test_guild_service_bot_sync.py (new file) - Bot sync tests
- **Success**:
  - Tests expect NotImplementedError
  - Test cases: new guild creation, existing guild skip, removed guild marking inactive
  - Tests mock DiscordAPIClient.get_guilds() and get_guild_channels()
  - Tests verify database state after sync
  - Tests verify return values (new_guilds, new_channels counts)
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Sync logic specification
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing requirements
- **Dependencies**: Task 4.1 completion

### Task 4.3: Implement guild creation logic (new guilds only)

Implement new guild creation from bot guild list (GREEN phase).

- **Files**:
  - services/api/services/guild_service.py - Guild creation implementation
- **Success**:
  - Fetches bot guilds using bot token
  - Queries existing guild IDs from database
  - Creates GuildConfiguration for new guilds only
  - Sets is_active=True for new guilds
  - Returns count of new guilds created
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Implementation details
- **Dependencies**: Task 4.2 completion

### Task 4.4: Implement channel creation for new guilds

Implement channel fetching and creation for newly added guilds (GREEN phase).

- **Files**:
  - services/api/services/guild_service.py - Channel creation logic
- **Success**:
  - Fetches channels for each new guild
  - Creates ChannelConfiguration for text/voice/announcement channels (types 0, 2, 5)
  - Sets is_active=True
  - Returns count of new channels created
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Channel sync specification
- **Dependencies**: Task 4.3 completion

### Task 4.5: Implement default template creation and inactive guild marking

Complete sync logic with template creation and removed guild detection (GREEN phase).

- **Files**:
  - services/api/services/guild_service.py - Template creation and inactive marking
- **Success**:
  - Creates default GameTemplate for each new guild (is_default=True)
  - Marks guilds as inactive if bot no longer present (optional)
  - Commits transaction with proper error handling
  - Logs sync results
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 263-339) - Complete sync implementation
- **Dependencies**: Task 4.4 completion

### Task 4.6: Update tests and add comprehensive edge cases

Update tests for actual behavior and add edge cases (REFACTOR phase).

- **Files**:
  - tests/unit/api/services/test_guild_service_bot_sync.py - Updated and expanded tests
- **Success**:
  - Tests verify new guild/channel/template creation
  - Tests verify existing guilds unchanged
  - Edge cases: empty guild list, Discord API errors, database constraint violations
  - Tests verify idempotency (safe to run multiple times)
  - Test coverage >95%
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing strategy
- **Dependencies**: Task 4.5 completion

## Phase 5: RabbitMQ Integration for Webhook

### Task 5.1: Update webhook endpoint to publish sync_guild message

Connect webhook endpoint to sync logic via RabbitMQ message.

- **Files**:
  - services/api/routes/webhooks.py - RabbitMQ message publishing
- **Success**:
  - Injects RabbitMQ client dependency
  - Publishes {"type": "sync_guild"} message on APPLICATION_AUTHORIZED
  - Logs message publication
  - Handles RabbitMQ errors gracefully (still returns 204)
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 227-261) - RabbitMQ architecture
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 153-225) - Webhook implementation
- **Dependencies**: Phase 4 completion

### Task 5.2: Add integration tests for RabbitMQ message publishing

Add tests verifying RabbitMQ message publication.

- **Files**:
  - tests/integration/api/routes/test_webhooks.py - RabbitMQ integration tests
- **Success**:
  - Tests mock RabbitMQ client
  - Tests verify publish() called with correct exchange/routing_key/message
  - Tests verify webhook succeeds even if RabbitMQ fails
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 390-409) - Integration testing
- **Dependencies**: Task 5.1 completion

## Phase 6: Lazy Channel Loading (TDD)

### Task 6.1: Create refresh_guild_channels function stub

Create channel refresh function stub in guild service.

- **Files**:
  - services/api/services/guild_service.py - Channel refresh stub
- **Success**:
  - Function signature: async def refresh_guild_channels(db: AsyncSession, guild_id: int, bot_token: str) -> list
  - Raises NotImplementedError
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - Lazy loading specification
- **Dependencies**: Phase 5 completion

### Task 6.2: Write failing tests for channel refresh

Write comprehensive tests for on-demand channel refresh (RED phase).

- **Files**:
  - tests/unit/api/services/test_guild_service_channel_refresh.py (new file) - Channel refresh tests
- **Success**:
  - Tests expect NotImplementedError
  - Test cases: new channel creation, deleted channel marking inactive, reactivated channel
  - Tests mock Discord API channel fetch
  - Tests verify database state after refresh
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - Channel refresh logic
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing requirements
- **Dependencies**: Task 6.1 completion

### Task 6.3: Implement channel fetching and database sync

Implement fresh channel fetching and database synchronization (GREEN phase).

- **Files**:
  - services/api/services/guild_service.py - Channel refresh implementation
- **Success**:
  - Fetches channels from Discord for specified guild
  - Creates new ChannelConfiguration records
  - Marks deleted channels as inactive
  - Reactivates previously inactive channels that reappear
  - Returns updated channel list
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - Implementation details
- **Dependencies**: Task 6.2 completion

### Task 6.4: Add refresh query parameter to GET /guilds/{guild_id}/channels

Add refresh capability to existing guild channels endpoint.

- **Files**:
  - services/api/routes/guilds.py - Update channels endpoint
- **Success**:
  - Adds refresh: bool = Query(False) parameter
  - Calls refresh_guild_channels() when refresh=true
  - Returns channels from database
  - Maintains backward compatibility (refresh=false uses cached channels)
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 341-355) - API endpoint specification
- **Dependencies**: Task 6.3 completion

### Task 6.5: Update tests and add comprehensive edge cases

Update tests for actual behavior and add edge cases (REFACTOR phase).

- **Files**:
  - tests/unit/api/services/test_guild_service_channel_refresh.py - Updated tests
  - tests/integration/api/routes/test_guilds.py - Endpoint integration tests
- **Success**:
  - Tests verify channel refresh updates database
  - Tests verify refresh=false uses cached channels
  - Edge cases: Discord API errors, no channels in guild, all channels deleted
  - Test coverage >95%
  - All tests pass
- **Research References**:
  - #file:../research/20260214-01-discord-webhook-events-automatic-sync-research.md (Lines 379-388) - Testing strategy
- **Dependencies**: Task 6.4 completion

## Phase 7: Manual Discord Portal Configuration

### Task 7.1: Document webhook configuration steps in deployment docs

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
- **Dependencies**: Phase 6 completion

### Task 7.2: Create testing checklist for webhook validation

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
- **Dependencies**: Task 7.1 completion

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
