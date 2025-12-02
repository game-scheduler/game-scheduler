<!-- markdownlint-disable-file -->

# Research: Remove channel_name from Database

**Date**: 2025-12-01  
**Task**: Remove `channel_name` column from `channel_configurations` table and fetch channel names dynamically from Discord API with caching

## Overview

The `channel_name` field is currently stored in the `channel_configurations` table as a `NOT NULL` field. Similar to `guild_name`, this creates staleness issues when Discord channel names change. This research documents current implementation and provides guidance for removing the field and implementing dynamic fetch with caching.

## Research Executed

### File Analysis
- **shared/models/channel.py** (Line 46)
  - Defines `channel_name: Mapped[str] = mapped_column(String(100))`
  - Used in `__repr__` method (Line 62)

- **shared/schemas/channel.py**
  - `ChannelConfigCreateRequest` (Line 29): Includes `channel_name` as required input field
  - `ChannelConfigUpdateRequest` (Line 52): Includes `channel_name` as optional field
  - `ChannelConfigResponse` (Line 68): Includes `channel_name` in response (should be kept, fetched dynamically)

- **services/api/routes/channels.py**
  - `get_channel()` (Line 89): Returns `channel_name` from database model
  - `create_channel_config()` (Line 129): Accepts `channel_name` from request, stores in database
  - `update_channel_config()` (Line 176): Accepts `channel_name` in updates, stores in database

- **services/api/services/config.py**
  - `create_channel_config()` (Line 254): Accepts `channel_name` parameter, stores in database
  - `update_channel_config()` (Line 282): Updates `channel_name` if provided

- **services/bot/commands/config_channel.py**
  - `config_channel_command()` (Line 90): Gets channel name from Discord interaction
  - `_get_or_create_channel_config()` (Line 189): Accepts `channel_name` parameter, stores in database

- **alembic/versions/001_initial_schema.py** (Line 80)
  - Defines column: `sa.Column("channel_name", sa.String(100), nullable=False)`

### Code Search Results
- **channel_name usage across codebase**
  - tests/integration/test_notification_daemon.py (Lines 110-116): SQL INSERT with channel_name
  - tests/e2e/test_game_notification_api_flow.py (Lines 137-144): SQL INSERT with channel_name
  - frontend/src/types/index.ts (Lines 41, 61): TypeScript interface definitions
  - frontend/src/components/GameForm.tsx (Line 395): Displays channel_name
  - frontend/src/pages/ChannelConfig.tsx (Line 209): Displays channel_name
  - frontend/src/pages/GuildDashboard.tsx (Line 211): Displays channel_name
  - frontend/src/pages/BrowseGames.tsx (Line 127): Displays channel_name
  - frontend/src/pages/GameDetails.tsx (Line 244): Displays channel_name from game object

### External Research
- #fetch:https://discord.com/developers/docs/resources/channel
  - Discord API provides channel objects with `id`, `name`, `type`, `guild_id`, and other properties
  - Channel names can be fetched via GET `/channels/{channel.id}` endpoint
  - Requires bot token with appropriate permissions

### Project Conventions
- Standards referenced: Python coding conventions, TypeScript 5/ES2022 standards
- Instructions followed: Minimal code changes, preserve existing patterns
- Caching pattern: Redis caching with TTL already implemented for Discord API calls

## Key Discoveries

### Project Structure
The codebase follows a clear separation:
1. **Database Layer**: SQLAlchemy models define storage schema
2. **API Layer**: FastAPI routes handle HTTP requests, fetch Discord data dynamically
3. **Bot Layer**: Discord.py commands interact with Discord directly
4. **Frontend Layer**: React TypeScript components display data from API

### Implementation Patterns

**Current Discord API Caching Infrastructure** (Already Implemented):

