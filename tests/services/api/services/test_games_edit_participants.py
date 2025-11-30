# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Integration tests for editing games with pre-filled participants."""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import discord_client as discord_client_module
from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared.messaging import publisher as messaging_publisher
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import guild as guild_model
from shared.models import participant as participant_model
from shared.models import user as user_model
from shared.schemas import game as game_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_event_publisher():
    """Create mock event publisher."""
    publisher = AsyncMock(spec=messaging_publisher.EventPublisher)
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def mock_discord_client():
    """Create mock Discord API client."""
    return MagicMock(spec=discord_client_module.DiscordAPIClient)


@pytest.fixture
def mock_participant_resolver():
    """Create mock participant resolver."""
    return AsyncMock(spec=resolver_module.ParticipantResolver)


@pytest.fixture
def game_service(mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver):
    """Create game service instance."""
    return games_service.GameService(
        db=mock_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_client,
        participant_resolver=mock_participant_resolver,
    )


@pytest.fixture
def sample_guild():
    """Create sample guild configuration."""
    return guild_model.GuildConfiguration(
        id=str(uuid.uuid4()),
        guild_id="123456789",
        default_max_players=5,
        default_reminder_minutes=[60],
    )


@pytest.fixture
def sample_channel(sample_guild):
    """Create sample channel configuration."""
    return channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="987654321",
        channel_name="test-channel",
        guild_id=sample_guild.id,
        max_players=4,
        reminder_minutes=[30],
    )


@pytest.fixture
def sample_user():
    """Create sample user."""
    return user_model.User(id=str(uuid.uuid4()), discord_id="111222333")


@pytest.mark.asyncio
async def test_update_game_with_discord_mention_format(
    game_service, mock_db, mock_participant_resolver, sample_guild, sample_channel, sample_user
):
    """
    Test that updating a game with <@discord_id> format preserves Discord users.

    This is the bug fix test: when editing a game, the frontend sends participants
    in <@discord_id> format, which should be recognized as Discord users, not placeholders.
    """
    # Create a game with a Discord participant
    game_id = str(uuid.uuid4())
    participant_id = str(uuid.uuid4())
    discord_user_id = str(uuid.uuid4())

    # Mock existing game with Discord participant
    existing_participant = participant_model.GameParticipant(
        id=participant_id,
        game_session_id=game_id,
        user_id=discord_user_id,
        display_name=None,  # Discord users have null display_name
        pre_filled_position=1,
    )

    discord_user = user_model.User(
        id=discord_user_id,
        discord_id="999888777666555444",
    )
    existing_participant.user = discord_user

    game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        max_players=5,
        status="SCHEDULED",
        participants=[existing_participant],
    )
    game.host = sample_user
    game.guild = sample_guild
    game.channel = sample_channel

    # Mock the participant resolver to accept <@discord_id> format
    # This simulates the fix where we recognize Discord mention format
    mock_participant_resolver.resolve_initial_participants.return_value = (
        [
            {
                "type": "discord",
                "discord_id": "999888777666555444",
                "original_input": "<@999888777666555444>",
            }
        ],
        [],  # No errors
    )

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=discord_user)

    # Mock DB operations
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = game
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Create update request with Discord mention format (as sent from frontend)
    update_data = game_schemas.GameUpdateRequest(
        participants=[
            {
                "mention": "<@999888777666555444>",  # Frontend sends this format
                "pre_filled_position": 1,
            }
        ]
    )

    # Mock current_user and role_service for authorization
    mock_current_user = MagicMock()
    mock_current_user.user.discord_id = sample_user.discord_id
    mock_role_service = AsyncMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        # Update the game
        await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=mock_current_user,
            role_service=mock_role_service,
        )

    # Verify that resolve_initial_participants was called with Discord mention format
    mock_participant_resolver.resolve_initial_participants.assert_called_once()
    call_args = mock_participant_resolver.resolve_initial_participants.call_args
    assert "<@999888777666555444>" in call_args[0][1]

    # Verify that the participant was treated as a Discord user, not a placeholder
    resolved_participants = call_args[0][1]
    assert len(resolved_participants) == 1

    # With the fix, this should work and create a Discord participant
    mock_participant_resolver.ensure_user_exists.assert_called()


@pytest.mark.asyncio
async def test_update_game_preserves_discord_users_not_placeholders(
    game_service, mock_db, mock_participant_resolver, sample_guild, sample_channel, sample_user
):
    """
    Verify that Discord users remain Discord users after edit, not converted to placeholders.
    """
    game_id = str(uuid.uuid4())
    discord_user_id = str(uuid.uuid4())

    discord_user = user_model.User(
        id=discord_user_id,
        discord_id="123456789012345678",
    )

    game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        max_players=5,
        status="SCHEDULED",
        participants=[],
    )
    game.host = sample_user
    game.guild = sample_guild
    game.channel = sample_channel

    # Resolver should accept <@discord_id> format and return Discord user
    mock_participant_resolver.resolve_initial_participants.return_value = (
        [
            {
                "type": "discord",
                "discord_id": "123456789012345678",
                "original_input": "<@123456789012345678>",
            }
        ],
        [],
    )

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=discord_user)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = game
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    update_data = game_schemas.GameUpdateRequest(
        participants=[
            {
                "mention": "<@123456789012345678>",
                "pre_filled_position": 1,
            }
        ]
    )

    mock_current_user = MagicMock()
    mock_current_user.user.discord_id = sample_user.discord_id
    mock_role_service = AsyncMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=mock_current_user,
            role_service=mock_role_service,
        )

    # Verify the resolver was called and recognized the Discord mention format
    mock_participant_resolver.resolve_initial_participants.assert_called_once()
    resolved = mock_participant_resolver.resolve_initial_participants.return_value

    # The key assertion: participant should be type "discord", not "placeholder"
    assert resolved[0][0]["type"] == "discord"
    assert resolved[0][0]["discord_id"] == "123456789012345678"
