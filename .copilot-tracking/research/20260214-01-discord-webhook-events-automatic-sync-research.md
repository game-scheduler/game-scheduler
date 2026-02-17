<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Webhook Events for Automatic Guild Sync

## Research Executed

### Discord Webhook Events Documentation

- #fetch:https://docs.discord.com/developers/events/webhook-events
  - APPLICATION_AUTHORIZED event sent when bot added to guild (integration_type=0)
  - APPLICATION_DEAUTHORIZED event sent when user deauthorizes app
  - No GUILD_DELETE or guild-specific removal events available
  - Webhooks require public HTTPS endpoint with Ed25519 signature validation
  - PING validation required during initial setup (respond 204)
  - Must respond within 3 seconds or Discord retries with exponential backoff

### Discord Application API

- #fetch:https://docs.discord.com/developers/resources/application#edit-current-application
  - PATCH /applications/@me can configure webhook URL programmatically
  - Requires bot token authentication (Authorization: Bot {token})
  - event_webhooks_url: public HTTPS endpoint
  - event_webhooks_status: 1=disabled, 2=enabled, 3=disabled_by_discord
  - event_webhooks_types: array of event type strings
  - Public key available in Developer Portal → General Information

### Python Ed25519 Libraries

- #fetch:https://pynacl.readthedocs.io/en/latest/signing/
  - PyNaCl: VerifyKey.verify(timestamp + body, signature)
  - Simple API, widely used in Discord community
- #fetch:https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
  - cryptography: Ed25519PublicKey.verify(signature, timestamp + body)
  - Alternative if PyNaCl not desired

### Project Code Analysis

- services/api/routes/guilds.py (Lines 293-318)
  - Existing sync_guilds endpoint calls guild_service.sync_user_guilds()
  - Requires user authentication (access token)
  - Returns GuildSyncResponse with new_guilds, new_channels, updated_channels
- services/api/services/guild_service.py
  - sync_user_guilds() orchestrates full guild/channel sync
  - Fetches bot guilds via Discord API
  - Creates missing guilds with channels and default templates
  - Updates existing guilds' channels
- shared/discord/client.py
  - DiscordAPIClient.get_guilds() fetches guilds (bot or user token)
  - Bot token format: 3 parts separated by 2 dots (BASE64.TIMESTAMP.SIGNATURE)
- services/api/config.py
  - APIConfig has discord_bot_token
  - No DISCORD_PUBLIC_KEY in current config

## Key Discoveries

### Webhook Event Structure

**PING Validation (type=0):**

```json
{
  "version": 1,
  "application_id": "1234567890",
  "type": 0
}
```

Response: 204 No Content with Content-Type header

**APPLICATION_AUTHORIZED (type=1):**

```json
{
  "version": 1,
  "application_id": "1234567890",
  "type": 1,
  "event": {
    "type": "APPLICATION_AUTHORIZED",
    "timestamp": "2024-10-18T14:42:53.064834",
    "data": {
      "integration_type": 0,
      "scopes": ["applications.commands"],
      "user": { "id": "...", "username": "..." },
      "guild": { "id": "...", "name": "..." }
    }
  }
}
```

**Critical Fields:**

- `integration_type`: 0 = guild install, 1 = user install
- `guild`: Present only when integration_type=0
- `guild.id`: Discord snowflake ID of the guild

### Signature Validation Requirements

**Headers Provided by Discord:**

- `X-Signature-Ed25519`: Hex-encoded signature
- `X-Signature-Timestamp`: Unix timestamp as string

**Validation Process:**

1. Extract public key from environment (DISCORD_PUBLIC_KEY)
2. Concatenate timestamp + raw request body
3. Verify signature using Ed25519 public key
4. Return 401 if validation fails

**PyNaCl Implementation:**

```python
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

verify_key = VerifyKey(bytes.fromhex(public_key))
try:
    verify_key.verify(
        timestamp.encode() + body,
        bytes.fromhex(signature)
    )
except BadSignatureError:
    raise HTTPException(status_code=401, detail="Invalid signature")
```

### Sync Logic Integration Challenge

**Problem**: Existing sync_user_guilds() requires user access token:

