# End-to-End Testing Setup

This guide explains how to set up and run true end-to-end tests that validate Discord bot behavior and message content.

## Overview

End-to-end tests verify the complete system flow from API calls through to Discord message delivery:

1. **API Creates Game** → publishes GAME_CREATED event → **Bot posts announcement to Discord channel**
2. **API Updates Game** → publishes GAME_UPDATED event → **Bot edits Discord message**
3. **User Joins Game** → API updates participants → **Bot refreshes participant list in Discord**
4. **Notification Daemon** → processes scheduled reminders → **Bot sends DM to participants**
5. **Status Daemon** → processes status transitions → **Bot updates game status in Discord**

These tests use the **DiscordTestHelper** to read and verify actual Discord messages, ensuring that users see correct information in their Discord channels.

## Why a Separate Test Discord Guild?

Using a dedicated test guild ensures:

- ✅ Test messages don't spam your production or development guilds
- ✅ Hermetic isolation from other environments
- ✅ Safe to run destructive test scenarios
- ✅ Reproducible test conditions
- ✅ Can be automated in CI/CD pipelines with dedicated test credentials

## Setup Steps

### 1. Create Test Discord Bots

You need **two bots** for E2E testing:

#### Main Bot (Message Sending)

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "Game Scheduler Test Bot"
4. Go to "Bot" section and click "Add Bot"
5. **Enable Privileged Intents:**
   - SERVER MEMBERS INTENT (required)
   - MESSAGE CONTENT INTENT (required for reading message content in tests)
6. Copy the **Bot Token** - this becomes `DISCORD_BOT_TOKEN`

#### Admin Bot (Guild Management)

1. Create another application: "Game Scheduler Test Admin Bot"
2. Add bot and copy the token - this becomes `DISCORD_ADMIN_BOT_TOKEN`
3. Copy **Application ID** from General Information - this becomes `DISCORD_ADMIN_BOT_CLIENT_ID`
4. Generate client secret under OAuth2 → Client Secret - this becomes `DISCORD_ADMIN_BOT_CLIENT_SECRET`

**Why two bots?**
- **Main bot**: Sends game announcements and DMs (MESSAGE_CONTENT intent required)
- **Admin bot**: Used by tests for authentication and guild sync (no privileged intents needed)

### 2. Create a Test Discord Guild (Server)

1. In Discord, create a new server
2. Name it "Game Scheduler Test" (or similar)
3. **Keep it private** - don't invite real users
4. **Enable Developer Mode**: Settings → Advanced → Developer Mode
5. Right-click the server name → "Copy Server ID" - this becomes `DISCORD_GUILD_ID`

### 3. Create a Test Channel

1. In your test guild, create a text channel named "test-games" (or similar)
2. Right-click the channel → "Copy Channel ID" - this becomes `DISCORD_CHANNEL_ID`

### 4. Invite Both Bots to Test Guild

#### Invite Main Bot

Generate OAuth2 invite URL:

1. In Developer Portal, go to bot's "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select bot permissions (required):
   - **View Channels** (read channel list)
   - **Send Messages** (post game announcements)
   - **Send Messages in Threads** (post in threads)
   - **Embed Links** (rich game embeds)
   - **Attach Files** (game images)DM test assertions)

1. In Discord, ensure Developer Mode is enabled (step 2.4)
2. Right-click your username → "Copy User ID" - this becomes `DISCORD_USER_ID`
3. **Join the test guild** with this account (used for DM verification in tests)
4. Optionally, create additional test user accounts for multi-user scenarios
#### Invite Admin Bot

1. Generate OAuth2 URL for admin bot with same permissions
2. Additionally grant **Manage Server** permission (required for guild sync in tests)
3. Invite to test guild and authorize

### 5. Get Your Discord User ID (for test assertions)

