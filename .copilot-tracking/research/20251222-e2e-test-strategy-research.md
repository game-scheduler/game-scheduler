<!-- markdownlint-disable-file -->
# Task Research Notes: E2E Test Strategy

> **REFACTOR COMPLETE (2025-12-22)**
>
> Discord client token unification refactor has been successfully implemented and committed.
> E2E test development can now resume with simplified token handling.
>
> **Refactor Verification**:
> - ✅ `DiscordAPIClient._get_auth_header()` implemented with automatic token type detection
>   - Detects bot tokens (2 dots) and OAuth tokens (1 dot)
>   - Returns "Bot {token}" or "Bearer {token}" appropriately
> - ✅ `DiscordAPIClient.get_guilds(token, user_id)` implemented as unified method
>   - Works with both bot and OAuth tokens automatically
>   - Merged caching logic from separate methods
> - ✅ Deprecated methods removed (`get_bot_guilds()` and `get_user_guilds()`)
>   - All callers updated to use unified interface
> - ✅ Commit: `0d70d93` "Unify Discord API client token handling for bot and OAuth"
>
> **Ready to Resume E2E Work**:
> - Token type detection now simplified (no need to distinguish at call site)
> - Admin bot approach validated (bot tokens work with Discord API)
> - All E2E infrastructure in place (fixtures, helpers, Docker Compose)
> - Blocking issue resolved: Can now use bot token directly for authentication

## Research Executed

### File Analysis
- tests/e2e/test_game_notification_api_flow.py (338 lines)
  - Database-focused tests verifying notification_schedule CRUD operations
  - Uses direct SQL queries with psycopg2 for verification
  - Does NOT verify Discord message content or bot behavior
  - Tests: schedule population, daemon processing, schedule recalculation, cleanup
  - No Discord API interactions or message validation
- tests/e2e/test_guild_template_api.py (458 lines)
  - Integration tests for guild sync and template APIs
  - Uses mocked Discord API responses (Mock/patch)
  - Tests API endpoints, not full Discord integration
  - No actual Discord bot interaction
- TESTING_E2E.md (261 lines)
  - Documents Discord test environment setup requirements
  - Requires separate test Discord guild, bot, and test users
  - Configuration via env/env.e2e file
  - compose.e2e.yaml profile includes bot, notification-daemon, and full stack

### Code Search Results
- services/bot/events/handlers.py
  - _handle_game_created(): Posts announcement to Discord channel
  - _handle_game_reminder(): Sends DM reminders to participants
  - _handle_join_notification(): Sends DM when user joins game
  - _refresh_game_message(): Edits existing Discord message
  - All use discord.py TextChannel.fetch_message() to retrieve messages
- services/bot/formatters/game_message.py
  - format_game_announcement(): Creates embed with game details
  - Returns tuple: (content, embed, view) where content may contain role mentions
  - Embed includes: title, description, scheduled_at, host, participants, overflow
- shared/discord/client.py
  - DiscordAPIClient uses REST API (aiohttp) not discord.py
  - No fetch_message() method in DiscordAPIClient
  - Methods: get_bot_guilds, get_guild_channels, fetch_channel, fetch_guild, fetch_guild_roles, fetch_user, get_guild_member
- Discord.py bot usage (services/bot/)
  - bot.fetch_channel() - Get TextChannel object
  - channel.fetch_message(message_id) - Get Message object
  - message.content, message.embeds, message.author - Message properties

### External Research
- #fetch:https://discord.com/developers/docs/resources/message
  - Message objects contain: id, channel_id, author, content, timestamp, embeds, attachments, components
  - content: String up to 2000 characters (may be empty if MESSAGE_CONTENT intent not configured)
  - embeds: Array of embed objects with title, description, fields, author, footer, thumbnail, image
  - author: User object with id, username, avatar
  - embeds[].fields: Array of {name, value, inline} objects
  - GET /channels/{channel_id}/messages/{message_id} - Fetch specific message (requires VIEW_CHANNEL + READ_MESSAGE_HISTORY)
  - GET /channels/{channel_id}/messages?limit=N - Fetch recent messages (1-100)
  - MESSAGE_CONTENT privileged intent required to read content/embeds from Gateway events
  - REST API fetch_message() bypasses intent requirement (bot token has implicit permissions)

### Project Conventions
- Python: pytest, AsyncClient, AsyncSession, fixtures for setup/teardown
- Docker Compose profiles for test environments (int, e2e)
- E2E tests run in isolated containerized environment
- Tests use env/env.e2e for Discord credentials
- Integration tests use httpx.Client for API calls
- Bot uses discord.py library (Gateway + REST)

## Key Discoveries

### Current E2E Test State
The existing E2E tests are **database-focused integration tests**, NOT true end-to-end tests:
- Test database operations (notification_schedule CRUD)
- Verify API endpoints return correct status codes
- Use direct SQL queries for assertions
- **Do not verify Discord bot behavior or message content**
- **Do not validate what users actually see in Discord**
- Mock Discord API responses instead of using real Discord connection

**Gap**: No verification that:
- Game announcements actually appear in Discord channels
- Messages contain correct game details, embeds, buttons
- DM reminders are sent to participants
- Message updates reflect game changes
- Role mentions trigger Discord notifications
- Buttons are clickable and functional

### System Architecture for E2E Testing
Full stack includes:
1. **PostgreSQL** - Game sessions, users, channels, notification_schedule
2. **Valkey/Redis** - Caching, rate limiting
3. **RabbitMQ** - Event messaging between services
4. **API Service** (FastAPI) - REST endpoints for game CRUD
5. **Bot Service** (discord.py) - Gateway connection, slash commands, button handlers, message posting
6. **Notification Daemon** - Polls database for due notifications, publishes events
7. **Status Transition Daemon** - Updates game status (scheduled → in_progress → completed)
8. **Discord API** - External dependency (requires test guild, channel, bot token)

**Key Integration Points**:
- API creates game → publishes game.created event → Bot posts announcement to Discord
- User clicks Join button → Bot updates database → Bot edits Discord message
- Notification daemon finds due reminder → publishes notification.due → Bot sends DMs
- Game update via API → publishes game.updated → Bot edits Discord message

### Discord Message Reading Capabilities

**discord.py library provides**:
- `channel.fetch_message(message_id)` - Returns Message object
- `message.content` - String content (role mentions, text)
- `message.embeds` - List of Embed objects
- `message.embeds[0].title` - Embed title
- `message.embeds[0].description` - Embed description
- `message.embeds[0].fields` - List of EmbedField(name, value, inline)
- `message.embeds[0].author.name` - Author name
- `message.embeds[0].footer.text` - Footer text
- `message.embeds[0].thumbnail.url` - Thumbnail URL
- `message.embeds[0].image.url` - Image URL
- `message.author` - User who posted message (bot)
- `message.created_at` - Timestamp
- `message.components` - Button/select menu components (NOT directly accessible as Python objects)

**Limitations**:
- Button components exist but discord.py doesn't provide easy inspection API
- Cannot easily verify button labels, custom_ids, or disabled state from Message object
- Would need to access raw message data or use discord API types

**DM verification**:
- Bot can fetch DM channel: `user.create_dm()` or `bot.get_user(user_id).dm_channel`
- Can fetch recent messages: `dm_channel.history(limit=10)`
- Iterate messages to find specific game-related DM
- Verify DM content, embeds match expected reminder format

### Test Data Requirements

To test complete game announcement flow:
1. **Guild Configuration** (in database)
   - guild_id: Discord guild snowflake
   - Database: guild_configurations table
2. **Channel Configuration** (in database)
   - channel_id: Discord channel snowflake
   - Database: channel_configurations table
3. **Game Session** (in database)
   - title, description, scheduled_at, max_players
   - host_id (user UUID), channel reference
   - Database: game_sessions table
4. **User** (in database + Discord)
   - discord_id: Real Discord user ID (test account)
   - Database: users table
5. **Discord Resources** (external)
   - Test guild must exist in Discord
   - Test channel must exist in guild
   - Bot must be member of guild with permissions
   - Test user must be member of guild

**Message Storage**:
- game_sessions.message_id stores Discord message snowflake
- Used to edit/delete announcement messages
- Set when bot posts initial announcement

## Implementation Guidance