```python
async def sync_user_guilds(
    db: AsyncSession,
    access_token: str,  # User OAuth token
    user_discord_id: str
) -> dict:
```

**Webhook Context**: No user authentication when bot joins guild

- Bot joins via invite link (no user session)
- Webhook contains guild_id but no user context
- Need bot-driven sync, not user-driven sync

**Solution Options:**

1. **Bot-Only Sync (Recommended)**:
   - Create new sync function using bot token only
   - Fetch guilds via bot token: `client.get_guilds(token=bot_token)`
   - Create missing guilds with channels + default template
   - Don't require user context for initial setup

2. **Defer to Manual Sync**:
   - Keep webhook simple - just log the event
   - User clicks sync button on first visit
   - Simple but defeats automation purpose

3. **System User Approach**:
   - Create "system" user record in database
   - Use bot token as if it were user token
   - More complex, requires schema changes

### Manual Discord Portal Configuration

**Steps:**

1. Go to https://discord.com/developers/applications
2. Select your application
3. Click "Webhooks" in left sidebar
4. Under "Endpoint URL", enter: `https://yourdomain.com/api/v1/webhooks/discord`
5. Discord sends PING request - endpoint must respond 204
6. Once validated, toggle "Events" to ON
7. Select "Application Authorized" checkbox
8. Click "Save Changes"

**Public Key Location:**

- Developer Portal → Your App → General Information
- Copy "Public Key" field (hex string)
- Store as `DISCORD_PUBLIC_KEY` environment variable

## Recommended Approach

### Architecture: RabbitMQ-Based Decoupling

**Services:**

1. **API Service**: Webhook endpoint (signature validation only)
2. **RabbitMQ**: Message queue for `sync_guild` commands
3. **Bot Service**: Guild sync logic (owns Discord integration)

**Message Flow:**

```
Discord Webhook → API validates → Publish "sync_guild" → Bot syncs all guilds
Periodic Timer → Publish "sync_guild" → Bot syncs all guilds
Manual Trigger → Publish "sync_guild" → Bot syncs all guilds
```

**Why "all guilds" not specific guild:**

