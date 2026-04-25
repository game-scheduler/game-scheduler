<!-- markdownlint-disable-file -->

# Changes: Remove Dead Discord REST Methods

## Summary

Remove 9 dead `DiscordAPIClient` REST methods, 3 batch OTEL metric declarations, the `oauth2.get_user_guilds()` wrapper, 3 dead `CacheOperation` enum entries, and ~50 dead unit tests.

## Status

Complete

---

## Removed

### Phase 1: shared/discord/client.py

- [shared/discord/client.py](../../../shared/discord/client.py) — Task 1.1: removed `_batch_size_histogram`, `_batch_not_found_counter`, `_batch_duration_histogram` module-level OTEL metric declarations
- [shared/discord/client.py](../../../shared/discord/client.py) — Task 1.2: removed `get_guilds()`, `_handle_rate_limit_response()`, `_process_guilds_response()`, `_fetch_guilds_uncached()` methods
- [shared/discord/client.py](../../../shared/discord/client.py) — Task 1.3: removed `fetch_user()`, `get_guild_member()`, `get_guild_members_batch()`, `get_current_user_guild_member()` methods
- [shared/discord/client.py](../../../shared/discord/client.py) — Task 1.4: removed module-level `fetch_user_display_name_safe()` function

### Phase 2: oauth2.py and cache/operations.py

- [services/api/auth/oauth2.py](../../../services/api/auth/oauth2.py) — Task 2.1: removed `get_user_guilds()` function
- [shared/cache/operations.py](../../../shared/cache/operations.py) — Task 2.2: removed `FETCH_USER`, `GET_GUILD_MEMBER`, `GET_USER_GUILDS` entries from `CacheOperation` enum

### Phase 3: tests/unit/shared/discord/test_discord_api_client.py

- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Tasks 3.1–3.2: deleted `TestGuildMethods` and `TestUnifiedTokenFunctionality` classes (entire)
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Task 3.3: removed `test_fetch_user_cache_miss` and `test_fetch_user_cache_hit` from `TestCachedResourceMethods`
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Task 3.4: deleted standalone `test_get_guilds_uses_api_base_url`, `TestProcessGuildsResponseHttpError`, and `TestFetchGuildsUncachedSafetyRaise`
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Task 3.5: removed 3 `test_fetch_user_display_name_safe_*` tests from `TestHelperFunctions`
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Task 3.6: removed `test_fetch_user_delegates_to_get_or_fetch` and `test_get_guild_member_delegates_to_get_or_fetch` from `TestReadThroughDelegatesToGetOrFetch`; deleted `TestGetCurrentUserGuildMember` class
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Task 3.7: updated 2 `TestGetOrFetch` tests to replace `CacheOperation.FETCH_USER` with `CacheOperation.FETCH_GUILD`
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Also deleted `TestGuildMemberMethods` and `TestConcurrencyAndLocking` (all-dead classes identified in research but omitted from plan tasks)

### Phase 4: tests/unit/services/api/auth/test_oauth2.py

- [tests/unit/services/api/auth/test_oauth2.py](../../../tests/unit/services/api/auth/test_oauth2.py) — Task 4.1: removed `test_get_user_guilds` from `TestOAuth2Flow`; removed `get_user_guilds` from import

### Additional test cleanup (cascade from Phase 2)

Removing `oauth2.get_user_guilds` required cleaning up `patch()` calls in tests that still referenced the removed function:

- [tests/conftest.py](../../../tests/conftest.py) — removed `mock_oauth2_get_user_guilds` autouse fixture (patched the removed function)
- [tests/unit/shared/cache/test_operations.py](../../../tests/unit/shared/cache/test_operations.py) — removed `fetch_user`, `get_guild_member`, `get_user_guilds` from `_EXPECTED_OPERATIONS` set
- [tests/unit/services/api/routes/test_auth_routes.py](../../../tests/unit/services/api/routes/test_auth_routes.py) — removed dead `oauth2.get_user_guilds` patch from `test_get_user_info_no_guilds_field`
- [tests/unit/services/api/routes/test_guilds_routes.py](../../../tests/unit/services/api/routes/test_guilds_routes.py) — removed dead `oauth2.get_user_guilds` patches from multiple tests
- [tests/unit/services/api/database/test_queries.py](../../../tests/unit/services/api/database/test_queries.py) — removed dead `oauth2.get_user_guilds` patches from two tests
- [tests/unit/services/api/test_database_dependencies.py](../../../tests/unit/services/api/test_database_dependencies.py) — removed dead `oauth2.get_user_guilds` patch from regression test
- [tests/unit/services/api/test_negative_authorization.py](../../../tests/unit/services/api/test_negative_authorization.py) — removed dead `oauth2.get_user_guilds` patches from 7 tests
