# Phase 5 Testing Guide: Bot Service Instrumentation Verification

## Prerequisites

- Phase 4 completed successfully (API service instrumented and verified)
- Bot service environment configured with Discord credentials
- Grafana Cloud access configured

## Step 1: Rebuild and Restart Bot Service

```bash
# Rebuild bot container with telemetry code
docker compose build bot

# Restart bot service
docker compose up -d bot

# Wait for bot to start
sleep 5
```

## Step 2: Verify Bot Initialization

```bash
# Check bot logs for OpenTelemetry initialization
docker logs gamebot-bot | grep "OpenTelemetry"

# Expected output:
# INFO - OpenTelemetry tracing initialized
# INFO - OpenTelemetry metrics initialized
# INFO - OpenTelemetry logging initialized
```

## Step 3: Verify Bot Connected to Discord

```bash
# Check bot connection status
docker logs gamebot-bot | grep "Bot connected"

# Expected output:
# INFO - Bot connected as YourBotName (ID: 123456789)
# INFO - Connected to N guilds
# INFO - Bot is ready to receive events
```

## Step 4: Trigger Discord Command

Using Discord client, execute a slash command in a channel where the bot is present:

```
/list-games
```

or

```
/my-games
```

## Step 5: Verify Bot Traces in Grafana Cloud Tempo

1. Navigate to Grafana Cloud → Explore → Tempo
2. Search for traces with query:
   ```
   {service.name="bot-service"}
   ```
3. Verify trace structure:
   - Root span: `discord.on_interaction` (from interaction event)
   - Child span: `discord.command.list_games` or `discord.command.my_games`
   - Child spans: database queries (if games exist)

## Step 6: Verify Span Attributes

Click on a trace and inspect span attributes:

**Expected on `discord.on_interaction` span:**
- `discord.interaction_type` = "application_command"
- `discord.user_id` = <Discord user ID>
- `discord.channel_id` = <Discord channel ID>
- `discord.guild_id` = <Discord guild/server ID>

**Expected on `discord.command.*` span:**
- `discord.command` = "list-games" or "my-games"
- `discord.user_id` = <Discord user ID>
- `discord.guild_id` = <Discord guild/server ID>
- `discord.channel_id` = <Discord channel ID>

## Step 7: Verify Trace Propagation to Database

Expand the trace to see child spans:

1. Should see SQLAlchemy/asyncpg spans for database queries
2. Span names like `SELECT shared.game_sessions` or similar
3. Database spans should be children of the command span

## Step 8: Verify Bot Metrics in Grafana Cloud Mimir

1. Navigate to Grafana Cloud → Explore → Prometheus/Mimir
2. Query for bot service metrics:
   ```
   {service_name="bot-service"}
   ```
3. Verify metrics are being collected (may take a few minutes to appear)

## Step 9: Verify Bot Logs with Trace Correlation

1. Navigate to Grafana Cloud → Explore → Loki
2. Query for bot logs:
   ```
   {service_name="bot-service"}
   ```
3. Click on a log entry and verify `trace_id` field is present
4. Click on trace ID to jump to corresponding trace in Tempo

## Success Criteria

- ✅ Bot logs show OpenTelemetry initialization (tracing, metrics, logging)
- ✅ Discord slash commands create traces in Tempo with `service.name="bot-service"`
- ✅ Root span is `discord.on_interaction` with correct interaction type
- ✅ Command spans (`discord.command.*`) are children of interaction span
- ✅ Span attributes include Discord user ID, channel ID, guild ID
- ✅ Database query spans appear as children of command spans
- ✅ Logs include trace IDs for correlation with traces
- ✅ Metrics are collected for bot service (may be minimal if no HTTP traffic)

## Troubleshooting

### Bot Not Initializing OpenTelemetry

**Symptoms:** No "OpenTelemetry initialized" messages in logs

**Solution:**
1. Verify `shared/telemetry.py` is accessible in bot container
2. Check for import errors: `docker logs gamebot-bot | grep -i error`
3. Rebuild bot container: `docker compose build bot`

### No Traces Appearing in Tempo

**Symptoms:** Bot logs show initialization, but no traces in Grafana Cloud

**Solution:**
1. Verify bot has OTEL_EXPORTER_OTLP_ENDPOINT set correctly:
   ```bash
   docker exec gamebot-bot env | grep OTEL
   ```
2. Check Alloy is receiving data from bot:
   ```bash
   docker logs gamebot-grafana-alloy | grep "bot-service"
   ```
3. Verify Alloy is forwarding to Grafana Cloud (check for auth errors)

### Spans Missing Discord Attributes

**Symptoms:** Traces exist but missing `discord.user_id`, etc.

**Solution:**
1. Verify span attributes are set in bot code
2. Check for AttributeError in logs
3. Ensure attributes are strings (convert IDs with `str()`)

### Database Spans Not Appearing

**Symptoms:** Command spans exist but no child database spans

**Solution:**
1. Verify SQLAlchemy/asyncpg instrumentation is initialized
2. Check bot logs for instrumentation errors
3. Ensure commands actually query the database (some may return empty results)

## Next Steps

After successful verification:
- Proceed to Phase 6: Daemon Services Instrumentation
- Monitor bot traces during normal operations
- Look for opportunities to add custom span attributes for business logic
