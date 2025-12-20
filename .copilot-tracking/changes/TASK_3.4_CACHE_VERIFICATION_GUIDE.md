# Task 3.4: Avatar Caching and Performance Verification Guide

## Overview

This guide provides practical steps to verify avatar caching behavior and performance in your development environment.

**Note:** This guide focuses on testing the **API service's avatar caching**, which is already implemented via DisplayNameResolver. The bot service currently makes uncached Discord API calls, which will be addressed in a future consolidation effort (see `.copilot-tracking/research/20251220-discord-client-consolidation-research.md`).

## Prerequisites

- Development environment running with `docker compose up`
- Access to Redis container
- Active Discord bot with test games

## Verification Steps

### 1. Monitor Cache Operations in Real-Time

Watch Redis commands as they happen to see cache hits and misses:

```bash
# Open a terminal and monitor all Redis commands
docker compose exec valkey redis-cli MONITOR
```

**What to look for:**
- `GET "display_avatar:<guild_id>:<user_id>"` - Cache read attempt
- `SETEX "display_avatar:<guild_id>:<user_id>" 300 ...` - Cache write with 300s TTL
- Multiple GETs without intervening SETs indicate cache hits

**Test procedure:**
1. Start the monitor
2. **Load a game page in the web frontend** (this triggers API calls with caching)
3. Observe the GET commands for display_avatar keys
4. Reload the same page within 5 minutes
5. You should see GET commands succeed (cache hit) without new SETs

**Note:** Discord bot embeds do NOT use this cache currently - they make direct Discord API calls. Only the web frontend API calls benefit from caching.

---

### 2. Inspect Cached Avatar Data

Check what's actually stored in the cache:

```bash
# List all display_avatar keys
docker compose exec valkey redis-cli KEYS "display_avatar:*"

# Get the value of a specific cache key (replace with actual guild_id and user_id)
docker compose exec valkey redis-cli GET "display_avatar:<guild_id>:<user_id>"

# Check TTL (time to live) of a key
docker compose exec valkey redis-cli TTL "display_avatar:<guild_id>:<user_id>"
```

**Expected results:**
- Keys should be in format: `display_avatar:<guild_id>:<user_id>`
- Values should be JSON with `display_name` and `avatar_url` fields
- TTL should be between 0-300 seconds (5 minutes)

**Example output:**
```json
{"display_name": "BretMckee", "avatar_url": "https://cdn.discordapp.com/guilds/123.../users/456.../avatars/abc123.png?size=64"}
```

---

### 3. Calculate Cache Hit Rate

Monitor cache hits vs misses over a period:

```bash
# Get Redis stats
docker compose exec valkey redis-cli INFO stats | grep keyspace

# Reset stats (optional, to start fresh)
docker compose exec valkey redis-cli CONFIG RESETSTAT

# After some usage, check hit rate
docker compose exec valkey redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
```

**Calculate hit rate:**
```
Hit Rate = keyspace_hits / (keyspace_hits + keyspace_misses) * 100%
```

**Target:** > 80% hit rate after loading the same games multiple times

**Test procedure:**
1. Reset stats
2. Load a game page 3 times in quick succession
3. Check stats - first load will miss, subsequent loads should hit
4. Expected: ~67% hit rate (1 miss + 2 hits)

---

### 4. Verify Cache TTL Enforcement

Confirm that cached data expires after 5 minutes:

```bash
# Watch a key's TTL countdown
watch -n 1 'docker compose exec valkey redis-cli TTL "display_avatar:<guild_id>:<user_id>"'
```

**Test procedure:**
1. Load a game page to populate cache
2. Immediately check TTL - should be ~300 seconds
3. Wait and observe TTL counting down
4. After TTL reaches 0, the key is deleted
5. Next access will be a cache miss and will re-fetch from Discord API

**Alternative approach:**
```bash
# Set a short TTL for testing
docker compose exec valkey redis-cli EXPIRE "display_avatar:<guild_id>:<user_id>" 10

# Watch it expire in 10 seconds
docker compose exec valkey redis-cli TTL "display_avatar:<guild_id>:<user_id>"
```

---

### 5. Monitor API Response Times

Check if avatar URL construction impacts performance:

```bash
# Watch API logs for slow queries
docker compose logs -f api | grep -E "GET /api/games|display_name"
```