### Recommended: Start Fresh with Incremental Approach
The existing tests don't address the core gap (Discord message validation). Starting fresh allows us to:
- Design tests around actual user-facing behavior
- Build incrementally from simple to complex scenarios
- Establish patterns for future test development
- Avoid technical debt from half-implemented test infrastructure

### Priority E2E Test Scenarios

**Critical Path (Implement First)**:
1. **Game Creation → Announcement Posted**
   - Create game via API
   - Verify announcement appears in Discord channel
   - Validate embed contains: title, description, scheduled time, host mention, player count, Join/Leave buttons
   - **Why first**: Core functionality, highest user impact, establishes message reading pattern

**Essential Functionality**:
2. **Game Update → Message Refreshed**
   - Create game, update title/description via API
   - Verify Discord message edited with new content
   - Validate message_id unchanged
3. **User Joins Game → Participant List Updated**
   - Create game, simulate Join button click (via API participant add)
   - Verify Discord message shows user in participant list
   - Validate player count incremented
4. **Game Reminder → DM Sent**
   - Create game with reminder_minutes=[5]
   - Wait for notification daemon to process
   - Verify test user receives DM with game details
5. **Game Status Transition → Message Updated**
   - Create game scheduled 1 minute in future
   - Wait for status transition daemon to process SCHEDULED→IN_PROGRESS transition
   - Verify Discord message updated with IN_PROGRESS status
   - Wait for IN_PROGRESS→COMPLETED transition (after duration)
   - Verify Discord message updated with COMPLETED status
   - **Why critical**: Validates status_transition_daemon → RabbitMQ → Bot path (missing coverage)
6. **Game Deletion → Message Removed**
   - Create game, delete via API
   - Verify Discord message deleted from channel

**Advanced Scenarios** (Later):
7. **Role Mentions in Announcement** - Verify role mention in message.content triggers notifications
8. **Waitlist Promotion** - User moves from overflow to participant, receives DM
9. **Multiple Games in Channel** - Verify correct message updated when multiple games exist
10. **Permission Boundaries** - Non-host cannot edit game, button reflects disabled state
11. **Status Transition Edge Cases** - Invalid transitions rejected, idempotent handling of duplicate events

### Recommended First Test: Game Creation → Announcement Posted

**Why This Test First**:
- Validates core value proposition (scheduling games in Discord)
- Exercises complete stack (API → RabbitMQ → Bot → Discord)
- Establishes patterns for message reading and verification
- Simple scenario, clear success criteria
- No complex timing dependencies (unlike reminders)

**Test Structure**:
```python
async def test_game_creation_posts_announcement_to_discord():
    """
    E2E: Creating game via API posts announcement to Discord channel.

    Verifies:
    - Message appears in configured channel
    - Embed contains game details
    - Host is mentioned correctly
    - Buttons are present (Join, Leave)
    """
    # ARRANGE: Create guild, channel, user in database
    async with get_db() as db:
        guild_config = await create_test_guild(db, TEST_GUILD_ID)
        channel_config = await create_test_channel(db, guild_config.id, TEST_CHANNEL_ID)
        host_user = await create_test_user(db, TEST_HOST_DISCORD_ID)

    # ACT: Create game via API
    game_data = {
        "title": "E2E Test Game",
        "description": "Testing game announcement",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "guild_id": guild_config.id,
        "channel_id": channel_config.id,
        "host_id": host_user.id,
        "max_players": 4,
    }
    response = await api_client.post("/api/games", json=game_data)
    assert response.status_code == 201
    game_id = response.json()["id"]

    # Wait for bot to process game.created event
    await asyncio.sleep(2)

    # ASSERT: Verify message in Discord
    # Fetch message_id from database
    async with get_db() as db:
        game = await db.get(GameSession, game_id)
        assert game.message_id is not None, "Message ID should be set"

    # Fetch Discord message
    bot_client = discord.Client(intents=discord.Intents.default())
    await bot_client.login(TEST_BOT_TOKEN)
    channel = await bot_client.fetch_channel(int(TEST_CHANNEL_ID))
    message = await channel.fetch_message(int(game.message_id))

    # Verify message content
    assert len(message.embeds) == 1, "Should have one embed"
    embed = message.embeds[0]
    assert embed.title == "E2E Test Game"
    assert "Testing game announcement" in embed.description

    # Verify host mention
    host_field = next(f for f in embed.fields if f.name == "🎯 Host")
    assert f"<@{TEST_HOST_DISCORD_ID}>" in host_field.value

    # Verify player count
    players_field = next(f for f in embed.fields if f.name == "👥 Players")
    assert "0/4" in players_field.value

    await bot_client.close()
```

**Success Criteria**:
- Test passes when message appears with correct content
- Establishes reusable helper functions (create_test_guild, fetch_discord_message)
- Validates event-driven architecture works end-to-end

### Alternative Test Structures

**Option 1: Fixture-Based Setup** (Cleaner, Reusable)
```python
@pytest.fixture
async def test_environment():
    """Set up complete test environment with Discord resources."""
    # Create database records
    async with get_db() as db:
        guild_config = await create_test_guild(db, TEST_GUILD_ID)
        channel_config = await create_test_channel(db, guild_config.id, TEST_CHANNEL_ID)
        host_user = await create_test_user(db, TEST_HOST_DISCORD_ID)

    # Initialize Discord bot client
    bot_client = discord.Client(intents=discord.Intents.default())
    await bot_client.login(TEST_BOT_TOKEN)

    yield {
        "guild_config": guild_config,
        "channel_config": channel_config,
        "host_user": host_user,
        "bot_client": bot_client,
    }

    # Cleanup
    await bot_client.close()
    async with get_db() as db:
        # Delete test data
        pass

@pytest.mark.asyncio
async def test_game_creation_posts_announcement(test_environment, api_client):
    env = test_environment

    # Create game via API
    response = await api_client.post("/api/games", json={...})

    # Verify Discord message
    channel = await env["bot_client"].fetch_channel(TEST_CHANNEL_ID)
    # ...
```

**Option 2: Helper Module Pattern** (Most Scalable)
```python
# tests/e2e/helpers/discord.py
class DiscordTestHelper:
    def __init__(self, bot_token):
        self.client = discord.Client(intents=discord.Intents.default())
        self.bot_token = bot_token

    async def connect(self):
        await self.client.login(self.bot_token)

    async def get_channel_message(self, channel_id: str, message_id: str):
        channel = await self.client.fetch_channel(int(channel_id))
        return await channel.fetch_message(int(message_id))

    async def verify_game_announcement(self, message, expected_title, expected_host_id):
        assert len(message.embeds) == 1
        embed = message.embeds[0]
        assert embed.title == expected_title
        # ...

    async def get_user_dms(self, user_id: str, limit: int = 10):
        user = await self.client.fetch_user(int(user_id))
        dm_channel = await user.create_dm()
        messages = []
        async for msg in dm_channel.history(limit=limit):
            messages.append(msg)
        return messages

# tests/e2e/test_game_announcement.py
@pytest.fixture
async def discord_helper():
    helper = DiscordTestHelper(TEST_BOT_TOKEN)
    await helper.connect()
    yield helper
    await helper.client.close()

async def test_game_creation(discord_helper):
    # Use helper for all Discord operations
    message = await discord_helper.get_channel_message(CHANNEL_ID, message_id)
    await discord_helper.verify_game_announcement(message, "Test Game", host_id)
```

### Recommendation: Start with Helper Module Pattern

**Rationale**:
- Separates test logic from Discord API interactions
- Reusable verification functions reduce duplication
- Easy to extend for new scenarios (DMs, reactions, etc.)
- Clear interface for Discord operations
- Testable helper functions independently

**Implementation Phases**:
1. **Phase 1: Helper Module + First Test**
   - Create tests/e2e/helpers/discord.py
   - Implement DiscordTestHelper.connect(), get_channel_message()
   - Write test_game_creation_posts_announcement()
   - Validate pattern works end-to-end
2. **Phase 2: Verification Utilities**
   - Add verify_game_announcement(), verify_game_embed_field()
   - Implement get_user_dms(), verify_reminder_dm()
   - Expand test coverage to scenarios 2-5
3. **Phase 3: Advanced Scenarios**
   - Add support for component inspection (buttons)
   - Test role mentions, waitlist, status transitions
   - Performance/timing tests for reminder delivery