1. In Discord, enable Developer Mode: Settings → Advanced → Developer Mode
2. Right-click your username → "Copy User ID" - this becomes `TEST_DISCORD_USER_ID`
3. Optionally, create additional test user accounts if needed

### 6. (Optional) Set Up Guild B for Cross-Guild Isolation Tests

To test guild isolation features (ensuring users can only see data from their own guilds):

1. **Create a second test guild** named "Game Scheduler Test B"
2. **Create a channel** in Guild B and get its ID → `DISCORD_GUILD_B_ID` and `DISCORD_CHANNEL_B_ID`
3. **Create a second test user** (different from User A)
   - Right-click username → "Copy User ID" → `DISCORD_USER_B_ID`
   - Get OAuth token for User B → `DISCORD_USER_B_TOKEN`
4. **Important:** User B should be a member of Guild B ONLY (not Guild A)
5. Invite both bots to Guild B with same permissions as Guild A

**When to skip:** If not testing guild isolation features, leave these environment variables unset.

### 7. Configure Environment Variables

The project uses environment files in the `env/` directory. Update the test environment files:

#### `env/env.int` (for integration tests - no Discord required)

```bash
# Compose file configuration
COMPOSE_FILE=compose.yaml:compose.int.yaml

# Infrastructure settings
CONTAINER_PREFIX=gamebot-integration
POSTGRES_USER=gamebot_integration
POSTGRES_PASSWORD=integration_password
POSTGRES_DB=game_scheduler_integration
POSTGRES_HOST_PORT=5434
RABBITMQ_DEFAULT_USER=gamebot_integration
RABBITMQ_DEFAULT_PASS=integration_password
RABBITMQ_HOST_PORT=5674
RABBITMQ_MGMT_HOST_PORT=15674
REDIS_HOST_PORT=6381
DATABASE_URL=postgresql://gamebot_integration:integration_password@postgres:5432/game_scheduler_integration
RABBITMQ_URL=amqp://gamebot_integration:integration_password@rabbitmq:5672/
REDIS_URL=redis://redis:6379/0
TEST_ENVIRONMENT=true
```
s)

```bash
# Compose file configuration
COMPOSE_FILE=compose.yaml:compose.e2e.yaml

# Infrastructure settings
CONTAINER_PREFIX=gamebot-e2e
POSTGRES_USER=gamebot_e2e
POSTGRES_PASSWORD=e2e_password
POSTGRES_DB=game_scheduler_e2e
POSTGRES_HOST_PORT=5433
RABBITMQ_DEFAULT_USER=gamebot_e2e
RABBITMQ_DEFAULT_PASS=e2e_password
RABBITMQ_HOST_PORT=5673
RABBITMQ_MGMT_HOST_PORT=15673
REDIS_HOST_PORT=6380
DATABASE_URL=postgresql://gamebot_e2e:e2e_password@postgres:5432/game_scheduler_e2e
RABBITMQ_URL=amqp://gamebot_e2e:e2e_password@rabbitmq:5672/
REDIS_URL=redis://redis:6379/0

# Main Bot Configuration (MESSAGE_CONTENT intent required)
DISCORD_BOT_TOKEN=your_main_bot_token_here

# Admin Bot Configuration (used for test authentication)
DISCORD_ADMIN_BOT_TOKEN=your_admin_bot_token_here
DISCORD_ADMIN_BOT_CLIENT_ID=your_admin_bot_client_id_here
DISCORD_ADMIN_BOT_CLIENT_SECRET=your_admin_bot_client_secret_here

# Test Discord Environment IDs
DISCORD_GUILD_ID=123456789012345678
DISCORD_CHANNEL_ID=123456789012345678
DISCORD_CHANNEL_ID=123456789012345678
TEST_DISCORD_USER_ID=123456789012345678

# Optional: Guild B and User B for cross-guild isolation testing
# User B must be a member of Guild B ONLY (not Guild A)
# Leave commented if not testing cross-guild isolation
# DISCORD_GUILD_B_ID=987654321098765432
# DISCORD_CHANNEL_B_ID=987654321098765432
# DISCORD_USER_B_ID=987654321098765432
# DISCORD_USER_B_TOKEN=your_user_b_bot_token_here

TEST_ENVIRONMENT=true
API_HOST_PORT=8001
FRONTEND_HOST_PORT=3001
```

