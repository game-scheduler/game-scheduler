# Changes: Channel Recognition Bug Fixes

## Status

Phase 2 complete.

## Added

- `services/api/services/channel_resolver.py` — Added module-level `render_where_display(where, channels)` function that replaces `<#id>` tokens with `#name` using a pre-fetched channel list
- `services/api/services/channel_resolver.py` — Added private `_check_snowflake_tokens` helper method to `ChannelResolver` that validates `<#id>` tokens against the guild channel list
- `shared/discord/client.py` — Added module-level `get_guild_channels_safe(guild_id, client)` helper that fetches guild channels via the global client singleton with error handling (returns `[]` on failure), following the `fetch_channel_name_safe` pattern
- `tests/unit/services/api/routes/test_games_helpers.py` — Added `TestBuildGameResponse` class with test asserting `where_display` is populated by `render_where_display` when `game.where` contains a `<#id>` token

## Modified

- `services/api/services/channel_resolver.py` — Changed `_channel_mention_pattern` regex from `#([\w-]+)` to `(?<!<)#([^\s<>]+)` to accept emoji/Unicode channel names (Bug 1 fix)
- `services/api/services/channel_resolver.py` — Added `_snowflake_token_pattern` and snowflake detection to `resolve_channel_mentions`; valid `<#id>` tokens pass through silently, invalid ones produce a `not_found` error (Bug 2 fix)
- `shared/schemas/game.py` — Added `where_display: str | None` field to `GameResponse` with default `None`
- `services/api/routes/games.py` — Updated `_build_game_response` to call `get_guild_channels_safe` and `render_where_display`, populating `where_display` in `GameResponse`; also imported `get_guild_channels_safe`
- `tests/unit/services/api/routes/test_channel_resolver.py` — Added 5 regression tests: emoji channel name resolution, valid `<#id>` token accepted, unknown `<#id>` token error, `render_where_display` with `None`, and `render_where_display` token substitution; all written as `xfail` first then made passing
- `tests/unit/services/api/routes/test_games_helpers.py` — Added `_build_game_response` and `ParticipantResponse` to imports
- `tests/unit/services/api/routes/test_games_participant_count.py` — Added `get_guild_channels_safe` patch to all 4 tests that call `_build_game_response`
- `tests/unit/services/api/routes/test_games_timezone.py` — Added `get_guild_channels_safe` patch to all 4 tests that call `_build_game_response`

## Removed

None.

## Divergences from Plan

None.
