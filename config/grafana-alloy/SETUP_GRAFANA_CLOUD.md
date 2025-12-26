# Grafana Cloud Setup Instructions

## Task 1.1: Create Grafana Cloud Account and Obtain Credentials

This task requires manual steps on Grafana Cloud's website. Follow these
instructions carefully.

## Step 1: Create Grafana Cloud Account

1. Navigate to https://grafana.com/auth/sign-up/create-user
2. Sign up for a free account (no credit card required)
3. Verify your email address
4. Complete the onboarding wizard

## Step 2: Obtain Tempo (Tracing) Credentials

1. Log into your Grafana Cloud portal
2. Navigate to **Connections** → **Tempo** (or search for "Tempo")
3. Look for the **Tempo** configuration section
4. Note the following information:

   **Tempo Instance ID** (7-digit number, e.g., `1413606`)

   - Found in the connection details
   - This is used for direct OTLP trace ingestion

   **Tempo Endpoint URL** (format:
   `tempo-prod-{number}-prod-{region}.grafana.net:443`)

   - Example: `tempo-prod-15-prod-us-west-0.grafana.net:443`
   - Includes port `:443` for gRPC over TLS

## Step 3: Obtain Prometheus Instance ID

1. In Grafana Cloud portal, navigate to **Connections** → **Prometheus**
2. Look for **"Prometheus/Mimir"** configuration
3. Note the following:

   **Prometheus Instance ID** (7-digit number, e.g., `1234567`)

   - This is DIFFERENT from OTLP instance ID
   - Found in the remote_write configuration

   **Prometheus Endpoint URL**

   - Format:
     `https://prometheus-prod-{number}-prod-{region}.grafana.net/api/prom/push`
   - Example:
     `https://prometheus-prod-36-prod-us-west-0.grafana.net/api/prom/push`

## Step 3.5: Obtain Loki Instance ID

1. In Grafana Cloud portal, navigate to **Connections** → **Loki**
2. Look for **"Loki"** configuration
3. Note the following:

   **Loki Instance ID** (7-digit number, e.g., `1419296`)

   - This is DIFFERENT from both OTLP and Prometheus instance IDs
   - Found in the Loki push endpoint configuration

   **Loki Endpoint URL**

   - Format: `https://logs-prod-{number}.grafana.net/loki/api/v1/push`
   - Example: `https://logs-prod-012.grafana.net/loki/api/v1/push`

## Step 4: Generate API Key

1. Navigate to **Security** → **API Keys** (or **Cloud Access Policies**)
2. Create a new API key with the following permissions:
   - **Metrics**: Write
   - **Logs**: Write
   - **Traces**: Write
3. Name it: `opentelemetry-alloy` (or similar)
4. Copy the API key (format: `glc_xxxxx...`)
5. **IMPORTANT**: Save this immediately - you cannot view it again!

## Step 5: Save All Credentials

Create a secure note or file with all the following values:

```bash
# Tempo Configuration (for application traces via OTLP)
GRAFANA_CLOUD_TEMPO_INSTANCE_ID=1413606  # Your Tempo instance ID
GRAFANA_CLOUD_API_KEY=glc_xxxxx          # Your API key (same for all services)
GRAFANA_CLOUD_TEMPO_ENDPOINT=tempo-prod-15-prod-us-west-0.grafana.net:443

# Prometheus Configuration (for infrastructure metrics)
GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID=1234567  # Your Prometheus instance ID (DIFFERENT from OTLP!)
GRAFANA_CLOUD_PROMETHEUS_ENDPOINT=https://prometheus-prod-36-prod-us-west-0.grafana.net/api/prom/push

# Loki Configuration (for log aggregation)
GRAFANA_CLOUD_LOKI_INSTANCE_ID=1419296  # Your Loki instance ID (DIFFERENT from OTLP and Prometheus!)
GRAFANA_CLOUD_LOKI_ENDPOINT=https://logs-prod-012.grafana.net/loki/api/v1/push
```

## Important Notes

- **Three DIFFERENT Instance IDs**: Grafana Cloud requires separate instance IDs
  for:
  - **Tempo** (traces via OTLP - send directly to Tempo)
  - **Prometheus** (infrastructure metrics via remote_write)
  - **Loki** (log aggregation)
- **One API Key**: The same API key works across all three services
- **Region Consistency**: Make sure all endpoints are in the same region
- **No Credit Card**: The free tier does not require a credit card
- **Direct to Tempo**: We use the Tempo endpoint directly (not OTLP Gateway) for
  better gRPC support

## Free Tier Limits (Verify Current Limits)

- **Traces**: 50 GB/month
- **Logs**: 50 GB/month
- **Metrics**: 10,000 active series
- **Retention**: 14 days for traces/logs, 13 months for metrics

## Next Steps

Once you have all credentials saved:

1. Add them to your `.env` file (we'll do this in Task 1.4)
2. **Do NOT commit** the `.env` file with these credentials
3. Proceed to Task 1.2 to create the Alloy configuration file

## Troubleshooting

**Can't find instance IDs?**

- Go to Connections → Select the specific integration (OTLP or Prometheus)
- Look for "Configuration" or "Remote Write" sections
- Instance IDs are usually displayed prominently

**API key not working?**

- Verify you gave it Write permissions for Metrics, Logs, and Traces
- Check that the key hasn't expired
- Try regenerating a new key if issues persist

**Wrong endpoint URL?**

- Make sure you're copying from the correct integration page
- OTLP endpoint should NOT have `https://` prefix (we add that in config)
- Prometheus endpoint SHOULD have `https://` prefix
