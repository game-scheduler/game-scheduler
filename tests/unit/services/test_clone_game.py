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


"""Unit tests for GameService.clone_game method.

These tests verify clone_game correctly copies source game fields, carries
over participants in order when requested, and enforces permissions.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.schemas.clone_game import CarryoverOption, CloneGameRequest
from services.api.services.games import GameService
from shared.models import game as game_model
from shared.models import participant as participant_model
from shared.models.signup_method import SignupMethod
from shared.schemas import auth as auth_schemas

SCHEDULED_AT = datetime.datetime(2026, 9, 1, 18, 0, 0)
CLONE_AT = datetime.datetime(2026, 10, 1, 18, 0, 0)


@pytest.fixture
def source_game():
    """Source game with two participants (one player, one waitlist)."""
    game = MagicMock(spec=game_model.GameSession)
    game.id = "source-game-uuid"
    game.title = "Original Game"
    game.description = "A great game"
    game.signup_instructions = "Join here"
    game.scheduled_at = SCHEDULED_AT
    game.where = "Discord"
    game.max_players = 1
    game.template_id = "template-uuid"
    game.guild_id = "guild-db-uuid"
    game.channel_id = "channel-db-uuid"
    game.host_id = "host-db-uuid"
    game.reminder_minutes = [30, 10]
    game.notify_role_ids = ["role-1"]
    game.allowed_player_role_ids = None
    game.expected_duration_minutes = 120
    game.status = game_model.GameStatus.SCHEDULED.value
    game.signup_method = SignupMethod.SELF_SIGNUP
    game.thumbnail_id = None
    game.banner_image_id = None
    game.message_id = "discord-message-id-999"

    game.host = MagicMock()
    game.host.discord_id = "host-discord-id"
    game.guild = MagicMock()
    game.guild.guild_id = "guild-discord-id"
    game.channel = MagicMock()

    player = MagicMock(spec=participant_model.GameParticipant)
    player.user_id = "user1-uuid"
    player.display_name = None
    player.position_type = participant_model.ParticipantType.HOST_ADDED
    player.position = 1
    player.user = MagicMock()
    player.user.discord_id = "player1-discord"

    waitlisted = MagicMock(spec=participant_model.GameParticipant)
    waitlisted.user_id = "user2-uuid"
    waitlisted.display_name = None
    waitlisted.position_type = participant_model.ParticipantType.SELF_ADDED
    waitlisted.position = 2
    waitlisted.user = MagicMock()
    waitlisted.user.discord_id = "player2-discord"

    game.participants = [player, waitlisted]
    return game


@pytest.fixture
def current_user(source_game):
    """Current user matching the game host."""
    user = MagicMock()
    user.discord_id = source_game.host.discord_id
    cu = MagicMock(spec=auth_schemas.CurrentUser)
    cu.user = user
    cu.access_token = "mock_token"
    return cu


@pytest.fixture
def role_service():
    """Mock role service."""
    return MagicMock()


@pytest.fixture
def game_service():
    """Build a GameService with all dependencies mocked."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    execute_result = MagicMock()
    execute_result.scalar_one = MagicMock(return_value=MagicMock(participants=[]))
    db.execute = AsyncMock(return_value=execute_result)

    event_publisher = MagicMock()
    event_publisher.publish_deferred = MagicMock()

    return GameService(
        db=db,
        event_publisher=event_publisher,
        discord_client=AsyncMock(),
        participant_resolver=AsyncMock(),
        channel_resolver=AsyncMock(),
    )


def _make_clone_request(
    player_carryover: CarryoverOption = CarryoverOption.NO,
    waitlist_carryover: CarryoverOption = CarryoverOption.NO,
) -> CloneGameRequest:
    return CloneGameRequest(
        scheduled_at=CLONE_AT,
        player_carryover=player_carryover,
        waitlist_carryover=waitlist_carryover,
    )


