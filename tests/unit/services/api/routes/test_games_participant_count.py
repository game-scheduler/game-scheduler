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


"""Unit tests for participant count calculation in game responses."""

import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from services.api.routes import games as games_routes
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import guild as guild_model
from shared.models import participant as participant_model
from shared.models import user as user_model
from shared.models.participant import ParticipantType


@pytest.fixture
def mock_display_name_resolver():
    """Create mock display name resolver."""
    resolver = AsyncMock()
    resolver.resolve_display_names = AsyncMock(return_value={})
    return resolver


@pytest.fixture
def mock_discord_client():
    """Create mock Discord client."""
    client = AsyncMock()
    client.fetch_channel = AsyncMock(return_value={"name": "test-channel"})
    return client


@pytest.mark.asyncio
async def test_participant_count_includes_discord_users_only(
    mock_display_name_resolver, mock_discord_client
):
    """Test participant count with only Discord-linked users."""
    game_id = str(uuid.uuid4())
    host_id = str(uuid.uuid4())
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    host_user = user_model.User(id=host_id, discord_id="111111111")
    user1 = user_model.User(id=user1_id, discord_id="222222222")
    user2 = user_model.User(id=user2_id, discord_id="333333333")

    guild = guild_model.GuildConfiguration(id=str(uuid.uuid4()), guild_id="999999999")
    channel = channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="888888888",
        guild_id=guild.id,
    )

    game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        max_players=10,
        guild_id=guild.id,
        channel_id=channel.id,
        host_id=host_id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    game.host = host_user
    game.guild = guild
    game.channel = channel
    game.participants = [
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=user1_id,
            joined_at=datetime.datetime.now(datetime.UTC),
            user=user1,
            position_type=ParticipantType.SELF_ADDED,
            position=0,
        ),
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=user2_id,
            joined_at=datetime.datetime.now(datetime.UTC),
            user=user2,
            position_type=ParticipantType.SELF_ADDED,
            position=0,
        ),
    ]

    with (
        patch(
            "services.api.routes.games.display_names_module.get_display_name_resolver",
            return_value=mock_display_name_resolver,
        ),
        patch(
            "services.api.routes.games.get_discord_client",
            return_value=mock_discord_client,
        ),
        patch(
            "services.api.routes.games.fetch_channel_name_safe",
            return_value="test-channel",
        ),
        patch(
            "services.api.routes.games.fetch_guild_name_safe",
            return_value="test-guild",
        ),
    ):
        response = await games_routes._build_game_response(game)

    assert response.participant_count == 2
    assert len(response.participants) == 2


@pytest.mark.asyncio
async def test_participant_count_includes_placeholder_participants(
    mock_display_name_resolver, mock_discord_client
):
    """Test participant count includes placeholder participants (no Discord user_id)."""
    game_id = str(uuid.uuid4())
    host_id = str(uuid.uuid4())

    host_user = user_model.User(id=host_id, discord_id="111111111")

    guild = guild_model.GuildConfiguration(id=str(uuid.uuid4()), guild_id="999999999")
    channel = channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="888888888",
        guild_id=guild.id,
    )

    game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        max_players=10,
        guild_id=guild.id,
        channel_id=channel.id,
        host_id=host_id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    game.host = host_user
    game.guild = guild
    game.channel = channel
    game.participants = [
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=None,
            display_name="Placeholder Player 1",
            joined_at=datetime.datetime.now(datetime.UTC),
            user=None,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        ),
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=None,
            display_name="Placeholder Player 2",
            joined_at=datetime.datetime.now(datetime.UTC),
            user=None,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        ),
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=None,
            display_name="Placeholder Player 3",
            joined_at=datetime.datetime.now(datetime.UTC),
            user=None,
            position_type=ParticipantType.HOST_ADDED,
            position=2,
        ),
    ]

    with (
        patch(
            "services.api.routes.games.display_names_module.get_display_name_resolver",
            return_value=mock_display_name_resolver,
        ),
        patch(
            "services.api.routes.games.get_discord_client",
            return_value=mock_discord_client,
        ),
        patch(
            "services.api.routes.games.fetch_channel_name_safe",
            return_value="test-channel",
        ),
        patch(
            "services.api.routes.games.fetch_guild_name_safe",
            return_value="test-guild",
        ),
    ):
        response = await games_routes._build_game_response(game)

    assert response.participant_count == 3
    assert len(response.participants) == 3
    assert all(p.user_id is None for p in response.participants)


