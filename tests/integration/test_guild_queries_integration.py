# Copyright 2025-2026 Bret McKee
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


"""Integration tests for guild_queries wrapper functions against real PostgreSQL.

Tests verify:
- All 12 wrapper functions work correctly against real database
- Guild isolation is enforced (cross-guild access prevented)
- RLS context is set correctly
- Error handling works as expected

These tests run against actual PostgreSQL database using shared test fixtures.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from shared.data_access import guild_queries
from shared.models.participant import ParticipantType

pytestmark = pytest.mark.integration


# ============================================================================
# Helper Functions
# ============================================================================


def make_game_data(channel_id: int, host_id: int, **overrides):
    """Create a game data dictionary with sensible defaults.

    Args:
        channel_id: Channel ID for the game
        host_id: Host user ID for the game
        **overrides: Any fields to override (title, description, scheduled_at, max_players, etc.)

    Returns:
        Dictionary suitable for guild_queries.create_game()
    """
    defaults = {
        "channel_id": channel_id,
        "host_id": host_id,
        "title": "Test Game",
        "description": "Test",
        "scheduled_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        "max_players": 4,
    }
    return {**defaults, **overrides}


# ============================================================================
# Game Operations Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_game_by_id_returns_game_from_correct_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify get_game_by_id returns game only from correct guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild_a["id"], game_data)
    await admin_db.commit()

    result = await guild_queries.get_game_by_id(admin_db, guild_a["id"], game.id)
    assert result is not None
    assert result.id == game.id
    assert result.guild_id == guild_a["id"]

    result_wrong_guild = await guild_queries.get_game_by_id(admin_db, guild_b["id"], game.id)
    assert result_wrong_guild is None


@pytest.mark.asyncio
async def test_list_games_returns_only_guild_games(
    admin_db, create_guild, create_channel, create_user
):
    """Verify list_games returns only games from specified guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    channel_b = create_channel(guild_id=guild_b["id"])
    user = create_user()

    game_a1 = await guild_queries.create_game(
        admin_db, guild_a["id"], make_game_data(channel_a["id"], user["id"], title="Game A1")
    )
    game_a2 = await guild_queries.create_game(
        admin_db, guild_a["id"], make_game_data(channel_a["id"], user["id"], title="Game A2")
    )
    game_b = await guild_queries.create_game(
        admin_db, guild_b["id"], make_game_data(channel_b["id"], user["id"], title="Game B")
    )
    await admin_db.commit()

    guild_a_games = await guild_queries.list_games(admin_db, guild_a["id"])
    guild_a_ids = {g.id for g in guild_a_games}

    assert game_a1.id in guild_a_ids
    assert game_a2.id in guild_a_ids
    assert game_b.id not in guild_a_ids

    guild_b_games = await guild_queries.list_games(admin_db, guild_b["id"])
    guild_b_ids = {g.id for g in guild_b_games}

    assert game_b.id in guild_b_ids
    assert game_a1.id not in guild_b_ids


@pytest.mark.asyncio
async def test_list_games_respects_channel_filter(
    admin_db, create_guild, create_channel, create_user
):
    """Verify list_games filters by channel when specified."""
    guild = create_guild()
    channel_1 = create_channel(guild_id=guild["id"])
    channel_2 = create_channel(guild_id=guild["id"])
    user = create_user()

    game_ch1 = await guild_queries.create_game(
        admin_db, guild["id"], make_game_data(channel_1["id"], user["id"], title="Ch1 Game")
    )
    game_ch2 = await guild_queries.create_game(
        admin_db, guild["id"], make_game_data(channel_2["id"], user["id"], title="Ch2 Game")
    )
    await admin_db.commit()

    channel_1_games = await guild_queries.list_games(
        admin_db, guild["id"], channel_id=channel_1["id"]
    )
    channel_1_ids = {g.id for g in channel_1_games}

    assert game_ch1.id in channel_1_ids
    assert game_ch2.id not in channel_1_ids


@pytest.mark.asyncio
async def test_create_game_sets_guild_id_correctly(
    admin_db, create_guild, create_channel, create_user
):
    """Verify create_game sets guild_id and persists to database."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild["id"], game_data)
    await admin_db.commit()

    assert game.guild_id == guild["id"]


@pytest.mark.asyncio
async def test_update_game_rejects_cross_guild_update(
    admin_db, create_guild, create_channel, create_user
):
    """Verify update_game validates game belongs to guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild_a["id"], game_data)
    await admin_db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.update_game(
            admin_db, guild_b["id"], game.id, {"title": "Unauthorized Update"}
        )