### Discord Message Reading Implementation Example

```python
# tests/e2e/helpers/discord.py
import discord
from typing import Optional

class DiscordTestHelper:
    def __init__(self, bot_token: str):
        self.client = discord.Client(intents=discord.Intents.default())
        self.bot_token = bot_token
        self._connected = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        if not self._connected:
            await self.client.login(self.bot_token)
            self._connected = True

    async def disconnect(self):
        if self._connected:
            await self.client.close()
            self._connected = False

    async def get_message(self, channel_id: str, message_id: str) -> discord.Message:
        """Fetch specific message from channel."""
        channel = await self.client.fetch_channel(int(channel_id))
        return await channel.fetch_message(int(message_id))

    async def get_recent_messages(self, channel_id: str, limit: int = 10) -> list[discord.Message]:
        """Fetch recent messages from channel."""
        channel = await self.client.fetch_channel(int(channel_id))
        messages = []
        async for msg in channel.history(limit=limit):
            messages.append(msg)
        return messages

    async def find_message_by_embed_title(
        self, channel_id: str, title: str, limit: int = 10
    ) -> Optional[discord.Message]:
        """Find message with specific embed title."""
        messages = await self.get_recent_messages(channel_id, limit)
        for msg in messages:
            if msg.embeds and msg.embeds[0].title == title:
                return msg
        return None

    def extract_embed_field_value(self, embed: discord.Embed, field_name: str) -> Optional[str]:
        """Extract value from embed field by name."""
        for field in embed.fields:
            if field.name == field_name:
                return field.value
        return None

    async def get_user_recent_dms(self, user_id: str, limit: int = 5) -> list[discord.Message]:
        """Fetch recent DM messages sent to user."""
        user = await self.client.fetch_user(int(user_id))
        dm_channel = await user.create_dm()
        messages = []
        async for msg in dm_channel.history(limit=limit):
            if msg.author.id == self.client.user.id:  # Only bot's messages
                messages.append(msg)
        return messages

    async def find_game_reminder_dm(
        self, user_id: str, game_title: str
    ) -> Optional[discord.Message]:
        """Find DM reminder for specific game."""
        dms = await self.get_user_recent_dms(user_id, limit=10)
        for dm in dms:
            if dm.embeds and "Game Reminder" in dm.embeds[0].title:
                if game_title in dm.embeds[0].description:
                    return dm
        return None

    def verify_game_embed(
        self,
        embed: discord.Embed,
        expected_title: str,
        expected_host_id: str,
        expected_max_players: int,
    ):
        """Verify game announcement embed structure and content."""
        assert embed.title == expected_title, f"Title mismatch: {embed.title}"

        host_field = self.extract_embed_field_value(embed, "🎯 Host")
        assert host_field is not None, "Host field missing"
        assert f"<@{expected_host_id}>" in host_field, f"Host mention incorrect: {host_field}"

        players_field = self.extract_embed_field_value(embed, "👥 Players")
        assert players_field is not None, "Players field missing"
        assert f"/{expected_max_players}" in players_field, f"Max players incorrect: {players_field}"
```

### Test Execution Considerations

**Environment Requirements**:
- TEST_DISCORD_TOKEN: Bot token with permissions (SEND_MESSAGES, EMBED_LINKS, SEND_MESSAGES_IN_THREADS)
- TEST_DISCORD_GUILD_ID: Test guild snowflake (bot must be member)
- TEST_DISCORD_CHANNEL_ID: Test channel snowflake (in test guild)
- TEST_DISCORD_USER_ID: Test user snowflake (for DM verification)

**Timing Considerations**:
- Game creation → announcement posted: ~1-2 seconds (RabbitMQ + bot processing)
- Notification daemon polling: Every 60 seconds
- Status transition daemon: Every 60 seconds
- Tests should use asyncio.sleep() with generous timeouts
- Consider exponential backoff for message polling

**Status Transition Test Timing**:
- Create game scheduled 1 minute in future (short enough for E2E test)
- Status daemon polls every 60 seconds, may process immediately or wait up to 60s
- IN_PROGRESS transition: scheduled_at time
- COMPLETED transition: scheduled_at + expected_duration_minutes
- Use expected_duration_minutes=2 to keep test duration reasonable (~3-4 minutes total)
- Alternative: Query game_status_schedule table to verify schedule entries without waiting

**Isolation**:
- Each test should create unique game titles (include test name + timestamp)
- Clean up Discord messages after test (delete announcement)
- Use separate test channel per test run or clean channel before tests
- Database cleanup in fixtures (existing pattern)

**CI/CD Considerations**:
- E2E tests require external Discord resources (cannot run in standard CI)
- Option 1: Skip E2E tests in CI, run manually before releases
- Option 2: Dedicated test Discord guild for CI with long-lived bot
- Option 3: Conditional execution based on env var (ENABLE_E2E_TESTS)

### Key Tasks

1. Create tests/e2e/helpers/discord.py with DiscordTestHelper
2. Create tests/e2e/test_game_announcement.py with first test
3. Update compose.e2e.yaml to ensure bot connects to Discord (not mocked)
4. Document Discord test setup in TESTING_E2E.md (already exists, verify completeness)
5. Establish pattern for message verification (embed structure, field extraction)
6. Add timing utilities (wait_for_message, poll_until_found)
7. Implement DM verification for reminder tests
8. Create reusable fixtures for test environment setup
9. Document test execution in CI/CD (likely manual-only)

### Dependencies
- pytest-asyncio for async test support (likely already installed)
- discord.py library (already used by bot service)
- Access to test Discord guild, channel, bot token
- Running full stack (compose.e2e.yaml profile)

### Success Criteria
- test_game_creation_posts_announcement passes, verifying message content
- Helper module provides clean API for Discord operations
- Pattern established for future E2E test development
- Documentation updated with test execution instructions
- Clear path forward for implementing remaining test scenarios
- **Status transition test validates status_transition_daemon → RabbitMQ → Bot message update path**

### Status Transition Test Implementation Details

**System Flow to Test**:
1. **Game Creation** - API creates game with scheduled_at and expected_duration_minutes
2. **Schedule Population** - Two game_status_schedule entries created:
   - Entry 1: target_status=IN_PROGRESS, transition_time=scheduled_at
   - Entry 2: target_status=COMPLETED, transition_time=scheduled_at + duration
3. **Status Transition Daemon** - Polls game_status_schedule for due transitions
4. **Event Publishing** - Daemon publishes game.status_transition_due to RabbitMQ
5. **Bot Handler** - _handle_status_transition_due() updates game status and refreshes Discord message

**Test Implementation**:
```python
async def test_game_status_transitions(
    authenticated_admin_client,
    db_session,
    discord_helper,
    test_guild_id,
    test_channel_id,
    test_host_id,
    test_template_id,
    discord_channel_id,
    clean_test_data,
):
    """
    E2E: Game status transitions trigger Discord message updates.

    Verifies:
    - Status transition daemon processes schedule entries
    - game.status_transition_due events published to RabbitMQ
    - Bot updates game status in database
    - Bot refreshes Discord message with new status
    - Both SCHEDULED→IN_PROGRESS and IN_PROGRESS→COMPLETED transitions work
    """
    # Create game scheduled 1 minute in future with 2 minute duration
    game_title = f"E2E Status Transition Test {datetime.now(UTC).isoformat()}"
    scheduled_at = datetime.now(UTC) + timedelta(minutes=1)

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing status transitions",
        "scheduled_at": scheduled_at.isoformat(),
        "max_players": 4,
        "expected_duration_minutes": 2,  # Short duration for E2E test
    }

    response = await authenticated_admin_client.post("/api/v1/games", json=game_data)
    assert response.status_code == 201
    game_id = response.json()["id"]

    # Verify schedule entries created
    result = await db_session.execute(
        text("SELECT id, target_status, transition_time FROM game_status_schedule WHERE game_id = :game_id ORDER BY transition_time"),
        {"game_id": game_id}
    )
    schedules = result.fetchall()
    assert len(schedules) == 2, "Should have IN_PROGRESS and COMPLETED schedules"
    assert schedules[0].target_status == "IN_PROGRESS"
    assert schedules[1].target_status == "COMPLETED"

    # Get initial message_id from database
    result = await db_session.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :id"),
        {"id": game_id}
    )
    message_id = result.scalar_one()

    # Wait for scheduled time + daemon processing (up to 90 seconds)
    wait_time = 90  # 60s for scheduled_at + 30s daemon polling margin
    await asyncio.sleep(wait_time)

    # Verify game transitioned to IN_PROGRESS
    result = await db_session.execute(
        text("SELECT status FROM game_sessions WHERE id = :id"),
        {"id": game_id}
    )
    status = result.scalar_one()
    assert status == "IN_PROGRESS", f"Expected IN_PROGRESS but got {status}"

    # Fetch Discord message and verify status displayed
    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord message should still exist"
    # Message embed or content should reflect IN_PROGRESS status
    # (Implementation depends on how status is displayed in embed)

    # Wait for COMPLETED transition (2 more minutes + margin)
    wait_time = 150  # 120s duration + 30s daemon polling margin
    await asyncio.sleep(wait_time)

    # Verify game transitioned to COMPLETED
    result = await db_session.execute(
        text("SELECT status FROM game_sessions WHERE id = :id"),
        {"id": game_id}
    )
    status = result.scalar_one()
    assert status == "COMPLETED", f"Expected COMPLETED but got {status}"

    # Fetch Discord message and verify status displayed
    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord message should still exist"
    # Message embed or content should reflect COMPLETED status
```

