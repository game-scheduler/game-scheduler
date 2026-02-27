<!-- markdownlint-disable-file -->

# Task Research Notes: Remove Discord Webhooks and Use Gateway Events

## Research Executed

### Discord Intent Changes Discovery

- **Key Finding**: Discord changed privileged intents rules - `GUILD_CREATE` and `GUILD_REMOVE` gateway events are now **non-privileged**
- **Impact**: No longer need HTTP webhooks with Ed25519 signature validation for guild join/remove events
- **Source**: User discovered this after implementing webhook solution

### File Analysis

- [services/api/routes/webhooks.py](../../services/api/routes/webhooks.py)
  - HTTP webhook endpoint handling APPLICATION_AUTHORIZED events
  - Ed25519 signature validation via dependency injection
  - Publishes GUILD_SYNC_REQUESTED to RabbitMQ

- [services/api/dependencies/discord_webhook.py](../../services/api/dependencies/discord_webhook.py)
  - Ed25519 signature validation using PyNaCl library
  - Validates X-Signature-Ed25519 and X-Signature-Timestamp headers
  - Requires DISCORD_PUBLIC_KEY environment variable

- [services/bot/bot.py](../../services/bot/bot.py)
  - `on_guild_join()` currently only logs events (lines 193-207)
  - `on_guild_remove()` currently only logs events (lines 209-222)
  - `setup_hook()` already syncs all guilds on startup (lines 107-124)
  - Uses `discord.Intents.none()` - no privileged intents needed

- [services/bot/events/handlers.py](../../services/bot/events/handlers.py)
  - `_handle_guild_sync_requested()` consumes RabbitMQ event (lines 1080-1118)
  - Calls `sync_all_bot_guilds()` when event received

- [services/api/routes/guilds.py](../../services/api/routes/guilds.py)
  - `/sync` endpoint calls `sync_user_guilds()` directly (lines 301-329)
  - TODO comment mentions migrating to RabbitMQ pattern (never implemented)
  - Returns sync counts to user (needs synchronous response)

- [services/api/services/guild_service.py](../../services/api/services/guild_service.py)
  - `sync_user_guilds()`: Uses OAuth token, syncs guilds where user has MANAGE_GUILD permission AND bot is present
  - Also refreshes channels for existing guilds

- [services/bot/guild_sync.py](../../services/bot/guild_sync.py)
  - `sync_all_bot_guilds()`: Uses bot token, syncs ALL guilds bot is in
  - Only creates new guilds, doesn't update existing

### Code Search Results

- RabbitMQ event usage:
  - `EventType.GUILD_SYNC_REQUESTED` defined in [shared/messaging/events.py](../../shared/messaging/events.py)
  - Used only for webhook→bot communication
  - Not used by GUI sync button (that calls service directly)

- Rate limiting infrastructure:
  - slowapi library already configured in [services/api/app.py](../../services/api/app.py)
  - Used for public image endpoints in [services/api/routes/public.py](../../services/api/routes/public.py)
  - In-memory storage, per-IP limiting

- Channel sync on-demand:
  - `/api/v1/guilds/{guild_id}/channels?refresh=true` parameter
  - Calls `refresh_guild_channels()` when needed
  - No need for guild sync to refresh channels

### External Research

- Discord Gateway Events: `on_guild_join` and `on_guild_remove` are non-privileged
- No special intents required for these events
- Bot receives them automatically when joining/leaving guilds

### Project Conventions

- Event-driven architecture using RabbitMQ for cross-service communication
- Rate limiting with slowapi for public/sensitive endpoints
- TDD methodology for new features
- Synchronous responses for user-initiated actions requiring feedback

## Key Discoveries

### Architectural Insights

**Current Webhook Flow (Unnecessarily Complex)**:

```
Discord Webhook (HTTP) → API validates Ed25519 signature →
Publish GUILD_SYNC_REQUESTED to RabbitMQ →
Bot consumes event → Calls sync_all_bot_guilds()
```

**Why This Was Built**:

- Webhooks were believed necessary for guild join/remove events
- Required Ed25519 cryptographic signature validation
- Needed public HTTPS endpoint configuration in Discord Developer Portal
- Used RabbitMQ for cross-service communication (API→Bot)

**What Changed**:

- Discord made guild join/remove gateway events non-privileged
- Bot already receives `on_guild_join` and `on_guild_remove` events via WebSocket gateway
- No HTTP endpoint needed
- No signature validation needed
- Bot can handle events directly (has database access and bot token)

### Guild Sync Functions Comparison

**Two Different Functions Exist**:

1. **`sync_all_bot_guilds()`** (in bot service):
   - Uses bot token
   - Syncs ALL guilds bot is in (no permission checks)
   - Only creates new guilds (doesn't update existing)
   - Returns: `{"new_guilds": int, "new_channels": int}`

2. **`sync_user_guilds()`** (in API service):
   - Uses user's OAuth token
   - Syncs guilds where: user has MANAGE_GUILD AND bot is present
   - Also refreshes channels for existing guilds
   - Returns: `{"new_guilds": int, "new_channels": int, "updated_channels": int}`

**Discovery**: Channel refresh is ALREADY on-demand via `/channels?refresh=true` query parameter, so `sync_user_guilds()` channel refresh is redundant.

### RabbitMQ Usage Analysis

**Current Event Usage**:

- Webhook endpoint publishes `GUILD_SYNC_REQUESTED`
- Bot handler consumes and processes

**GUI Sync Button**:

- Does NOT use RabbitMQ (despite TODO comment)
- Calls `sync_user_guilds()` directly
- Returns counts synchronously to user

**Why RabbitMQ Isn't Needed**:

- Original purpose: API service (webhook) needed to tell Bot service to do something
- With gateway events: Bot service receives event directly, no cross-service communication needed
- GUI sync: User needs immediate response with counts (fire-and-forget doesn't work)

### Rate Limiting Discovery

**Infrastructure Exists**:

- slowapi library (v0.1.9) already configured
- Used for public endpoints
- In-memory storage (resets on restart, but acceptable)
- Per-IP limiting with `get_remote_address` key function

**Easy to Add**:

```python
from services.api.app import limiter

@router.post("/sync")
@limiter.limit("1/minute")
async def sync_guilds(request: Request, ...):
```

## Recommended Approach

### Unified Architecture

**Single Sync Function**: Use `sync_all_bot_guilds()` everywhere

- Bot has everything it needs (database access, bot token)
- API can import and use it with bot token from config
- Simpler than maintaining two different sync functions

**Event-Driven for Automation**:

- `on_guild_join` → directly call `sync_all_bot_guilds()`
- `on_guild_remove` → just log (keep guilds in database for historical data)
- Startup → already calls `sync_all_bot_guilds()` directly

**Synchronous for User Actions**:

- GUI sync button → directly call `sync_all_bot_guilds()` → return counts
- Channel refresh → already on-demand with `?refresh=true`

**No RabbitMQ Events Needed**:

- Remove `GUILD_SYNC_REQUESTED` event entirely
- No cross-service communication required
- Simpler architecture, fewer moving parts

### Changes Required

#### 1. Remove Complete Webhook Infrastructure

**Delete Files**:

- `services/api/routes/webhooks.py` - Webhook HTTP endpoint
- `services/api/dependencies/discord_webhook.py` - Ed25519 signature validation
- `tests/services/api/routes/test_webhooks.py` - Webhook endpoint tests
- `tests/services/api/dependencies/test_discord_webhook.py` - Signature validation tests
- `tests/integration/test_webhooks.py` - Integration tests
- `docs/deployment/discord-webhook-setup.md` - Setup documentation

**Remove Configuration**:

- Remove `DISCORD_PUBLIC_KEY` from all env files: `config/env.dev`, `config/env.int`, `config/env.e2e`, `config/env.staging`, `config/env.prod`
- Remove from `config.template/env.template`
- Remove `discord_public_key` field from `services/api/config.py`

**Remove Dependencies**:

- Remove `pynacl~=1.5.0` from `pyproject.toml` (only used for webhook signature validation)

**Update API App**:

- Remove `webhooks` import and router registration from `services/api/app.py`
- Remove from `services/api/dependencies/__init__.py` exports

#### 2. Remove RabbitMQ Guild Sync Event

**From `shared/messaging/events.py`**:

- Remove `GUILD_SYNC_REQUESTED = "guild.sync_requested"`

**From `services/bot/events/handlers.py`**:

- Remove `_handle_guild_sync_requested()` method (lines 1080-1118)
- Remove `GUILD_SYNC_REQUESTED` from `_handlers` dict initialization
- Remove from event subscriptions in `start_consuming()`

**From Tests**:

- Remove `test_handle_guild_sync_requested_*` tests from `tests/services/bot/events/test_handlers.py`

#### 3. Update Bot on_guild_join Event

**File**: `services/bot/bot.py` (lines 193-207)

**Change From** (just logging):

```python
async def on_guild_join(self, guild: discord.Guild) -> None:
    with tracer.start_as_current_span(...):
        logger.info("Bot added to guild: %s (ID: %s)", guild.name, guild.id)
```

**Change To** (sync immediately):

```python
async def on_guild_join(self, guild: discord.Guild) -> None:
    with tracer.start_as_current_span(
        "discord.on_guild_join",
        attributes={
            "discord.guild_id": str(guild.id),
            "discord.guild_name": guild.name,
        },
    ):
        logger.info("Bot added to guild: %s (ID: %s)", guild.name, guild.id)

        try:
            discord_client = get_discord_client()
            async with get_db_session() as db:
                sync_results = await sync_all_bot_guilds(
                    discord_client, db, self.config.discord_bot_token
                )
                await db.commit()
                logger.info(
                    "Synced after guild join: %d new guilds, %d new channels",
                    sync_results["new_guilds"],
                    sync_results["new_channels"],
                )
        except Exception as e:
            logger.exception("Failed to sync after guild join: %s", e)
```

#### 4. Simplify GUI Sync Endpoint with Rate Limiting

**File**: `services/api/routes/guilds.py` (lines 301-329)

**Add Imports**:

```python
from services.api.app import limiter
from services.bot.guild_sync import sync_all_bot_guilds
from shared.discord.client import get_discord_client
```

**Change From**:

```python
@router.post("/sync", response_model=guild_schemas.GuildSyncResponse)
async def sync_guilds(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildSyncResponse:
    """Sync user's Discord guilds..."""
    result = await guild_service.sync_user_guilds(db, access_token, user_discord_id)
    return guild_schemas.GuildSyncResponse(...)
```

**Change To**:

```python
@router.post("/sync", response_model=guild_schemas.GuildSyncResponse)
@limiter.limit("1/minute")
async def sync_guilds(
    request: Request,  # Required for rate limiter
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
    config: Annotated[APIConfig, Depends(get_api_config)],
) -> guild_schemas.GuildSyncResponse:
    """
    Sync bot's Discord guilds with database.

    Creates new guilds with channels and default templates.
    Rate limited to 1 request per minute per IP address.
    """
    discord_client = get_discord_client()
    result = await sync_all_bot_guilds(discord_client, db, config.discord_bot_token)
    await db.commit()

    return guild_schemas.GuildSyncResponse(
        new_guilds=result["new_guilds"],
        new_channels=result["new_channels"],
        updated_channels=0,  # sync_all_bot_guilds doesn't update existing
    )
```

#### 5. Remove Obsolete sync_user_guilds Function

**File**: `services/api/services/guild_service.py`

**Remove**:

- `sync_user_guilds()` function
- `_compute_candidate_guild_ids()` helper (only used by sync_user_guilds)
- `_create_guild_with_channels_and_template()` helper - check if used elsewhere!
- `_sync_guild_channels()` helper - check if used by `refresh_guild_channels()`

**Verify Before Removing**:

- Check if `refresh_guild_channels()` uses any of these helpers
- Keep only what's needed for on-demand channel refresh

#### 6. Update Tests

**Bot Tests** (`tests/services/bot/test_bot.py`):

- Update `test_on_guild_join_event` to mock and verify `sync_all_bot_guilds()` is called
- Keep `test_on_guild_remove_event` as-is (just logging)

**API Tests**:

- Update tests for `/api/v1/guilds/sync` endpoint
- Test rate limiting (429 response on second request within minute)
- Verify correct response format

**Remove Event Handler Tests**:

- Remove all `test_handle_guild_sync_requested_*` tests

## Implementation Guidance

- **Objectives**:
  - Simplify architecture by removing unnecessary webhook infrastructure
  - Enable automatic guild sync using Discord gateway events
  - Unify guild sync to single function
  - Add rate limiting to prevent sync button abuse

- **Key Tasks**:
  1. Delete webhook files and remove from router registration
  2. Remove DISCORD_PUBLIC_KEY configuration and PyNaCl dependency
  3. Remove GUILD_SYNC_REQUESTED event and handler
  4. Update on_guild_join to call sync directly
  5. Simplify GUI sync endpoint with rate limiting
  6. Remove obsolete sync_user_guilds function
  7. Update tests

- **Dependencies**:
  - Must remove webhook router before running API
  - Must update on_guild_join before deploying bot
  - Rate limiting uses existing slowapi infrastructure

- **Success Criteria**:
  - All webhook code removed
  - Bot automatically syncs when joining guilds
  - GUI sync button works and is rate-limited
  - All tests pass
  - No DISCORD_PUBLIC_KEY configuration needed
  - Simpler architecture with fewer moving parts
