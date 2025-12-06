# Deployment Quick Start

## Setting Up on a New Server

### 1. Configure Your Environment

Copy `.env.example` to `.env` and configure it for your server:

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
# Leave API_URL empty to use nginx proxy (works with any hostname)
API_URL=

# Set to your actual frontend URL
FRONTEND_URL=http://your-server-ip:3000

# Configure Discord OAuth callback
DISCORD_REDIRECT_URI=http://your-server-ip:8000/api/v1/auth/callback

# Set your Discord credentials
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret

# Change default passwords!
POSTGRES_PASSWORD=change_me
RABBITMQ_DEFAULT_PASS=change_me
RABBITMQ_URL=amqp://gamebot:change_me@rabbitmq:5672/
```

### 2. Build and Start

```bash
docker compose build
docker compose up -d
```

The init container will:

1. Run database migrations
2. Initialize RabbitMQ infrastructure (exchanges, queues, bindings)
3. Complete before application services start

### 3. Verify

Check that all services are running:

```bash
docker compose ps
```

Access the frontend at `http://your-server-ip:3000`

## Changing the API URL Later

No rebuild needed! Just update `.env` and restart the frontend:

```bash
# Edit .env and change API_URL
nano .env

# Restart only the frontend container
docker compose restart frontend
```

See [RUNTIME_CONFIG.md](RUNTIME_CONFIG.md) for more details.

## Using Different Hostnames/IPs

The default configuration (with `API_URL=` empty) uses nginx proxy mode, which
means:

- Access via `http://localhost:3000` - works ✓
- Access via `http://192.168.1.100:3000` - works ✓
- Access via `http://your-domain.com:3000` - works ✓

No configuration changes needed when accessing from different hostnames!

**How proxy mode works:**

1. User accesses: `http://your-server:3000`
2. Frontend makes requests to: `/api/v1/auth/user` (relative URL)
3. Nginx proxies internally to: `http://api:8000/api/v1/auth/user` (Docker
   network)

This is why `API_URL` can remain empty - the nginx proxy handles routing.

## When to Set API_URL

Only set `API_URL` if your API is on a **completely different server/domain**
than your frontend:

```bash
# Example: Frontend at https://game.example.com, API at https://api.example.com
API_URL=https://api.example.com
```

For the standard docker-compose deployment where both services run on the same
server, **leave API_URL empty**.

## Infrastructure Initialization

The init container automatically sets up:

- **Database:** Runs all Alembic migrations to create/update schema
- **RabbitMQ:** Creates exchanges, queues, and routing bindings

This happens automatically on first startup and ensures all services find
infrastructure ready.

## Credentials and Security

**Important:** Change all default passwords in `.env` before deployment:

```bash
# Database password
POSTGRES_PASSWORD=use_a_strong_random_password

# RabbitMQ password
RABBITMQ_DEFAULT_PASS=use_a_different_strong_password
RABBITMQ_URL=amqp://gamebot:use_a_different_strong_password@rabbitmq:5672/

# Discord credentials
DISCORD_CLIENT_SECRET=from_discord_developer_portal
```

**Note:** RabbitMQ credentials are set at runtime via environment variables. The
same container image works across all environments (dev, test, prod) with
different credentials.
