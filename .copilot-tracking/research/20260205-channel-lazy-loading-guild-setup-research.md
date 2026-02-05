<!-- markdownlint-disable-file -->
# Task Research Notes: Channel Sync via Guild Sync Button

## Implementation Decision (2026-02-05)

**FINAL APPROACH:** After attempting lazy loading implementation, reverted to simpler sync-based approach.

### Why Lazy Loading Was Abandoned

**Original Plan:** Fetch channels from Discord on-demand during template/game creation, with lazy database writes.

**Why This Didn't Work:**
1. **Unnecessary complexity** - Lazy loading added conditional logic throughout codebase
2. **Existing sync pattern works** - Guild sync already creates channels for new guilds
3. **No caching needed** - Template/game creation is infrequent (manual operation)
4. **Simple fix available** - Just extend sync to refresh channels for existing guilds

### Final Architecture: Extend Guild Sync to Refresh Channels

**Pattern: Manual Sync Button Updates Everything**

When user clicks "Sync guilds and channels" button:
1. **New guilds**: Create guild + all text channels + default template (existing behavior)
2. **Existing guilds**: Fetch channels from Discord, sync to database (new behavior)
3. **Channel sync**: Add new channels, mark missing channels as inactive (preserves foreign keys)

**Key Benefits:**
- ✅ No frontend changes needed (uses existing sync button with updated label)
- ✅ No new API endpoints needed
- ✅ No caching complexity needed
- ✅ Manual operation - Discord rate limits not a concern
- ✅ Preserves foreign key references (inactive channels remain in DB)
- ✅ Simple get-or-create pattern for channel sync

## Research Executed

### Problem Discovery
- User reported: Channels added to Discord guild don't appear in template creation dropdown
- Root cause: Channels only synced to database when guild is first added
- Existing guilds never refresh their channel list

