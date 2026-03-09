---
applyTo: '.copilot-tracking/changes/20260308-04-auth-oauth-testing-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Auth Route Testing via Fake Discord Server

## Overview

Enable full integration-test coverage for all 5 auth endpoints by making Discord API URLs configurable and standing up a fake Discord HTTP service.

## Objectives

- Refactor `DiscordAPIClient` to accept a configurable `api_base_url` at construction time
- Add `discord_api_base_url` and `discord_oauth_url` config fields to `ApiConfig`; add `discord_api_base_url` to bot config
- Wire both `DiscordAPIClient()` callsites and `oauth2.py` to use config-driven URLs
- Add a `fake-discord` service to `compose.int.yaml` serving canned token, user, and guilds responses
- Write integration tests for `GET /auth/login`, `GET /auth/callback`, `GET /auth/refresh`, `GET /auth/logout`, `GET /auth/me` covering success and error paths
- Achieve this with no `patch()` calls — all interactions go through the real request path

## Research Summary

### Project Files

- `shared/discord/client.py` — `DiscordAPIClient` with 4 hardcoded module-level URL constants; no `api_base_url` parameter
- `services/api/auth/oauth2.py` — `DISCORD_OAUTH_URL` module-level constant; `exchange_code()` and `refresh_token()` call `DiscordAPIClient`
- `services/api/dependencies/discord.py` — only API callsite constructing `DiscordAPIClient()` (line 44)
- `services/bot/dependencies/discord_client.py` — only bot callsite constructing `DiscordAPIClient()` (line 44)
- `services/api/routes/auth.py` — 5 endpoints; 26% coverage at last measurement
- `tests/e2e/conftest.py` — pre-seeds tokens directly into Redis; OAuth flow never exercised
- `compose.int.yaml` — integration compose file to receive new `fake-discord` service

### External References

- #file:../research/20260308-04-auth-oauth-testing-research.md — full research with code examples and approach rationale

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/integration-tests.instructions.md — integration test patterns
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/task-implementation.instructions.md — implementation tracking

## Implementation Checklist

### [x] Phase 1: `DiscordAPIClient` URL Refactor (TDD)

- [x] Task 1.1: Add `api_base_url` stub parameter to `DiscordAPIClient.__init__` (accepted but URLs still use module constants)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 22-42)

- [x] Task 1.2: Write unit tests verifying `api_base_url` controls request URLs — mark as `@pytest.mark.xfail` (RED)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 43-62)

- [x] Task 1.3: Implement full URL refactor — move module-level constants to `self._*` instance attributes; update all internal references; remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 63-85)

- [x] Task 1.4: Refactor — verify default (no arg) still targets real Discord; remove module-level URL constants entirely
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 86-97)

### [x] Phase 2: Config + OAuth URL Wiring (TDD)

- [x] Task 2.1: Add `discord_api_base_url` and `discord_oauth_url` stub fields to `ApiConfig`; add `discord_api_base_url` to bot config with defaults matching current hardcoded values
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 100-118)

- [x] Task 2.2: Write unit tests verifying config fields are forwarded to `DiscordAPIClient` and `oauth2.py` — mark as `@pytest.mark.xfail` (RED)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 119-135)

- [x] Task 2.3: Wire both `DiscordAPIClient()` callsites to pass `api_base_url=config.discord_api_base_url`; update `oauth2.py` to read `discord_oauth_url` from `ApiConfig`; remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 136-155)

- [x] Task 2.4: Refactor — confirm no module-level URL constants remain in `oauth2.py`; run existing tests to confirm no regressions
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 156-165)

### [ ] Phase 3: Fake Discord Service (Infrastructure)

- [ ] Task 3.1: Create `tests/integration/fixtures/fake_discord_app.py` — minimal `aiohttp.web` script with configurable token, user, and guilds handlers; HTTP entry point for standalone execution
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 168-204)

- [ ] Task 3.2: Add `fake-discord` service to `compose.int.yaml` using `fake_discord_app.py`; set `DISCORD_API_BASE_URL=http://fake-discord:8080` on the `api` service in the integration compose file
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 205-222)

### [ ] Phase 4: Auth Integration Tests (TDD)

- [ ] Task 4.1: Create `tests/integration/test_auth_routes.py` skeleton with placeholder structure and imports
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 225-237)

- [ ] Task 4.2: Write integration tests for all 5 auth endpoints covering primary success paths — mark all as `@pytest.mark.xfail` (RED)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 238-285)

- [ ] Task 4.3: Verify tests pass against fake Discord service; remove xfail markers (GREEN)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 286-295)

- [ ] Task 4.4: Add error-path and edge-case tests (state mismatch, Discord 5xx, missing session, expired token)
  - Details: .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md (Lines 296-316)

## Dependencies

- `aiohttp` (already in `pyproject.toml`) — used for fake Discord server
- Phase 1 must complete before Phase 2
- Phases 1 and 2 must complete before Phase 3 and 4
- **Prerequisite**: Doc 03 coverage collection fix must be landed before beginning this work to ensure test results are trustworthy (per research guidance)

## Success Criteria

- All unit tests for `DiscordAPIClient` URL behavior pass with no xfail markers remaining
- `ApiConfig` and bot config expose `discord_api_base_url`; `ApiConfig` also exposes `discord_oauth_url`
- Both production `DiscordAPIClient()` callsites pass URL from config; `oauth2.py` reads `discord_oauth_url` from config
- `fake-discord` service starts cleanly in `compose.int.yaml` and is reachable from the `api` container
- Integration tests exercise all 5 auth endpoints via real HTTP to the API container with no `patch()` calls
- All new and modified code passes lint checks and pre-commit hooks