@pytest.mark.asyncio
async def test_participant_count_includes_mixed_participants(
    mock_display_name_resolver, mock_discord_client
):
    """Test participant count with mix of Discord users and placeholders."""
    game_id = str(uuid.uuid4())
    host_id = str(uuid.uuid4())
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    host_user = user_model.User(id=host_id, discord_id="111111111")
    user1 = user_model.User(id=user1_id, discord_id="222222222")
    user2 = user_model.User(id=user2_id, discord_id="333333333")

    guild = guild_model.GuildConfiguration(id=str(uuid.uuid4()), guild_id="999999999")
    channel = channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="888888888",
        guild_id=guild.id,
    )

    game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        max_players=10,
        guild_id=guild.id,
        channel_id=channel.id,
        host_id=host_id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    game.host = host_user
    game.guild = guild
    game.channel = channel
    game.participants = [
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=user1_id,
            joined_at=datetime.datetime.now(datetime.UTC),
            user=user1,
            position_type=ParticipantType.SELF_ADDED,
            position=0,
        ),
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=None,
            display_name="Placeholder Player",
            joined_at=datetime.datetime.now(datetime.UTC),
            user=None,
            position_type=ParticipantType.HOST_ADDED,
            position=0,
        ),
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=user2_id,
            joined_at=datetime.datetime.now(datetime.UTC),
            user=user2,
            position_type=ParticipantType.SELF_ADDED,
            position=0,
        ),
        participant_model.GameParticipant(
            id=str(uuid.uuid4()),
            game_session_id=game_id,
            user_id=None,
            display_name="Another Placeholder",
            joined_at=datetime.datetime.now(datetime.UTC),
            user=None,
            position_type=ParticipantType.HOST_ADDED,
            position=1,
        ),
    ]

    with (
        patch(
            "services.api.routes.games.display_names_module.get_display_name_resolver",
            return_value=mock_display_name_resolver,
        ),
        patch(
            "services.api.routes.games.get_discord_client",
            return_value=mock_discord_client,
        ),
        patch(
            "services.api.routes.games.fetch_channel_name_safe",
            return_value="test-channel",
        ),
        patch(
            "services.api.routes.games.fetch_guild_name_safe",
            return_value="test-guild",
        ),
    ):
        response = await games_routes._build_game_response(game)

    assert response.participant_count == 4
    assert len(response.participants) == 4
    discord_users = [p for p in response.participants if p.user_id is not None]
    placeholders = [p for p in response.participants if p.user_id is None]
    assert len(discord_users) == 2
    assert len(placeholders) == 2


@pytest.mark.asyncio
async def test_participant_count_with_empty_participants(
    mock_display_name_resolver, mock_discord_client
):
    """Test participant count with no participants."""
    game_id = str(uuid.uuid4())
    host_id = str(uuid.uuid4())

    host_user = user_model.User(id=host_id, discord_id="111111111")

    guild = guild_model.GuildConfiguration(id=str(uuid.uuid4()), guild_id="999999999")
    channel = channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="888888888",
        guild_id=guild.id,
    )

    game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        max_players=10,
        guild_id=guild.id,
        channel_id=channel.id,
        host_id=host_id,
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    game.host = host_user
    game.guild = guild
    game.channel = channel
    game.participants = []

    with (
        patch(
            "services.api.routes.games.display_names_module.get_display_name_resolver",
            return_value=mock_display_name_resolver,
        ),
        patch(
            "services.api.routes.games.get_discord_client",
            return_value=mock_discord_client,
        ),
        patch(
            "services.api.routes.games.fetch_channel_name_safe",
            return_value="test-channel",
        ),
        patch(
            "services.api.routes.games.fetch_guild_name_safe",
            return_value="test-guild",
        ),
    ):
        response = await games_routes._build_game_response(game)

    assert response.participant_count == 0
    assert len(response.participants) == 0
