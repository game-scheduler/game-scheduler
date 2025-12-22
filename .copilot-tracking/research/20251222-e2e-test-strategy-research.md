<!-- markdownlint-disable-file -->
# Task Research Notes: E2E Test Strategy

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
5. **Game Deletion → Message Removed**
   - Create game, delete via API
   - Verify Discord message deleted from channel

**Advanced Scenarios** (Later):
6. **Role Mentions in Announcement** - Verify role mention in message.content triggers notifications
7. **Waitlist Promotion** - User moves from overflow to participant, receives DM
8. **Game Status Transitions** - Message updates when game moves scheduled → in_progress → completed
9. **Multiple Games in Channel** - Verify correct message updated when multiple games exist
10. **Permission Boundaries** - Non-host cannot edit game, button reflects disabled state

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