**Alternative: Fast Test without Waiting**
```python
async def test_game_status_schedule_population(
    authenticated_admin_client,
    db_session,
    test_template_id,
    clean_test_data,
):
    """
    E2E: Verify status schedule entries created correctly.

    Tests schedule population without waiting for transitions.
    Much faster than full transition test (~1s vs ~5 minutes).
    """
    game_title = f"E2E Schedule Test {datetime.now(UTC).isoformat()}"
    scheduled_at = datetime.now(UTC) + timedelta(hours=1)

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "scheduled_at": scheduled_at.isoformat(),
        "expected_duration_minutes": 120,
    }

    response = await authenticated_admin_client.post("/api/v1/games", json=game_data)
    assert response.status_code == 201
    game_id = response.json()["id"]

    # Verify both schedule entries exist
    result = await db_session.execute(
        text("""
            SELECT target_status, transition_time
            FROM game_status_schedule
            WHERE game_id = :game_id
            ORDER BY transition_time
        """),
        {"game_id": game_id}
    )
    schedules = result.fetchall()

    assert len(schedules) == 2, "Should have 2 schedule entries"

    # Verify IN_PROGRESS schedule
    assert schedules[0].target_status == "IN_PROGRESS"
    assert schedules[0].transition_time == scheduled_at.replace(tzinfo=None)

    # Verify COMPLETED schedule
    assert schedules[1].target_status == "COMPLETED"
    expected_completion = scheduled_at + timedelta(minutes=120)
    assert schedules[1].transition_time == expected_completion.replace(tzinfo=None)
```

**Recommendation**: Implement **both tests**:
- Fast test validates schedule population (runs in <5s, catches most bugs)
- Full transition test validates entire daemon→bot path (runs in ~5 minutes, comprehensive)

## Microservice Communication Path Analysis (December 24, 2025)

### Complete Service Architecture

**Services Identified**:
1. **API Service** (FastAPI) - REST endpoints, publishes events
2. **Bot Service** (discord.py) - Discord Gateway, consumes events, sends messages
3. **Notification Daemon** - Polls notification_schedule table, publishes events
4. **Status Transition Daemon** - Polls game_status_schedule table, publishes events
5. **Init Service** - One-time setup (migrations, seeding)
6. **PostgreSQL** - Database
7. **RabbitMQ** - Event messaging broker
8. **Valkey/Redis** - Caching, rate limiting
9. **Frontend** (React) - User interface (tested separately)
10. **Grafana Alloy** - Observability collector

### Event Types and Publishers

**API Service Publishes**:
- `GAME_CREATED` → Bot posts announcement to Discord
- `GAME_UPDATED` → Bot refreshes Discord message
- `GAME_CANCELLED` → Bot updates/deletes Discord message
- `PLAYER_REMOVED` → Bot sends DM to removed user
- `NOTIFICATION_SEND_DM` → Bot sends promotional DM (waitlist promotion)

**Notification Daemon Publishes**:
- `NOTIFICATION_DUE` → Bot sends reminder DMs to participants

**Status Transition Daemon Publishes**:
- `GAME_STATUS_TRANSITION_DUE` → Bot updates game status and refreshes Discord message

**Unused Event Types** (defined but not actively published):
- `GAME_STARTED` - Deprecated (replaced by status transitions)
- `GAME_COMPLETED` - Deprecated (replaced by status transitions)
- `PLAYER_JOINED` - Not published (joins trigger GAME_UPDATED instead)
- `PLAYER_LEFT` - Not published (leaves trigger GAME_UPDATED instead)
- `WAITLIST_ADDED` - Defined but never published
- `WAITLIST_REMOVED` - Defined but never published
- `NOTIFICATION_SENT` - Defined but never published
- `NOTIFICATION_FAILED` - Defined but never published
- `GUILD_CONFIG_UPDATED` - Defined but never published
- `CHANNEL_CONFIG_UPDATED` - Defined but never published

### Communication Paths and Current E2E Test Coverage

| Path | Event Type | E2E Test Status |
|------|------------|----------------|
| **API → RabbitMQ → Bot** | | |
| Game creation | `GAME_CREATED` | ✅ test_game_announcement.py |
| Game update | `GAME_UPDATED` | ✅ test_game_update.py |
| Game cancellation | `GAME_CANCELLED` | ❌ **MISSING** |
| Player removed | `PLAYER_REMOVED` | ❌ **MISSING** |
| Waitlist promotion DM | `NOTIFICATION_SEND_DM` | ⚠️ test_waitlist_promotion.py **(NOT VALIDATED)** |
| **Notification Daemon → RabbitMQ → Bot** | | |
| Game reminders | `NOTIFICATION_DUE` (type=reminder) | ✅ test_game_reminder.py |
| Join notifications | `NOTIFICATION_DUE` (type=join_notification) | ❌ **MISSING** |
| **Status Transition Daemon → RabbitMQ → Bot** | | |
| Status transitions | `GAME_STATUS_TRANSITION_DUE` | ❌ **MISSING** (identified earlier) |
| **API → Database → Notification Daemon** | | |
| Notification schedule population | (database trigger) | ⚠️ Partial (verified in reminder test) |
| **API → Database → Status Daemon** | | |
| Status schedule population | (database trigger) | ⚠️ Partial (no explicit test) |
| **Discord User Action → Bot → API** | | |
| User join via button | (slash command/button) | ✅ test_user_join.py (simulated via API) |
| User leave via button | (slash command/button) | ❌ **MISSING** |

### Identified Test Coverage Gaps

**Critical Gaps** (Should implement):

1. **Game Cancellation → Message Update**
   - Path: API publishes `GAME_CANCELLED` → Bot updates/deletes message
   - Why critical: Common user action, different from update (may delete message)
   - Validates: API → RabbitMQ → Bot cancellation path

2. **Player Removal → DM Notification**
   - Path: API publishes `PLAYER_REMOVED` → Bot sends DM to removed user
   - Why critical: User notification requirement, different from reminder DMs
   - Validates: API → RabbitMQ → Bot removal notification path

3. **Waitlist Promotion → DM Notification** ⚠️ **IMPLEMENTED BUT NOT VALIDATED**
   - Path: API publishes `NOTIFICATION_SEND_DM` → Bot sends promotion DM
   - Why critical: Important user experience (getting off waitlist)
   - Validates: API → RabbitMQ → Bot promotional DM path (different from PLAYER_REMOVED)
   - Note: Uses different event type (NOTIFICATION_SEND_DM vs PLAYER_REMOVED)
   - **Status**: Implemented in `test_waitlist_promotion.py` with 2 scenarios
     - Scenario 1: Promotion via placeholder removal
     - Scenario 2: Promotion via max_players increase
   - **Bug Fixed**: Promotion detection now correctly handles placeholder participants using `partition_participants()` utility
   - **⚠️ VALIDATION PENDING**: Test has not been run since bug fix - needs verification

