<!-- markdownlint-disable-file -->

# Research: Remove guild_name from Database and Implement Fetch/Cache

**Date**: 2025-11-30  
**Task**: Remove `guild_name` column from `guild_configurations` table and fetch guild names dynamically from Discord API with caching

## Overview

Currently, `guild_name` is stored in the `guild_configurations` table as a `NOT NULL` field. This creates staleness issues when Discord guild names change, and the recent defect investigation revealed that maintaining this field adds unnecessary complexity. This research documents the current implementation and provides guidance for removing the field and implementing dynamic fetch with caching.

## Current Implementation

### Database Schema

**File**: `alembic/versions/001_initial_schema.py` (Lines 54-67)
```python
op.create_table(
    "guild_configurations",
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("guild_id", sa.String(20), nullable=False, unique=True),
    sa.Column("guild_name", sa.String(100), nullable=False),  # ← TO BE REMOVED
    sa.Column("default_max_players", sa.Integer(), nullable=True),
    sa.Column("default_reminder_minutes", sa.JSON(), nullable=False, server_default="[60, 15]"),
    # ... other columns
)
```

### SQLAlchemy Model

**File**: `shared/models/guild.py` (Lines 45)
```python
class GuildConfiguration(Base):
    __tablename__ = "guild_configurations"
    
    guild_name: Mapped[str] = mapped_column(String(100), nullable=False)  # ← TO BE REMOVED
```

### Pydantic Schemas

**File**: `shared/schemas/guild.py`

**GuildConfigResponse** (Line 59) - KEEP (fetched at runtime):
```python
guild_name: str = Field(..., description="Discord guild name")
```

**GuildConfigCreateRequest** - Does NOT include `guild_name` (correct, no change needed)

**GuildConfigUpdateRequest** - Does NOT include `guild_name` (correct, no change needed)

### API Routes - Current Fetch Pattern

**File**: `services/api/routes/guilds.py`

