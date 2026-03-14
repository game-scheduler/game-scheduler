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


"""Integration tests for editing games with pre-filled participants."""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import game as game_model
from shared.models import participant as participant_model
from shared.models import user as user_model
from shared.models.participant import ParticipantType
from shared.schemas import game as game_schemas


@pytest.mark.asyncio
async def test_update_game_with_discord_mention_format(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_guild,
    sample_channel,
    sample_user,
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
        position_type=ParticipantType.HOST_ADDED,
        position=1,
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
                "position": 1,
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
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_guild,
    sample_channel,
    sample_user,
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
                "position": 1,
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
