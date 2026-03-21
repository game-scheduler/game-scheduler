<!-- markdownlint-disable-file -->

# Changes: Rewards Feature

## Summary

Add `rewards` (nullable text) and `remind_host_rewards` (bool) to game sessions and
templates, wire them through the API and bot, add a spoiler display in Discord and on
the web, a "Save and Archive" shortcut button, and a host completion-reminder DM.

## Added

- `alembic/versions/20260321_add_rewards_fields.py` — migration adding `rewards TEXT NULL` and `remind_host_rewards BOOLEAN NOT NULL DEFAULT false` to `game_sessions`, and `remind_host_rewards BOOLEAN NOT NULL DEFAULT false` to `game_templates` (Task 1.1)

## Modified

## Removed
