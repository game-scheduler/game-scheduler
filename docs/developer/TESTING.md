# Testing Guide

This comprehensive guide covers all testing approaches for the Game Scheduler project, including unit tests, integration tests, end-to-end tests, coverage collection, and OAuth testing.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Types Overview](#test-types-overview)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [End-to-End Tests](#end-to-end-tests)
- [Coverage Collection](#coverage-collection)
- [OAuth Testing](#oauth-testing)
- [Test Infrastructure](#test-infrastructure)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Run All Tests with Coverage

```bash
# Run all tests (unit, integration, e2e) and generate coverage reports
./scripts/coverage-report.sh

# Skip e2e tests if Discord credentials not configured
./scripts/coverage-report.sh --skip-e2e
```

### Run Specific Test Types

```bash
# Unit tests only (fast, no external dependencies)
pre-commit run pytest-all --hook-stage manual

# Integration tests (requires Docker)
./scripts/run-integration-tests.sh

# End-to-end tests (requires Discord test environment)
./scripts/run-e2e-tests.sh
```

## Test Types Overview

The project uses three complementary testing levels:

| Test Type       | Speed           | External Deps    | Coverage Focus                             |
| --------------- | --------------- | ---------------- | ------------------------------------------ |
| **Unit**        | Fast (seconds)  | None             | Business logic, edge cases, error handling |
| **Integration** | Medium (30-60s) | Docker           | Database, RabbitMQ, daemon scheduling      |
| **End-to-End**  | Slow (8-12 min) | Docker + Discord | Complete flows with Discord API            |

**Testing Philosophy:**

- Unit tests verify component behavior in isolation
- Integration tests verify service interactions
- E2E tests verify user-visible behavior end-to-end

## Unit Tests

### Overview

Unit tests focus on testing individual functions, classes, and modules in isolation without external dependencies.

### Running Unit Tests

```bash
# Run all unit tests
pre-commit run pytest-all --hook-stage manual

# Run specific test file
pytest tests/unit/test_game_service.py -v

# Run specific test function
pytest tests/unit/test_game_service.py::test_create_game -v

# Run with coverage
pytest --cov=shared --cov=services tests/unit/
```

### Test Structure

```python
# tests/unit/services/test_game_service.py
import pytest
from services.api.services.game_service import GameService

@pytest.fixture
def mock_db_session():
    # Create mock database session
    pass

@pytest.fixture
def game_service(mock_db_session):
    return GameService(mock_db_session)

def test_create_game_validates_max_players(game_service):
    # Arrange
    invalid_data = {"max_players": -1}

    # Act & Assert
    with pytest.raises(ValidationError):
        game_service.create_game(invalid_data)
```

### Test Fixtures

Common unit test fixtures are defined in `tests/conftest.py`:

- `mock_db_session` - Mock database session
- `mock_discord_client` - Mock Discord API client
- `test_user` - Sample user object
- `test_guild` - Sample guild object

### Best Practices

**Do:**

- Test one thing per test function
- Use descriptive test names (`test_create_game_with_invalid_max_players`)
- Mock external dependencies (database, Discord API, RabbitMQ)
- Test edge cases and error conditions
- Use parametrized tests for similar scenarios

**Don't:**

- Make network calls or database queries
- Depend on test execution order
- Use real Discord credentials
- Test implementation details (test behavior, not internals)

## Integration Tests

### Overview

Integration tests verify that services work correctly with real infrastructure (PostgreSQL, RabbitMQ, Redis) but without requiring Discord.

### Running Integration Tests

```bash
# Run all integration tests
./scripts/run-integration-tests.sh

# Run specific test file
docker compose --env-file config/env/env.int run --rm integration-tests \
  tests/integration/test_notification_daemon.py -v
```

### Test Environment

Integration tests use isolated Docker environment:

- **Database**: `game_scheduler_integration` (port 5434)
- **RabbitMQ**: Dedicated instance (port 5674)
- **Redis**: Dedicated instance (port 6381)
- **Network**: `gamebot-integration-network`
- **Containers**: Prefixed with `gamebot-integration-`

### What Integration Tests Verify

**Notification Daemon**:

- PostgreSQL LISTEN/NOTIFY triggers work correctly
- Notification schedules populated on game creation
- MIN() query pattern finds next due notification
- RabbitMQ events published when notifications due
- Daemon wakes immediately on database NOTIFY

**Database Operations**:

- Game creation with participants
- Notification schedule management
- Status transition scheduling
- Row-Level Security (RLS) enforcement

**Message Broker**:

- RabbitMQ event publishing
- Event consumption patterns
- Queue durability and acknowledgment

### Test Structure

```python
# tests/integration/test_notification_daemon.py
import pytest
from datetime import datetime, UTC, timedelta

@pytest.mark.asyncio
async def test_notification_daemon_processes_due_reminders(
    db_session,
    rabbitmq_connection
):
    # Create game with imminent reminder
    scheduled_at = datetime.now(UTC) + timedelta(minutes=2)
    game = await create_test_game(
        db_session,
        scheduled_at=scheduled_at,
        reminder_minutes=[1]
    )

    # Wait for daemon to process
    await asyncio.sleep(70)  # Past reminder time + daemon poll interval

    # Verify event published to RabbitMQ
    messages = await consume_rabbitmq_messages(rabbitmq_connection)
    assert any(m.type == "NOTIFICATION_DUE" for m in messages)
```

### Environment Configuration

Integration tests use `config/env/env.int`:

```bash
COMPOSE_FILE=compose.yaml:compose.int.yaml
CONTAINER_PREFIX=gamebot-integration
POSTGRES_USER=gamebot_integration
POSTGRES_PASSWORD=integration_password
POSTGRES_DB=game_scheduler_integration
DATABASE_URL=postgresql://gamebot_integration:integration_password@postgres:5432/game_scheduler_integration
RABBITMQ_URL=amqp://gamebot_integration:integration_password@rabbitmq:5672/
TEST_ENVIRONMENT=true
```

## End-to-End Tests

### Overview

E2E tests verify the complete system flow from API calls through Discord message delivery, ensuring users see correct information in their Discord channels.

### Test Flow Examples

1. **Game Creation** → API publishes GAME_CREATED → Bot posts to Discord channel
2. **Game Update** → API publishes GAME_UPDATED → Bot edits Discord message
3. **User Joins** → API updates participants → Bot refreshes Discord message
4. **Reminders** → Daemon publishes NOTIFICATION_DUE → Bot sends DMs
5. **Status Transitions** → Daemon publishes transition event → Bot updates status

### Prerequisites: Discord Test Environment

E2E tests require a dedicated Discord test guild to avoid spamming production servers.

#### 1. Create Two Test Bots

**Main Bot** (sends messages):

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create "Game Scheduler Test Bot"
3. Enable **SERVER MEMBERS INTENT** and **MESSAGE CONTENT INTENT**
4. Copy bot token → `DISCORD_BOT_TOKEN`

**Admin Bot** (test authentication):

1. Create "Game Scheduler Test Admin Bot"
2. Copy bot token → `DISCORD_ADMIN_BOT_TOKEN`
3. Copy application ID → `DISCORD_ADMIN_BOT_CLIENT_ID`
4. Generate client secret → `DISCORD_ADMIN_BOT_CLIENT_SECRET`

#### 2. Create Test Guild and Channel

1. Create new Discord server "Game Scheduler Test"
2. Enable Developer Mode (Settings → Advanced)
3. Right-click server name → "Copy Server ID" → `DISCORD_GUILD_ID`
4. Create text channel "test-games"
5. Right-click channel → "Copy Channel ID" → `DISCORD_CHANNEL_ID`

#### 3. Invite Bots to Test Guild

Generate OAuth2 invite URL with permissions:

- View Channels
- Send Messages
- Send Messages in Threads
- Embed Links
- Attach Files

Invite both bots to test guild.

#### 4. Get Your Discord User ID

1. Enable Developer Mode
2. Right-click your username → "Copy User ID" → `TEST_DISCORD_USER_ID`
3. Join the test guild (required for DM verification)

#### 5. Configure E2E Environment

Update `config/env/env.e2e`:

```bash
COMPOSE_FILE=compose.yaml:compose.e2e.yaml
CONTAINER_PREFIX=gamebot-e2e
POSTGRES_DB=game_scheduler_e2e
DATABASE_URL=postgresql://gamebot_e2e:e2e_password@postgres:5432/game_scheduler_e2e

# Main Bot (MESSAGE_CONTENT intent required)
DISCORD_BOT_TOKEN=your_main_bot_token

# Admin Bot (test authentication)
DISCORD_ADMIN_BOT_TOKEN=your_admin_bot_token
DISCORD_ADMIN_BOT_CLIENT_ID=your_admin_bot_client_id
DISCORD_ADMIN_BOT_CLIENT_SECRET=your_admin_bot_client_secret

# Test Environment
DISCORD_GUILD_ID=123456789012345678
DISCORD_CHANNEL_ID=123456789012345678
TEST_DISCORD_USER_ID=123456789012345678

TEST_ENVIRONMENT=true
```

#### 6. Role-Based Signup E2E Test Roles

`tests/e2e/test_role_based_signup.py` requires two roles in Guild A:

| Role                    | Who holds it             | Purpose                                          |
| ----------------------- | ------------------------ | ------------------------------------------------ |
| **E2E Priority Role A** | Admin Bot A              | Used as the "matched" role in parametrized cases |
| **E2E Priority Role B** | Nobody (not Admin Bot A) | Used as the "unmatched" role                     |

**Setup steps:**

1. In Discord, open Guild A → Server Settings → Roles
2. Create role **"E2E Priority Role A"** (any color/permissions; it is only used in tests)
3. Create role **"E2E Priority Role B"** (same; do not assign it to the bot)
4. Assign **"E2E Priority Role A"** to Admin Bot A in Guild A
5. Enable Developer Mode (Settings → Advanced → Developer Mode)
6. Right-click each role → **Copy Role ID**
7. Set the values in `config/env.e2e`:

```bash
DISCORD_TEST_ROLE_A_ID=<id of "E2E Priority Role A">
DISCORD_TEST_ROLE_B_ID=<id of "E2E Priority Role B">
```

If either variable is absent, the four parametrized cases in `test_role_based_signup.py`
will **fail** with a clear error message pointing to this section.

### Running E2E Tests

```bash
# Run all e2e tests
./scripts/run-e2e-tests.sh

# Run specific test file
docker compose --env-file config/env/env.e2e run --rm e2e-tests \
  tests/e2e/test_game_announcement.py -v

# Run specific test function
docker compose --env-file config/env/env.e2e run --rm e2e-tests \
  tests/e2e/test_game_announcement.py::test_game_creation_posts_announcement -v
```

### Test Execution Times

- **Quick tests** (2-5 seconds): Game creation, updates, cancellation
- **Medium tests** (10-30 seconds): Participant joins, waitlist promotion
- **Long tests** (2-5 minutes): Reminders, status transitions (wait for daemon polling)

**Full test suite**: ~8-12 minutes (includes real-time waits for daemon polling)

### E2E Test Architecture

#### Hermetic Test Fixtures

E2E tests use hermetic fixtures that create guilds on-demand and clean up automatically:

**Guild Creation Fixtures:**

```python
async def test_game_creation(fresh_guild_a):
    # fresh_guild_a provides GuildContext with all IDs
    guild_db_id = fresh_guild_a.db_id
    template_id = fresh_guild_a.template_id
    channel_discord_id = fresh_guild_a.channel_discord_id
```

**Available Fixtures:**

- `discord_ids` - Session-scoped fixture with environment variable validation
- `fresh_guild_a` - Function-scoped Guild A with automatic cleanup
- `fresh_guild_b` - Function-scoped Guild B for cross-guild isolation tests
- `test_user_a` - Function-scoped admin bot user with cleanup
- `test_user_b` - Function-scoped bot B user with cleanup
- `test_user_main_bot` - Function-scoped main notification bot user with cleanup

**GuildContext Dataclass:**

All guild fixtures return a `GuildContext` containing:

```python
@dataclass
class GuildContext:
    db_id: str              # Database UUID for guild_configurations
    discord_id: str         # Discord snowflake ID
    channel_db_id: str      # Database UUID for channel_configurations
    channel_discord_id: str # Discord channel snowflake ID
    template_id: str        # Database UUID for default game_templates
```

**Fixture Behavior:**

- Guilds created via direct database INSERTs (no external API dependencies)
- Automatic cleanup in `finally` block (guaranteed even on test failure)
- Each test gets isolated guild state (no shared data)
- Can create multiple guilds in one test for isolation testing

**Example Usage:**

```python
async def test_cross_guild_isolation(fresh_guild_a, fresh_guild_b):
    # Create game in Guild A
    response = await client.post(
        "/api/v1/games",
        json={"template_id": fresh_guild_a.template_id, "title": "Game A"}
    )

    # Verify Guild B cannot see it
    response = await client_b.get("/api/v1/games")
    assert not any(g["title"] == "Game A" for g in response.json())
```

**Environment Variable Validation:**

The `discord_ids` fixture validates all required Discord IDs at session start:

```python
async def test_environment_configured(discord_ids):
    # Validates all Discord IDs are present and valid snowflakes
    assert discord_ids.guild_a_id
    assert discord_ids.channel_a_id
    assert discord_ids.user_a_id
```

Required environment variables:

- `DISCORD_GUILD_A_ID` - Guild A Discord ID (17-19 digit snowflake)
- `DISCORD_GUILD_A_CHANNEL_ID` - Guild A active game channel Discord ID
- `DISCORD_ARCHIVE_CHANNEL_ID` - Guild A archive channel Discord ID
- `DISCORD_USER_ID` - Admin bot user Discord ID
- `DISCORD_GUILD_B_ID` - Guild B Discord ID
- `DISCORD_GUILD_B_CHANNEL_ID` - Guild B channel Discord ID
- `DISCORD_ADMIN_BOT_B_CLIENT_ID` - Bot B user Discord ID

#### Authentication

Tests authenticate using admin bot token:

```python
async def test_game_creation(authenticated_admin_client):
    # Client has session_token cookie set
    response = await authenticated_admin_client.post("/api/v1/games", json=data)
```

#### Discord Message Verification

Use `DiscordTestHelper` to verify messages:

```python
async def test_game_creation(discord_helper, main_bot_helper):
    # Fetch channel message
    message = await discord_helper.get_message(channel_id, message_id)

    # Verify embed structure
    embed = message.embeds[0]
    discord_helper.verify_game_embed(embed, "Game Title", "123456", max_players=4)

    # Check user DMs
    dms = await main_bot_helper.get_user_recent_dms(user_id)
    reminder = await main_bot_helper.find_game_reminder_dm(user_id, "Game Title")
    assert reminder is not None
```

#### Timing and Synchronization

**Wait for message creation:**

```python
# Poll database for message_id (bot sets after posting)
for attempt in range(10):
    message_id = await db_session.scalar(
        select(GameSession.message_id).where(GameSession.id == game_id)
    )
    if message_id:
        break
    await asyncio.sleep(0.5)
```

**Wait for scheduled notifications:**

```python
# Create game with 1 minute reminder
scheduled_at = datetime.now(UTC) + timedelta(minutes=2)

# Wait up to 150 seconds for notification daemon
# (60s scheduled time + 60s daemon poll + 30s margin)
for elapsed in range(0, 150, 5):
    dms = await main_bot_helper.get_user_recent_dms(user_id)
    if await main_bot_helper.find_game_reminder_dm(user_id, title):
        break
    await asyncio.sleep(5)
```

### Test Environment Isolation

E2E tests use completely isolated Docker environment:

- **Database**: `game_scheduler_e2e` (port 5433)
- **RabbitMQ**: Dedicated instance (port 5673)
- **Redis**: Dedicated instance (port 6380)
- **Network**: `gamebot-e2e-network`
- **Containers**: Prefixed with `gamebot-e2e-`

Integration and E2E environments can run simultaneously without conflicts.

## Coverage Collection

### Overview

The project collects coverage data from all three test types and combines them into comprehensive reports.

### Running Coverage

```bash
# All tests with coverage
./scripts/coverage-report.sh

# Skip e2e tests
./scripts/coverage-report.sh --skip-e2e
```

### How It Works

Each test type writes to its own coverage file:

- Unit tests → `.coverage`
- Integration tests → `.coverage.integration`
- E2E tests → `.coverage.e2e`

The `coverage combine` command merges all files for unified reporting.

### Coverage Configuration

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["shared", "services"]
relative_files = true  # Portable between host and containers
omit = [
    "*/tests/*",
    "*/alembic/*",
    "*/__pycache__/*"
]

[tool.coverage.report]
precision = 2
skip_empty = true
fail_under = 80  # Minimum coverage threshold
```

### Coverage Reports

**Terminal Report:**

```bash
./scripts/coverage-report.sh
```

Shows table with statement and branch coverage per file.

**HTML Report:**

```bash
./scripts/coverage-report.sh
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Provides:

- Color-coded source files showing covered/uncovered lines
- Branch coverage details
- Sortable tables with search

**XML Report:**

Generated as `coverage.xml` in Cobertura format for CI/CD systems.

### Docker Integration

Compose files set `COVERAGE_FILE` environment variable:

- `compose.int.yaml`: `COVERAGE_FILE=.coverage.integration`
- `compose.e2e.yaml`: `COVERAGE_FILE=.coverage.e2e`

Both mount workspace root (`.:/app`) so coverage data persists after container cleanup.

## OAuth Testing

### Overview

Test Discord OAuth2 authentication flow with the web dashboard.

### Prerequisites

1. **Discord Application Setup:**
   - Create application at https://discord.com/developers/applications
   - Copy Client ID and Client Secret
   - Add redirect: `http://localhost:8000/api/v1/auth/callback`

2. **Environment Configuration:**
   ```bash
   DISCORD_CLIENT_SECRET=your_client_secret
   FRONTEND_URL=http://localhost:3000
   BACKEND_URL=http://localhost:8000
   ```

### Testing OAuth Flow

#### Method 1: Manual Testing with curl

```bash
# Step 1: Get authorization URL
curl "http://localhost:8000/api/v1/auth/login?redirect_uri=http://localhost:8000/api/v1/auth/callback"

# Response contains authorization_url and state token
# Copy authorization_url and open in browser

# Step 2: Authorize application in browser
# You'll be redirected to callback with success=true
```

#### Method 2: API Documentation (Swagger UI)

1. Open http://localhost:8000/docs
2. Find `/api/v1/auth/login` endpoint
3. Click "Try it out"
4. Execute and copy `authorization_url` from response
5. Open URL in browser to complete flow

### Verifying OAuth Flow

**Check API logs:**

```
INFO - Successfully exchanged authorization code for tokens
INFO - Fetched user info for Discord ID: 123456789
INFO - Created new user with Discord ID: 123456789
INFO - Stored tokens for user 123456789
```

**Check Valkey session storage:**

```bash
# Connect to Valkey
docker exec -it gamebot-redis valkey-cli

# List sessions
KEYS session:*

# View session data
GET session:your_session_token
```

### OAuth Security Notes

- Never commit real credentials to version control
- Use environment variables for all secrets
- Rotate client secrets periodically
- Test OAuth with non-production Discord app
- Validate redirect URIs match configured values

## Test Infrastructure

### Docker Compose Test Configurations

**Base Configuration (`compose.yaml`):**

- Production-ready base shared by all environments

**Integration Tests (`compose.int.yaml`):**

- Overrides for integration test environment
- Postgres, RabbitMQ, Redis only (no bot)
- Separate ports to avoid conflicts

**E2E Tests (`compose.e2e.yaml`):**

- Full stack including bot and daemons
- Complete test environment with Discord integration
- Separate network and ports

### Environment Variables

Each test environment has dedicated config in `config/env/`:

- `config/env/env.int` - Integration tests
- `config/env/env.e2e` - End-to-end tests

The `COMPOSE_FILE` variable specifies which compose files to load:

```bash
COMPOSE_FILE=compose.yaml:compose.int.yaml
```

### Test Fixtures

Common fixtures in `tests/conftest.py`:

**Database:**

- `db_session` - SQLAlchemy session with transaction rollback
- `clean_test_data` - Cleanup after tests

**Discord:**

- `discord_helper` - Helper for Discord API operations (admin bot)
- `main_bot_helper` - Helper for verifying main bot messages
- `authenticated_admin_client` - HTTP client with session auth

**Configuration:**

- `test_guild_id` - Test Discord guild snowflake
- `test_channel_id` - Test Discord channel snowflake
- `synced_guild` - Guild configuration pre-seeded in database

### Common Test Patterns

**Polling for async results:**

```python
# Wait for bot to set message_id
for attempt in range(max_attempts):
    value = await get_value_from_db()
    if value:
        break
    await asyncio.sleep(interval)
assert value, "Expected value not found"
```

**Unique test data:**

```python
# Avoid conflicts with parallel tests
game_title = f"E2E Test {uuid4().hex[:8]}"
```

**Database cleanup:**

```python
@pytest.fixture
async def clean_test_data(db_session):
    yield
    # Delete test data after test
    await db_session.execute(
        text("DELETE FROM game_sessions WHERE title LIKE 'E2E%'")
    )
    await db_session.commit()
```

## CI/CD Integration

### Recommended Strategy

**Run in CI:**

- ✅ Unit tests (fast, no external dependencies)
- ✅ Integration tests (Docker-based, reliable)

**Run manually before releases:**

- ⚠️ E2E tests (require live Discord infrastructure)

### Why Manual E2E Execution?

E2E tests require external Discord resources:

- Real Discord guilds, bots, channels
- Tests take 8-12 minutes due to real-time waits
- Discord API rate limits can cause flakiness
- Sensitive bot tokens must be managed as secrets
- Test guild state can accumulate over runs

### Standard CI Pipeline

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Unit Tests
        run: pytest tests/unit/ --cov=shared --cov=services

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Integration Tests
        run: ./scripts/run-integration-tests.sh
```

### Conditional E2E Execution (Optional)

```yaml
name: E2E Tests (Manual Trigger)

on:
  workflow_dispatch:
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
          cat > config/env/env.e2e << EOF
          COMPOSE_FILE=compose.yaml:compose.e2e.yaml
          DISCORD_BOT_TOKEN=${{ secrets.DISCORD_BOT_TOKEN }}
          DISCORD_ADMIN_BOT_TOKEN=${{ secrets.DISCORD_ADMIN_BOT_TOKEN }}
          DISCORD_GUILD_ID=${{ secrets.DISCORD_GUILD_ID }}
          DISCORD_CHANNEL_ID=${{ secrets.DISCORD_CHANNEL_ID }}
          TEST_DISCORD_USER_ID=${{ secrets.TEST_DISCORD_USER_ID }}
          EOF

      - name: Run E2E Tests
        run: ./scripts/run-e2e-tests.sh
        timeout-minutes: 20

      - name: Cleanup
        if: always()
        run: docker compose --env-file config/env/env.e2e down -v
```

**Required GitHub Secrets:**

- `DISCORD_BOT_TOKEN`
- `DISCORD_ADMIN_BOT_TOKEN`
- `DISCORD_ADMIN_BOT_CLIENT_ID`
- `DISCORD_ADMIN_BOT_CLIENT_SECRET`
- `DISCORD_GUILD_ID`
- `DISCORD_CHANNEL_ID`
- `TEST_DISCORD_USER_ID`

## Troubleshooting

### Common Issues

#### Hermetic Fixture Cleanup Failures

**Symptoms:** Tests fail with "Guild already exists" or database constraint violations

**Root Cause:** Fixture cleanup didn't complete in previous test run

**Solutions:**

1. **Check for orphaned database records:**

   ```bash
   # Connect to E2E database
   docker exec -it gamebot-e2e-postgres psql -U gamebot_e2e -d game_scheduler_e2e

   # List guilds (should be empty between test runs)
   SELECT id, guild_id FROM guild_configurations;

   # Clean up manually if needed
   DELETE FROM guild_configurations WHERE guild_id IN ('guild_a_id', 'guild_b_id');
   ```

2. **Verify CASCADE DELETE constraints:**

   ```sql
   # Check foreign key constraints have CASCADE
   SELECT conname, conrelid::regclass, confrelid::regclass, confdeltype
   FROM pg_constraint
   WHERE contype = 'f' AND confrelid::regclass::text = 'guild_configurations';
   ```

   All `confdeltype` should be `c` (CASCADE). If not, run Alembic migration `cc016b875896`.

3. **Fresh database state:**

   ```bash
   # Nuclear option: completely reset E2E environment
   docker compose --env-file config/env/env.e2e down -v
   ./scripts/run-e2e-tests.sh
   ```

4. **Check test isolation:**
   - Verify tests don't share guild_db_id between tests
   - Ensure each test uses its own `fresh_guild_a` fixture
   - Don't cache `GuildContext` objects across tests

#### Environment Variable Validation Errors

**Symptoms:** Tests fail immediately with "Missing required environment variables"

**Solutions:**

1. **Verify all Discord IDs configured in `config/env/env.e2e`:**

   ```bash
   grep DISCORD_ config/env/env.e2e
   ```

   Required variables:
   - `DISCORD_GUILD_A_ID`
   - `DISCORD_GUILD_A_CHANNEL_ID`
   - `DISCORD_ARCHIVE_CHANNEL_ID`
   - `DISCORD_USER_ID`
   - `DISCORD_GUILD_B_ID`
   - `DISCORD_GUILD_B_CHANNEL_ID`
   - `DISCORD_ADMIN_BOT_B_CLIENT_ID`

2. **Validate Discord ID format (17-19 digit snowflakes):**

   ```python
   # Valid Discord snowflake
   DISCORD_GUILD_A_ID=123456789012345678

   # Invalid - too short
   DISCORD_GUILD_A_ID=12345

   # Invalid - contains non-digits
   DISCORD_GUILD_A_ID=abc123xyz
   ```

3. **Check environment file loaded:**
   ```bash
   # Verify compose loads correct env file
   docker compose --env-file config/env/env.e2e config | grep DISCORD_
   ```

#### User Fixture Failures

**Symptoms:** Tests fail with "User not found" or "User already exists"

**Solutions:**

1. **Verify user fixtures used correctly:**

   ```python
   # Good: Use user fixtures
   async def test_with_user(test_user_a, fresh_guild_a):
       pass

   # Bad: Create users manually
   async def test_without_fixture(admin_db):
       user = User(discord_id="123")  # Will conflict with fixtures
   ```

2. **Check user cleanup:**

   ```bash
   # Connect to database
   docker exec -it gamebot-e2e-postgres psql -U gamebot_e2e -d game_scheduler_e2e

   # List users (should only see persistent users)
   SELECT id, discord_id FROM users;

   # Clean up test users if needed
   DELETE FROM users WHERE discord_id IN ('env_user_a_id', 'env_user_b_id');
   ```

#### Bot doesn't connect to test guild

**Symptoms:** Tests fail with "Guild not found" or timeout errors

**Solutions:**

- Verify bot token correct in `config/env/env.e2e`
- Check bot has proper permissions (use generated invite URL)
- Ensure bot actually invited to test guild
- Verify **MESSAGE_CONTENT** intent enabled in Developer Portal
- Check bot wasn't kicked or banned

#### Tests fail to find Discord channel

**Symptoms:** `discord.NotFound: 404 Not Found (error code: 10003): Unknown Channel`

**Solutions:**

- Verify `DISCORD_CHANNEL_ID` matches actual channel
- Check bot has **View Channels** permission
- Ensure channel isn't deleted or archived
- Verify channel is in correct guild

#### Tests timeout waiting for messages

**Symptoms:** `AssertionError: Message ID should be populated`

**Solutions:**

- Check RabbitMQ running: `docker ps | grep rabbitmq`
- Verify bot service started: `docker logs gamebot-e2e-bot`
- Check bot logs for errors
- Ensure bot has **Send Messages** and **Embed Links** permissions
- Verify RabbitMQ events publishing (check management UI)

#### Tests timeout waiting for DMs

**Symptoms:** Tests waiting for reminders timeout after 150 seconds

**Solutions:**

- Check notification daemon running: `docker ps | grep notification-daemon`
- Verify daemon logs: `docker logs gamebot-e2e-notification-daemon`
- Check notification_schedule table populated
- Ensure game scheduled time hasn't passed
- Verify user ID matches Discord account
- Check bot can DM user (must share server, DMs not blocked)

#### Authentication failures

**Symptoms:** `{"type":"missing","field":"cookie.session_token"}`

**Solutions:**

- Verify admin bot token correct in `config/env/env.e2e`
- Check init service seeded admin bot user
- Ensure guild sync succeeded
- Verify Valkey/Redis running: `docker ps | grep redis`

#### Database state issues

**Symptoms:** "Guild configuration not found" or "Template not found"

**Solutions:**

- Ensure init service completed: `docker logs gamebot-e2e-init`
- Check guild sync ran successfully
- Verify database seeding
- Try fresh database: `docker compose --env-file config/env/env.e2e down -v`

#### Flaky tests

**Symptoms:** Tests pass sometimes, fail other times

**Solutions:**

- Increase wait timeouts if system is slow
- Check for Discord API rate limiting (429 errors)
- Verify adequate system resources for Docker
- Run tests sequentially (default)
- Check for clock skew

#### Permission denied errors

**Symptoms:** Bot operations fail with 403 Forbidden

**Solutions:**

- Re-generate bot invite URL with correct permissions
- Remove bot from guild and re-invite
- Verify permissions in Server Settings → Roles
- Check channel-specific permission overrides

### Getting Help

If you encounter issues not covered here:

1. Check service logs: `docker compose logs <service>`
2. Review test output for specific error messages
3. Verify environment configuration in `config/env/env.*`
4. Check Discord Developer Portal for bot status
5. Ensure all dependencies up to date
6. Open an issue on GitHub with:
   - Full error message
   - Test command run
   - Relevant logs
   - Environment details

## Security Notes

⚠️ **IMPORTANT:**

- Never commit `config/env/env.int` or `config/env/env.e2e` with real credentials
- Keep test bot tokens separate from production
- Limit test guild membership to test accounts only
- Use minimal bot permissions for test bots
- The `.gitignore` already protects `config/env/*` from being committed

## Related Documentation

- [SETUP.md](SETUP.md) - Development environment setup
- [architecture.md](architecture.md) - System architecture and design
- [database.md](database.md) - Database schema and RLS
- [oauth-flow.md](oauth-flow.md) - OAuth2 authentication details