**Note:** The `COMPOSE_FILE` variable in each env file specifies which compose files Docker Compose will load. This eliminates the need for explicit `-f` flags in commands.

## Running Tests

### Integration Tests (No Discord Required)

Test notification daemon and PostgreSQL LISTEN/NOTIFY without Discord:

```bash
./scripts/run-integration-tests.sh
```

Or manually:

```bash
# The COMPOSE_FILE variable in env/env.int specifies compose.yaml:compose.int.yaml
docker compose --env-file env/env.int --profile integration up \
  --build --abort-on-container-exit
```

### End-to-End Tests (Requires Test Discord Setup)

Test complete flow including Discord bot interactions:

```bash
./scripts/run-e2e-tests.sh
```

Run specific test file:

```bash
docker compose --env-file env/env.e2e run --rm e2e-tests tests/e2e/test_game_announcement.py -v
```

Run specific test function:

```bash
docker compose --env-file env/env.e2e run --rm e2e-tests tests/e2e/test_game_announcement.py::test_game_creation_posts_announcement_to_discord -v
```

### Test Execution Times

E2E tests vary in duration based on what they're testing:

- **Quick tests** (2-5 seconds): Game creation, updates, cancellation
- **Medium tests** (10-30 seconds): Participant joins, waitlist promotion
- **Long tests** (2-5 minutes): Reminders, status transitions (wait for daemon polling)

**Why some tests are slow:**
- Notification daemon polls database every 60 seconds
- Status transition daemon polls every 60 seconds
- Tests must wait for real time to pass (scheduled game times)
- Discord API rate limits require spacing between operations

**Full test suite:** ~8-12 minutes (includes daemon wait times)

## E2E Test Architecture

### Test Fixtures and Helpers

#### Authentication (`authenticated_admin_client`)

E2E tests authenticate using the admin bot token:

```python
async def test_game_creation(authenticated_admin_client, db_session):
    # authenticated_admin_client has session_token cookie set
    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
```

**How it works:**
1. Admin bot's Discord user ID extracted from token
2. Session created in Valkey/Redis with bot's ID
3. HTTP client cookie set with session_token
4. API validates session exists (treats bot as authenticated user)

#### Guild Sync (`synced_guild`)

Tests use pre-seeded guild/channel configurations:

```python
async def test_game_creation(synced_guild, test_guild_id, test_channel_id):
    # synced_guild fixture called /api/v1/guilds/sync
    # test_guild_id and test_channel_id are now available
```

**What happens:**
1. Init service seeds admin bot user in database
2. `synced_guild` fixture calls guild sync endpoint with admin bot auth
3. Guild/channel configurations created via API (production code path)
4. Default template created for the guild

#### Discord Helper (`discord_helper`, `main_bot_helper`)

Two helper instances for different purposes:

```python
async def test_game_creation(discord_helper, main_bot_helper):
    # discord_helper - uses admin bot token (for reading channel messages)
    message = await discord_helper.get_message(channel_id, message_id)

    # main_bot_helper - uses main bot token (for reading DMs sent by main bot)
    dms = await main_bot_helper.get_user_recent_dms(user_id)
```

**DiscordTestHelper API:**

```python
# Fetch specific message
message = await helper.get_message(channel_id, message_id)

# Find message by embed title
message = await helper.find_message_by_embed_title(channel_id, "Game Title")

# Get recent DMs sent to user
dms = await helper.get_user_recent_dms(user_id, limit=10)

# Find specific game reminder DM
reminder = await helper.find_game_reminder_dm(user_id, "Game Title")

# Verify embed structure
helper.verify_game_embed(embed, "Expected Title", "123456", max_players=4)

# Extract embed field value
host_value = helper.extract_embed_field_value(embed, "🎯 Host")
```