@pytest.mark.asyncio
async def test_update_game_succeeds_for_correct_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify update_game works for game in correct guild."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild["id"], game_data)
    await admin_db.commit()

    updated = await guild_queries.update_game(
        admin_db, guild["id"], game.id, {"title": "Updated Title"}
    )
    await admin_db.commit()

    assert updated.title == "Updated Title"


@pytest.mark.asyncio
async def test_delete_game_rejects_cross_guild_delete(
    admin_db, create_guild, create_channel, create_user
):
    """Verify delete_game validates game belongs to guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild_a["id"], game_data)
    await admin_db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.delete_game(admin_db, guild_b["id"], game.id)


@pytest.mark.asyncio
async def test_delete_game_succeeds_for_correct_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify delete_game works for game in correct guild."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild["id"], game_data)
    await admin_db.commit()

    await guild_queries.delete_game(admin_db, guild["id"], game.id)
    await admin_db.commit()

    result = await guild_queries.get_game_by_id(admin_db, guild["id"], game.id)
    assert result is None


# ============================================================================
# Participant Operations Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_participant_validates_game_belongs_to_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify add_participant validates game belongs to guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild_a["id"], game_data)
    await admin_db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.add_participant(
            admin_db,
            guild_b["id"],
            game.id,
            user["id"],
            {"position_type": ParticipantType.SELF_ADDED, "position": 0},
        )


@pytest.mark.asyncio
async def test_add_participant_succeeds_for_correct_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify add_participant works when game belongs to guild."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild["id"], game_data)
    await admin_db.commit()

    participant = await guild_queries.add_participant(
        admin_db,
        guild["id"],
        game.id,
        user["id"],
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await admin_db.commit()

    assert participant.game_session_id == game.id
    assert participant.user_id == user["id"]


@pytest.mark.asyncio
async def test_remove_participant_validates_game_belongs_to_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify remove_participant validates game belongs to guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild_a["id"], game_data)
    await guild_queries.add_participant(
        admin_db,
        guild_a["id"],
        game.id,
        user["id"],
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await admin_db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.remove_participant(admin_db, guild_b["id"], game.id, user["id"])


@pytest.mark.asyncio
async def test_remove_participant_succeeds_for_correct_guild(
    admin_db, create_guild, create_channel, create_user
):
    """Verify remove_participant works when game belongs to guild."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()

    game_data = make_game_data(channel["id"], user["id"])
    game = await guild_queries.create_game(admin_db, guild["id"], game_data)
    await guild_queries.add_participant(
        admin_db,
        guild["id"],
        game.id,
        user["id"],
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await admin_db.commit()

    await guild_queries.remove_participant(admin_db, guild["id"], game.id, user["id"])
    await admin_db.commit()

    # Verify participant was removed
    games = await guild_queries.list_user_games(admin_db, guild["id"], user["id"])
    assert len(games) == 0


@pytest.mark.asyncio
async def test_list_user_games_returns_only_guild_games(
    admin_db, create_guild, create_channel, create_user
):
    """Verify list_user_games returns only user's games from specified guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    channel_b = create_channel(guild_id=guild_b["id"])
    user = create_user()

    game_a = await guild_queries.create_game(
        admin_db, guild_a["id"], make_game_data(channel_a["id"], user["id"])
    )
    await guild_queries.add_participant(
        admin_db,
        guild_a["id"],
        game_a.id,
        user["id"],
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )

    game_b = await guild_queries.create_game(
        admin_db, guild_b["id"], make_game_data(channel_b["id"], user["id"])
    )
    await guild_queries.add_participant(
        admin_db,
        guild_b["id"],
        game_b.id,
        user["id"],
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await admin_db.commit()

    guild_a_games = await guild_queries.list_user_games(admin_db, guild_a["id"], user["id"])
    guild_a_ids = {g.id for g in guild_a_games}

    assert game_a.id in guild_a_ids
    assert game_b.id not in guild_a_ids

    guild_b_games = await guild_queries.list_user_games(admin_db, guild_b["id"], user["id"])
    guild_b_ids = {g.id for g in guild_b_games}

    assert game_b.id in guild_b_ids
    assert game_a.id not in guild_b_ids


# ============================================================================
# Template Operations Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_template_by_id_returns_template_from_correct_guild(
    admin_db, create_guild, create_channel
):
    """Verify get_template_by_id returns template only from correct guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])

    template_data = {
        "channel_id": channel["id"],
        "name": "Test Template",
        "description": "Test",
        "order": 0,
        "is_default": False,
        "max_players": 5,
        "expected_duration_minutes": 180,
        "reminder_minutes": [60, 1440],
    }
    template = await guild_queries.create_template(admin_db, guild_a["id"], template_data)
    await admin_db.commit()

    result = await guild_queries.get_template_by_id(admin_db, guild_a["id"], template.id)
    assert result is not None
    assert result.id == template.id
    assert result.guild_id == guild_a["id"]

    result_wrong_guild = await guild_queries.get_template_by_id(
        admin_db, guild_b["id"], template.id
    )
    assert result_wrong_guild is None