4. **Join Notification → Delayed DM**
   - Path: API creates notification_schedule entry (type=join_notification) → Notification daemon publishes `NOTIFICATION_DUE` → Bot sends join instructions DM
   - Why critical: Validates second notification_type path (only reminder tested)
   - Validates: API → Database → Notification Daemon → RabbitMQ → Bot join notification path

5. **Status Transition → Message Update** (Already identified)
   - Path: Status daemon publishes `GAME_STATUS_TRANSITION_DUE` → Bot updates status and refreshes message
   - Why critical: Validates third daemon path (notification daemon tested, status daemon not)
   - Validates: Status Transition Daemon → RabbitMQ → Bot path

**Lower Priority Gaps**:

6. **User Leave via Button → Message Update**
   - Would require Discord interaction testing (button click simulation)
   - Currently not easily testable in E2E (requires Discord API interaction)
   - Alternative: Test via API endpoint that simulates leave

7. **Schedule Population Verification**
   - Fast tests to verify notification_schedule and game_status_schedule entries created correctly
   - Already partially covered in existing tests (checked implicitly)
   - Could add explicit tests for edge cases

### Recommendation: Prioritized Implementation Order

**Phase 1 - Core Missing Paths** (Highest ROI):
1. **test_game_cancellation.py** - Validates GAME_CANCELLED event handling
2. **test_player_removal.py** - Validates PLAYER_REMOVED event and DM
3. **test_game_status_transitions.py** - Validates status daemon path (already detailed earlier)

**Phase 2 - Notification System Completeness**:
4. ⚠️ **test_waitlist_promotion.py** - Validates NOTIFICATION_SEND_DM event **[IMPLEMENTED - NEEDS VALIDATION]**
5. **test_join_notification.py** - Validates second notification daemon path

**Phase 3 - Edge Cases and Schedule Validation**:
6. **test_schedule_population.py** - Fast tests for both notification and status schedules
7. **test_user_leave.py** - If Discord button simulation becomes feasible

### Architecture Insights

**Three Event Publishing Patterns**:
1. **Immediate API Events** - Published synchronously during API requests
   - GAME_CREATED, GAME_UPDATED, GAME_CANCELLED, PLAYER_REMOVED, NOTIFICATION_SEND_DM
2. **Scheduled Notification Events** - Published by notification daemon polling database
   - NOTIFICATION_DUE (both reminder and join_notification types)
3. **Scheduled Status Events** - Published by status transition daemon polling database
   - GAME_STATUS_TRANSITION_DUE

**Current E2E Coverage**:
- ✅ Pattern 1: 2/5 event types tested and validated (GAME_CREATED, GAME_UPDATED)
- ⚠️ Pattern 1: 1/5 implemented but not validated (NOTIFICATION_SEND_DM)
- ✅ Pattern 2: 1/2 notification types tested (reminder only)
- ❌ Pattern 3: 0/1 tested (status transitions not tested)

**Complete Coverage Requires**: Validate 1 test + implement 6 additional E2E tests

## Progress Update (December 22, 2025)

### Phase 1 Implementation Status: PARTIALLY COMPLETE

**✅ Completed Work**:

1. **Discord Test Helper Module** - `tests/e2e/helpers/discord.py`
   - DiscordTestHelper class with connect/disconnect lifecycle
   - get_message(channel_id, message_id) - Fetch specific Discord message
   - verify_game_embed() - Validate game announcement embed structure
   - Context manager support for clean resource management
   - Status: **FULLY IMPLEMENTED**

2. **E2E Test Infrastructure** - `tests/e2e/conftest.py`
   - Environment variable fixtures (discord_token, discord_guild_id, discord_channel_id, discord_user_id)
   - Database session fixtures (db_engine, db_session) with proper connection pooling
   - HTTP client fixture for API requests
   - discord_helper fixture with automatic connect/disconnect
   - All fixtures use proper scopes (session vs function)
   - Status: **FULLY IMPLEMENTED**

3. **Environment Validation Tests** - `tests/e2e/test_00_environment.py`
   - test_environment_variables() - Verify all required env vars present
   - test_discord_bot_can_connect() - Validate bot token and Discord login
   - test_discord_guild_exists() - Confirm bot has access to test guild
   - test_discord_channel_exists() - Verify channel exists and is text channel
   - test_discord_user_exists() - Validate test user exists in Discord
   - test_database_seeded() - Confirm init service seeded guild/channel/user
   - test_api_accessible() - Check API /health endpoint responds
   - **All 7 tests PASSING** ✅
   - Status: **COMPLETE AND VALIDATED**

4. **E2E Data Seeding** - `services/init/seed_e2e.py`
   - Idempotent seeding (checks if data already exists)
   - Seeds guild_configurations, channel_configurations, users tables
   - Uses TEST_ENVIRONMENT flag to trigger seeding
   - Integrated into init service startup
   - Status: **FULLY IMPLEMENTED AND TESTED**

5. **Docker Compose Configuration** - `compose.e2e.yaml`
   - All services configured with proper environment variables
   - PYTEST_RUNNING=1 disables telemetry (eliminates noise)
   - Environment variables standardized (removed TEST_ prefix confusion)
   - Database connection variables (POSTGRES_*) passed to test container
   - Status: **OPTIMIZED AND WORKING**

6. **Test Execution Script** - `scripts/run-e2e-tests.sh`
   - Validates required environment variables
   - Builds test container
   - Runs pytest with proper arguments
   - Cleans up Docker resources after execution
   - Status: **FUNCTIONAL**

**⚠️ Partially Complete Work**:

1. **Game Announcement Test** - `tests/e2e/test_game_announcement.py`
   - Test structure created with proper fixtures
   - clean_test_data fixture removes game records between tests
   - test_guild_id, test_channel_id, test_host_id fixtures query seeded data
   - Main test function skeleton implemented
   - **Status: BLOCKED - Needs Authentication + Template**

**🔴 Blocking Issues Discovered**:

### Authentication Requirements
The API endpoint `/api/v1/games` POST requires:
1. **Session Token Cookie**: `session_token` must be present in cookies
   - Error: `{"field":"cookie.session_token","message":"Field required","type":"missing"}`
   - The API uses OAuth/session-based authentication
   - Tests need to authenticate before making API requests

2. **Template ID Field**: Request body must include `template_id`
   - Error: `{"field":"body.template_id","message":"Field required","type":"missing"}`
   - Games are created from templates, not from scratch
   - Tests need to either:
     - Query existing default template from database
     - Create test template as part of setup
     - Use template_id from seeded data

### Required Next Steps

**Priority 1: Authentication Solution**

**✅ RECOMMENDED: Use Bot as Authenticated User**

Discord bots ARE Discord users with a token (`DISCORD_TOKEN` in env.e2e). We can:
1. **Use bot's Discord user ID as the authenticated user**
   - Bot token: `YOUR_BOT_TOKEN_HERE.TIMESTAMP.SIGNATURE`
   - Bot's Discord user ID can be extracted from token (first part base64 decoded)
   - Bot is already a member of test guild with all necessary permissions
2. **Create session directly in Valkey (Redis)**
   - Call `tokens.store_user_tokens(bot_discord_id, "dummy_access", "dummy_refresh", 604800)`
   - Returns session_token UUID to use in cookies
   - Simpler than full OAuth flow, but uses real token storage mechanism
3. **Include session_token in API requests**
   - Set `session_token` cookie in test HTTP client
   - API validates session exists in Valkey
   - User record with bot's Discord ID already exists in database (seeded)

**Why This Approach is Best**:
- ✅ **Bot token already available** (`DISCORD_TOKEN` in env/env.e2e)
- ✅ **Bot is real Discord user** with guild membership
- ✅ **No OAuth flow complexity** (no need for authorization code exchange)
- ✅ **Uses real session mechanism** (Valkey storage, not mocking)
- ✅ **Bot has all necessary permissions** (manage channels, send messages)
- ✅ **Idempotent** (can run tests repeatedly without auth expiry)
- ✅ **No API changes needed** (uses existing token storage functions)

**Alternative Approaches Considered (Not Recommended)**:
- Full OAuth flow - Too complex, requires browser automation
- Direct Valkey insertion - Bypasses token functions, may break if format changes
- Test-only endpoint - Requires API changes, security risk if leaked to prod