**list_guilds** (Lines 39-89):
- Currently fetches guild names from `oauth2.get_user_guilds()` (user's OAuth token)
- Stores in `user_guilds_dict`
- Passes `guild_name` to `GuildConfigResponse` constructor (Line 69, 75)

**get_guild** (Lines 92-146):
- Fetches guild names from `oauth2.get_user_guilds()` 
- Passes `guild_name` to `GuildConfigResponse` (Line 136, 141)

**create_guild_config** (Lines 149-197):
- Fetches guild names from `oauth2.get_user_guilds()`
- Passes `guild_name` to `GuildConfigResponse` (Line 186, 191)

**update_guild_config** (Lines 200-241):
- Fetches guild names from `oauth2.get_user_guilds()`
- Passes `guild_name` to `GuildConfigResponse` (Line 229, 234)

**Pattern**: All endpoints fetch guild names at runtime from Discord, never from database. Database field is write-only.

### Bot Commands

**File**: `services/bot/commands/config_guild.py` (Lines 64-75)
```python
# Get guild name - if not available in interaction, fetch via HTTP API
guild_name = interaction.guild.name
if not guild_name:
    try:
        guild = await interaction.client.fetch_guild(interaction.guild.id)
        guild_name = guild.name
        logger.info(f"Fetched guild name via HTTP API: {guild_name}")
    except Exception as e:
        logger.warning(f"Failed to fetch guild name: {e}")
        guild_name = "Unknown Guild"
```

**_get_or_create_guild_config** (Lines 157-195):
- Accepts `guild_name` parameter
- Passes to `GuildConfiguration()` constructor
- After removal, this parameter will be eliminated

### Frontend TypeScript

**File**: `frontend/src/types/index.ts` (Line 27)
```typescript
export interface Guild {
  guild_name: string;  // ← KEEP (API response field)
}
```

**Usage**:
- `frontend/src/pages/GuildListPage.tsx` (Lines 112, 115) - Displays `guild.guild_name`
- `frontend/src/pages/GuildDashboard.tsx` (Line 126) - Displays `guild.guild_name`

## Existing Caching Infrastructure

### Discord API Client with Caching

**File**: `services/api/auth/discord_client.py` (Lines 370-420)

```python
async def fetch_guild(self, guild_id: str) -> dict[str, Any]:
    """
    Fetch guild information using bot token with Redis caching.
    """
    cache_key = f"discord:guild:{guild_id}"
    redis = await cache_client.get_redis_client()

    # Check cache first
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for guild: {guild_id}")
        return json.loads(cached)

    # Fetch from Discord API
    session = await self._get_session()
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}"

    # ... fetch logic ...
    
    # Cache successful result
    await redis.set(
        cache_key, json.dumps(response_data), ttl=ttl.CacheTTL.DISCORD_GUILD
    )
    logger.debug(f"Cached guild: {guild_id}")
    return response_data
```

**Key Points**:
- Uses bot token for authentication
- Caches in Redis with key `discord:guild:{guild_id}`
- TTL: `CacheTTL.DISCORD_GUILD` = 600 seconds (10 minutes)
- Returns full guild object with `id`, `name`, `icon`, `features`, etc.

### Cache TTL Configuration

**File**: `shared/cache/ttl.py` (Lines 33)
```python
class CacheTTL:
    DISCORD_GUILD: int = 600  # 10 minutes - Discord guild objects
```

**Recommendation**: 10 minutes is reasonable for guild names. Could be extended to 1 hour (3600) if desired.

### OAuth2 User Guilds Caching

**File**: `services/api/auth/oauth2.py`

The `get_user_guilds()` function already implements caching with user OAuth tokens:
- Cache key: `discord:user:{user_id}:guilds`
- TTL: `CacheTTL.USER_GUILDS` = 300 seconds (5 minutes)

## Test Coverage

### Tests Using guild_name in SQL INSERT

**File**: `tests/integration/test_notification_daemon.py` (Lines 95-101)
```python
"(id, guild_id, guild_name, created_at, updated_at) "
"VALUES (:id, :guild_id, :guild_name, :created_at, :updated_at)"
```
**Action**: Remove `guild_name` from INSERT statement

**File**: `tests/e2e/test_game_notification_api_flow.py` (Lines 118-126)
```python
"(id, guild_id, guild_name, created_at, updated_at, "
"VALUES (:id, :guild_id, :guild_name, :created_at, :updated_at, "
```
**Action**: Remove `guild_name` from INSERT statement

### Tests Asserting guild_name in Responses

**File**: `tests/services/api/routes/test_guilds.py`
- Line 109: `assert result.guilds[0].guild_name == "Test Guild"`
- Line 156: `assert result.guild_name == "Test Guild"`

**Action**: Keep these assertions - they validate API response includes guild_name fetched from Discord

## Migration Strategy

### Database Migration

**New Migration File**: `alembic/versions/016_remove_guild_name_column.py`

```python
def upgrade() -> None:
    """Remove guild_name column from guild_configurations table."""
    op.drop_column("guild_configurations", "guild_name")

def downgrade() -> None:
    """Restore guild_name column."""
    op.add_column(
        "guild_configurations",
        sa.Column("guild_name", sa.String(100), nullable=True)
    )
```

**Note**: Downgrade creates nullable column since we can't restore data.

## Implementation Plan Components

### Phase 1: Remove Database Storage

1. **Create Alembic Migration** (016_remove_guild_name_column.py)
   - Drop `guild_name` column from `guild_configurations` table
   
2. **Update SQLAlchemy Model** (shared/models/guild.py)
   - Remove `guild_name: Mapped[str]` field
   
3. **Update Bot Commands** (services/bot/commands/config_guild.py)
   - Remove `guild_name` parameter from `_get_or_create_guild_config()`
   - Remove guild name fetch logic (lines 64-75)
   - Remove `guild_name` from `GuildConfiguration()` constructor call

4. **Update API Service** (services/api/services/config.py)
   - No changes needed - `create_guild_config()` uses `**settings`, doesn't explicitly pass guild_name

5. **Update Test Fixtures**
   - Remove `guild_name` from SQL INSERT statements in integration/e2e tests

### Phase 2: Verify API Routes Already Fetch Dynamically

**Current State**: All API routes already fetch guild names from Discord at runtime
- `list_guilds()` - Uses `oauth2.get_user_guilds()` with caching
- `get_guild()` - Uses `oauth2.get_user_guilds()` with caching  
- `create_guild_config()` - Uses `oauth2.get_user_guilds()` with caching
- `update_guild_config()` - Uses `oauth2.get_user_guilds()` with caching

**Action**: No changes needed - verify existing caching is working

### Phase 3: Testing and Validation

1. Run unit tests - ensure no guild_name assertions fail inappropriately
2. Run integration tests - validate SQL INSERT statements work without guild_name
3. Run e2e tests - validate full flow works
4. Manual testing - verify guild names display correctly in frontend

## Success Criteria

- [ ] Database migration removes `guild_name` column successfully
- [ ] SQLAlchemy model updated - no `guild_name` field
- [ ] Bot `/config-guild` command works without storing guild_name
- [ ] API endpoints return guild_name in responses (fetched from Discord)
- [ ] Frontend displays guild names correctly
- [ ] All tests pass
- [ ] Guild name changes in Discord are reflected immediately (no staleness)

## Related Files Summary

### Files to Modify

1. **alembic/versions/** - Create 016_remove_guild_name_column.py
2. **shared/models/guild.py** - Remove guild_name field (line 45)
3. **services/bot/commands/config_guild.py** - Remove guild_name logic (lines 64-75, 82-83, 169-170)
4. **tests/integration/test_notification_daemon.py** - Remove guild_name from INSERT (lines 95-96, 101)
5. **tests/e2e/test_game_notification_api_flow.py** - Remove guild_name from INSERT (lines 118, 120, 126)

### Files to Keep Unchanged

1. **shared/schemas/guild.py** - Keep guild_name in GuildConfigResponse (fetched at runtime)
2. **services/api/routes/guilds.py** - Already fetches dynamically, no changes needed
3. **services/api/auth/discord_client.py** - Caching already implemented
4. **frontend/src/types/index.ts** - Keep guild_name in Guild interface
5. **frontend/src/pages/** - Keep guild_name display logic
6. **tests/services/api/routes/test_guilds.py** - Keep guild_name assertions (validate API response)

## Historical Context

From `.copilot-tracking/changes/20251114-discord-game-scheduling-system-changes.md` (Lines 5689-5747):

**Previous Attempt**: A migration `c643f8bf378c_make_guild_name_nullable.py` was created to drop guild_name, but was later reverted.

**Decision at that time**: "Remove `guild_name` from database storage entirely. Guild names can change in Discord and storing them creates stale data issues."

**This research validates that decision and provides a complete implementation path.**

## References

- Discord API Documentation: https://discord.com/developers/docs/resources/guild
- Existing caching infrastructure: #file:shared/cache/ttl.py
- Discord client with caching: #file:services/api/auth/discord_client.py
- OAuth2 with guild fetching: #file:services/api/auth/oauth2.py
