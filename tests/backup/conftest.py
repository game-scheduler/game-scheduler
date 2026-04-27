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


"""pytest configuration for backup/restore tests.

Re-exports shared fixtures from e2e conftest.  Overrides test_user_a and
defines synced_guild_created without cleanup so game data persists past pytest
teardown for the backup container to capture.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from tests.e2e.conftest import (  # noqa: F401
    DiscordTestEnvironment,
    GuildContext,
    authenticated_admin_client,
    bot_discord_id,
    discord_archive_channel_id,
    discord_channel_b_id,
    discord_channel_id,
    discord_guild_b_id,
    discord_guild_id,
    discord_helper,
    discord_ids,
    discord_token,
    discord_user_b_id,
    discord_user_b_token,
    discord_user_id,
    guild_a_db_id,
    guild_a_template_id,
    guild_b_db_id,
    guild_b_template_id,
    wait_for_game_message_id,
)

__all__ = ["bot_discord_id", "discord_ids"]


@pytest.fixture
async def test_user_a(
    admin_db: AsyncSession,
    bot_discord_id: str,
):
    """Find or create User A — no cleanup so FK constraints don't block teardown."""
    result = await admin_db.execute(
        text("SELECT id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": bot_discord_id},
    )
    row = result.fetchone()
    if row is None:
        user = User(discord_id=bot_discord_id)
        admin_db.add(user)
        await admin_db.commit()
        await admin_db.refresh(user)
    else:
        user = await admin_db.get(User, str(row[0]))
    assert user is not None
    return user


@pytest.fixture
async def synced_guild_created(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
    test_user_a: User,
) -> AsyncGenerator[GuildContext]:
    """Create Guild A without cleanup so data persists for the backup container."""
    guild_db_id = str(uuid4())
    channel_db_id = str(uuid4())
    template_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    await admin_db.execute(
        text("DELETE FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_ids.guild_a_id},
    )
    await admin_db.commit()

    await admin_db.execute(
        text(
            """
            INSERT INTO guild_configurations (id, guild_id, created_at, updated_at)
            VALUES (:id, :guild_id, :created_at, :updated_at)
            """
        ),
        {
            "id": guild_db_id,
            "guild_id": discord_ids.guild_a_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    await admin_db.execute(
        text(
            """
            INSERT INTO channel_configurations
                (id, channel_id, guild_id, created_at, updated_at)
            VALUES
                (:id, :channel_id, :guild_id, :created_at, :updated_at)
            """
        ),
        {
            "id": channel_db_id,
            "channel_id": discord_ids.channel_a_id,
            "guild_id": guild_db_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    await admin_db.execute(
        text(
            """
            INSERT INTO game_templates
            (id, guild_id, channel_id, name, is_default, created_at, updated_at)
            VALUES (:id, :guild_id, :channel_id, :name, :is_default, :created_at, :updated_at)
            """
        ),
        {
            "id": template_id,
            "guild_id": guild_db_id,
            "channel_id": channel_db_id,
            "name": "Default Template",
            "is_default": True,
            "created_at": now,
            "updated_at": now,
        },
    )

    await admin_db.commit()

    return GuildContext(
        db_id=guild_db_id,
        discord_id=discord_ids.guild_a_id,
        channel_db_id=channel_db_id,
        channel_discord_id=discord_ids.channel_a_id,
        template_id=template_id,
    )


@pytest.fixture
async def synced_guild_existing(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
) -> AsyncGenerator[GuildContext]:
    """Look up the existing Guild A by discord_id — no create, no cleanup.

    Used by Phase 2 to reuse the guild left by Phase 1 without touching it.
    """
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_ids.guild_a_id},
    )
    row = result.fetchone()
    assert row is not None, f"Guild {discord_ids.guild_a_id} not found — ensure Phase 1 has run"
    guild_db_id = str(row[0])

    result = await admin_db.execute(
        text("SELECT id FROM channel_configurations WHERE guild_id = :guild_id LIMIT 1"),
        {"guild_id": guild_db_id},
    )
    row = result.fetchone()
    assert row is not None, f"Channel for guild {guild_db_id} not found"
    channel_db_id = str(row[0])

    result = await admin_db.execute(
        text(
            "SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true LIMIT 1"
        ),
        {"guild_id": guild_db_id},
    )
    row = result.fetchone()
    assert row is not None, f"Default template for guild {guild_db_id} not found"
    template_id = str(row[0])

    return GuildContext(
        db_id=guild_db_id,
        discord_id=discord_ids.guild_a_id,
        channel_db_id=channel_db_id,
        channel_discord_id=discord_ids.channel_a_id,
        template_id=template_id,
    )
