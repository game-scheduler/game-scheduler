<!-- markdownlint-disable-file -->

# Task Details: Channel Sync via Guild Sync Button

## Research Reference

**Source Research**: #file:../research/20260205-channel-lazy-loading-guild-setup-research.md

## Phase 1: Backend - Channel Sync Helper

### Task 1.1: Create `_sync_guild_channels()` helper function

Create a new private helper function in guild_service.py that syncs channels from Discord to the database for a specific guild.

- **Files**:
  - services/api/services/guild_service.py - Add `_sync_guild_channels()` function

- **Implementation**:
  ```python
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
              channel = existing_channels[channel_discord_id]
              if not channel.is_active:
                  channel.is_active = True
                  channels_updated += 1
          else:
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

- **Success**:
  - Function returns accurate count of channels added/updated
  - New channels created with `is_active=True`
  - Deleted Discord channels marked with `is_active=False`
  - Existing active channels remain unchanged

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 156-214) - Complete implementation with get-or-create pattern

- **Dependencies**:
  - `channel_service.create_channel_config()` method
  - `ChannelConfiguration` model
  - SQLAlchemy select query

## Phase 2: Backend - Extend sync_user_guilds

### Task 2.1: Update `sync_user_guilds()` to process existing guilds

Modify the guild sync function to refresh channels for existing guilds in addition to creating new guilds.

- **Files**:
  - services/api/services/guild_service.py - Modify `sync_user_guilds()` function

- **Implementation**:
  ```python
  async def sync_user_guilds(db: AsyncSession, access_token: str, user_id: str) -> dict[str, int]:
      """
      Sync user's Discord guilds with database.

      - Creates new guilds with channels and default template
      - Refreshes channels for existing guilds
      - Marks missing channels as inactive

      Returns dict with new_guilds, new_channels, updated_channels counts
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
          guild_config = await queries.get_guild_by_discord_id(db, guild_discord_id)
          if guild_config:
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

- **Success**:
  - New guilds created with channels (existing behavior maintained)
  - Existing guilds have channels synced from Discord
  - Return dict includes all three counts accurately

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 216-274) - Full implementation with existing guild processing

- **Dependencies**:
  - Task 1.1 completion (`_sync_guild_channels()` function)
  - `queries.get_guild_by_discord_id()` method

## Phase 3: Backend - Schema and Response Updates

### Task 3.1: Add `updated_channels` field to GuildSyncResponse schema

Extend the response schema to include the count of channels updated for existing guilds.

- **Files**:
  - shared/schemas/guild.py - Modify `GuildSyncResponse` class

- **Implementation**:
  ```python
  class GuildSyncResponse(BaseModel):
      """Response from guild sync operation."""

      new_guilds: int = Field(..., description="Number of new guilds created")
      new_channels: int = Field(..., description="Number of channels added for new guilds")
      updated_channels: int = Field(
          ...,
          description="Number of channels added/updated for existing guilds"
      )
  ```

- **Success**:
  - Schema includes `updated_channels` field
  - Field has appropriate description
  - All fields are required (non-optional)

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 276-290) - Schema definition

- **Dependencies**:
  - None (schema update only)

### Task 3.2: Update sync_guilds endpoint to return new response format

Modify the endpoint to use the new response schema with all three count fields.

- **Files**:
  - services/api/routes/guilds.py - Modify `sync_guilds()` endpoint

- **Implementation**:
  ```python
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

- **Success**:
  - Endpoint returns all three count values
  - Response matches updated schema
  - Existing behavior preserved for new guilds

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 292-315) - Endpoint implementation

- **Dependencies**:
  - Task 2.1 completion (updated service method)
  - Task 3.1 completion (updated schema)

## Phase 4: Backend - Filter Inactive Channels

### Task 4.1: Filter channels by `is_active=True` in list_guild_channels endpoint

Modify the channel listing endpoint to only return active channels, hiding deleted Discord channels from dropdowns.

- **Files**:
  - services/api/routes/guilds.py - Modify `list_guild_channels()` endpoint

- **Implementation**:
  ```python
  @router.get("/{guild_id}/channels", response_model=list[channel_schemas.ChannelConfigResponse])
  async def list_guild_channels(...):
      """
      List active channels for a guild.

      Only returns channels with is_active=True to hide deleted Discord channels.
      """
      guild_config = await queries.require_guild_by_id(db, guild_id, ...)
      await permissions.verify_guild_membership(guild_config.guild_id, current_user, db)

      channels = await queries.get_channels_by_guild(db, guild_config.id)

      channel_responses = []
      for channel in channels:
          if channel.is_active:  # Filter active channels only
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

- **Success**:
  - Endpoint returns only active channels
  - Inactive channels hidden from template/game creation dropdowns
  - Existing games/templates with inactive channels unaffected

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 317-370) - Filtering implementation

- **Dependencies**:
  - None (independent endpoint modification)

## Phase 5: Frontend - UI Updates

### Task 5.1: Update sync button label to "Sync guilds and channels"

Change the button text to reflect that both guilds and channels are synced.

- **Files**:
  - frontend/src/pages/MyGuilds.tsx (or similar guild management page)

- **Implementation**:
  Locate the sync button and update its label:
  ```typescript
  <Button onClick={handleSync}>
    Sync guilds and channels
  </Button>
  ```

- **Success**:
  - Button displays "Sync guilds and channels" text
  - Button functionality unchanged (still calls sync endpoint)

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 372-381) - Button label update

- **Dependencies**:
  - None (UI-only change)

### Task 5.2: Update success message to display updated channel count

Modify the post-sync success message to show both new and updated channel counts.

- **Files**:
  - frontend/src/pages/MyGuilds.tsx (or similar)

- **Implementation**:
  ```typescript
  // Update success message handler
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

- **Success**:
  - Message shows new guild count when guilds added
  - Message shows updated channel count when channels synced
  - Message handles singular/plural correctly
  - "Up to date" message shown when no changes

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 383-401) - Success message implementation

- **Dependencies**:
  - Task 3.2 completion (endpoint returns updated_channels)

## Phase 6: Testing and Validation

### Task 6.1: Write integration tests for channel sync operations

Create comprehensive tests validating channel sync behavior for both new and existing guilds.

- **Files**:
  - tests/integration/test_guild_sync.py (or similar)

- **Test Cases**:
  1. Sync new guild creates channels with is_active=True
  2. Sync existing guild adds new Discord channels to database
  3. Sync existing guild marks deleted Discord channels as is_active=False
  4. Sync existing guild reactivates previously inactive channels
  5. Multiple guild sync returns accurate counts
  6. list_guild_channels endpoint filters inactive channels

- **Success**:
  - All test cases pass
  - Tests validate counts in sync response
  - Tests verify is_active flag behavior
  - Tests check channel filtering in list endpoint

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 435-448) - Testing checklist

- **Dependencies**:
  - All backend tasks completed (Phase 1-4)

### Task 6.2: Validate foreign key integrity and inactive channel behavior

Manual and automated validation that inactive channels preserve database relationships.

- **Files**:
  - Existing game/template records with channels

- **Validation Steps**:
  1. Create game with specific channel
  2. Delete channel from Discord
  3. Run guild sync
  4. Verify channel marked is_active=False
  5. Verify game still displays channel name (read-only)
  6. Verify channel not in template creation dropdown
  7. Verify database foreign keys intact (no orphaned records)

- **Success**:
  - Games/templates with inactive channels load correctly
  - Foreign key constraints not violated
  - Inactive channels hidden from new game/template forms
  - No database errors or warnings

- **Research References**:
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 86-95) - Foreign key discussion
  - #file:../research/20260205-channel-lazy-loading-guild-setup-research.md (Lines 108-122) - Channel filtering behavior

- **Dependencies**:
  - All implementation phases completed
  - Test data with existing games/templates

## Dependencies

- Python async/await support
- FastAPI framework
- SQLAlchemy ORM
- Discord API client
- Existing database schema with ChannelConfiguration table

## Success Criteria

- Channel sync helper function works correctly for individual guilds
- Guild sync processes both new and existing guilds
- Response schema includes all three count fields
- Inactive channels filtered from list endpoint
- Frontend displays updated button label and success messages
- Integration tests validate all sync behaviors
- Foreign key integrity maintained throughout
- No breaking changes to existing functionality