**Implementation Steps**:
1. Extract bot's Discord user ID from `DISCORD_TOKEN` (base64 decode first segment)
2. Add fixture `authenticated_bot_client` that:
   - Calls `tokens.store_user_tokens(bot_discord_id, "e2e_access", "e2e_refresh", 604800)`
   - Sets session_token cookie in HTTP client
3. Update seed_e2e.py to create user record for bot's Discord ID
4. Use `authenticated_bot_client` in tests instead of plain `http_client`

## Bot Token Authentication Deep Dive

### Discord Bot Token Structure

Discord bot tokens have format: `BASE64_USER_ID.TIMESTAMP.HMAC_SIGNATURE`
- First segment (BASE64_USER_ID): Bot's Discord user ID encoded in base64
- Example: `MTIzNDU2Nzg5MDEyMzQ1Njc4` decodes to `123456789012345678` (placeholder)

**Extracting Bot's Discord User ID**:
```python
import base64
token_parts = DISCORD_TOKEN.split('.')
bot_user_id = base64.b64decode(token_parts[0] + '==').decode('utf-8')
```

### Complete Implementation Code

**1. Extract Bot Discord ID Utility** (not needed - seed can skip this):
```python
# Seed service no longer needs to create guild/channel configs
# They're created via /api/v1/guilds/sync endpoint instead
```

**2. Update Seed Service (services/init/seed_e2e.py)** - Simplified:
```python
async def seed_e2e_data(db_session: AsyncSession):
    """Seed E2E test data - only bot user needed."""
    bot_token = os.environ.get("DISCORD_TOKEN", "")
    bot_discord_id = extract_bot_discord_id(bot_token)

    # Only seed bot user - guild/channels created via sync endpoint
    result = await db_session.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": bot_discord_id}
    )
    if not result.fetchone():
        await db_session.execute(
            text("INSERT INTO users (discord_id) VALUES (:discord_id)"),
            {"discord_id": bot_discord_id}
        )
        print(f"✓ Seeded bot user: {bot_discord_id}")
```

**2. Test Fixtures (tests/e2e/conftest.py)**:
```python
@pytest.fixture
async def admin_bot_discord_id(discord_admin_token):
    """Extract admin bot's Discord user ID from token."""
    return extract_bot_discord_id(discord_admin_token)

@pytest.fixture
async def authenticated_admin_client(http_client, admin_bot_discord_id, discord_admin_token):
    """HTTP client with admin bot authentication."""
    # Create session using admin bot's Discord ID and bot token as access_token
    session_token = await tokens.store_user_tokens(
        user_id=admin_bot_discord_id,
        access_token=discord_admin_token,  # Admin bot token (will be detected as Bot token)
        refresh_token="e2e_admin_refresh",
        expires_in=604800
    )
    http_client.cookies.set("session_token", session_token)
    yield http_client
    await tokens.delete_user_tokens(session_token)

@pytest.fixture(scope="session")
async def synced_guild(authenticated_admin_client):
    """Sync admin bot's guilds to create test configs."""
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response.status_code == 200
    result = response.json()
    print(f"✓ Synced {result['new_guilds']} guilds, {result['new_channels']} channels")
    return result

@pytest.fixture
async def test_guild_id(db_session, synced_guild, discord_guild_id):
    """Get guild config UUID after sync."""
    result = await db_session.execute(
        select(GuildConfiguration).where(
            GuildConfiguration.guild_id == discord_guild_id
        )
    )
    return result.scalar_one().id

@pytest.fixture
async def test_template_id(db_session, test_guild_id):
    """Get default template UUID created by sync."""
    result = await db_session.execute(
        select(GameTemplate).where(
            GameTemplate.guild_id == test_guild_id,
            GameTemplate.is_default.is_(True)
        )
    )
    return result.scalar_one().id
```

### Why Bot Authentication Works

- ✅ Bot IS a Discord user (has user ID, guild membership, permissions)
- ✅ API validates session exists, doesn't verify OAuth tokens in E2E context
- ✅ Bot user seeded in database by init service
- ✅ Matches production flow: session_token cookie → Valkey → user lookup
- ✅ No mocking, no API changes, uses real session mechanism

### Using Admin Bot Token with Guild Sync Endpoint

**Key Insight**: Bot tokens can be distinguished from OAuth tokens and work with Discord API!

- **Bot token format**: `BASE64_ID.TIMESTAMP.SIGNATURE` (3 parts separated by dots)
- **OAuth token format**: Single random string (no dots or different structure)
- **Solution**: Add token type detection to `DiscordAPIClient._get_auth_header()`
  - If token has 3 dot-separated parts → `Authorization: Bot {token}`
  - Otherwise → `Authorization: Bearer {token}`

**Benefits**:
- ✅ Admin bot token works with `/api/v1/guilds/sync` endpoint
- ✅ No OAuth flow needed for E2E tests
- ✅ Tests real production sync path (creates guild/channels/template via service layer)
- ✅ Realistic permission separation (admin bot vs regular bot)
- ✅ General improvement (all DiscordAPIClient methods now support both token types)

**Priority 2: Setup via Guild Sync Endpoint**

Use real production sync path with admin bot token:

**1. Create Admin Bot in Discord Developer Portal**:
- Name: "Game Scheduler E2E Admin Bot"
- Copy bot token → `DISCORD_ADMIN_TOKEN` in env.e2e
- Invite to test guild with `MANAGE_GUILD` permission
- Bot OAuth URL: `https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&scope=bot&permissions=32` (MANAGE_GUILD=32)

**2. Environment Variables**:
```bash
# env/env.e2e
DISCORD_TOKEN=regular_bot_token_here        # Regular bot (message permissions)
DISCORD_ADMIN_TOKEN=admin_bot_token_here    # Admin bot (MANAGE_GUILD)
DISCORD_GUILD_ID=test_guild_id
DISCORD_CHANNEL_ID=test_channel_id
DISCORD_USER_ID=test_user_id
```

**3. Add Bot Token Detection (shared/discord/client.py)**:
```python
def _get_auth_header(self, token: str) -> str:
    """Detect token type and return appropriate Authorization header."""
    # Bot tokens: BASE64_ID.TIMESTAMP.SIGNATURE (3 parts)
    is_bot_token = len(token.split('.')) == 3
    return f"Bot {token}" if is_bot_token else f"Bearer {token}"
```

**4. Update all Discord API calls to use helper**:
```python
# Replace hardcoded f"Bearer {access_token}" with:
headers={"Authorization": self._get_auth_header(access_token)}
```

**Why This Approach**:
- ✅ Tests real production sync path
- ✅ Admin bot has appropriate permissions (MANAGE_GUILD)
- ✅ Regular bot keeps minimal permissions (production-realistic)
- ✅ No manual config seeding needed
- ✅ Service layer creates everything correctly
- ✅ Bot token detection improves entire codebase
- ✅ More realistic end-to-end testing

**Priority 3: Complete Game Announcement Test**

Once authentication and sync resolved:
1. Admin bot syncs guild (creates configs)
2. Test authenticates as admin bot
3. Include template_id in game creation request
4. Validate 201 response and proceed with Discord verification
5. Complete remaining assertions (embed content, fields, etc.)

### Complete Implementation Code

**1. Update Seed Service (services/init/seed_e2e.py)** - Seed admin bot user only:
```python
import base64
from sqlalchemy import select
from shared.models.user import User

def extract_bot_discord_id(bot_token: str) -> str:
    """Extract Discord user ID from bot token."""
    token_parts = bot_token.split('.')
    encoded_id = token_parts[0]
    padding = 4 - (len(encoded_id) % 4)
    if padding != 4:
        encoded_id += '=' * padding
    return base64.b64decode(encoded_id).decode('utf-8')

async def seed_e2e_data(db_session: AsyncSession):
    """Seed E2E test data - admin bot user only."""
    # Seed admin bot user (used for guild sync)
    admin_bot_discord_id = extract_bot_discord_id(os.environ["DISCORD_ADMIN_TOKEN"])

    result = await db_session.execute(
        select(User).where(User.discord_id == admin_bot_discord_id)
    )
    if not result.scalar_one_or_none():
        admin_bot_user = User(discord_id=admin_bot_discord_id)
        db_session.add(admin_bot_user)
        await db_session.commit()
        print(f"✓ Seeded admin bot user: {admin_bot_discord_id}")

    # Note: Guild/channel/template configs created via /api/v1/guilds/sync in tests
```