```python
# services/api/auth/discord_client.py (Lines 319-368)
async def fetch_channel(self, channel_id: str) -> dict[str, Any]:
    """
    Fetch channel information using bot token with Redis caching.
    
    Returns:
        Channel object with id, name, type, guild_id, etc.
    """
    cache_key = f"discord:channel:{channel_id}"
    redis = await cache_client.get_redis_client()

    # Check cache first
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for channel: {channel_id}")
        return json.loads(cached)

    # Fetch from Discord API
    session = await self._get_session()
    url = f"{DISCORD_API_BASE}/channels/{channel_id}"

    async with session.get(
        url,
        headers={"Authorization": f"Bot {self.bot_token}"},
    ) as response:
        response_data = await response.json()

        if response.status != 200:
            error_msg = response_data.get("message", "Unknown error")
            if response.status == 404:
                # Cache negative result briefly
                await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
            raise DiscordAPIError(response.status, error_msg, dict(response.headers))

        # Cache successful result
        await redis.set(
            cache_key, json.dumps(response_data), ttl=ttl.CacheTTL.DISCORD_CHANNEL
        )
        logger.debug(f"Cached channel: {channel_id}")
        return response_data
```

**Cache TTL Configuration**:
```python
# shared/cache/ttl.py (Line 32)
DISCORD_CHANNEL: int = 300  # 5 minutes - Discord channel objects
```

### Complete Examples

**Pattern from guild_name removal** (Reference):
```python
# services/api/routes/guilds.py - Dynamic fetch pattern
@router.get("/{guild_id}", response_model=guild_schemas.GuildConfigResponse)
async def get_guild(
    guild_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
) -> guild_schemas.GuildConfigResponse:
    # Fetch guild config from database
    service = config_service.ConfigurationService(db)
    guild_config = await service.get_guild_by_id(guild_id)
    
    # Fetch guild name from Discord API with caching
    user_guilds = await oauth2.get_user_guilds(
        current_user.access_token, current_user.user.discord_id
    )
    user_guilds_dict = {g["id"]: g["name"] for g in user_guilds}
    guild_name = user_guilds_dict.get(guild_config.guild_id, "Unknown Guild")
    
    # Return response with dynamically fetched guild_name
    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_id=guild_config.guild_id,
        guild_name=guild_name,  # From Discord, not database
        # ... other fields
    )
```

**Proposed pattern for channels**:
```python
# services/api/routes/channels.py - Updated pattern
@router.get("/{channel_id}", response_model=channel_schemas.ChannelConfigResponse)
async def get_channel(
    channel_id: str,
    current_user: auth_schemas.CurrentUser = Depends(dependencies.auth.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    discord_client: DiscordClient = Depends(dependencies.get_discord_client),
) -> channel_schemas.ChannelConfigResponse:
    # Fetch channel config from database
    service = config_service.ConfigurationService(db)
    channel_config = await service.get_channel_by_id(channel_id)
    
    # Fetch channel name from Discord API with caching
    try:
        discord_channel = await discord_client.fetch_channel(channel_config.channel_id)
        channel_name = discord_channel.get("name", "Unknown Channel")
    except DiscordAPIError:
        logger.warning(f"Could not fetch channel name for {channel_config.channel_id}")
        channel_name = "Unknown Channel"
    
    # Return response with dynamically fetched channel_name
    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_name,  # From Discord, not database
        # ... other fields
    )
```

### API and Schema Documentation

**Discord Channel Object Structure**:
```json
{
  "id": "123456789012345678",
  "type": 0,
  "guild_id": "987654321098765432",
  "name": "general",
  "position": 0,
  "permission_overwrites": [],
  "nsfw": false,
  "parent_id": null
}
```

**Key Fields**:
- `id`: Channel snowflake ID (string)
- `name`: Channel name (string) - what we need
- `type`: Channel type (0 = text, 2 = voice, etc.)
- `guild_id`: Parent guild ID

### Configuration Examples

