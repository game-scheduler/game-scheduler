# Discord Webhook Configuration Guide

## Overview

This guide explains how to configure Discord webhooks for automatic guild synchronization when the bot joins new servers. The webhook integration enables the Game Scheduler to automatically create guild configurations without requiring manual sync operations.

## Prerequisites

- Access to the Discord Developer Portal
- Application (bot) already created
- Bot token configured in your environment
- Public HTTPS endpoint accessible to Discord servers
- Game Scheduler API service deployed and running

## Configuration Steps

### Step 1: Access Discord Developer Portal

1. Navigate to [Discord Developer Portal](https://discord.com/developers/applications)
2. Log in with your Discord account
3. Select your Game Scheduler application from the list

### Step 2: Obtain Public Key

The public key is required for webhook signature verification.

1. In your application dashboard, click **General Information** in the left sidebar
2. Locate the **Public Key** field (hex string format)
3. Copy the public key value

Example public key format:

```
a1b2c3d4e5f6... (64 hexadecimal characters)
```

### Step 3: Configure Environment Variable

Add the public key to your environment configuration (env.dev, env.prod, etc.):

```bash
DISCORD_PUBLIC_KEY=your_public_key_from_step_2
```

**Important:** Restart your API service after updating the environment variable.

### Step 4: Configure Webhook

#### Step 4.1: Configure Endpoint URL

1. In the Discord Developer Portal, click **Webhooks** in the left sidebar
2. Under **Endpoint URL**, enter your webhook endpoint using this format:

```
<BACKEND_URL>/api/v1/webhooks/discord
```

**Note:** Replace `<BACKEND_URL>` with the value of `BACKEND_URL` from your API service's environment configuration file (env.dev, env.prod, etc.). Do not include a port number - HTTPS uses port 443 by default.

**Important:** In setups using reverse proxies (e.g., cloudflared tunnel + nginx), your `BACKEND_URL` and `FRONTEND_URL` may be the same. This is correct - the nginx configuration routes `/api/` requests to the backend service automatically.

URL Format Guidelines:

- Must use HTTPS (HTTP not supported by Discord)
- Must be publicly accessible from Discord servers
- No port number needed (uses standard HTTPS port 443)
- No authentication headers required (signature validation used instead)

Example URLs:

- Production: `https://game-scheduler.example.com/api/v1/webhooks/discord`
- Staging: `https://staging.game-scheduler.example.com/api/v1/webhooks/discord`
- Development with tunnel: `https://game-scheduler-dev.boneheads.us/api/v1/webhooks/discord`

#### Step 4.2: Enable Webhook Events

1. Toggle **Events** to **ON**
2. Locate **Applications** section
3. Check the **Application Authorized** and **Application Deauthorized** checkboxes
4. Click **Save Changes**

Event Details:

- **Application Authorized**: Triggered when your bot is added to a new server
  - Event data includes guild ID and basic guild information
  - Guild configurations are created automatically by the bot service
- **Application Deauthorized**: Triggered when your bot is removed from a server
  - Event data includes guild ID
  - Guild cleanup will be handled automatically by the bot service

### Step 5: Validate Webhook Endpoint

After saving the configuration, Discord automatically sends a PING request to validate the endpoint.

What happens:

1. Discord sends POST request with `type: 0` (PING)
2. Your endpoint validates the signature
3. Your endpoint responds with `204 No Content`
4. Discord marks endpoint as validated
5. API logs message: `"Received Discord PING webhook"`

To verify successful validation:

```bash
docker compose logs api | grep "PING"
```

If validation fails:

- Check that DISCORD_PUBLIC_KEY is correctly configured
- Verify API service is running and accessible
- Check API logs for signature validation errors
- Ensure HTTPS certificate is valid

## Environment Variable Reference

### Required Variables

```bash
# Discord webhook signature verification
DISCORD_PUBLIC_KEY=your_hex_public_key_from_portal

# Discord bot authentication (existing)
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_BOT_CLIENT_ID=your_bot_client_id
```

### Variable Locations

- **Development**: `config/env.dev`
- **Integration Tests**: `config/env.int`
- **E2E Tests**: `config/env.e2e`
- **Staging**: `config/env.staging`
- **Production**: `config/env.prod`

## Troubleshooting

### Endpoint Validation Fails

Symptoms:

- Discord shows "Invalid endpoint" error
- Cannot save webhook URL

Solutions:

1. Verify DISCORD_PUBLIC_KEY is set correctly:

   ```bash
   docker compose exec api env | grep DISCORD_PUBLIC_KEY
   ```

2. Check API service logs for signature validation errors:

   ```bash
   docker compose logs api | grep "webhook"
   ```

3. Test endpoint manually:

   ```bash
   curl -X POST https://yourdomain.com/api/v1/webhooks/discord \
     -H "Content-Type: application/json" \
     -d '{"type": 0}'
   ```

   Expected response: `401 Unauthorized` (signature missing)

4. Verify HTTPS certificate is valid:
   ```bash
   curl -I https://yourdomain.com/api/v1/webhooks/discord
   ```

### Guilds Not Syncing Automatically

Symptoms:

- Bot joins server but guild configuration not created
- No errors in Discord portal

Solutions:

1. Check bot service logs for sync operations:

   ```bash
   docker compose logs bot | grep "sync"
   ```

2. Verify RabbitMQ message delivery:

   ```bash
   docker compose logs rabbitmq | grep "GUILD_SYNC_REQUESTED"
   ```

3. Check API logs for webhook event processing:

   ```bash
   docker compose logs api | grep "APPLICATION_AUTHORIZED"
   ```

4. Verify guild was created in database:
   ```bash
   docker compose exec postgres psql -U game_scheduler -d game_scheduler \
     -c "SELECT id, guild_id, guild_name FROM guild_configurations;"
   ```

### Invalid Signature Errors

Symptoms:

- API logs show "Invalid Discord webhook signature"
- Discord shows delivery failures

Solutions:

1. Verify public key matches Discord portal value
2. Ensure DISCORD_PUBLIC_KEY has no extra spaces or newlines
3. Restart API service after environment changes
4. Check that request body is not being modified before signature validation

### Webhook Events Not Received

Symptoms:

- Endpoint validated successfully
- Bot joins servers but no webhook events received

Solutions:

1. Verify **Events** toggle is **ON** in Discord portal
2. Confirm **Application Authorized** is checked
3. Check Discord portal for delivery failures under **Recent Deliveries**
4. Verify endpoint URL is still valid (not changed after deployment)

## Testing Checklist

Use this checklist to verify webhook functionality after configuration.

### Initial Setup Validation

- [ ] Public key copied from Discord portal
- [ ] DISCORD_PUBLIC_KEY environment variable configured
- [ ] API service restarted after environment update
- [ ] Webhook endpoint URL configured in Discord portal
- [ ] PING validation completed successfully
- [ ] Events toggle enabled in Discord portal
- [ ] Application Authorized event selected

### PING Validation Test

Test that your endpoint responds correctly to Discord PING requests.

**Steps:**

1. Configure webhook URL in Discord portal
2. Discord automatically sends PING request
3. Verify endpoint responds with `204 No Content`
4. Discord marks endpoint as validated

**Expected Results:**

- Endpoint validation succeeds
- No error messages in Discord portal
- API logs show successful signature validation

**Command to view logs:**

```bash
docker compose logs api | grep -A 5 "webhook"
```

### Application Authorized Event Test

Test the complete flow from bot invitation to guild sync.

**Prerequisites:**

- Webhook configured and validated
- Bot service running
- RabbitMQ operational

**Steps:**

1. Create a test Discord server (or use existing test server)
2. Generate bot invitation URL:
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
   ```
3. Open invitation URL in browser
4. Select test server and authorize bot
5. Wait 5-10 seconds for processing

**Expected Results:**

- API receives APPLICATION_AUTHORIZED webhook event
- API validates signature and publishes RabbitMQ message
- Bot service processes message and syncs all guilds
- New guild configuration created in database
- Guild name and ID stored correctly

**Verification Commands:**

```bash
# Check API received webhook
docker compose logs api | grep "APPLICATION_AUTHORIZED"

# Check RabbitMQ message published
docker compose logs api | grep "GUILD_SYNC_REQUESTED"

# Check bot processed sync
docker compose logs bot | grep "sync"

# Verify guild in database
docker compose exec postgres psql -U game_scheduler -d game_scheduler \
  -c "SELECT guild_id, guild_name, created_at FROM guild_configurations ORDER BY created_at DESC LIMIT 5;"
```

### Signature Validation Test

Verify that invalid signatures are rejected.

**Test with invalid signature:**

```bash
curl -X POST https://yourdomain.com/api/v1/webhooks/discord \
  -H "Content-Type: application/json" \
  -H "X-Signature-Ed25519: invalidsiginvalidsiginvalidsiginvalidsig" \
  -H "X-Signature-Timestamp: $(date +%s)" \
  -d '{"type": 1}'
```

**Expected Result:**

- HTTP 401 Unauthorized response
- API logs show "Invalid Discord webhook signature"

**Test with missing signature:**

```bash
curl -X POST https://yourdomain.com/api/v1/webhooks/discord \
  -H "Content-Type: application/json" \
  -d '{"type": 1}'
```

**Expected Result:**

- HTTP 401 Unauthorized response

### End-to-End Integration Test

Complete workflow validation.

**Scenario:**

1. Bot joins new server via OAuth2
2. Webhook triggers guild sync
3. User logs into Game Scheduler
4. User creates game template
5. Channels populated automatically

**Steps:**

1. Invite bot to new test server
2. Wait for automatic sync (check logs)
3. Log into Game Scheduler web interface
4. Navigate to the new guild
5. Click "Create Template"
6. Verify channels list populated with Discord channels

**Expected Results:**

- Guild appears in dropdown
- Channels synced automatically on first template creation
- Active channels displayed
- Deleted Discord channels marked inactive

### Troubleshooting Reference

| Issue               | Check             | Solution                                                     |
| ------------------- | ----------------- | ------------------------------------------------------------ |
| Validation fails    | Public key        | Verify DISCORD_PUBLIC_KEY matches portal                     |
| 401 responses       | Signature headers | Ensure X-Signature-Ed25519 and X-Signature-Timestamp present |
| Guild not created   | Bot service logs  | Check for RabbitMQ message processing errors                 |
| Channels missing    | Channel refresh   | Manually refresh channels from template editor               |
| Events not received | Discord portal    | Verify Events toggle ON and event subscribed                 |

## Architecture Notes

### Message Flow

```
Discord Server (Bot Added)
         ↓
APPLICATION_AUTHORIZED webhook
         ↓
API Service (Signature Validation)
         ↓
RabbitMQ (GUILD_SYNC_REQUESTED event)
         ↓
Bot Service (Sync All Guilds)
         ↓
Database (Guild Configurations Created)
```

### Why "Sync All Guilds" Approach

The webhook triggers a sync of ALL guilds the bot is in, not just the newly authorized guild:

- **Idempotent**: Safe to run repeatedly without duplicates
- **Efficient**: Single Discord API call fetches all guilds
- **Simple**: Same code path for webhooks, periodic sync, and manual triggers
- **Comprehensive**: Ensures database stays synchronized
- **Lightweight**: Only creates new guilds (doesn't update channels)

### Channel Loading Strategy

Channels are loaded lazily to minimize API calls:

- **Guild Creation**: Only guild ID and name stored
- **Channel Sync**: Triggered when user accesses template editor
- **Refresh Parameter**: Optional `refresh=true` query parameter forces channel update
- **Active Tracking**: Deleted Discord channels marked inactive automatically

## Security Considerations

### Ed25519 Signature Validation

All webhook requests are validated using Ed25519 signatures:

1. Discord signs request body with private key
2. Signature included in `X-Signature-Ed25519` header
3. API validates signature using DISCORD_PUBLIC_KEY
4. Invalid signatures rejected with 401 Unauthorized

**Important:** Request body must NOT be parsed or modified before signature validation.

### Public Key Management

- Store public key as environment variable (not in code)
- Different keys for different environments (dev, staging, prod)
- Rotate keys if compromised (update in Discord portal and environment)
- Never commit public keys to version control

### HTTPS Requirements

- Discord only supports HTTPS endpoints
- Valid SSL/TLS certificate required
- Self-signed certificates not accepted
- Use Let's Encrypt or commercial CA

## Additional Resources

- [Discord Webhook Events Documentation](https://docs.discord.com/developers/events/webhook-events)
- [Ed25519 Signature Verification](https://pynacl.readthedocs.io/en/latest/signing/)
- [Game Scheduler Deployment Guide](configuration.md)
- [Docker Deployment Guide](docker.md)
