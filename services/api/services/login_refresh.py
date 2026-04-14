# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Background task for refreshing display names at login time."""

import logging

from sqlalchemy import select

from services.api.auth.oauth2 import get_user_guilds
from services.api.database.queries import setup_rls_and_convert_guild_ids
from services.api.dependencies.discord import get_discord_client
from services.api.services.user_display_names import UserDisplayNameService
from shared.data_access.guild_isolation import clear_current_guild_ids
from shared.database import AsyncSessionLocal
from shared.discord.client import DiscordAPIError
from shared.models.guild import GuildConfiguration

logger = logging.getLogger(__name__)


def _resolve_member_display_name(member: dict) -> str:
    return member.get("nick") or member["user"].get("global_name") or member["user"]["username"]


def _resolve_member_avatar_url(
    user_discord_id: str, guild_discord_id: str, member: dict
) -> str | None:
    member_avatar = member.get("avatar")
    user_avatar = member["user"].get("avatar")
    if member_avatar:
        return f"https://cdn.discordapp.com/guilds/{guild_discord_id}/users/{user_discord_id}/avatars/{member_avatar}.png?size=64"
    if user_avatar:
        return f"https://cdn.discordapp.com/avatars/{user_discord_id}/{user_avatar}.png?size=64"
    return None


async def refresh_display_name_on_login(
    user_discord_id: str,
    access_token: str,
) -> None:
    """
    Refresh the logged-in user's display name across all bot-registered guilds.

    Runs as a FastAPI background task after the OAuth callback so it does not
    block the login response. Uses the user's own OAuth token, leaving the bot
    token rate limit budget untouched.
    """
    logger.info("refresh_display_name_on_login: started for user %s", user_discord_id)
    try:
        user_guilds = await get_user_guilds(access_token, user_discord_id)
        discord_guild_ids = [g["id"] for g in user_guilds]
        async with AsyncSessionLocal() as db:
            await setup_rls_and_convert_guild_ids(db, discord_guild_ids)
            result = await db.execute(select(GuildConfiguration))
            guilds = result.scalars().all()

            logger.info(
                "refresh_display_name_on_login: found %d guild(s) for user %s",
                len(guilds),
                user_discord_id,
            )

            if not guilds:
                return

            client = get_discord_client()
            entries = []

            for guild_config in guilds:
                logger.info(
                    "refresh_display_name_on_login: fetching member data from guild %s for user %s",
                    guild_config.guild_id,
                    user_discord_id,
                )
                try:
                    member = await client.get_current_user_guild_member(
                        guild_config.guild_id, access_token
                    )
                except DiscordAPIError as e:
                    logger.info(
                        "refresh_display_name_on_login: skipping guild %s for user %s (%s)",
                        guild_config.guild_id,
                        user_discord_id,
                        e,
                    )
                    continue

                entries.append({
                    "user_discord_id": user_discord_id,
                    "guild_discord_id": guild_config.guild_id,
                    "display_name": _resolve_member_display_name(member),
                    "avatar_url": _resolve_member_avatar_url(
                        user_discord_id, guild_config.guild_id, member
                    ),
                })

            logger.info(
                "refresh_display_name_on_login: upserting %d entries for user %s",
                len(entries),
                user_discord_id,
            )
            service = UserDisplayNameService(db=db)
            await service.upsert_batch(entries)
            await db.commit()
            logger.info("refresh_display_name_on_login: completed for user %s", user_discord_id)
    except Exception:
        logger.exception(
            "refresh_display_name_on_login: unhandled error for user %s", user_discord_id
        )
    finally:
        clear_current_guild_ids()