**Alembic Migration Template** (drop column):
```python
"""Remove channel_name from channel_configurations

Revision ID: 016_remove_channel_name
"""

from alembic import op
import sqlalchemy as sa

revision = '016_remove_channel_name'
down_revision = '015_remove_min_players_field'

def upgrade() -> None:
    """Remove channel_name column."""
    op.drop_column('channel_configurations', 'channel_name')

def downgrade() -> None:
    """Restore channel_name column."""
    op.add_column(
        'channel_configurations',
        sa.Column('channel_name', sa.String(100), nullable=False, server_default='Unknown Channel')
    )
```

### Technical Requirements

**Database Changes**:
1. Create Alembic migration to drop `channel_name` column
2. Remove field from SQLAlchemy model
3. Remove from `__repr__` method

**API Changes**:
1. Update `services/api/routes/channels.py`:
   - Inject `discord_client` dependency in all endpoints
   - Fetch channel names using `discord_client.fetch_channel()`
   - Handle errors gracefully (default to "Unknown Channel")

2. Update `services/api/services/config.py`:
   - Remove `channel_name` parameter from `create_channel_config()`
   - Remove `channel_name` from `update_channel_config()`

3. Update `shared/schemas/channel.py`:
   - Remove `channel_name` from `ChannelConfigCreateRequest`
   - Remove `channel_name` from `ChannelConfigUpdateRequest`
   - **KEEP** `channel_name` in `ChannelConfigResponse` (populated at runtime)

**Bot Changes**:
1. Update `services/bot/commands/config_channel.py`:
   - Remove `channel_name` parameter from `_get_or_create_channel_config()`
   - Remove `channel_name` from `ChannelConfiguration()` constructor

**Test Changes**:
1. Update `tests/integration/test_notification_daemon.py`:
   - Remove `channel_name` from SQL INSERT
2. Update `tests/e2e/test_game_notification_api_flow.py`:
   - Remove `channel_name` from SQL INSERT

**Frontend Changes**:
- No changes needed - frontend already consumes `channel_name` from API responses
- TypeScript interfaces remain the same (API still provides the field)

## Recommended Approach

Follow the same pattern as `guild_name` removal:

1. **Phase 1: Database Migration**
   - Create migration to drop `channel_name` column
   - Test migration on development database

2. **Phase 2: Update Models**
   - Remove from SQLAlchemy model
   - Remove from `__repr__` method
   - Keep in Pydantic response schemas

3. **Phase 3: Update API Routes**
   - Inject `discord_client` dependency
   - Fetch channel names dynamically using existing `fetch_channel()` method
   - Handle errors gracefully with fallback to "Unknown Channel"

4. **Phase 4: Update Bot Commands**
   - Remove `channel_name` parameter from helper functions
   - Remove from database operations

5. **Phase 5: Update Tests**
   - Remove `channel_name` from test SQL INSERTs
   - Add mocking for `discord_client.fetch_channel()` if needed

6. **Phase 6: Validation**
   - Run all tests
   - Manual testing to verify channel names display correctly
   - Verify caching is working (check Redis)

## Implementation Guidance

**Objectives**:
- Eliminate stale channel name data from database
- Leverage existing Redis caching infrastructure for Discord API calls
- Maintain backward compatibility in API responses
- Ensure all tests pass

**Key Tasks**:
1. Create and test Alembic migration
2. Update SQLAlchemy model and schemas
3. Modify API routes to fetch channel names dynamically
4. Update bot commands to remove channel_name storage
5. Fix test fixtures
6. Comprehensive testing

**Dependencies**:
- Existing `discord_client.fetch_channel()` method (already implemented)
- Redis caching with `CacheTTL.DISCORD_CHANNEL = 300` seconds
- Bot token with channel read permissions

**Success Criteria**:
- Database no longer stores channel_name
- API responses still include channel_name (fetched from Discord)
- Frontend displays channel names correctly
- All tests pass
- Channel name changes in Discord reflect within 5 minutes (cache TTL)
