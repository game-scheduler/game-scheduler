# Cloudflare Tunnel Setup for Local Development

## Why Use Cloudflare Tunnel?

Discord needs to fetch game images from a publicly accessible URL. In local development, your API is not accessible from the internet. Cloudflare Tunnel creates a secure connection from Cloudflare's edge to your local environment, making your API publicly accessible without opening ports or configuring your firewall.

## Prerequisites

- A Cloudflare account (free tier works)
- Access to the Cloudflare Zero Trust dashboard

## Step 1: Create a Tunnel

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks → Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as the connector type
5. Name your tunnel (e.g., `game-scheduler-dev`)
6. Click **Save tunnel**

## Step 2: Configure the Tunnel

1. In the tunnel configuration, you'll see a token that looks like:
   ```
   eyJhIjoiYWJjMTIzLi4uIn0=
   ```
2. **Copy this token** - you'll need it in the next step

3. Under **Public Hostname**, click **Add a public hostname**:
   - **Subdomain**: Choose a subdomain (e.g., `game-scheduler-dev`)
   - **Domain**: Select your Cloudflare-managed domain (or use a free `.trycloudflare.com` domain)
   - **Type**: `HTTP`
   - **URL**: `api:8000`

4. Click **Save hostname**

## Step 3: Configure Environment Variables

1. Edit `env/env.dev` and set:
   ```bash
   # Add your tunnel token
   CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiYWJjMTIzLi4uIn0=

   # Set API_BASE_URL to your tunnel's public URL
   API_BASE_URL=https://your-subdomain.your-domain.com
   ```

2. If you're using a Cloudflare-provided domain (`.trycloudflare.com`), it will look like:
   ```bash
   API_BASE_URL=https://your-tunnel-name.trycloudflare.com
   ```

## Step 4: Start Services with Cloudflare Profile

Start the services with the `cloudflare` profile enabled:

```bash
docker compose --profile cloudflare up -d
```

Or if rebuilding:

```bash
docker compose --profile cloudflare up -d --build
```

## Step 5: Verify the Tunnel

1. Check that the cloudflared container is running:
   ```bash
   docker compose ps cloudflared
   ```

2. Check the logs:
   ```bash
   docker compose logs cloudflared
   ```

   You should see messages indicating the tunnel is connected.

3. Test external access:
   ```bash
   curl https://your-subdomain.your-domain.com/health
   ```

## Step 6: Test Discord Image Embeds

1. Create a game with images through the web UI
2. Join the game in Discord
3. The game announcement should now display the thumbnail and banner images

## Stopping the Tunnel

To stop the tunnel but keep other services running:

```bash
docker compose stop cloudflared
```

To stop all services:

```bash
docker compose down
```

## Troubleshooting

### Tunnel not connecting

- Verify your `CLOUDFLARE_TUNNEL_TOKEN` is correct in `env/env.dev`
- Check cloudflared logs: `docker compose logs cloudflared`
- Ensure the tunnel is active in the Cloudflare dashboard

### Images not displaying in Discord

- Verify `API_BASE_URL` in `env/env.dev` matches your tunnel's public URL
- Test the image endpoint directly: `curl https://your-domain.com/api/v1/games/{game-id}/thumbnail`
- Check bot logs: `docker compose logs bot`
- Ensure the bot service was restarted after changing `API_BASE_URL`

### 502 Bad Gateway

- Verify the tunnel is configured to route to `api:8000` (not `localhost:8000`)
- Ensure api service is running: `docker compose ps api`
- Check api logs: `docker compose logs api`

## Security Notes

- The tunnel token is sensitive - keep it secret and don't commit it to version control
- Consider using different tunnels for different environments (dev, staging, prod)
- You can configure access policies in Cloudflare Zero Trust to restrict who can access your tunnel

## Alternative: Free Subdomain

If you don't have a Cloudflare-managed domain, you can use Cloudflare's free `.trycloudflare.com` subdomains:

1. When creating the public hostname, choose **Quick Tunnels**
2. Cloudflare will generate a random subdomain like `https://random-words-123.trycloudflare.com`
3. Use this URL as your `API_BASE_URL`

Note: These free subdomains change each time you restart the tunnel, so they're best for quick testing.