### File Analysis
- [services/api/routes/guilds.py](services/api/routes/guilds.py#L200-L249)
  - `list_guild_channels()` queries `ChannelConfiguration` table only
  - Returns channels previously stored in database
  - No sync with Discord on read
  - Returns all channels without filtering by `is_active`
- [services/api/routes/guilds.py](services/api/routes/guilds.py#L290-L310)
  - `sync_guilds()` endpoint calls `guild_service.sync_user_guilds()`
  - Returns `GuildSyncResponse` with counts
- [services/api/services/guild_service.py](services/api/services/guild_service.py#L153-L209)
  - `_create_guild_with_channels_and_template()` creates channels during guild creation
  - Fetches channels via `client.get_guild_channels(guild_discord_id)`
  - Creates `ChannelConfiguration` for each text channel with `is_active=True`
- [services/api/services/guild_service.py](services/api/services/guild_service.py#L219-L259)
  - `sync_user_guilds()` only processes NEW guilds
  - Existing guilds are completely ignored by sync operation
  - Returns dict with `new_guilds` and `new_channels` counts
- [shared/discord/client.py](shared/discord/client.py#L391-L430)
  - `get_guild_channels()` fetches all channels from Discord API
  - Returns list of channel dictionaries with id, name, type
  - No caching currently implemented
- [shared/schemas/guild.py](shared/schemas/guild.py#L87-L90)
  - `GuildSyncResponse` has `new_guilds` and `new_channels` fields
  - `new_channels` only counts channels for new guilds

### Code Search Results
- `ChannelConfiguration.is_active` field
  - Boolean flag for enabling/disabling channels in UI
  - Not filtered in `list_guild_channels()` endpoint
  - Used in channel config update endpoint
  - Default value is `True` when channels created
- Foreign key relationships
  - `GameSession.channel_id` → `ChannelConfiguration.id`
  - `GameTemplate.channel_id` → `ChannelConfiguration.id`
  - Channels cannot be deleted if referenced by games/templates
  - Marking inactive preserves referential integrity

### External Research
- Discord API: `GET /guilds/{guild_id}/channels` returns current channel list
- Discord rate limits: Bot tokens allow 50 requests per second
- Manual sync operation: Rate limits not a concern
- Channel type 0 = text channel (relevant for filtering)

### Project Conventions
- Guild names: Fetched from Discord dynamically (cached 10 min)
- Channel names: Fetched from Discord dynamically (cached 5 min)
- Channel existence: Stored in database for foreign key relationships
- Pattern: Sync operations are manual, user-triggered via button

## Key Discoveries

### Current Guild Sync Behavior

**What Happens Now:**
```python
# services/api/services/guild_service.py
async def sync_user_guilds(db, access_token, user_id):
    # Get candidate guilds (user has MANAGE_GUILD + bot is member)
    candidate_guild_ids = await _compute_candidate_guild_ids(...)

    # Check which are already in database
    existing_guild_ids = await _get_existing_guild_ids(db)
    new_guild_ids = candidate_guild_ids - existing_guild_ids

    # ONLY process new guilds
    for guild_discord_id in new_guild_ids:
        guilds_created, channels_created = await _create_guild_with_channels_and_template(...)
        total_guilds += guilds_created
        total_channels += channels_created

    # Existing guilds: NOTHING HAPPENS
    return {"new_guilds": total_guilds, "new_channels": total_channels}
```

**Problem:** Existing guilds never get channel updates.

### Why Channels Must Stay in Database

**Critical Reasons:**
1. **Foreign Key References** - GameSession and GameTemplate require ChannelConfiguration.id (UUID)
2. **is_active Flag** - Application state for hiding deleted Discord channels from dropdowns
3. **Guild Association** - Multi-tenant isolation via guild_id relationship

**Not Needed For:**
- ❌ Channel metadata (name, type) - fetched from Discord dynamically
- ❌ Caching - names already cached separately via `fetch_channel_name_safe()`

### Sync Response Message

**Current Frontend Display:**
```typescript
// After sync completes, shows:
`Added ${result.new_guilds} new servers and ${result.new_channels} channels`
```

**Proposed New Display:**
```typescript
// Should show something like:
`Added ${result.new_guilds} new servers, updated ${result.updated_channels} channels for existing servers`
```

### Channel Dropdown Filtering

**Current Behavior:**
- Template form fetches: `GET /api/v1/guilds/{guild_id}/channels`
- Returns ALL channels in database (no `is_active` filtering)
- Frontend doesn't filter by `is_active`
- Channels with `is_active=False` should be hidden from dropdowns
- Existing games/templates with inactive channels should still display them (read-only)

**Problem:** Deleted Discord channels still appear in dropdowns.

**Solution:** Filter channels by `is_active=True` when returning from `list_guild_channels()` endpoint.

## Recommended Approach

### Architecture: Sync Channels for All Guilds

**Core Principle:** Extend existing sync operation to refresh channels for all guilds (new and existing).

### Implementation Steps

**Step 1: Create Channel Sync Helper Function**

```python
# services/api/services/guild_service.py

async def _sync_guild_channels(
    db: AsyncSession,
    client: DiscordAPIClient,
    guild_config_id: str,
    guild_discord_id: str,
) -> int:
    """
    Sync channels from Discord to database for a guild.

    - Adds new text channels with is_active=True (get-or-create pattern)
    - Marks channels missing from Discord as is_active=False
    - Returns count of channels added/updated

    Args:
        db: Database session
        client: Discord API client
        guild_config_id: Guild UUID in database
        guild_discord_id: Guild snowflake ID in Discord

    Returns:
        Number of channels added or updated
    """
    # Fetch current channels from Discord
    discord_channels = await client.get_guild_channels(guild_discord_id)
    discord_text_channel_ids = {
        ch["id"] for ch in discord_channels if ch.get("type") == 0
    }

    # Get existing channels from database
    result = await db.execute(
        select(ChannelConfiguration).where(
            ChannelConfiguration.guild_id == guild_config_id
        )
    )
    existing_channels = {ch.channel_id: ch for ch in result.scalars().all()}

    channels_updated = 0

    # Add new channels or reactivate existing ones
    for channel_discord_id in discord_text_channel_ids:
        if channel_discord_id in existing_channels:
            # Channel exists, ensure it's active
            channel = existing_channels[channel_discord_id]
            if not channel.is_active:
                channel.is_active = True
                channels_updated += 1
        else:
            # New channel, create it
            await channel_service.create_channel_config(
                db, guild_config_id, channel_discord_id, is_active=True
            )
            channels_updated += 1

    # Mark missing channels as inactive
    for channel_discord_id, channel in existing_channels.items():
        if channel_discord_id not in discord_text_channel_ids:
            if channel.is_active:
                channel.is_active = False
                channels_updated += 1

    return channels_updated
```

**Step 2: Update sync_user_guilds to Process All Guilds**

```python
# services/api/services/guild_service.py

async def sync_user_guilds(db: AsyncSession, access_token: str, user_id: str) -> dict[str, int]:
    """
    Sync user's Discord guilds with database.

    - Creates new guilds with channels and default template
    - Refreshes channels for existing guilds
    - Marks missing channels as inactive

    Returns:
        Dictionary with counts: {
            "new_guilds": number of new guilds created,
            "new_channels": number of channels added for new guilds,
            "updated_channels": number of channels synced for existing guilds
        }
    """
    client = await get_discord_bot_client()

    candidate_guild_ids = await _compute_candidate_guild_ids(db, client, access_token, user_id)
    existing_guild_ids = await _get_existing_guild_ids(db)
    new_guild_ids = candidate_guild_ids - existing_guild_ids
    existing_candidate_guild_ids = candidate_guild_ids & existing_guild_ids

    total_guilds = 0
    total_new_channels = 0
    total_updated_channels = 0

    # Process new guilds (existing behavior)
    for guild_discord_id in new_guild_ids:
        guilds_created, channels_created = await _create_guild_with_channels_and_template(
            db, client, guild_discord_id
        )
        total_guilds += guilds_created
        total_new_channels += channels_created

    # Process existing guilds (new behavior)
    for guild_discord_id in existing_candidate_guild_ids:
        # Get guild config from database
        guild_config = await queries.get_guild_by_discord_id(db, guild_discord_id)
        if guild_config:
            # Sync channels for this guild
            updated = await _sync_guild_channels(
                db, client, guild_config.id, guild_discord_id
            )
            total_updated_channels += updated

    return {
        "new_guilds": total_guilds,
        "new_channels": total_new_channels,
        "updated_channels": total_updated_channels,
    }
```

**Step 3: Update GuildSyncResponse Schema**

```python
# shared/schemas/guild.py

class GuildSyncResponse(BaseModel):
    """Response from guild sync operation."""

    new_guilds: int = Field(..., description="Number of new guilds created")
    new_channels: int = Field(..., description="Number of channels added for new guilds")
    updated_channels: int = Field(
        ...,
        description="Number of channels added/updated for existing guilds"
    )
```

**Step 4: Update sync_guilds Endpoint Response**

```python
# services/api/routes/guilds.py

@router.post("/sync", response_model=guild_schemas.GuildSyncResponse)
async def sync_guilds(...):
    """
    Sync user's Discord guilds and channels with database.

    - Creates new guilds with channels and default template
    - Refreshes channels for existing guilds
    - Marks deleted Discord channels as inactive

    Returns count of new guilds, new channels, and updated channels.
    """
    result = await guild_service.sync_user_guilds(db, access_token, user_discord_id)

    return guild_schemas.GuildSyncResponse(
        new_guilds=result["new_guilds"],
        new_channels=result["new_channels"],
        updated_channels=result["updated_channels"],
    )
```

**Step 5: Filter Inactive Channels in list_guild_channels**

```python
# services/api/routes/guilds.py

@router.get("/{guild_id}/channels", response_model=list[channel_schemas.ChannelConfigResponse])
async def list_guild_channels(...):
    """
    List active channels for a guild.

    Only returns channels with is_active=True to hide deleted Discord channels.
    """
    guild_config = await queries.require_guild_by_id(db, guild_id, ...)
    await permissions.verify_guild_membership(guild_config.guild_id, current_user, db)

    # Get all channels for guild
    channels = await queries.get_channels_by_guild(db, guild_config.id)

    # Filter active channels only
    channel_responses = []
    for channel in channels:
        if channel.is_active:  # Only show active channels
            channel_name = await fetch_channel_name_safe(channel.channel_id)
            channel_responses.append(
                channel_schemas.ChannelConfigResponse(
                    id=channel.id,
                    guild_id=channel.guild_id,
                    guild_discord_id=guild_config.guild_id,
                    channel_id=channel.channel_id,
                    channel_name=channel_name,
                    is_active=channel.is_active,
                    created_at=channel.created_at.isoformat(),
                    updated_at=channel.updated_at.isoformat(),
                )
            )

    return channel_responses
```

**Step 6: Update Frontend Button Label and Message**

```typescript
// frontend/src/pages/MyGuilds.tsx or similar

// Button label
<Button onClick={handleSync}>
  Sync guilds and channels
</Button>

// Success message after sync
if (result.new_guilds > 0 || result.updated_channels > 0) {
  let message = [];
  if (result.new_guilds > 0) {
    message.push(`Added ${result.new_guilds} new server${result.new_guilds > 1 ? 's' : ''}`);
  }
  if (result.updated_channels > 0) {
    message.push(`updated ${result.updated_channels} channel${result.updated_channels > 1 ? 's' : ''}`);
  }
  showSuccess(message.join(', '));
} else {
  showInfo('All guilds and channels are up to date');
}
```

## Implementation Guidance

### Objectives
- Refresh channel list for existing guilds when user clicks sync
- Add new channels as active, mark deleted channels as inactive
- Update sync response to show both new and updated channel counts
- Filter inactive channels from template/game creation dropdowns
- Preserve foreign key references (never delete channels)
- No caching needed (manual operation, rate limits not a concern)

### Key Tasks

1. Create `_sync_guild_channels()` helper function in guild_service
2. Update `sync_user_guilds()` to process existing guilds
3. Update `GuildSyncResponse` schema with `updated_channels` field
4. Update `sync_guilds` endpoint to return new response format
5. Filter channels by `is_active=True` in `list_guild_channels` endpoint
6. Update frontend sync button label to "Sync guilds and channels"
7. Update frontend success message to show updated channel count

### Dependencies
- Existing `get_guild_channels()` method in DiscordAPIClient
- Existing `channel_service.create_channel_config()` method
- Existing `queries.get_channels_by_guild()` method
- Existing `queries.get_guild_by_discord_id()` method

### Success Criteria
- ✅ New Discord channels appear after clicking sync
- ✅ Deleted Discord channels marked inactive and hidden from dropdowns
- ✅ Existing guilds get channel refreshes during sync
- ✅ Sync response shows meaningful counts for new and existing guilds
- ✅ Frontend displays clear success message
- ✅ Inactive channels preserved in database (foreign key integrity)
- ✅ No breaking changes to existing games/templates
- ✅ All integration tests pass

### Error Handling
- Discord API failure during sync: Continue with other guilds (partial success pattern)
- Individual guild sync failure: Log error, continue with remaining guilds
- Channel sync failure: Log error, guild still marked as processed
- Frontend displays partial success results to user

### Testing Checklist
- [ ] Create channel in Discord, run sync, verify appears in template dropdown
- [ ] Delete channel in Discord, run sync, verify disappears from template dropdown
- [ ] Verify inactive channel still visible in existing game/template (read-only)
- [ ] Sync with multiple guilds, verify counts are accurate
- [ ] Verify foreign key integrity maintained (no orphaned games/templates)
- [ ] Test partial failure scenario (one guild fails, others succeed)
