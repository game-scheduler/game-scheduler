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

## Removed

_(none yet)_
