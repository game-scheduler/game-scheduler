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


"""Integration tests for guild sync channel operations.

Tests verify:
- Channel sync adds new Discord channels to database
- Channel sync marks deleted Discord channels as inactive
- Channel sync reactivates previously inactive channels
- list_guild_channels endpoint filters inactive channels
- Foreign key integrity maintained with inactive channels
- Sync response returns accurate counts

These tests run against actual PostgreSQL database using shared test fixtures.
Discord client is mocked since integration tests don't have Discord connectivity.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text

from services.api.database import queries
from services.api.services.guild_service import _sync_guild_channels, sync_user_guilds
from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_sync_new_guild_creates_channels_with_active_flag(
    admin_db,
    create_guild,
):
    """Verify new guild sync creates channels with is_active=True."""
    guild = create_guild()
    mock_client = AsyncMock()
    mock_client.get_guild_channels.return_value = [
        {"id": "100001", "name": "general", "type": 0},
        {"id": "100002", "name": "announcements", "type": 0},
    ]

    with patch(
        "services.api.services.guild_service.get_discord_client",
        return_value=mock_client,
    ):
        updated_count = await _sync_guild_channels(
            admin_db,
            mock_client,
            guild["id"],
            guild["guild_id"],
        )
        await admin_db.commit()

    assert updated_count == 2

    channels = await queries.get_channels_by_guild(admin_db, guild["id"])
    assert len(channels) == 2
    for channel in channels:
        assert channel.is_active is True


@pytest.mark.asyncio
async def test_sync_existing_guild_adds_new_discord_channels(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
):
    """Verify existing guild sync adds new Discord channels to database."""
    guild = create_guild()
    _existing_channel = create_channel(guild_id=guild["id"], discord_channel_id="200001")

    mock_client = AsyncMock()
    mock_client.get_guild_channels.return_value = [
        {"id": "200001", "name": "existing", "type": 0},
        {"id": "200002", "name": "new-channel", "type": 0},
        {"id": "200003", "name": "another-new", "type": 0},
    ]

    with patch(
        "services.api.services.guild_service.get_discord_client",
        return_value=mock_client,
    ):
        updated_count = await _sync_guild_channels(
            admin_db,
            mock_client,
            guild["id"],
            guild["guild_id"],
        )
        await admin_db.commit()

    assert updated_count == 2

    channels = await queries.get_channels_by_guild(admin_db, guild["id"])
    assert len(channels) == 3

    channel_ids = {ch.channel_id for ch in channels}
    assert "200001" in channel_ids
    assert "200002" in channel_ids
    assert "200003" in channel_ids

    for channel in channels:
        assert channel.is_active is True


@pytest.mark.asyncio
async def test_sync_existing_guild_marks_deleted_channels_inactive(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
):
    """Verify sync marks Discord-deleted channels as is_active=False."""
    guild = create_guild()
    _channel_keep = create_channel(guild_id=guild["id"], discord_channel_id="300001")
    _channel_delete = create_channel(guild_id=guild["id"], discord_channel_id="300002")

    mock_client = AsyncMock()
    mock_client.get_guild_channels.return_value = [
        {"id": "300001", "name": "kept-channel", "type": 0},
    ]

    with patch(
        "services.api.services.guild_service.get_discord_client",
        return_value=mock_client,
    ):
        updated_count = await _sync_guild_channels(
            admin_db,
            mock_client,
            guild["id"],
            guild["guild_id"],
        )
        await admin_db.commit()

    assert updated_count == 1

    channels = await queries.get_channels_by_guild(admin_db, guild["id"])
    assert len(channels) == 1
    assert channels[0].channel_id == "300001"
    assert channels[0].is_active is True

    # Verify deleted channel is marked inactive (check all channels, not just active)
    result = await admin_db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild["id"])
    )
    all_channels = result.scalars().all()
    assert len(all_channels) == 2

    inactive_channel = next(ch for ch in all_channels if ch.channel_id == "300002")
    assert inactive_channel.is_active is False


@pytest.mark.asyncio
async def test_sync_reactivates_previously_inactive_channels(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
):
    """Verify sync reactivates channels that were previously inactive."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"], discord_channel_id="400001")

    # Manually mark channel as inactive
    admin_db_sync.execute(
        text("UPDATE channel_configurations SET is_active = false WHERE id = :id"),
        {"id": channel["id"]},
    )
    admin_db_sync.commit()

    mock_client = AsyncMock()
    mock_client.get_guild_channels.return_value = [
        {"id": "400001", "name": "reactivated-channel", "type": 0},
    ]

    with patch(
        "services.api.services.guild_service.get_discord_client",
        return_value=mock_client,
    ):
        updated_count = await _sync_guild_channels(
            admin_db,
            mock_client,
            guild["id"],
            guild["guild_id"],
        )
        await admin_db.commit()

    assert updated_count == 1

    channels = await queries.get_channels_by_guild(admin_db, guild["id"])
    assert len(channels) == 1
    assert channels[0].channel_id == "400001"
    assert channels[0].is_active is True