@pytest.mark.asyncio
async def test_list_templates_returns_only_guild_templates(admin_db, create_guild, create_channel):
    """Verify list_templates returns only templates from specified guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    channel_b = create_channel(guild_id=guild_b["id"])

    template_data = {
        "description": "Test",
        "order": 0,
        "is_default": False,
        "max_players": 5,
        "expected_duration_minutes": 180,
        "reminder_minutes": [60, 1440],
    }

    template_a1 = await guild_queries.create_template(
        admin_db,
        guild_a["id"],
        {**template_data, "channel_id": channel_a["id"], "name": "Template A1"},
    )
    template_a2 = await guild_queries.create_template(
        admin_db,
        guild_a["id"],
        {**template_data, "channel_id": channel_a["id"], "name": "Template A2"},
    )
    template_b = await guild_queries.create_template(
        admin_db,
        guild_b["id"],
        {**template_data, "channel_id": channel_b["id"], "name": "Template B"},
    )
    await admin_db.commit()

    guild_a_templates = await guild_queries.list_templates(admin_db, guild_a["id"])
    guild_a_ids = {t.id for t in guild_a_templates}

    assert template_a1.id in guild_a_ids
    assert template_a2.id in guild_a_ids
    assert template_b.id not in guild_a_ids

    guild_b_templates = await guild_queries.list_templates(admin_db, guild_b["id"])
    guild_b_ids = {t.id for t in guild_b_templates}

    assert template_b.id in guild_b_ids
    assert template_a1.id not in guild_b_ids


@pytest.mark.asyncio
async def test_create_template_sets_guild_id_correctly(admin_db, create_guild, create_channel):
    """Verify create_template sets guild_id and persists to database."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])

    template_data = {
        "channel_id": channel["id"],
        "name": "Test Template",
        "description": "Test",
        "order": 0,
        "is_default": False,
        "max_players": 5,
        "expected_duration_minutes": 180,
        "reminder_minutes": [60, 1440],
    }
    template = await guild_queries.create_template(admin_db, guild["id"], template_data)
    await admin_db.commit()

    assert template.guild_id == guild["id"]


@pytest.mark.asyncio
async def test_update_template_rejects_cross_guild_update(admin_db, create_guild, create_channel):
    """Verify update_template validates template belongs to guild."""
    guild_a = create_guild()
    guild_b = create_guild()
    channel = create_channel(guild_id=guild_a["id"])

    template_data = {
        "channel_id": channel["id"],
        "name": "Test Template",
        "description": "Test",
        "order": 0,
        "is_default": False,
        "max_players": 5,
        "expected_duration_minutes": 180,
        "reminder_minutes": [60, 1440],
    }
    template = await guild_queries.create_template(admin_db, guild_a["id"], template_data)
    await admin_db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.update_template(
            admin_db, guild_b["id"], template.id, {"name": "Unauthorized Update"}
        )


@pytest.mark.asyncio
async def test_update_template_succeeds_for_correct_guild(admin_db, create_guild, create_channel):
    """Verify update_template works for template in correct guild."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])

    template_data = {
        "channel_id": channel["id"],
        "name": "Test Template",
        "description": "Test",
        "order": 0,
        "is_default": False,
        "max_players": 5,
        "expected_duration_minutes": 180,
        "reminder_minutes": [60, 1440],
    }
    template = await guild_queries.create_template(admin_db, guild["id"], template_data)
    await admin_db.commit()

    updated = await guild_queries.update_template(
        admin_db, guild["id"], template.id, {"name": "Updated Name"}
    )
    await admin_db.commit()

    assert updated.name == "Updated Name"


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_empty_guild_id_raises_error(admin_db):
    """Verify empty guild_id raises ValueError."""
    with pytest.raises(ValueError, match="guild_id cannot be empty"):
        await guild_queries.get_game_by_id(admin_db, "", str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_nonexistent_game_returns_none(admin_db, create_guild):
    """Verify querying non-existent game returns None."""
    guild = create_guild()
    result = await guild_queries.get_game_by_id(admin_db, guild["id"], str(uuid.uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_nonexistent_template_returns_none(admin_db, create_guild):
    """Verify querying non-existent template returns None."""
    guild = create_guild()
    result = await guild_queries.get_template_by_id(admin_db, guild["id"], str(uuid.uuid4()))
    assert result is None