**2. Test Fixtures (tests/e2e/conftest.py)**:
```python
@pytest.fixture
async def admin_bot_discord_id(discord_admin_token):
    """Extract admin bot's Discord user ID from token."""
    return extract_bot_discord_id(discord_admin_token)

@pytest.fixture
async def authenticated_admin_client(http_client, admin_bot_discord_id, discord_admin_token):
    """HTTP client with admin bot authentication."""
    # Create session using admin bot's Discord ID and bot token as access_token
    session_token = await tokens.store_user_tokens(
        user_id=admin_bot_discord_id,
        access_token=discord_admin_token,  # Admin bot token (will be detected as Bot token)
        refresh_token="e2e_admin_refresh",
        expires_in=604800
    )
    http_client.cookies.set("session_token", session_token)
    yield http_client
    await tokens.delete_user_tokens(session_token)

@pytest.fixture(scope="session")
async def synced_guild(authenticated_admin_client):
    """Sync admin bot's guilds to create test configs."""
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response.status_code == 200
    result = response.json()
    print(f"✓ Synced {result['new_guilds']} guilds, {result['new_channels']} channels")
    return result

@pytest.fixture
async def test_guild_id(db_session, synced_guild, discord_guild_id):
    """Get guild config UUID after sync."""
    result = await db_session.execute(
        select(GuildConfiguration).where(
            GuildConfiguration.guild_id == discord_guild_id
        )
    )
    return result.scalar_one().id

@pytest.fixture
async def test_template_id(db_session, test_guild_id):
    """Get default template UUID created by sync."""
    result = await db_session.execute(
        select(GameTemplate).where(
            GameTemplate.guild_id == test_guild_id,
            GameTemplate.is_default.is_(True)
        )
    )
    return result.scalar_one().id
```
    row = result.fetchone()
    if not row:
        pytest.fail("Default template not found - seed may have failed")
    return row[0]

# Update test function signature
async def test_game_creation_posts_announcement_to_discord(
    authenticated_client,  # Changed from http_client
    db_session,
    discord_helper,
    test_guild_id,
    test_channel_id,
    test_host_id,
    test_template_id,  # Added
    discord_channel_id,
    discord_user_id,
    clean_test_data,
):
    # Update game_data to include template_id
    game_data = {
        "template_id": test_template_id,  # Added
        "title": game_title,
        # ... rest of fields
    }

    # Rest of test unchanged - authentication handled by fixture
```

### Technical Debt / Known Issues

1. **AsyncClient API change**: Old tests in test_guild_template_api.py used `AsyncClient(app=app)` which is no longer valid in current httpx version
   - Solution: Removed old broken tests, using httpx.Client() for new tests

2. **Environment Variable Naming**: Initial confusion between TEST_DISCORD_* and DISCORD_* variable names
   - Solution: Standardized on DISCORD_* throughout (compose, tests, seed service)

3. **Telemetry Noise**: Init service was sending OpenTelemetry data during tests, causing errors
   - Solution: Set PYTEST_RUNNING=1 in compose.e2e.yaml to disable telemetry

4. **Duplicate Fixtures**: Both conftest.py and test file defined same fixtures causing conflicts
   - Solution: Moved all fixtures to conftest.py as single source of truth

### Files Modified/Created

**Created**:
- `tests/e2e/conftest.py` - Pytest fixtures for E2E tests
- `tests/e2e/test_00_environment.py` - Environment validation tests (7 passing)
- `tests/e2e/helpers/discord.py` - DiscordTestHelper for message verification
- `services/init/seed_e2e.py` - E2E test data seeding

**Modified**:
- `compose.e2e.yaml` - Environment variables, PYTEST_RUNNING flag
- `scripts/run-e2e-tests.sh` - Variable name updates (DISCORD_* not TEST_DISCORD_*)
- `tests/e2e/test_game_announcement.py` - Test structure, fixtures, API endpoint path
- `services/init/main.py` - Integration of seed_e2e_data() call

**Removed**:
- `tests/e2e/test_guild_template_api.py` - Old broken integration test
- `tests/e2e/test_game_notification_api_flow.py` - Database-focused test (not true E2E)

### Test Execution Results

**Current Status: 7/8 tests passing** (87.5% passing)

```
tests/e2e/test_00_environment.py::test_environment_variables PASSED
tests/e2e/test_00_environment.py::test_discord_bot_can_connect PASSED
tests/e2e/test_00_environment.py::test_discord_guild_exists PASSED
tests/e2e/test_00_environment.py::test_discord_channel_exists PASSED
tests/e2e/test_00_environment.py::test_discord_user_exists PASSED
tests/e2e/test_00_environment.py::test_database_seeded PASSED
tests/e2e/test_00_environment.py::test_api_accessible PASSED
tests/e2e/test_game_announcement.py::test_game_creation_posts_announcement_to_discord FAILED
```

**Failure Details**:
```
AssertionError: Failed to create game: {
  "error":"validation_error",
  "message":"Invalid request data",
  "details":[
    {"field":"cookie.session_token","message":"Field required","type":"missing"},
    {"field":"body.template_id","message":"Field required","type":"missing"}
  ]
}
assert 422 == 201
```

### Summary

**Achievements**:
- ✅ Complete E2E test infrastructure established
- ✅ Environment validation tests all passing
- ✅ Discord test helper fully functional
- ✅ Database seeding working correctly
- ✅ Docker compose configuration optimized
- ✅ Clean, noise-free test output

**Remaining Work**:
- 🔴 Implement authentication for E2E tests (blocking)
- 🔴 Add template seeding/lookup (blocking)
- 🟡 Complete game announcement test with Discord verification
- 🟡 Implement remaining Phase 2-4 test scenarios
- 🟡 Document authentication approach in TESTING_E2E.md

**Estimated Effort to Complete Phase 1**:
- Authentication solution: 1-2 hours (research + implementation)
- Template seeding: 30 minutes (add to seed_e2e.py)
- Complete announcement test: 1 hour (finish assertions, debug)
- Total: ~3-4 hours to have first true E2E test passing

## Refactor Completion Update (December 22, 2025)

### ✅ Discord Client Token Unification - COMPLETE

**Refactor Successfully Implemented:**
- Commit: `0d70d93` "Unify Discord API client token handling for bot and OAuth"
- All pre-commit hooks passing
- All 52 Discord client unit tests passing
- All 791 unit tests passing

**Key Changes Verified:**
1. **`shared/discord/client.py:_get_auth_header()`**
   - ✅ Automatic token type detection implemented
   - ✅ Bot tokens (2 dots) → `"Bot {token}"`
   - ✅ OAuth tokens (1 dot) → `"Bearer {token}"`
   - ✅ Invalid tokens rejected with clear error message

2. **`shared/discord/client.py:get_guilds(token, user_id)`**
   - ✅ Unified method replacing `get_bot_guilds()` and `get_user_guilds()`
   - ✅ Works with both token types via automatic detection
   - ✅ Merged caching logic from separate implementations
   - ✅ Supports implicit (default bot token) and explicit (OAuth) usage

3. **`services/api/auth/oauth2.py:get_user_guilds()`**
   - ✅ Updated to call `discord.get_guilds(token=access_token, user_id=user_id)`
   - ✅ Uses unified interface, no longer calls removed method

4. **`services/api/auth/roles.py:has_permissions()`**
   - ✅ Updated to call `self.discord_client.get_guilds(token=access_token, user_id=user_id)`
   - ✅ Uses unified interface, no longer calls removed method

5. **Test Suite**
   - ✅ 52 Discord client tests all passing
   - ✅ 8 OAuth2 tests all passing
   - ✅ 14 roles tests all passing
   - ✅ 33 API auth tests all passing
   - ✅ No type errors (mypy: 125 files checked)
   - ✅ Code properly formatted (ruff)

### Ready to Resume E2E Work

**Blocking Issues Resolved:**
- ✅ Token type detection now built into `DiscordAPIClient`
- ✅ Can use bot tokens directly with Discord API endpoints
- ✅ OAuth tokens work seamlessly alongside bot tokens
- ✅ No need to distinguish token types at call site

**Next Steps for E2E Test Implementation:**

**Immediate (Phase 1 - Core Authentication):**
1. Extract bot Discord ID from `DISCORD_TOKEN` (base64 decode first segment)
2. Create `authenticated_admin_client` fixture using bot token
   - Call `tokens.store_user_tokens()` with bot token as access_token
   - Set session_token cookie in HTTP client
   - This provides API authentication for E2E tests
3. Update `seed_e2e.py` to seed admin bot user (if needed)
4. Add `synced_guild` fixture to call `/api/v1/guilds/sync`
   - Uses admin bot token to discover test guild
   - Creates guild_configurations, channel_configurations, default template
   - Returns config IDs for use in game creation tests

**Phase 2 - Complete First Test:**
1. Update `test_game_announcement.py` to use authenticated client
2. Include `template_id` in game creation request
3. Validate game created successfully (201 response)
4. Verify Discord announcement message posted
5. Complete embed content validation

**Phase 3 - Remaining Scenarios:**
1. Game update → message refresh
2. User joins → participant list update
3. Game reminder → DM verification
4. Game deletion → message removed
5. Advanced: Role mentions, waitlist, status transitions

### Implementation Pattern Established

The unified token handling enables a clean pattern for E2E tests:

```python
# In E2E tests, use admin bot token directly for both:
# 1. Session creation (pass as access_token)
# 2. Guild sync (automatically detected as bot token by _get_auth_header())

