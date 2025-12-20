<!-- markdownlint-disable-file -->

# Release Changes: Discord API Client Consolidation

**Related Plan**: 20251220-discord-client-consolidation-plan.instructions.md
**Implementation Date**: 2025-12-20

## Summary

Consolidation of Discord API client from API service to shared layer, enabling cache sharing across API and bot services to reduce Discord API rate limit consumption.

## Changes

### Added

- [shared/discord/__init__.py](shared/discord/__init__.py) - Shared Discord API client module initialization and exports
- [shared/discord/client.py](shared/discord/client.py) - DiscordAPIClient moved from API service for cross-service usage
- [tests/shared/discord/__init__.py](tests/shared/discord/__init__.py) - Test package initialization for shared Discord tests
- [tests/shared/discord/test_client.py](tests/shared/discord/test_client.py) - Comprehensive unit tests for DiscordAPIClient (39 test cases covering all methods, error handling, caching, and concurrency)

### Modified

### Removed
