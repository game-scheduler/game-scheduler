---
applyTo: '.copilot-tracking/changes/20260318-01-discord-channel-link-location-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Channel Link Resolution in Game Location

## Overview

Extend the channel resolver to detect and validate `discord.com/channels/{gid}/{cid}` URLs in the game location field, converting valid same-guild links to `<#channel_id>` and returning typed errors for invalid ones.

## Objectives

- Detect discord.com channel URL format in the location field before the existing `#channel-name` pass
- Convert valid same-guild channel URLs to `<#channel_id>` notation (solving the ambiguous-name problem)
- Return a `not_found` error for discord.com URLs where the channel is not a valid text channel in the game's guild
- Pass through wrong-guild discord.com URLs silently, consistent with other plain URLs
- Update frontend `ChannelValidationErrors` alert title to cover both mention and URL errors

## Research Summary

### Project Files

- `services/api/services/channel_resolver.py` - Core resolver; `resolve_channel_mentions()` handles all substitution
- `services/api/services/games.py` - Calls resolver and raises `ValidationError` on errors
- `services/api/routes/games.py` - Catches `ValidationError`, returns HTTP 422
- `frontend/src/components/ChannelValidationErrors.tsx` - Renders channel errors; AlertTitle is hardcoded
- `tests/unit/services/api/services/test_channel_resolver.py` - Existing unit tests with async fixtures

### External References

- #file:../research/20260318-01-discord-channel-link-location-research.md - Verified findings: URL regex, logic table, frontend change spec, channel dict schema

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment guidelines

## Implementation Checklist

### [x] Phase 1: TDD - Write Failing Unit Tests

- [x] Task 1.1: Add unit tests for URL resolution cases to `test_channel_resolver.py`
  - Details: .copilot-tracking/planning/details/20260318-01-discord-channel-link-location-details.md (Lines 9-23)

### [x] Phase 2: Implement URL Resolution in Backend

- [x] Task 2.1: Add URL regex to `ChannelResolver.__init__` and refactor channel fetch
  - Details: .copilot-tracking/planning/details/20260318-01-discord-channel-link-location-details.md (Lines 25-40)

- [x] Task 2.2: Add URL detection loop to `resolve_channel_mentions`
  - Details: .copilot-tracking/planning/details/20260318-01-discord-channel-link-location-details.md (Lines 42-56)

### [x] Phase 3: Update Frontend Alert Title

- [x] Task 3.1: Update `AlertTitle` in `ChannelValidationErrors.tsx`
  - Details: .copilot-tracking/planning/details/20260318-01-discord-channel-link-location-details.md (Lines 58-72)

## Dependencies

- Python 3.13+, pytest, pytest-asyncio
- No new third-party libraries required

## Success Criteria

- Valid same-guild discord.com channel URL in location → stored as `<#channel_id>`
- Wrong-guild discord.com URL → game created unchanged, no error (consistent with plain URLs)
- Valid guild + channel not found → HTTP 422 with `not_found` error, game blocked
- Plain non-discord URLs → unchanged, no error
- Existing `#channel-name` behavior unchanged; all existing tests unmodified
- Frontend AlertTitle reads "Location contains an invalid channel reference"
