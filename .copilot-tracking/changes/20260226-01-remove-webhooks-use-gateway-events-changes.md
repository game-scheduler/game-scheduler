---
applyTo: '.copilot-tracking/changes/20260226-01-remove-webhooks-use-gateway-events-changes.md'
---

<!-- markdownlint-disable-file -->

# Changes Record: Remove Discord Webhooks and Use Gateway Events

## Overview

This document tracks all changes made during the implementation of removing Discord webhook infrastructure and replacing it with Discord gateway events for automatic guild synchronization.

## Implementation Progress

**Status**: In Progress
**Started**: 2026-02-26
**Phases Completed**: 2/6

## Changes Summary

### Added

_List of new files and functionality added during implementation_

### Modified

- [services/api/app.py](../../services/api/app.py) - Removed webhooks router import and registration
- [services/api/dependencies/**init**.py](../../services/api/dependencies/__init__.py) - Removed discord_webhook from exports
- [services/api/config.py](../../services/api/config.py) - Removed discord_public_key configuration field from APIConfig
- [config/env.dev](../../config/env.dev) - Removed DISCORD_PUBLIC_KEY configuration
- [config/env.int](../../config/env.int) - Removed DISCORD_PUBLIC_KEY configuration
- [config/env.e2e](../../config/env.e2e) - Removed DISCORD_PUBLIC_KEY configuration
- [config/env.staging](../../config/env.staging) - Removed DISCORD_PUBLIC_KEY configuration
- [config/env.prod](../../config/env.prod) - Removed DISCORD_PUBLIC_KEY configuration
- [config.template/env.template](../../config.template/env.template) - Removed DISCORD_PUBLIC_KEY configuration template
- [pyproject.toml](../../pyproject.toml) - Removed pynacl~=1.5.0 dependency
- [shared/messaging/events.py](../../shared/messaging/events.py) - Removed GUILD_SYNC_REQUESTED event definition
- [services/bot/events/handlers.py](../../services/bot/events/handlers.py) - Removed guild sync event handler registration and implementation
- [tests/services/bot/events/test_handlers.py](../../tests/services/bot/events/test_handlers.py) - Removed all test*handle_guild_sync_requested*\* tests

### Removed

- [services/api/routes/webhooks.py](../../services/api/routes/webhooks.py) - Deleted HTTP webhook endpoint
- [services/api/dependencies/discord_webhook.py](../../services/api/dependencies/discord_webhook.py) - Deleted Ed25519 signature validation
- [tests/services/api/routes/test_webhooks.py](../../tests/services/api/routes/test_webhooks.py) - Deleted webhook endpoint tests
- [tests/services/api/dependencies/test_discord_webhook.py](../../tests/services/api/dependencies/test_discord_webhook.py) - Deleted signature validation tests
- [tests/integration/test_webhooks.py](../../tests/integration/test_webhooks.py) - Deleted webhook integration tests
- [docs/deployment/discord-webhook-setup.md](../../docs/deployment/discord-webhook-setup.md) - Deleted webhook setup documentation

## Detailed Changes by Phase

### Phase 1: Remove Webhook Infrastructure

**Status**: Completed
**Tasks Completed**: 4/4

#### Task 1.1: Delete webhook files ✓

- Deleted 6 webhook-related files using rm command
- Removed all webhook endpoint and signature validation code
- Removed webhook tests and documentation

#### Task 1.2: Remove webhook router registration from API app ✓

- Removed webhooks import from services/api/app.py
- Removed webhooks.router registration from FastAPI app
- Removed discord_webhook from services/api/dependencies/**init**.py exports

#### Task 1.3: Remove DISCORD_PUBLIC_KEY configuration ✓

- Removed DISCORD_PUBLIC_KEY from 5 environment config files (dev, int, e2e, staging, prod)
- Removed DISCORD_PUBLIC_KEY from config.template/env.template
- Removed discord_public_key field from APIConfig class in services/api/config.py

#### Task 1.4: Remove PyNaCl dependency ✓

- Removed pynacl~=1.5.0 from pyproject.toml dependencies
- Ran `uv lock` successfully to update dependency lock file
- PyNaCl v1.5.0 removed from project

### Phase 2: Remove RabbitMQ Guild Sync Event

**Status**: Completed
**Tasks Completed**: 3/3

#### Task 2.1: Remove GUILD_SYNC_REQUESTED event definition ✓

- Removed GUILD_SYNC_REQUESTED = "guild.sync_requested" from shared/messaging/events.py
- Removed "Bot synchronization events" comment section

#### Task 2.2: Remove guild sync event handler from bot ✓

- Removed EventType.GUILD_SYNC_REQUESTED from \_handlers dict in services/bot/events/handlers.py
- Removed guild sync handler registration from start_consuming() method
- Removed entire \_handle_guild_sync_requested() method (39 lines)

#### Task 2.3: Remove event handler tests ✓

- Removed test_handle_guild_sync_requested_success test
- Removed test_handle_guild_sync_requested_no_config test
- Removed test_handle_guild_sync_requested_sync_failure test
- Removed test_handle_guild_sync_requested_empty_results test
- Total: 110 lines of test code removed
- Fixed test_event_handlers_initialization to remove GUILD_SYNC_REQUESTED assertion
- Fixed test_start_consuming to expect 7 handlers instead of 8
- Removed dangling @pytest.mark.asyncio decorator

### Phase 3: Update Bot on_guild_join Event (TDD)

**Status**: Not Started
**Tasks Completed**: 0/4

### Phase 4: Simplify GUI Sync Endpoint with Rate Limiting (TDD)

**Status**: Not Started
**Tasks Completed**: 0/4

### Phase 5: Remove Obsolete Functions

**Status**: Not Started
**Tasks Completed**: 0/2

### Phase 6: Verification and Cleanup

**Status**: Not Started
**Tasks Completed**: 0/2

## Notes

_Any important notes, decisions, or deviations from the plan_
