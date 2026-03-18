<!-- markdownlint-disable-file -->

# Changes: Discord Channel Link Resolution in Game Location

## Overview

Extends the channel resolver to detect and validate `discord.com/channels/{gid}/{cid}` URLs in game
location text, converting valid same-guild links to `<#channel_id>` and returning typed errors for
invalid same-guild references. Updates the frontend alert title to cover both mention and URL errors.

## Status

Complete

## Added

- `tests/unit/services/api/services/test_channel_resolver.py` — Added 5 new unit tests covering
  same-guild URL substitution, wrong-guild URL pass-through, same-guild channel not found, non-text
  channel not found, and URL coexisting with a `#` mention in the same string.

## Modified

- `services/api/services/channel_resolver.py` — Added `_discord_channel_url_pattern` compiled
  regex to `__init__`; refactored `resolve_channel_mentions` to fetch channels unconditionally when
  either URL or `#` patterns are present; added URL detection pass before the existing `#` pass
  implementing the three-branch logic (wrong guild → pass-through, channel not found → `not_found`
  error, valid → replace with `<#channel_id>`).
- `frontend/src/components/ChannelValidationErrors.tsx` — Changed `AlertTitle` from
  "Could not resolve some #channel mentions" to "Location contains an invalid channel reference".

## Removed