### Test Data Management

#### Database Cleanup (`clean_test_data`)

Each test cleans up its game data:

```python
@pytest.fixture
async def clean_test_data(db_session):
    yield
    # After test: delete game_sessions and related data
    await db_session.execute(text("DELETE FROM game_sessions WHERE title LIKE 'E2E%'"))
```

**Guild/channel configurations persist** across tests (created once by init service).

#### Unique Game Titles

Tests use unique titles to avoid conflicts:

```python
game_title = f"E2E Test {uuid4().hex[:8]}"
```

### Timing and Synchronization

#### Wait for Message Creation

```python
# Poll database for message_id (bot sets after posting)
for attempt in range(10):
    result = db_session.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :id"),
        {"id": game_id}
    )
    message_id = result.scalar_one()
    if message_id:
        break
    await asyncio.sleep(0.5)

# Now fetch from Discord
message = await discord_helper.get_message(channel_id, message_id)
```

#### Wait for Scheduled Notifications

```python
# Create game with 1 minute reminder
scheduled_at = datetime.now(UTC) + timedelta(minutes=2)
reminder_minutes = [1]

# Wait up to 150 seconds for notification daemon
max_wait = 150
check_interval = 5

for elapsed in range(0, max_wait, check_interval):
    dms = await main_bot_helper.get_user_recent_dms(user_id)
    reminder = await main_bot_helper.find_game_reminder_dm(user_id, game_title)
    if reminder:
        break
    await asyncio.sleep(check_interval)
```

**Why 150 seconds:**
- 60s scheduled time + 60s daemon polling interval + 30s margin

#### Wait for Status Transitions

```python
# Game scheduled 1 min in future, 2 min duration
scheduled_at = datetime.now(UTC) + timedelta(minutes=1)
expected_duration_minutes = 2

# Wait for IN_PROGRESS transition
for elapsed in range(0, 150, 5):
    status = db_session.execute(
        text("SELECT status FROM game_sessions WHERE id = :id"),
        {"id": game_id}
    ).scalar_one()
    if status == "IN_PROGRESS":
        break
    await asyncio.sleep(5)
```

## Test Environment Isolation

The project uses environment-controlled Docker Compose configuration for each test type:

- **`compose.yaml`**: Base configuration shared by all environments
- **`compose.int.yaml`**: Integration test overrides (postgres, rabbitmq, redis only)
- **`compose.e2e.yaml`**: E2E test overrides (full stack with Discord bot)
- **`env/env.int`**: Integration test environment (sets `COMPOSE_FILE=compose.yaml:compose.int.yaml`)
- **`env/env.e2e`**: E2E test environment (sets `COMPOSE_FILE=compose.yaml:compose.e2e.yaml`)

Different configurations for each test type:

| Aspect           | Integration Tests            | E2E Tests            |
| ---------------- | ---------------------------- | -------------------- |
| Database         | `game_scheduler_integration` | `game_scheduler_e2e` |
| Network          | `gamebot-integration-*`      | `gamebot-e2e-*`      |
| Containers       | `gamebot-integration-*`      | `gamebot-e2e-*`      |
| Ports            | 5434, 5674, 6381             | 5433, 5673, 6380     |
| Discord Required | No                           | Yes                  |

Both test environments can run simultaneously without conflicts since they use separate networks, databases, and host ports.

## Test Data Cleanup

All test data is automatically cleaned up:

- **Integration tests**: Use database fixtures with rollback
- **E2E tests**: Each test creates/deletes its own games
- **After test run**: `docker compose down -v` removes all volumes

## CI/CD Integration

### Recommended Strategy: Manual E2E Execution

E2E tests require external Discord resources (live guilds, bots, channels) which makes them unsuitable for standard CI/CD automation:

✅ **Recommended:** Run E2E tests manually before releases
❌ **Not Recommended:** Automate E2E tests in standard CI pipelines

**Why manual execution:**
- Requires real Discord infrastructure (guilds, bots with specific permissions)
- Tests take 8-12 minutes due to real-time waiting (daemon polling intervals)
- Discord API rate limits can cause flakiness in busy CI environments
- Sensitive bot tokens must be managed as secrets
- Test guild state can accumulate over runs if not properly cleaned

### Alternative: Conditional CI Execution

If automated E2E testing is required, use conditional execution:

```yaml
name: E2E Tests (Manual/Conditional)

on:
  workflow_dispatch:  # Manual trigger only
    inputs:
      run_e2e_tests:
        description: 'Run E2E Tests'
        required: true
        default: 'false'
        type: choice
        options:
          - 'true'
          - 'false'

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    if: ${{ github.event.inputs.run_e2e_tests == 'true' }}

    steps:
      - uses: actions/checkout@v4

      - name: Create E2E Environment File
        run: |
          cat > env/env.e2e << EOF
          COMPOSE_FILE=compose.yaml:compose.e2e.yaml
          CONTAINER_PREFIX=gamebot-e2e
          POSTGRES_USER=gamebot_e2e
          POSTGRES_PASSWORD=e2e_password
          POSTGRES_DB=game_scheduler_e2e
          DATABASE_URL=postgresql://gamebot_e2e:e2e_password@postgres:5432/game_scheduler_e2e
          RABBITMQ_URL=amqp://gamebot_e2e:e2e_password@rabbitmq:5672/
          REDIS_URL=redis://redis:6379/0

          # Bot tokens from GitHub secrets
          DISCORD_BOT_TOKEN=${{ secrets.DISCORD_BOT_TOKEN }}
          DISCORD_ADMIN_BOT_TOKEN=${{ secrets.DISCORD_ADMIN_BOT_TOKEN }}
          DISCORD_ADMIN_BOT_CLIENT_ID=${{ secrets.DISCORD_ADMIN_BOT_CLIENT_ID }}
          DISCORD_ADMIN_BOT_CLIENT_SECRET=${{ secrets.DISCORD_ADMIN_BOT_CLIENT_SECRET }}

          # Test environment IDs from secrets
          DISCORD_GUILD_ID=${{ secrets.DISCORD_GUILD_ID }}
          DISCORD_CHANNEL_ID=${{ secrets.DISCORD_CHANNEL_ID }}
          DISCORD_USER_ID=${{ secrets.DISCORD_USER_ID }}

          TEST_ENVIRONMENT=true
          EOF

      - name: Run E2E Tests
        run: ./scripts/run-e2e-tests.sh
        timeout-minutes: 20  # Allow time for daemon waits

      - name: Cleanup
        if: always()
        run: docker compose --env-file env/env.e2e down -v
```

**Required GitHub Secrets:**
- `DISCORD_BOT_TOKEN` - Main bot token (MESSAGE_CONTENT intent)
- `DISCORD_ADMIN_BOT_TOKEN` - Admin bot token
- `DISCORD_ADMIN_BOT_CLIENT_ID` - Admin bot application ID
- `DISCORD_ADMIN_BOT_CLIENT_SECRET` - Admin bot client secret
- `DISCORD_GUILD_ID` - Test guild snowflake
- `DISCORD_CHANNEL_ID` - Test channel snowflake
- `DISCORD_USER_ID` - Test user snowflake

### Standard CI: Integration Tests Only

For regular CI pipelines, run only integration tests (no Discord required):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Integration Tests
        run: ./scripts/run-integration-tests.sh