- Database query for all guilds is cheap (<100ms for 1000 guilds with index)
- Bot guild fetch is cheap (single API call)
- Idempotent: safe to run repeatedly
- Only creates NEW guilds (doesn't update channels for existing guilds)
- Channel updates handled lazily (when user accesses edit template screen)
- Same code path for webhook, periodic sync, and manual trigger

### Phase 1: Webhook Endpoint (API Service)

**Route: POST /api/v1/webhooks/discord**

```python
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

async def validate_discord_webhook(
    request: Request,
    x_signature_ed25519: str = Header(...),
    x_signature_timestamp: str = Header(...),
) -> bytes:
    """Validate Discord webhook Ed25519 signature."""
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    body = await request.body()

    verify_key = VerifyKey(bytes.fromhex(public_key))
    try:
        verify_key.verify(
            x_signature_timestamp.encode() + body,
            bytes.fromhex(x_signature_ed25519)
        )
    except BadSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body

@router.post("/webhooks/discord")
async def discord_webhook(
    validated_body: Annotated[bytes, Depends(validate_discord_webhook)],
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq),
):
    """
    Receive Discord webhook events.

    - Validates Ed25519 signature
    - Responds to PING
    - Publishes sync_guild message for bot service to consume
    """
    payload = json.loads(validated_body)

    # Handle PING validation (Discord tests endpoint)
    if payload.get("type") == 0:
        return Response(status_code=204)

    # Handle APPLICATION_AUTHORIZED (bot added to guild)
    if payload.get("type") == 1:
        event = payload.get("event", {})
        if event.get("type") == "APPLICATION_AUTHORIZED":
            data = event.get("data", {})
            if data.get("integration_type") == 0:  # Guild install (not user)
                # Publish sync command to RabbitMQ
                await rabbitmq.publish(
                    exchange="guild_sync",
                    routing_key="sync",
                    message={"type": "sync_guild"}
                )
                logger.info("Published sync_guild message after APPLICATION_AUTHORIZED")

    return Response(status_code=204)
```

### Phase 2: Bot Sync Logic (Bot Service)

**RabbitMQ Consumer:**

```python
# In bot service
async def handle_sync_guild_message(message: dict):
    """Handle sync_guild message from RabbitMQ."""
    if message.get("type") == "sync_guild":
        await sync_all_bot_guilds()

# Register consumer
await rabbitmq.consume(
    queue="guild_sync",
    callback=handle_sync_guild_message
)
```

**Guild Sync Function (Creates NEW Guilds Only):**

```python
async def sync_all_bot_guilds() -> dict:
    """
    Sync all guilds bot is in using bot token.

    - Fetches all bot guilds from Discord (1 API call)
    - Creates missing guilds with channels and default template
    - DOES NOT update channels for existing guilds (lazy loading via edit template screen)
    - Marks removed guilds as inactive (optional)

    Returns:
        Dict with counts: new_guilds, new_channels
    """
    async with get_db_session() as db:
        # Fetch all guilds bot is in (bot token, not user token)
        bot_guilds = await discord_client.get_guilds(token=bot_token)
        bot_guild_ids = {g["id"] for g in bot_guilds}

        # Fetch all existing guild IDs from database
        result = await db.execute(select(GuildConfiguration.guild_discord_id))
        db_guild_ids = {row[0] for row in result.all()}

        new_guilds = 0
        new_channels = 0

        # Create missing guilds ONLY
        for guild_data in bot_guilds:
            guild_id = guild_data["id"]

            if guild_id not in db_guild_ids:
                # Create new guild
                guild = GuildConfiguration(
                    guild_discord_id=guild_id,
                    is_active=True
                )
                db.add(guild)
                await db.flush()
                new_guilds += 1

                # Fetch and create channels for NEW guild
                channels = await discord_client.get_guild_channels(guild_id)
                for channel_data in channels:
                    if channel_data["type"] in [0, 2, 5]:  # Text/Voice/Announcement
                        channel = ChannelConfiguration(
                            channel_discord_id=channel_data["id"],
                            guild_id=guild.id,
                            is_active=True
                        )
                        db.add(channel)
                        new_channels += 1

                # Create default template
                default_template = GameTemplate(
                    guild_id=guild.id,
                    name="Default Game",
                    description="Default game template",
                    max_players=10,
                    is_default=True
                )
                db.add(default_template)

        # Optional: Mark removed guilds inactive
        removed_guild_ids = db_guild_ids - bot_guild_ids
        if removed_guild_ids:
            await db.execute(
                update(GuildConfiguration)
                .where(GuildConfiguration.guild_discord_id.in_(removed_guild_ids))
                .values(is_active=False)
            )

        await db.commit()

        logger.info(
            "Guild sync complete: %d new guilds, %d new channels",
            new_guilds, new_channels
        )

        return {
            "new_guilds": new_guilds,
            "new_channels": new_channels,
        }
```

### Phase 3: Lazy Channel Loading (Edit Template Screen)

**Why Lazy Loading:**

- Channel updates for existing guilds are rare
- Most expensive part of sync is fetching channels for ALL guilds
- Users only interact with channels when editing templates
- Fresh channel list ensures accurate UI without background sync overhead

**Frontend: Refetch Channels on Template Edit**

```typescript
// When user opens edit template dialog
const fetchGuildChannels = async (guildId: string) => {
  // API endpoint triggers channel refresh for specific guild
  const response = await fetch(`/api/v1/guilds/${guildId}/channels?refresh=true`);
  return response.json();
};
```

**API Endpoint: Refresh Guild Channels on Demand**

```python
@router.get("/guilds/{guild_id}/channels")
async def get_guild_channels(
    guild_id: int,
    refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_guild_member),
) -> list[ChannelResponse]:
    """
    Get channels for guild.

    - If refresh=true: Fetch fresh channels from Discord and update database
    - If refresh=false: Return cached channels from database
    """
    # Verify user has access to guild
    guild = await get_guild_by_id(db, guild_id)

    if refresh:
        # Fetch fresh channels from Discord
        channels = await discord_client.get_guild_channels(
            guild.guild_discord_id,
            token=bot_token
        )

        discord_channel_ids = {c["id"] for c in channels}

        # Get existing channels
        result = await db.execute(
            select(ChannelConfiguration).where(
                ChannelConfiguration.guild_id == guild_id
            )
        )
        existing_channels = result.scalars().all()
        existing_channel_map = {
            c.channel_discord_id: c for c in existing_channels
        }

        # Create new channels
        for channel_data in channels:
            if channel_data["type"] in [0, 2, 5]:
                if channel_data["id"] not in existing_channel_map:
                    channel = ChannelConfiguration(
                        channel_discord_id=channel_data["id"],
                        guild_id=guild_id,
                        is_active=True
                    )
                    db.add(channel)
                else:
                    # Reactivate if was inactive
                    existing = existing_channel_map[channel_data["id"]]
                    if not existing.is_active:
                        existing.is_active = True

        # Mark deleted channels inactive
        for existing in existing_channels:
            if existing.channel_discord_id not in discord_channel_ids:
                if existing.is_active:
                    existing.is_active = False

        await db.commit()

    # Return channels from database
    result = await db.execute(
        select(ChannelConfiguration).where(
            ChannelConfiguration.guild_id == guild_id,
            ChannelConfiguration.is_active == True
        )
    )
    return result.scalars().all()
```

### Environment Variables

**Add to all environment files:**

```bash
# Discord webhook configuration
DISCORD_PUBLIC_KEY=your_hex_public_key_from_portal
```

**Existing variables (already have):**

```bash
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_BOT_CLIENT_ID=your_client_id
```

### Dependencies

**Add PyNaCl:**

```toml
# pyproject.toml
dependencies = [
    # ... existing deps
    "PyNaCl>=1.5.0",
]
```

### Testing Strategy

**Unit Tests:**

- Mock validate_discord_webhook dependency
- Test PING response (type 0 → 204)
- Test APPLICATION_AUTHORIZED handling
- Test signature validation (valid/invalid)

**Integration Tests:**

- Send PING with valid signature → expect 204
- Send APPLICATION_AUTHORIZED → verify guild created
- Send invalid signature → expect 401
- Send APPLICATION_AUTHORIZED for existing guild → no duplicate

**Manual Testing:**

1. Configure webhook URL in Discord portal
2. Discord sends PING → verify 204 response
3. Add bot to test guild
4. Verify APPLICATION_AUTHORIZED received
5. Verify guild/channels/template created in database

## Implementation Guidance

**Objectives:**

- Automatic guild creation when bot joins server
- No user interaction required for initial setup
- Minimal changes to existing sync logic
- Secure signature validation

**Key Tasks:**

1. Add DISCORD_PUBLIC_KEY environment variable
2. Install PyNaCl dependency
3. Create webhook signature validation dependency
4. Create POST /api/v1/webhooks/discord endpoint
5. Implement bot-driven sync function
6. Add unit and integration tests
7. Manually configure webhook in Discord portal

**Dependencies:**

- PyNaCl for Ed25519 signature verification
- Existing DiscordAPIClient for guild/channel fetching
- Existing database models (GuildConfiguration, ChannelConfiguration, GameTemplate)

**Success Criteria:**

- Webhook endpoint responds 204 to PING
- Signature validation rejects invalid requests (401)
- APPLICATION_AUTHORIZED creates guild + channels + default template
- Existing guilds not duplicated
- Comprehensive test coverage
- Manual sync button still works (for channel updates)
- No breaking changes to existing sync functionality

## Notes

**Why Not Use Existing sync_user_guilds()?**

- Requires user access token (OAuth2)
- Webhook has no user context
- Bot joins happen without user authentication
- Need bot-token-only sync for automation

**Webhook Limitations:**

- No GUILD_DELETE event (bot removal not detected)
- Can't detect guild updates (name changes, etc.)
- Manual sync button still useful for:
  - Channel updates
  - Detecting removed guilds
  - User-initiated refresh

**Future Enhancements:**

- Periodic cleanup job to detect removed guilds
- Track last_seen timestamp on guilds
- Mark guilds inactive if bot not present during cleanup
- Consider polling as fallback for removal detection

## Architectural Issues and Refactoring Plan

### Problem: Misplaced Guild Sync Logic

The initial implementation (Phase 4) placed `sync_all_bot_guilds()` in [services/api/services/guild_service.py](services/api/services/guild_service.py) and called it directly from API startup in [services/api/app.py](services/api/app.py). This violates the project's RabbitMQ-based microservice architecture in several ways:

**Architecture Violations:**

1. **Service Boundary Violation**: Guild synchronization is a bot-driven operation that should be handled by the bot service, not the API service
2. **Tight Coupling**: Direct function calls between services prevent independent deployment and scaling
3. **Missing Message Bus**: Bypasses the RabbitMQ event-driven architecture used elsewhere in the project
4. **Token Misplacement**: API service shouldn't directly use bot token for Discord operations

**Evidence from Codebase:**

- Existing bot operations use RabbitMQ event handlers in [services/bot/events/handlers.py](services/bot/events/handlers.py)
- Game lifecycle events publish to RabbitMQ rather than calling service methods directly
- Bot service owns Discord bot operations (status management, embeds, notifications)
- API service publishes events; bot service consumes and executes Discord actions

### Refactoring Approach: RabbitMQ-Based Guild Sync

**Architecture Decision: Two Different Sync Triggers**

Guild sync is triggered in two fundamentally different scenarios:

1. **Bot Startup Sync** (Internal Operation)
   - Triggered by: Bot service starting up
   - Handler: Bot service calls `sync_all_bot_guilds()` directly in its startup lifecycle
   - Message Queue: **NOT used** - bot manages its own initialization
   - Rationale: Each service handles its own startup responsibilities

2. **Webhook Sync** (External Event)
   - Triggered by: Discord APPLICATION_AUTHORIZED webhook received by API
   - Handler: API publishes `GUILD_SYNC_REQUESTED` event → Bot service consumes and syncs
   - Message Queue: **Used** - enables cross-service communication
   - Rationale: External events arrive at API, which publishes to bot for Discord operations

This separation keeps concerns clear: internal operations are self-managed, external events use the message bus.

**Step 1: Add Guild Sync Event Type**

Add new event type to [shared/messaging/events.py](shared/messaging/events.py):

```python
class EventType(IntEnum):
    # Existing events...
    GUILD_SYNC_REQUESTED = 11  # Request bot to sync all guilds
```

**Step 2: Move Sync Logic to Bot Service**

Create [services/bot/guild_sync.py](services/bot/guild_sync.py) with relocated `sync_all_bot_guilds()` function:

```python
async def sync_all_bot_guilds(
    discord_client: DiscordAPIClient,
    db: AsyncSession
) -> None:
    """Sync all guilds the bot is member of, creating configs and default templates."""
    # Move implementation from services/api/services/guild_service.py
    # Uses bot token from bot service config
    # Handles RLS context setup
    # Creates missing guilds/channels/templates
```

**Step 3: Add Bot Startup Sync**

Modify [services/bot/app.py](services/bot/app.py) to sync guilds on bot service startup:

```python
# In bot service lifespan/startup
async def startup():
    logger.info("Starting bot service...")
    await sync_all_bot_guilds(discord_client, db)
    logger.info("Guild sync complete")
    # Continue with normal bot startup...
```

**Rationale**: Bot owns guild sync logic, so it should sync on its own startup. No need for API to publish message telling bot to do its internal initialization.

**Step 4: Add Bot Event Handler for Webhooks**

Update [services/bot/events/handlers.py](services/bot/events/handlers.py) to handle webhook-triggered syncs:

```python
async def handle_guild_sync_requested(event: Event) -> None:
    """Handle webhook-triggered request to sync all bot guilds."""
    async with get_async_session() as db:
        await sync_all_bot_guilds(discord_client, db)

# Register in EventHandlers.__init__
self._handlers[EventType.GUILD_SYNC_REQUESTED] = handle_guild_sync_requested
```

**Rationale**: Webhooks arrive at API service (external event), so API publishes RabbitMQ event for bot to process. This separates concerns: API handles HTTP, bot handles Discord operations.

**Step 5: Move and Update Tests**

- Move tests from [tests/unit/services/api/services/test_guild_service_bot_sync.py](tests/unit/services/api/services/test_guild_service_bot_sync.py) to `tests/unit/services/bot/test_guild_sync.py`
- Update imports and fixture references
- Add integration tests for RabbitMQ message flow

### E2E Testing Strategy

**Challenge:** E2E tests were failing with duplicate key violations because:

1. API startup sync creates guilds (e.g., guild_id 111)
2. Test fixtures also try to create the same guilds
3. PostgreSQL unique constraint violation on `ix_users_discord_id`

**Solution: Session-Scoped Autouse Fixture**

Add to [tests/e2e/conftest.py](tests/e2e/conftest.py):

```python
@pytest.fixture(scope="session", autouse=True)
async def verify_and_cleanup_startup_sync(
    async_session_maker: Callable[[], AsyncContextManager[AsyncSession]]
) -> AsyncGenerator[None, None]:
    """
    Verify startup sync creates guilds, then clean up for hermetic tests.

    Runs before pytest-randomly because session fixtures execute first.
    Provides test coverage for automatic guild sync feature.
    """
    # Wait for API startup sync to complete
    await asyncio.sleep(2)

    # Verify expected guilds were created
    async with async_session_maker() as session:
        result = await session.execute(
            select(GuildConfiguration).where(
                GuildConfiguration.guild_id.in_([111, 222])
            )
        )
        guilds = result.scalars().all()
        assert len(guilds) == 2, "Startup sync should create test guilds"

        # Verify channels and templates created
        for guild in guilds:
            channels = await session.execute(
                select(ChannelConfiguration).where(
                    ChannelConfiguration.guild_id == guild.guild_id
                )
            )
            assert len(channels.scalars().all()) > 0, f"Guild {guild.guild_id} missing channels"

            templates = await session.execute(
                select(GameTemplate).where(
                    GameTemplate.guild_id == guild.guild_id
                )
            )
            assert len(templates.scalars().all()) > 0, f"Guild {guild.guild_id} missing templates"

    # Clean up startup-created data for hermetic tests
    async with async_session_maker() as session:
        # Delete in correct order to respect foreign keys
        await session.execute(delete(GameTemplate).where(GameTemplate.guild_id.in_([111, 222])))
        await session.execute(delete(ChannelConfiguration).where(ChannelConfiguration.guild_id.in_([111, 222])))
        await session.execute(delete(GuildConfiguration).where(GuildConfiguration.guild_id.in_([111, 222])))
        await session.commit()

    yield

    # Cleanup after all tests (if needed)
```

**Key Benefits:**

- Session scope ensures runs once before all tests
- Autouse means no explicit fixture dependency needed
- Runs before pytest-randomly because session fixtures execute first
- Provides actual test coverage for startup sync feature
- Cleans up for hermetic test execution
- No need to disable startup sync in e2e environment

**Alternative Considered: Environment-Based Disabling**

Initially considered adding `ENVIRONMENT=e2e` to [config/env.e2e](config/env.e2e) and checking in startup code:

```python
if config.environment not in ["test", "e2e"]:
    await sync_all_bot_guilds(...)
```

**Rejected because:**

- Reduces test coverage by disabling the feature being tested
- E2E environment should mimic production behavior
- Loses ability to verify automatic sync works correctly
- Session fixture approach tests the feature AND maintains hermetic tests

### Implementation Dependencies

**Files to Modify:**

- [shared/messaging/events.py](shared/messaging/events.py) - Add GUILD_SYNC_REQUESTED event type
- [services/api/app.py](services/api/app.py) - Replace direct call with RabbitMQ publish
- [services/bot/events/handlers.py](services/bot/events/handlers.py) - Add sync handler
- [tests/e2e/conftest.py](tests/e2e/conftest.py) - Add session-scoped autouse fixture

**Files to Create:**

- [services/bot/guild_sync.py](services/bot/guild_sync.py) - Move sync logic here
- [tests/unit/services/bot/test_guild_sync.py](tests/unit/services/bot/test_guild_sync.py) - Move/update tests

**Files to Remove:**

- Tests in [tests/unit/services/api/services/test_guild_service_bot_sync.py](tests/unit/services/api/services/test_guild_service_bot_sync.py) (after moving)

### Success Criteria

**Refactoring Complete When:**

- Guild sync logic resides in bot service, not API service
- Bot service syncs guilds on its own startup (no RabbitMQ message needed)
- API webhook endpoint publishes GUILD_SYNC_REQUESTED event for webhook-triggered syncs
- Bot service consumes GUILD_SYNC_REQUESTED events and executes sync
- All unit tests moved and passing
- E2E tests include session fixture verifying bot startup sync
- No duplicate key violations in e2e test runs
- Startup sync still works in all environments (dev, staging, production)
- Clear separation: internal operations self-managed, external events use message bus

## Alternative Solution: pytest-order for Random Test Ordering (2026-02-17)

### Problem: Session Fixture + pytest-randomly Conflict

The session-scoped autouse fixture in [tests/e2e/conftest.py](tests/e2e/conftest.py) (lines 58-143) has an event loop scope mismatch issue:

```
ScopeMismatch: You tried to access the function scoped fixture event_loop with a
session scoped request object, involved factories:
tests/e2e/conftest.py:58: def verify_and_cleanup_startup_sync()
```

**Root Cause**: Session-scoped async fixtures require a session-scoped `event_loop` fixture, but pytest-asyncio provides only function-scoped event loops by default.

**Additional Challenge**: Project uses `pytest-randomly>=4.0.1` which randomizes test order, making test*00*\* naming unreliable.

### Research Executed

- #fetch:https://github.com/pytest-dev/pytest-randomly
  - pytest-randomly automatically shuffles test order (modules, classes, functions)
  - Recommends pytest-order plugin for fixing order of specific tests
  - pytest-order executes after pytest-randomly, preserving order markers

- #fetch:https://pytest-order.readthedocs.io/en/latest/other_plugins.html#pytest-randomly
  - pytest-order works correctly with pytest-randomly
  - Marked tests execute in correct order; unmarked tests remain randomized
  - pytest-order uses `@pytest.mark.order()` marker

- #fetch:https://pytest-order.readthedocs.io/en/latest/usage.html
  - Order by index: `@pytest.mark.order(0)` or `@pytest.mark.order("first")`
  - Order numbers: 0, 1, 2... or "first", "second", "third"...
  - Negative numbers: -1, -2... or "last", "second_to_last"...
  - Scope: Global by default (cross-file ordering)

### Recommended Solution: pytest-order Plugin

**Architecture**: Convert session fixture to ordered test + cleanup fixture using pytest-order

**Step 1: Install pytest-order**

Add to [pyproject.toml](pyproject.toml) dev dependencies:

```toml
[dependency-groups]
dev = [
    # ... existing deps
    "pytest-order>=1.4.0",
]
```

**Step 2: Create Ordered Test**

Create [tests/e2e/test_00_bot_startup_sync.py](tests/e2e/test_00_bot_startup_sync.py):

```python
import asyncio
import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration
from shared.models.template import GameTemplate

pytestmark = [pytest.mark.e2e, pytest.mark.order(0)]


async def test_bot_startup_sync_creates_guilds(admin_db: AsyncSession) -> None:
    """
    Verify bot startup sync creates guilds automatically.

    This test MUST run first (pytest.mark.order(0)) before other E2E tests.
    Verifies automatic guild sync feature works on bot startup.
    """
    # Wait for bot startup sync to complete
    await asyncio.sleep(2)

    # Get Discord guild IDs from environment
    guild_a_id = os.getenv("DISCORD_GUILD_A_ID", "")
    guild_b_id = os.getenv("DISCORD_GUILD_B_ID", "")

    # Verify expected guilds were created by startup sync
    result = await admin_db.execute(
        select(GuildConfiguration).where(
            GuildConfiguration.guild_id.in_([guild_a_id, guild_b_id])
        )
    )
    guilds = result.scalars().all()
    assert len(guilds) == 2, f"Startup sync should create 2 guilds, found {len(guilds)}"

    # Verify channels and templates created for each guild
    for guild in guilds:
        channels_result = await admin_db.execute(
            select(ChannelConfiguration).where(
                ChannelConfiguration.guild_id == guild.guild_id
            )
        )
        channels = channels_result.scalars().all()
        assert len(channels) > 0, f"Guild {guild.guild_id} missing channels"

        templates_result = await admin_db.execute(
            select(GameTemplate).where(
                GameTemplate.guild_id == guild.guild_id
            )
        )
        templates = templates_result.scalars().all()
        assert len(templates) > 0, f"Guild {guild.guild_id} missing default template"
```

**Step 3: Add Cleanup Fixture**

Update [tests/e2e/conftest.py](tests/e2e/conftest.py) to replace async session fixture with cleanup:

```python
@pytest.fixture(scope="function", autouse=True)
async def cleanup_startup_sync_guilds(request, admin_db: AsyncSession) -> None:
    """
    Clean up startup-created guilds after first test runs.

    Executes after test_bot_startup_sync_creates_guilds to ensure
    hermetic test execution for remaining E2E tests.
    """
    yield  # Let test run first

    # Only cleanup after the bot startup sync test
    if request.node.name == "test_bot_startup_sync_creates_guilds":
        guild_a_id = os.getenv("DISCORD_GUILD_A_ID", "")
        guild_b_id = os.getenv("DISCORD_GUILD_B_ID", "")

        # Delete in correct order to respect foreign key constraints
        from sqlalchemy import delete
        await admin_db.execute(
            delete(GameTemplate).where(
                GameTemplate.guild_id.in_([guild_a_id, guild_b_id])
            )
        )
        await admin_db.execute(
            delete(ChannelConfiguration).where(
                ChannelConfiguration.guild_id.in_([guild_a_id, guild_b_id])
            )
        )
        await admin_db.execute(
            delete(GuildConfiguration).where(
                GuildConfiguration.guild_id.in_([guild_a_id, guild_b_id])
            )
        )
        await admin_db.commit()
```

**Step 4: Remove Session Fixture**

Delete the async `verify_and_cleanup_startup_sync` fixture from [tests/e2e/conftest.py](tests/e2e/conftest.py) lines 58-143.

### Key Benefits

**Solves Event Loop Issue**:

- Function-scoped test uses function-scoped event_loop (no scope mismatch)
- Function-scoped cleanup fixture reuses same event loop
- No need for session-scoped event_loop configuration

**Works with pytest-randomly**:

- pytest-order executes after pytest-randomly
- `@pytest.mark.order(0)` ensures test runs first despite randomization
- Other E2E tests remain randomized (good for finding dependencies)
- Module-level `pytestmark` applies order to entire file

**Proper Test Reporting**:

- Test appears in pytest output with PASS/FAIL status
- Counts toward test coverage metrics
- Failures properly reported with stack traces
- Cleanup happens in fixture, separate from verification logic

**Maintains Hermetic Tests**:

- First test verifies startup sync feature
- Cleanup removes startup-created data before other tests
- Other E2E tests create their own guilds via fixtures
- No duplicate key violations

### Implementation Dependencies

**Files to Modify**:

- [pyproject.toml](pyproject.toml) - Add pytest-order dependency
- [tests/e2e/conftest.py](tests/e2e/conftest.py) - Remove async session fixture, add cleanup fixture

**Files to Create**:

- [tests/e2e/test_00_bot_startup_sync.py](tests/e2e/test_00_bot_startup_sync.py) - New ordered test

**Files to Remove**:

- None (replace fixture with test)

### Alternative Approaches Considered

**Option 1: Session-scoped event_loop** (Rejected)

- Add session-scoped event_loop fixture to pytest-asyncio config
- Risk: Historical issues with wrong event loop problems in project
- Risk: Single event loop for entire test session increases coupling

**Option 2: asyncio.run() wrapper** (Considered)

- Use `asyncio.run()` in session fixture to create isolated event loop
- Works but doesn't provide test reporting
- Fixture assertions don't appear in pytest output

**Option 3: Disable randomization** (Rejected)

- Use `pytest -p no:randomly` to disable plugin
- Loses benefit of random test order finding dependencies
- Would need test*00*\* naming convention (alphabetically first)

**Option 4: Session fixture with global state** (Rejected)

- Session fixture sets global variable, test checks it
- Overcomplicated; splits verification from execution
- Still has event loop scope mismatch issue

### Success Criteria

**Solution Complete When**:

- pytest-order installed and available
- test_bot_startup_sync_creates_guilds runs first despite pytest-randomly
- Test verifies guilds/channels/templates created by bot startup
- Cleanup fixture removes data after first test
- All 71 E2E tests pass without ScopeMismatch errors
- Test appears in pytest output with proper PASS/FAIL reporting
- Random test order maintained for unmarked tests (finding dependencies)