@pytest.mark.asyncio
async def test_multiple_guild_sync_returns_accurate_counts(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
):
    """Verify sync_user_guilds returns accurate counts for new and updated channels."""
    # Create guilds with specific Discord IDs
    guild_a_data = create_guild()
    guild_b_data = create_guild()

    # Update Discord IDs to match our mock
    admin_db_sync.execute(
        text("UPDATE guild_configurations SET guild_id = :new_id WHERE id = :id"),
        {"id": guild_a_data["id"], "new_id": "500001"},
    )
    admin_db_sync.execute(
        text("UPDATE guild_configurations SET guild_id = :new_id WHERE id = :id"),
        {"id": guild_b_data["id"], "new_id": "500002"},
    )
    admin_db_sync.commit()

    # Create existing channel for guild B
    _existing_channel = create_channel(guild_id=guild_b_data["id"], discord_channel_id="600001")

    mock_client = AsyncMock()

    def get_channels_side_effect(guild_discord_id):
        if guild_discord_id == "500001":
            return [
                {"id": "600011", "name": "guild-a-chan1", "type": 0},
                {"id": "600012", "name": "guild-a-chan2", "type": 0},
            ]
        if guild_discord_id == "500002":
            return [
                {"id": "600001", "name": "existing", "type": 0},
                {"id": "600002", "name": "new-in-guild-b", "type": 0},
            ]
        return []

    mock_client.get_guild_channels.side_effect = get_channels_side_effect
    mock_client.get_bot_guilds.return_value = [
        {"id": "500001", "name": "Guild A"},
        {"id": "500002", "name": "Guild B"},
    ]
    mock_client.get_guilds.return_value = [
        {
            "id": "500001",
            "name": "Guild A",
            "permissions": "32",
        },  # MANAGE_GUILD permission
        {"id": "500002", "name": "Guild B", "permissions": "32"},
    ]

    with (
        patch(
            "services.api.services.guild_service.get_discord_client",
            return_value=mock_client,
        ),
        patch("services.api.services.guild_service.channel_service") as mock_channel_svc,
    ):
        mock_channel_svc.create_channel_config = AsyncMock()

        result = await sync_user_guilds(
            admin_db,
            access_token="test-token",
            user_id="test-user",
        )
        await admin_db.commit()

    assert result["new_guilds"] == 0  # Both guilds already exist
    assert result["updated_channels"] == 3  # 2 in guild A, 1 in guild B


@pytest.mark.asyncio
async def test_inactive_channels_preserved_with_foreign_keys(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    create_template,
    create_game,
):
    """Verify inactive channels preserve foreign key relationships with games."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"], discord_channel_id="700001")
    user = create_user()
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    game_data = {
        "guild_id": guild["id"],
        "channel_id": channel["id"],
        "host_id": user["id"],
        "title": "Test Game",
        "description": "Test Description",
        "scheduled_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        "max_players": 4,
        "template_id": template["id"],
    }
    game = create_game(**game_data)

    mock_client = AsyncMock()
    mock_client.get_guild_channels.return_value = []

    with patch(
        "services.api.services.guild_service.get_discord_client",
        return_value=mock_client,
    ):
        updated_count = await _sync_guild_channels(
            admin_db,
            mock_client,
            guild["id"],
            guild["guild_id"],
        )
        await admin_db.commit()

    assert updated_count == 1

    result = await admin_db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.id == channel["id"])
    )
    updated_channel = result.scalar_one()
    assert updated_channel.is_active is False

    result = await admin_db.execute(select(GameSession).where(GameSession.id == game["id"]))
    game_check = result.scalar_one()
    assert game_check.channel_id == channel["id"]


@pytest.mark.asyncio
async def test_list_channels_filters_inactive_channels(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
):
    """Verify get_channels_by_guild returns only active channels."""
    guild = create_guild()
    _active_channel = create_channel(guild_id=guild["id"], discord_channel_id="800001")
    inactive_channel = create_channel(guild_id=guild["id"], discord_channel_id="800002")

    # Mark second channel as inactive
    admin_db_sync.execute(
        text("UPDATE channel_configurations SET is_active = false WHERE id = :id"),
        {"id": inactive_channel["id"]},
    )
    admin_db_sync.commit()

    all_channels_query = await admin_db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild["id"])
    )
    all_channels = all_channels_query.scalars().all()
    assert len(all_channels) == 2

    active_channels = await queries.get_channels_by_guild(admin_db, guild["id"])
    assert len(active_channels) == 1
    assert active_channels[0].channel_id == "800001"
    assert active_channels[0].is_active is True


@pytest.mark.asyncio
async def test_sync_no_changes_returns_zero_count(
    admin_db,
    create_guild,
    create_channel,
):
    """Verify sync with no changes returns zero updated count."""
    guild = create_guild()
    _channel = create_channel(guild_id=guild["id"], discord_channel_id="900001")

    mock_client = AsyncMock()
    mock_client.get_guild_channels.return_value = [
        {"id": "900001", "name": "unchanged", "type": 0},
    ]

    with patch(
        "services.api.services.guild_service.get_discord_client",
        return_value=mock_client,
    ):
        updated_count = await _sync_guild_channels(
            admin_db,
            mock_client,
            guild["id"],
            guild["guild_id"],
        )
        await admin_db.commit()

    assert updated_count == 0