```

Integration tests verify:
- Database notification schedule operations
- RabbitMQ event publishing/consumption
- PostgreSQL LISTEN/NOTIFY triggers
- Notification daemon scheduling logic

But do NOT verify:
- Discord message content
- DM delivery
- Embed formatting
- Discord API interactions

## Troubleshooting

### Bot doesn't connect to test guild

**Symptoms:** Tests fail with "Guild not found" or timeout errors

**Solutions:**
- Verify bot token is correct in `env/env.e2e`
- Check bot has proper permissions in test guild (use invite URL from setup)
- Ensure bot is actually invited to the test guild (check Members list)
- Verify **MESSAGE_CONTENT** intent enabled for main bot in Developer Portal
- Check bot didn't get kicked or banned from guild

### Tests fail to find Discord channel

**Symptoms:** `discord.NotFound: 404 Not Found (error code: 10003): Unknown Channel`

**Solutions:**
- Verify `DISCORD_CHANNEL_ID` matches actual channel in test guild
- Check bot has **View Channels** permission
- Ensure channel isn't deleted or archived
- Verify channel is in the correct guild (not a different server)

### Tests timeout waiting for messages

**Symptoms:** `AssertionError: Message ID should be populated after announcement`

**Solutions:**
- Check RabbitMQ is running: `docker ps | grep rabbitmq`
- Verify bot service started: `docker logs gamebot-e2e-bot`
- Check for bot errors in logs: `docker logs gamebot-e2e-bot | grep ERROR`
- Ensure bot has **Send Messages** and **Embed Links** permissions
- Verify event publishing works: check RabbitMQ management UI (port 15673)

### Tests timeout waiting for DMs

**Symptoms:** Tests waiting for reminders or notifications timeout after 150 seconds

**Solutions:**
- Check notification daemon is running: `docker ps | grep notification-daemon`
- Verify daemon logs: `docker logs gamebot-e2e-notification-daemon`
- Check notification_schedule table populated: Connect to database and query
- Ensure game scheduled time hasn't already passed
- Verify user ID in test matches Discord account (case-sensitive snowflake)
- Check bot can DM user (user must share a server with bot, DMs not blocked)

### Authentication failures

**Symptoms:** `{"field":"cookie.session_token","message":"Field required","type":"missing"}`

**Solutions:**
- Verify admin bot token is correct in `env/env.e2e`
- Check init service seeded admin bot user: `docker logs gamebot-e2e-init`
- Ensure guild sync succeeded: Look for "Synced guilds" in test output
- Verify Valkey/Redis is running: `docker ps | grep redis`

### Database state issues

**Symptoms:** Tests fail with "Guild configuration not found" or "Template not found"

**Solutions:**
- Ensure init service completed successfully: `docker logs gamebot-e2e-init`
- Check guild sync ran: `synced_guild` fixture should print sync results
- Verify database seeding: Connect to database and check `guild_configurations` table
- Try fresh database: `docker compose --env-file env/env.e2e down -v` (removes volumes)

### Flaky tests

**Symptoms:** Tests pass sometimes, fail other times

**Solutions:**
- Increase wait timeouts if system is slow (edit test file)
- Check for Discord API rate limiting (429 errors in bot logs)
- Verify system resources adequate (Docker has sufficient memory/CPU)
- Run tests sequentially rather than parallel (default is sequential)
- Check for clock skew (scheduled times vs system time)

### Permission denied errors

**Symptoms:** Bot operations fail with 403 Forbidden

**Solutions:**
- Re-generate bot invite URL with correct permissions
- Remove bot from guild and re-invite with new URL
- Verify permissions in Discord: Server Settings → Roles → Bot Role
- Check channel-specific permission overrides

## Tests fail to find channel

## Security Notes

⚠️ **IMPORTANT**:

- Never commit `env/env.int` or `env/env.e2e` to version control with real credentials
- Keep test bot tokens separate from production
- Limit test guild membership to test accounts only
- Use minimal bot permissions for test bot
- The `.gitignore` already protects `env/*` from being committed

Existing `.gitignore` protection:

```
env/*
.env*
```