session_token = await tokens.store_user_tokens(
    user_id=bot_discord_id,
    access_token=bot_token,  # Token type auto-detected internally
    refresh_token="e2e_refresh",
    expires_in=604800
)

# Set cookie for API authentication
http_client.cookies.set("session_token", session_token)

# API calls now work without explicit token handling
response = await http_client.post("/api/v1/games", json=game_data)
```

### Architecture Insight

The refactor validates a key architectural insight:
- **Discord API accepts both token types** for appropriate endpoints
- **Bot tokens** have system-level permissions and full API access
- **OAuth tokens** have user-level permissions and scoped access
- **Single unified interface** simplifies code and enables flexible authentication

This unlocks the E2E testing pattern:
- Admin bot for setup (guild sync, configs)
- Regular bot for operations (message posting, DM sending)
- No OAuth complexity for E2E (bot tokens sufficient)
- Real production simulation (both auth types tested)

### Status Summary

**Refactoring Phase: COMPLETE ✅**
- Token unification implemented and tested
- All changes committed and pushed
- Code quality verified (linting, typing, tests)
- Ready for E2E development to resume

**E2E Testing Phase: READY TO BEGIN 🚀**
- Infrastructure in place (fixtures, helpers, Docker setup)

## Waitlist Promotion Test Implementation (December 24, 2025)
⚠️ Test Implemented: test_waitlist_promotion.py - AWAITING VALIDATION

**Status**: Implementation complete, bug fix applied, **validation pending**
**Status**: Implementation complete, awaiting validation

**Test File**: `tests/e2e/test_waitlist_promotion.py`

**Test Structure**:
- Parametrized test with 2 promotion scenarios:
  1. **via_removal**: User promoted when placeholder participant removed
  2. **via_max_players_increase**: User promoted when max_players increased

**Test Flow**:
1. Create game with placeholder participant in confirmed slot
2. Add test user as second participant (goes to overflow)
3. Verify initial Discord message shows user in overflow
4. Trigger promotion:
   - Scenario 1: Remove placeholder participant
   - Scenario 2: Increase max_players from 1 to 2
5. Verify updated Discord message shows user promoted to confirmed
6. **Verify test user receives promotion DM** with expected content:
   - "A spot opened up"
   - "moved from the waitlist"
   - Game title, scheduled time, host

**Key Implementation Details**:

**Fixtures Used**:
- `main_bot_helper` - Uses main bot token (sends notification DMs, not admin bot)
- `authenticated_admin_client` - Admin bot authentication for API calls
- `synced_guild` - Guild sync creates configs and default template
- `test_guild_id`, `test_template_id` - Database IDs from synced resources
- `clean_test_data` - Removes game data before/after test

**Helper Functions**:
```python
async def trigger_promotion_via_removal(client, db, game_id, placeholder_id) -> str:
    """Remove placeholder to trigger promotion."""

async def trigger_promotion_via_max_players_increase(client, game_id) -> str:
    """Increase max_players to trigger promotion."""

async def verify_promotion_dm_received(helper, user_id, game_title) -> bool:
    """Check DM history for promotion message."""
```

**Promotion Detection Bug Discovered**:
While implementing this test, discovered that promotion detection was broken when placeholder participants occupied confirmed slots.

**Bug**: Original code filtered placeholders BEFORE determining overflow position, but `max_players` applies to ALL participants. This caused real users to appear "confirmed" even when placeholders occupied those slots.

**Fix Applied**: Implemented architectural solution with centralized `partition_participants()` utility in `shared/utils/participant_sorting.py`:
- Includes ALL participants (placeholders + real users) when sorting
- Partitions into confirmed/overflow by position in sorted list
- Filters to real user IDs AFTER partitioning
- Provides `cleared_waitlist()` method to detect promotions

**Implementation**:
```python
# services/api/services/games.py::update_game()
old_partitioned = partition_participants(game.participants, old_max_players)
# ... updates happen ...
new_partitioned = partition_participants(game.participants, new_max_players)
promoted_discord_ids = new_partitioned.cleared_waitlist(old_partitioned)
```

### Validation Status

**Test Status**: ⚠️ NOT YET VALIDATED
- Test implementation: ✅ Complete
- Bug fix implementation: ✅ Complete
- Test execution: ❌ Not run since bug fix
- **MUST RUN** to verify promotion detection works correctly

**Critical Validation Step Required**:
The test was created to expose the promotion detection bug. The bug has been fixed with the `partition_participants()` utility, but we must validate that:
1. The test now passes (promotion DMs are sent)
2. Both scenarios work correctly (via_removal and via_max_players_increase)
3. No regressions were introduced by the fix

**Run Command**:
```bash
./scripts/run-e2e-tests.sh tests/e2e/test_waitlist_promotion.py -v
```

**Expected Output** (if fix is correct):
- ✅ Both parametrized tests pass (via_removal, via_max_players_increase)
- ✅ Debug output shows promotion DM received
- ✅ Message contains: "A spot opened up", "moved from the waitlist"

**Possible Failure Scenarios** (if issues remain):
- ❌ No promotion DM received (promotion detection still broken)
- ❌ Wrong user promoted (logic error in `cleared_waitlist()`)
- ❌ DM sent but missing expected content (formatter issue)
- ❌ Timeout waiting for DM (timing/daemon issue)

### Next Steps

**IMMEDIATE ACTION REQUIRED**:
1. Run the E2E test to validate the fix
2. If test passes → mark as ✅ COMPLETE and proceed to next test
3. If test fails → debug the remaining issue, update fix, re-test

### Related Documentation

**Bug Analysis**: `.copilot-tracking/research/20251224-promotion-detection-bug.md`
- Complete root cause analysis
- Before/after code comparison
- Architectural solution details
- Migration status for remaining code locations

**Resume Instructions**: `.copilot-tracking/research/20251224-resume-after-promotion-fix.md`
- Context restore after git history rewrite
- Verification steps
- Next steps for test completion

### Next Test Priority

**AFTER validation of waitlist promotion test**, next priority is:

**Test 5.4: Join Notification → Delayed DM** (from original plan)
- Create game with signup instructions
- User joins game
- Verify delayed DM sent after 60 seconds with signup instructions
- Validates: API → Database → Notification Daemon → Bot (join_notification path)
- File: `tests/e2e/test_join_notification.py`

This completes testing of the second notification_type (join_notification vs reminder).

### Coverage Update

**Phase 2 - Notification System Completeness**:
- ⚠️ **Test 4: Waitlist Promotion** (IMPLEMENTED - AWAITING VALIDATION)
- ❌ **Test 5: Join Notification** (BLOCKED until Test 4 validated)

**Updated Stats** (pending validation):
- Pattern 1 (Immediate API Events): 2/5 validated, 1/5 implemented (40% validated, 60% in progress)
- Pattern 2 (Notification Daemon): 1/2 tested (50%)
- Pattern 3 (Status Daemon): 0/1 tested (0%)
- **Overall Progress**: 3/8 core paths validated, 1/8 awaiting validation (37.5% validated)
- Blocking issues resolved (authentication pattern established)
- Clear implementation path forward
- All supporting systems operational