@pytest.mark.asyncio
async def test_clone_game_copies_source_fields(
    game_service, source_game, current_user, role_service
):
    """clone_game must create a new game copying all fields except excluded ones."""
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"

    with (
        patch.object(game_service, "get_game", new=AsyncMock(side_effect=[source_game, new_game])),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    # Capture the GameSession passed to db.add
    add_calls = game_service.db.add.call_args_list
    assert len(add_calls) >= 1, "db.add must be called at least once"
    new_game_obj = add_calls[0][0][0]

    assert isinstance(new_game_obj, game_model.GameSession), "First db.add must be a GameSession"
    assert new_game_obj.title == source_game.title
    assert new_game_obj.description == source_game.description
    assert new_game_obj.signup_instructions == source_game.signup_instructions
    assert new_game_obj.scheduled_at == CLONE_AT.replace(tzinfo=None)
    assert new_game_obj.where == source_game.where
    assert new_game_obj.max_players == source_game.max_players
    assert new_game_obj.template_id == source_game.template_id
    assert new_game_obj.guild_id == source_game.guild_id
    assert new_game_obj.channel_id == source_game.channel_id
    assert new_game_obj.host_id == source_game.host_id
    assert new_game_obj.reminder_minutes == source_game.reminder_minutes
    assert new_game_obj.notify_role_ids == source_game.notify_role_ids
    assert new_game_obj.expected_duration_minutes == source_game.expected_duration_minutes
    assert new_game_obj.signup_method == source_game.signup_method
    # Excluded fields must not carry over
    assert new_game_obj.id != source_game.id
    assert new_game_obj.message_id is None
    assert new_game_obj.status == game_model.GameStatus.SCHEDULED.value


@pytest.mark.asyncio
async def test_clone_game_yes_player_carryover_creates_participants(
    game_service, source_game, current_user, role_service
):
    """clone_game with YES player carryover must add player participants in order."""
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"

    with (
        patch.object(game_service, "get_game", new=AsyncMock(side_effect=[source_game, new_game])),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(player_carryover=CarryoverOption.YES),
            current_user=current_user,
            role_service=role_service,
        )

    add_calls = game_service.db.add.call_args_list
    participant_adds = [
        call[0][0]
        for call in add_calls
        if isinstance(call[0][0], participant_model.GameParticipant)
    ]

    # max_players=2 so source has 1 player (position 1) and 1 waitlist (position 2)
    # YES player carryover should carry over the 1 player (confirmed slot)
    assert len(participant_adds) == 1, "Should add exactly 1 player participant"
    assert participant_adds[0].position == 1
    assert participant_adds[0].user_id == source_game.participants[0].user_id
    assert participant_adds[0].position_type == source_game.participants[0].position_type


@pytest.mark.asyncio
async def test_clone_game_no_carryover_creates_no_participants(
    game_service, source_game, current_user, role_service
):
    """clone_game with NO carryover must not add any participants."""
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"

    with (
        patch.object(game_service, "get_game", new=AsyncMock(side_effect=[source_game, new_game])),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    add_calls = game_service.db.add.call_args_list
    participant_adds = [
        call[0][0]
        for call in add_calls
        if isinstance(call[0][0], participant_model.GameParticipant)
    ]
    assert len(participant_adds) == 0, "NO carryover must add no participants"


@pytest.mark.asyncio
async def test_clone_game_yes_with_deadline_raises_value_error(
    game_service, source_game, current_user, role_service
):
    """clone_game with YES_WITH_DEADLINE must raise ValueError (guard removed in Phase 7)."""
    clone_data = CloneGameRequest(
        scheduled_at=CLONE_AT,
        player_carryover=CarryoverOption.YES_WITH_DEADLINE,
        player_deadline=datetime.datetime(2027, 1, 1, 12, 0, 0),
    )

    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
    ):
        with pytest.raises(ValueError, match="YES_WITH_DEADLINE"):
            await game_service.clone_game(
                source_game_id=source_game.id,
                clone_data=clone_data,
                current_user=current_user,
                role_service=role_service,
            )


@pytest.mark.asyncio
async def test_clone_game_source_not_found_raises_value_error(
    game_service, current_user, role_service
):
    """clone_game must raise ValueError when source game does not exist."""
    with patch.object(game_service, "get_game", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError, match="not found"):
            await game_service.clone_game(
                source_game_id="nonexistent-id",
                clone_data=_make_clone_request(),
                current_user=current_user,
                role_service=role_service,
            )


@pytest.mark.asyncio
async def test_clone_game_non_host_raises_value_error(
    game_service, source_game, current_user, role_service
):
    """clone_game must raise ValueError when user cannot manage the game."""
    with (
        patch.object(game_service, "get_game", new=AsyncMock(return_value=source_game)),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=False),
    ):
        with pytest.raises(ValueError, match="permission"):
            await game_service.clone_game(
                source_game_id=source_game.id,
                clone_data=_make_clone_request(),
                current_user=current_user,
                role_service=role_service,
            )


@pytest.mark.asyncio
async def test_clone_game_yes_carryover_empty_participant_list(
    game_service, source_game, current_user, role_service
):
    """clone_game with YES carryover on a game with no participants adds none."""
    source_game.participants = []
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"

    with (
        patch.object(game_service, "get_game", new=AsyncMock(side_effect=[source_game, new_game])),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
    ):
        await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(player_carryover=CarryoverOption.YES),
            current_user=current_user,
            role_service=role_service,
        )

    add_calls = game_service.db.add.call_args_list
    participant_adds = [
        call[0][0]
        for call in add_calls
        if isinstance(call[0][0], participant_model.GameParticipant)
    ]
    assert len(participant_adds) == 0, "No participants to carry over when source is empty"


@pytest.mark.asyncio
async def test_clone_game_max_players_zero_does_not_raise(
    game_service, source_game, current_user, role_service
):
    """clone_game with max_players=0 does not raise (partition_participants defaults to DEFAULT)."""
    source_game.max_players = 0
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"

    with (
        patch.object(game_service, "get_game", new=AsyncMock(side_effect=[source_game, new_game])),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
    ):
        result = await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(player_carryover=CarryoverOption.YES),
            current_user=current_user,
            role_service=role_service,
        )

    assert result is new_game, (
        "clone_game must return the reloaded new game even when max_players=0"
    )


@pytest.mark.asyncio
async def test_clone_game_clones_cancelled_source_game(
    game_service, source_game, current_user, role_service
):
    """clone_game succeeds regardless of the source game status."""
    source_game.status = game_model.GameStatus.CANCELLED.value
    source_game.participants = []
    new_game = MagicMock(spec=game_model.GameSession)
    new_game.id = "new-game-uuid"

    with (
        patch.object(game_service, "get_game", new=AsyncMock(side_effect=[source_game, new_game])),
        patch("services.api.dependencies.permissions.can_manage_game", return_value=True),
        patch.object(game_service, "_setup_game_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()),
    ):
        result = await game_service.clone_game(
            source_game_id=source_game.id,
            clone_data=_make_clone_request(),
            current_user=current_user,
            role_service=role_service,
        )

    assert result is new_game, "clone_game must return the reloaded new game"

    add_calls = game_service.db.add.call_args_list
    new_game_obj = add_calls[0][0][0]
    # New game must be SCHEDULED regardless of source status
    assert new_game_obj.status == game_model.GameStatus.SCHEDULED.value
