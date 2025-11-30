# Runtime Configuration

The frontend supports runtime configuration, allowing you to change the API URL without rebuilding the Docker image.

## How It Works

1. At container startup, the frontend entrypoint script (`docker/frontend-entrypoint.sh`) reads the `API_URL` environment variable
2. It generates `/usr/share/nginx/html/config.js` by substituting the value into the template
3. The frontend loads this config file before the React app starts
4. The app uses the runtime configuration instead of build-time values

## Configuration

### When to Use Each Mode

**Use Proxy Mode (API_URL empty) when:**

- Frontend and API are accessed through the same hostname/IP
- Using the provided nginx proxy configuration (default docker-compose setup)
- You want maximum flexibility (works with any hostname: localhost, IP, domain)
- Both services are in the same Docker network

**Use Direct API Access (API_URL set) when:**

- API is on a completely different domain/server than the frontend
- Example: Frontend at `https://game-scheduler.example.com`, API at `https://api.example.com`
- You need to bypass the nginx proxy for some reason

### For Proxy Mode (Recommended for Standard Deployment)

Leave `API_URL` empty in your `.env` file:

```bash
API_URL=
```

**How it works:**

1. User accesses: `http://your-server:3000`
2. Frontend makes requests to: `/api/v1/auth/user` (relative URL)
3. Nginx proxies to: `http://api:8000/api/v1/auth/user` (internal Docker network)

This works whether users access via `localhost`, `192.168.1.100`, or any domain name.

### For Direct API Access

Set `API_URL` to your backend's full URL:

```bash
# Local development (if not using docker-compose)
API_URL=http://localhost:8000

# Production with separate API domain
API_URL=https://api.example.com

# Production with separate API server
API_URL=http://192.168.1.100:8000
```

**Note:** In the standard docker-compose deployment, port 8000 is exposed, but using direct access is less flexible than proxy mode.

## Changing Configuration

To change the API URL on a running system:

1. Update the `API_URL` value in your `.env` file
2. Restart only the frontend container:
   ```bash
   docker compose restart frontend
   ```

No rebuild required! The new configuration takes effect immediately.

## Development

During local development with `npm run dev`, the frontend uses:

1. `VITE_API_URL` environment variable (if set)
2. Vite proxy configuration (in `vite.config.ts`)

The runtime config mechanism only applies to production Docker deployments.
