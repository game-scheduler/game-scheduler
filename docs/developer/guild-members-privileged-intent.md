# Why We Need the GUILD_MEMBERS Privileged Gateway Intent

## Background

The game scheduler needs two pieces of per-user, per-guild data at the time a
user logs in and whenever they access guild-specific resources:

- **Role IDs** — used to enforce host restrictions, bot-manager permissions, and
  player-role gating on game sign-ups
- **Display name and avatar** — guild nickname (falling back to global name, then
  username) shown in the web dashboard participant lists

This document explains why we cannot obtain this data reliably from Discord's
REST API without the `GUILD_MEMBERS` privileged Gateway intent, and what that
intent provides.

## The REST API Options

Discord exposes three relevant endpoints:

### `GET /users/@me/guilds/{guild.id}/member` (OAuth token)

- Requires the `guilds.members.read` OAuth2 scope
- Returns the authenticated user's own member object for one guild
- **Rate limit: 5 requests per ~5 minutes, with one shared bucket across all
  calls for that user**

This means fetching a user's membership across 3 guilds costs 3 of 5 available
slots. A second login within the 5-minute window hits an empty bucket.

### `GET /guilds/{guild.id}/members/{user.id}` (bot token)

- Uses the bot token; no OAuth scope required
- Returns any member's object for one guild
- **Rate limit: 5 requests per ~5 minutes, per guild (independent buckets)**

Because each guild is a separate bucket, multiple concurrent users logging in
to the same guild compete for the same 5-slot window. Three users logging in
simultaneously consume 3 of 5 slots for each of their shared guilds. There is
no batch equivalent — every user × guild pair requires its own call.

### `GET /guilds/{guild.id}/members` (bot token, list all)

- Paginated list of all members in a guild
- **Explicitly requires the `GUILD_MEMBERS` privileged intent to be enabled**

This is not a viable workaround: it requires the same privileged intent, is
paginated (multiple requests for large guilds), and returns far more data than
needed.

### No batch or multi-guild endpoint exists

There is no Discord REST endpoint that returns role or display-name data for
a given user across all their guilds in a single call. Every approach requires
one HTTP round-trip per guild the user is in.

## Why the Rate Limits Make REST Impractical

A typical user is in 2–4 guilds that the bot monitors. At login, the
`login_refresh` background task fetches each guild's member data sequentially.
From staging measurements:

| Step                        | Time         |
| --------------------------- | ------------ |
| `get_guilds` cold fetch     | ~456 ms      |
| member fetch per guild (×3) | ~175 ms each |
| Total background task       | ~1076 ms     |

The 5-calls-per-5-minutes budget means:

- A user who refreshes their session or logs out and back in within 5 minutes
  will exhaust the budget before all guilds are fetched
- Multiple users logging in to the same guild simultaneously share the same
  per-guild bucket (3 concurrent logins = 3 of 5 slots consumed per shared
  guild at the same time)
- Any retry or cache miss — for example when the 5-minute Redis TTL expires and
  a request arrives — spends another slot from the same constrained pool

The REST endpoints were designed for occasional, user-triggered membership
verification (e.g. checking if a specific user is still in a server before
sending a DM). They were not designed to serve as a polling or cache-warming
mechanism for an application that needs current role and display-name data on
every request.

## What the GUILD_MEMBERS Privileged Intent Provides

When `GUILD_MEMBERS` is enabled:

- Discord sends a full member list as part of the `GUILD_CREATE` event when the
  bot connects, covering every member in every guild the bot is in
- `GUILD_MEMBER_ADD`, `GUILD_MEMBER_UPDATE`, and `GUILD_MEMBER_REMOVE` events
  arrive in real time as memberships and roles change
- `discord.py` maintains an in-process member cache populated from these events
- The bot can write role IDs and display names from interaction payloads and
  gateway events directly to Redis without any REST calls at all

This eliminates all per-user REST member fetches from the login path and from
display-name resolution, replacing them with a single write-through from data
that Discord pushes to the bot unprompted.

## Privileged Intent Requirements

Enabling `GUILD_MEMBERS` requires:

1. Toggling the intent on in the Discord Developer Portal for the application
2. For bots in **100 or more servers**: submitting a verification request to
   Discord explaining the use case

The game scheduler's bot is currently in a small number of servers and does
not require the verification step.

## Trade-offs Accepted

|                              | Without `GUILD_MEMBERS`                      | With `GUILD_MEMBERS`                             |
| ---------------------------- | -------------------------------------------- | ------------------------------------------------ |
| Rate limit pressure at login | High (N REST calls per user)                 | None                                             |
| Data freshness               | 5-minute Redis TTL, stale between logins     | Real-time via gateway events                     |
| REST calls for display names | 1 per user per guild per cache miss          | 0 (written from events)                          |
| Bot memory usage             | Low                                          | Higher (full member objects in discord.py cache) |
| Discord approval needed      | No                                           | Only for 100+ server bots                        |
| Login race condition         | Possible (background task vs. games request) | Eliminated                                       |
