---
applyTo: '.copilot-tracking/changes/20260421-02-bot-rest-api-elimination-changes.md'
---

<!-- markdownlint-disable-file -->

# Change Record: Bot REST API Elimination

## Overview

Eliminate all non-message REST calls from the Discord bot: replace `fetch_member`, `fetch_channel`, and `fetch_user` with in-memory gateway equivalents, and move guild sync out of `setup_hook` into `on_ready`.

## Added

_(none yet)_

## Modified

- `tests/unit/services/bot/auth/test_role_checker.py` — Task 1.1: replaced all 11 `mock_guild.fetch_member = AsyncMock(...)` setups with `mock_guild.get_member = MagicMock(...)` (synchronous); added `mock_guild.fetch_member.assert_not_called()` assertions to every permission-check test; updated three `_member_not_found` docstrings to reflect cache-miss rather than REST-miss semantics
- `services/bot/auth/role_checker.py` — Task 1.2: replaced `await guild.fetch_member(int(user_id))` with `guild.get_member(int(user_id))` (removed `await`, synchronous call) in `check_manage_guild_permission`, `check_manage_channels_permission`, and `check_administrator_permission`
- `tests/unit/services/bot/events/test_handlers.py` — Task 2.1: added `bot.fetch_channel = AsyncMock()` to `mock_bot` fixture; renamed `test_get_bot_channel_fetch_required` to `test_get_bot_channel_not_in_cache_returns_none` with `fetch_channel.assert_not_called()`; replaced three `_validate_channel_for_refresh` tests (removing discord_api patches, adding `fetch_channel.assert_not_called()` assertions); replaced `test_fetch_channel_and_message_channel_not_cached` and `test_fetch_channel_and_message_invalid_channel` to assert no `fetch_channel` call
- `services/bot/events/handlers.py` — Task 2.2: removed `discord_api.fetch_channel()` pre-check and `bot.fetch_channel()` fallback from `_validate_channel_for_refresh`; removed `bot.fetch_channel()` fallback from `_get_bot_channel`; removed `bot.fetch_channel()` try/except fallback from `_fetch_channel_and_message`; all three methods now use `bot.get_channel()` only
- `tests/unit/services/bot/events/test_handlers.py` — Task 3.1: added `bot.get_user = MagicMock()` to `mock_bot` fixture; updated `test_handle_send_notification_success` to use `get_user` instead of `fetch_user`/`discord_api.fetch_user`; updated `test_handle_send_notification_dm_disabled` to use `get_user`; added `test_handle_send_notification_user_not_in_cache`; updated `test_handle_clone_confirmation_sends_dm_with_view` to use `get_user` and assert `fetch_user.assert_not_called()`; added `test_handle_clone_confirmation_user_not_in_cache`; removed stale `get_discord_client` patches from `test_handle_game_created_success` and `test_validate_channel_for_refresh_does_not_call_discord_api`
- `services/bot/events/handlers.py` — Task 3.2: removed `discord_api.fetch_user()` pre-check and `bot.fetch_user()` call from `_send_dm`; replaced with `bot.get_user()` (synchronous) with None-guard log+return; removed `bot.fetch_user()` from `_handle_clone_confirmation`; replaced with `bot.get_user()` with None-guard log+return; removed now-unused `get_discord_client` import

## Removed

_(none yet)_
