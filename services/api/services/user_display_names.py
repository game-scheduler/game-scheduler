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


"""Persistent display name cache service backed by the user_display_names table."""

import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services.display_names import DisplayNameResolver
from shared.models.user_display_name import UserDisplayName

logger = logging.getLogger(__name__)


class UserDisplayNameService:
    """Wraps DisplayNameResolver with a DB read/write layer for persistence.

    The resolver is optional; bot handlers that only call upsert_one / upsert_batch
    may pass None.
    """

    def __init__(self, db: AsyncSession, resolver: DisplayNameResolver | None = None) -> None:
        self._db = db
        self._resolver = resolver

    async def resolve(
        self, guild_discord_id: str, user_discord_ids: list[str]
    ) -> dict[str, dict[str, str | None]]:
        """
        Resolve display names and avatars for a list of users in a guild.

        Checks DB first; falls through to DisplayNameResolver for any misses,
        then upserts the fetched data.
        """
        if not user_discord_ids:
            return {}

        stmt = select(UserDisplayName).where(
            UserDisplayName.guild_discord_id == guild_discord_id,
            UserDisplayName.user_discord_id.in_(user_discord_ids),
        )
        result = await self._db.execute(stmt)
        rows = result.scalars().all()

        cached: dict[str, dict[str, str | None]] = {
            row.user_discord_id: {
                "display_name": row.display_name,
                "avatar_url": row.avatar_url,
            }
            for row in rows
        }

        missing_ids = [uid for uid in user_discord_ids if uid not in cached]
        if missing_ids:
            if self._resolver is None:
                msg = "DisplayNameResolver required for resolve() but not provided"
                raise RuntimeError(msg)
            fetched = await self._resolver.resolve_display_names_and_avatars(
                guild_discord_id, missing_ids
            )
            entries = [
                {
                    "user_discord_id": uid,
                    "guild_discord_id": guild_discord_id,
                    "display_name": data["display_name"],
                    "avatar_url": data["avatar_url"],
                }
                for uid, data in fetched.items()
            ]
            await self.upsert_batch(entries)
            cached.update(fetched)

        return cached

    async def upsert_one(
        self,
        user_discord_id: str,
        guild_discord_id: str,
        display_name: str,
        avatar_url: str | None,
    ) -> None:
        """Insert or update a single display name row."""
        await self.upsert_batch([
            {
                "user_discord_id": user_discord_id,
                "guild_discord_id": guild_discord_id,
                "display_name": display_name,
                "avatar_url": avatar_url,
            }
        ])

    async def upsert_batch(
        self,
        entries: list[dict],
    ) -> None:
        """Bulk insert-or-update display name rows."""
        if not entries:
            return

        stmt = (
            insert(UserDisplayName)
            .values(entries)
            .on_conflict_do_update(
                index_elements=["user_discord_id", "guild_discord_id"],
                set_={
                    "display_name": insert(UserDisplayName).excluded.display_name,
                    "avatar_url": insert(UserDisplayName).excluded.avatar_url,
                    "updated_at": func.now(),
                },
            )
        )
        await self._db.execute(stmt)
