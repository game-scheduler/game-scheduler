# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Minimal fake Discord API server for integration tests.

Serves canned responses for the three Discord API endpoints used by the auth
flow. Response bodies are configurable via environment variables so compose
overrides can inject specific payloads without rebuilding the image.

Run standalone:
    python tests/integration/fixtures/fake_discord_app.py

Environment variables:
    PORT                  Listening port (default: 8080)
    FAKE_TOKEN_RESPONSE   JSON for POST /api/v10/oauth2/token (default: see below)
    FAKE_USER_RESPONSE    JSON for GET  /api/v10/users/@me    (default: see below)
    FAKE_GUILDS_RESPONSE  JSON for GET  /api/v10/users/@me/guilds (default: [])
"""

import asyncio
import json
import os
import signal

from aiohttp import web

_DEFAULT_TOKEN_RESPONSE = {
    "access_token": "fake.access_token",
    "refresh_token": "fake.refresh_token",
    "token_type": "Bearer",
    "expires_in": 604800,
    "scope": "identify guilds",
}

_DEFAULT_USER_RESPONSE = {
    "id": "123456789012345678",
    "username": "testuser",
    "discriminator": "0",
    "global_name": "Test User",
    "avatar": None,
}


def _load_response(env_var: str, default: object) -> object:
    raw = os.environ.get(env_var)
    if raw:
        return json.loads(raw)
    return default


def build_app() -> web.Application:
    token_response = _load_response("FAKE_TOKEN_RESPONSE", _DEFAULT_TOKEN_RESPONSE)
    user_response = _load_response("FAKE_USER_RESPONSE", _DEFAULT_USER_RESPONSE)
    guilds_response = _load_response("FAKE_GUILDS_RESPONSE", [])

    async def token_handler(request: web.Request) -> web.Response:
        data = await request.post()
        if data.get("code") == "error_trigger":
            return web.json_response({"error": "server_error"}, status=500)
        if data.get("refresh_token") == "error_refresh":
            return web.json_response({"error": "invalid_grant"}, status=401)
        return web.json_response(token_response)

    async def user_handler(_request: web.Request) -> web.Response:
        return web.json_response(user_response)

    async def guilds_handler(_request: web.Request) -> web.Response:
        return web.json_response(guilds_response)

    app = web.Application()
    app.router.add_post("/api/v10/oauth2/token", token_handler)
    app.router.add_get("/api/v10/users/@me", user_handler)
    app.router.add_get("/api/v10/users/@me/guilds", guilds_handler)
    return app


async def _main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    app = build_app()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)

    await stop_event.wait()
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(_main())