**What to look for:**
- API responses should complete quickly (< 500ms)
- No significant difference in response time with vs without avatar URLs
- Cached lookups should be nearly instant

**Test procedure:**
1. Clear cache: `docker compose exec valkey redis-cli FLUSHDB`
2. Load game page (uncached - will hit Discord API)
3. Note response time from browser DevTools Network tab
4. Reload page (cached - should be faster)
5. Compare response times

---

### 6. Monitor Memory Usage

Ensure avatar caching doesn't cause excessive memory consumption:

```bash
# Check Redis memory usage
docker compose exec valkey redis-cli INFO memory | grep used_memory_human

# Monitor memory over time
watch -n 5 'docker compose exec valkey redis-cli INFO memory | grep -E "used_memory_human|maxmemory"'

# Count keys by pattern
docker compose exec valkey redis-cli --scan --pattern "display_avatar:*" | wc -l
```

**Expected results:**
- Memory usage should be reasonable (< 50MB for typical usage)
- Each cache entry is ~200-400 bytes (JSON with display name + avatar URL)
- Keys should expire and memory should not grow indefinitely

---

### 7. Test Cache Invalidation

Verify that cache updates when Discord data changes:

**Manual invalidation:**
```bash
# Delete a specific cache key to force refresh
docker compose exec valkey redis-cli DEL "display_avatar:<guild_id>:<user_id>"

# Delete all display_avatar keys
docker compose exec valkey redis-cli --scan --pattern "display_avatar:*" | xargs docker compose exec -T valkey redis-cli DEL
```

**Test procedure:**
1. Load a game page and note the host's display name/avatar
2. Change your Discord nickname or avatar in the guild
3. Wait for cache to expire (5 minutes) OR manually delete cache key
4. Reload game page
5. Verify updated name/avatar displays

---

### 8. Enable Debug Logging (Optional)

Add cache hit/miss logging to the display name resolver:

Edit `services/api/services/display_names.py` around line 167:

```python
for user_id in user_ids:
    cache_key = cache_keys.CacheKeys.display_name_avatar(user_id, guild_id)
    if self.cache:
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                result[user_id] = json.loads(cached)
                logger.debug(f"Cache hit for display_avatar: {cache_key}")  # ADD THIS
                continue
            except (json.JSONDecodeError, TypeError):
                logger.debug(f"Cache parse error for: {cache_key}")  # ADD THIS
                pass
    logger.debug(f"Cache miss for display_avatar: {cache_key}")  # ADD THIS
    uncached_ids.append(user_id)
```

Then check logs:
```bash
docker compose logs -f api | grep "Cache.*display_avatar"
```

---

## Success Criteria Checklist

**API Caching (Currently Implemented):**
- [ ] Cache keys are stored in correct format with guild_id and user_id
- [ ] Cached values are valid JSON with display_name and avatar_url fields
- [ ] TTL is enforced at 5 minutes (300 seconds)
- [ ] Cache hit rate > 80% for repeated web frontend access within TTL window
- [ ] API response times are acceptable (< 500ms)
- [ ] Memory usage remains stable and reasonable
- [ ] Manual cache deletion triggers re-fetch from Discord API
- [ ] No errors in logs related to cache operations

**Bot Caching (Not Yet Implemented):**
- Bot currently makes uncached Discord API calls for member display info
- This is acceptable for now and will be addressed in future work
- See research document: `.copilot-tracking/research/20251220-discord-client-consolidation-research.md`

## Common Issues

**Issue:** No display_avatar keys in Redis
- **Cause:** Cache might be disabled or API not calling resolve_display_names_and_avatars
- **Fix:** Check that games are being accessed and API is running

**Issue:** TTL always shows -1 (no expiration)
- **Cause:** Cache set without TTL parameter
- **Fix:** Verify SETEX command is used, not SET

**Issue:** Hit rate very low (< 50%)
- **Cause:** TTL too short, or keys expiring too quickly
- **Fix:** Verify TTL is 300 seconds, check if system time is correct

**Issue:** Memory growing continuously
- **Cause:** Keys not expiring, TTL not set
- **Fix:** Check that SETEX is used with 300s TTL, verify expiration works

## Notes

- The cache uses JSON serialization to store both display_name and avatar_url together
- Avatar URLs are full CDN URLs with size parameter (64px by default)
- Guild-specific avatars take priority over user global avatars
- Cache misses result in Discord API calls which count against rate limits (5000/hour)
