---
applyTo: '.copilot-tracking/plans/20260308-04-auth-oauth-testing.plan.md'
---

<!-- markdownlint-disable-file -->

# Changes: Auth Route Testing via Fake Discord Server

## Summary

Enabling full integration-test coverage for all 5 auth endpoints by making Discord API URLs configurable and standing up a fake Discord HTTP service.

## Added

- `tests/unit/shared/discord/test_client.py` — Added `discord_client_fake_base` fixture, `_mock_session_returning` helper, and 4 tests verifying `api_base_url` controls all HTTP request URLs (`exchange_code`, `refresh_token`, `get_user_info`, `get_guilds`) — Tasks 1.2/1.3
- `tests/unit/test_discord_dependency.py` — New test file with 3 tests verifying config fields are forwarded: API dependency passes `discord_api_base_url`, bot dependency passes `discord_api_base_url`, `generate_authorization_url` uses `discord_oauth_url` — Tasks 2.2/2.3

## Modified

- `shared/discord/client.py` — Added `api_base_url: str = "https://discord.com/api/v10"` parameter to `DiscordAPIClient.__init__`; added `self._token_url`, `self._user_url`, `self._guilds_url` instance attributes derived from `api_base_url`; replaced all internal module-level URL constant usages with instance attributes across all 12 methods; removed the four module-level URL constants entirely — Tasks 1.1/1.3/1.4
- `tests/unit/shared/discord/test_client.py` — Removed `DISCORD_API_BASE` import (constant deleted); hardcoded expected URL in `test_get_application_info_uses_correct_url`; added `MagicMock` to imports — Tasks 1.2/1.4
- `services/api/config.py` — Added `discord_api_base_url` and `discord_oauth_url` fields to `APIConfig` with defaults matching current hardcoded values; both read from env vars `DISCORD_API_BASE_URL` and `DISCORD_OAUTH_URL` — Task 2.1
- `services/bot/config.py` — Added `discord_api_base_url` pydantic Field to `BotConfig` with default `"https://discord.com/api/v10"`; reads from `DISCORD_API_BASE_URL` env var — Task 2.1
- `services/api/dependencies/discord.py` — Added `api_base_url=api_config.discord_api_base_url` to `DiscordAPIClient()` constructor call — Task 2.3
- `services/bot/dependencies/discord_client.py` — Added `api_base_url=bot_config.discord_api_base_url` to `DiscordAPIClient()` constructor call — Task 2.3
- `services/api/auth/oauth2.py` — Removed `DISCORD_OAUTH_URL` module-level constant; `generate_authorization_url` now reads `api_config.discord_oauth_url` from `APIConfig` — Task 2.3

## Removed

<!-- Files removed by implementation -->

---

## Phase Progress

### Phase 1: `DiscordAPIClient` URL Refactor (TDD) — COMPLETE ✓

All Tasks 1.1–1.4 complete. 153 unit tests pass; 0 lint violations.

### Phase 2: Config + OAuth URL Wiring (TDD) — COMPLETE ✓

All Tasks 2.1–2.4 complete. 156 unit tests pass; 0 lint violations.
