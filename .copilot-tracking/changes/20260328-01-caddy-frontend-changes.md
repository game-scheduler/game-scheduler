<!-- markdownlint-disable-file -->

# Changes: Replace nginx Frontend with Caddy (SSL Termination)

## Summary

Replacing the nginx production frontend container with Caddy to provide automatic Let's Encrypt SSL in production while maintaining plain HTTP in staging.

---

## Added

- `docker/Caddyfile.staging` — new Caddyfile for staging: plain HTTP on `:80`, replicates all nginx behavior (gzip, security headers, SSE proxy, API proxy, SPA routing, static asset caching)
- `docker/Caddyfile.prod` — new Caddyfile for production: automatic HTTPS via Let's Encrypt using `{$DOMAIN}` and `{$ACME_EMAIL}` env vars

## Modified

- `docker/frontend.Dockerfile` — replaced `nginx:1.28-alpine` production stage with `caddy:2-alpine`; assets to `/srv`; fixed leftover nginx CMD/entrypoint lines: config template now at `/srv/templates/`, entrypoint at `/usr/local/bin/`, CMD replaced with `caddy run`; `ENTRYPOINT` wrapper pattern added
- `compose.yaml` — renamed `NGINX_LOG_LEVEL` to `FRONTEND_LOG_LEVEL` on frontend service (mapped to container `LOG_LEVEL`); added `Caddyfile.staging` volume mount
- `compose.staging.yaml` — renamed `NGINX_LOG_LEVEL: debug` to `LOG_LEVEL: debug` on frontend service; added `Caddyfile.staging` volume mount
- `compose.prod.yaml` — added `Caddyfile.prod` volume mount, `caddy_data`/`caddy_config` named volumes, and ports 80/443/443udp to frontend service; added top-level `volumes:` section
- `config/env.prod` — replaced `NGINX_LOG_LEVEL` with `FRONTEND_LOG_LEVEL`; added `DOMAIN=` and `ACME_EMAIL=` entries
- `config/env.dev` — replaced `NGINX_LOG_LEVEL` with `FRONTEND_LOG_LEVEL`; added `DOMAIN` and `ACME_EMAIL` as commented-out entries
- `config/env.staging` — replaced `NGINX_LOG_LEVEL` with `FRONTEND_LOG_LEVEL`; added `DOMAIN` and `ACME_EMAIL` as commented-out entries
- `config/env.e2e` — replaced `# NGINX_LOG_LEVEL` with `# FRONTEND_LOG_LEVEL`; added `DOMAIN` and `ACME_EMAIL` as commented-out entries
- `config/env.int` — replaced `# NGINX_LOG_LEVEL` with `# FRONTEND_LOG_LEVEL`; added `DOMAIN` and `ACME_EMAIL` as commented-out entries
- `docker/frontend-entrypoint.sh` — updated for Caddy: writes `config.js` to `/srv/config.js` (from `/srv/templates/config.template.js`); removed nginx log-level substitution; added `exec "$@"` to hand off to Caddy as CMD

## Removed

- `docker/frontend-nginx.conf` — deleted; no longer referenced in any Dockerfile or compose file
