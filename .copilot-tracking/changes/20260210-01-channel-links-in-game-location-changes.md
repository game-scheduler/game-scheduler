<!-- markdownlint-disable-file -->

# Release Changes: Discord Channel Links in Game Location Field

**Related Plan**: 20260210-01-channel-links-in-game-location-plan.instructions.md
**Implementation Date**: 2026-02-10

## Summary

Enable users to reference Discord channels in game location field using `#channel-name` format, with backend validation that converts mentions to clickable Discord channel links (`<#channel_id>`) in game announcements.

## Changes

### Added

- services/api/services/channel_resolver.py - Created ChannelResolver service stub with resolve_channel_mentions method raising NotImplementedError
- tests/services/api/services/test_channel_resolver.py - Created comprehensive unit tests testing actual desired behavior (7 test cases: single match returns `<#id>` format, disambiguation returns errors with suggestions, not found returns errors with suggestions, special characters work, mixed content resolves, empty text handled, plain text unchanged) - Tests properly fail with NotImplementedError (TDD RED phase)

### Modified

- services/api/services/channel_resolver.py - Implemented resolve_channel_mentions with regex pattern r'#([\w-]+)', Discord API channel lookup, single match conversion to <#id>, multiple match disambiguation errors, not found errors with fuzzy suggestions (TDD GREEN phase - all tests passing). Fixed line length formatting (E501).
- tests/services/api/services/test_channel_resolver.py - Added 8 edge case tests: multiple mentions in one location, channel at text start/end, adjacent mentions, empty guild channel list, filtering non-text channels, case-insensitive matching, mixed valid/invalid channels. Total 15 tests, 100% code coverage.

### Removed
