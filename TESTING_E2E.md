# End-to-End Testing Setup

This guide explains how to set up a dedicated test Discord environment for running end-to-end notification tests.

## Why a Separate Test Discord Guild?

End-to-end tests verify the complete notification flow:

1. Create game in database
2. Notification daemon triggers at scheduled time
3. RabbitMQ message published
4. Discord bot receives message
5. **Bot sends actual Discord DMs to test users**

Using a separate test guild ensures:

- ✅ Test messages don't spam your real guild
- ✅ Hermetic isolation from production/dev environments
- ✅ Safe to run destructive test scenarios
- ✅ Can be automated in CI/CD pipelines

## Setup Steps

### 1. Create a Test Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "Game Scheduler Test Bot" (or similar)
4. Go to "Bot" section and click "Add Bot"
5. Copy the **Bot Token** - this becomes `TEST_DISCORD_TOKEN`

### 2. Create a Test Discord Guild (Server)

1. In Discord, create a new server
2. Name it "Game Scheduler Test" (or similar)
3. **Keep it private** - don't invite real users
4. Right-click the server name → "Copy Server ID" - this becomes `TEST_DISCORD_GUILD_ID`

### 3. Create a Test Channel

1. In your test guild, create a text channel named "test-games" (or similar)
2. Right-click the channel → "Copy Channel ID" - this becomes `TEST_DISCORD_CHANNEL_ID`

### 4. Invite Test Bot to Test Guild

Generate OAuth2 invite URL:

1. In Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select bot permissions:
   - Send Messages
   - Send Messages in Threads
   - Embed Links
   - Read Message History
4. Copy the generated URL and open it in browser
5. Select your test guild and authorize

### 5. Get Your Discord User ID (for test assertions)

1. In Discord, enable Developer Mode: Settings → Advanced → Developer Mode
2. Right-click your username → "Copy User ID" - this becomes `TEST_DISCORD_USER_ID`
3. Optionally, create additional test user accounts if needed

### 6. Configure Environment Variables

Create separate environment files for each test type:

#### `.env.integration` (for integration tests - no Discord required)

```bash
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

#### `.env.e2e` (for end-to-end tests - requires Discord bot)

```bash
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

# Test Discord Bot Configuration (REQUIRED)
TEST_DISCORD_TOKEN=your_test_bot_token_here
TEST_DISCORD_GUILD_ID=123456789012345678
TEST_DISCORD_CHANNEL_ID=123456789012345678
TEST_DISCORD_USER_ID=123456789012345678

TEST_ENVIRONMENT=true
API_HOST_PORT=8001
FRONTEND_HOST_PORT=3001
```

## Running Tests

### Integration Tests (No Discord Required)

Test notification daemon and PostgreSQL LISTEN/NOTIFY without Discord:

```bash
./scripts/run-integration-tests.sh
```

Or manually:

```bash
docker compose -f docker-compose.test.yml --env-file .env.integration --profile integration up \
  --build --abort-on-container-exit
```

### End-to-End Tests (Requires Test Discord Setup)

Test complete flow including Discord bot interactions:

```bash
./scripts/run-e2e-tests.sh
```

Or manually:

```bash
docker compose -f docker-compose.test.yml --env-file .env.e2e --profile e2e up \
  --build --abort-on-container-exit
```

## Test Environment Isolation

The project uses separate Docker Compose files for each test type:

- **`docker-compose.base.yml`**: Shared service definitions (images, healthchecks, dependencies)
- **`docker-compose.integration.yml`**: Integration tests (postgres, rabbitmq, redis only)
- **`docker-compose.e2e.yml`**: E2E tests (full stack with Discord bot)
- **`.env.integration`**: Integration test environment (no Discord required)
- **`.env.e2e`**: E2E test environment (includes Discord bot credentials)

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

## CI/CD Considerations

For automated testing in CI/CD pipelines:

1. Create separate env files for integration and e2e tests using secrets

2. Use GitHub Actions workflow:

```yaml
- name: Run Integration Tests
  run: |
    # Create .env.integration
    cat > .env.integration << EOF
    CONTAINER_PREFIX=gamebot-integration
    POSTGRES_USER=gamebot_integration
    POSTGRES_PASSWORD=integration_password
    POSTGRES_DB=game_scheduler_integration
    DATABASE_URL=postgresql://gamebot_integration:integration_password@postgres:5432/game_scheduler_integration
    RABBITMQ_URL=amqp://gamebot_integration:integration_password@rabbitmq:5672/
    REDIS_URL=redis://redis:6379/0
    TEST_ENVIRONMENT=true
    EOF
    ./scripts/run-integration-tests.sh

- name: Run E2E Tests
  run: |
    # Create .env.e2e from secrets
    cat > .env.e2e << EOF
    CONTAINER_PREFIX=gamebot-e2e
    POSTGRES_USER=gamebot_e2e
    POSTGRES_PASSWORD=e2e_password
    POSTGRES_DB=game_scheduler_e2e
    DATABASE_URL=postgresql://gamebot_e2e:e2e_password@postgres:5432/game_scheduler_e2e
    RABBITMQ_URL=amqp://gamebot_e2e:e2e_password@rabbitmq:5672/
    REDIS_URL=redis://redis:6379/0
    TEST_DISCORD_TOKEN=${{ secrets.TEST_DISCORD_TOKEN }}
    TEST_DISCORD_GUILD_ID=${{ secrets.TEST_DISCORD_GUILD_ID }}
    TEST_DISCORD_CHANNEL_ID=${{ secrets.TEST_DISCORD_CHANNEL_ID }}
    TEST_DISCORD_USER_ID=${{ secrets.TEST_DISCORD_USER_ID }}
    TEST_ENVIRONMENT=true
    EOF
    ./scripts/run-e2e-tests.sh
```

## Troubleshooting

### Bot doesn't connect to test guild

- Verify bot token is correct
- Check bot has proper permissions in test guild
- Ensure bot is actually invited to the test guild

### Tests fail to find channel

## Security Notes

⚠️ **IMPORTANT**:

- Never commit `.env.test` to version control
- Keep test bot tokens separate from production
- Limit test guild membership to test accounts only
- Use minimal bot permissions for test bot

Add to `.gitignore`:

```
.env.test
```
