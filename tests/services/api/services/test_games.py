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


"""Unit tests for game management service."""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock

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
        guild_name="Test Guild",
        default_max_players=5,
        default_reminder_minutes=[60],
        default_rules="Guild rules",
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


@pytest.fixture
def sample_game_data(sample_guild, sample_channel):
    """Create sample game creation request."""
    return game_schemas.GameCreateRequest(
        guild_id=str(sample_guild.id),
        channel_id=str(sample_channel.id),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        max_players=4,
        reminder_minutes=[60],
        rules="Test rules",
    )


@pytest.mark.asyncio
async def test_create_game_without_participants(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game without initial participants."""
    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    # Mock get_game call after commit
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(side_effect=[guild_result, channel_result, host_result, reload_result])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    def mock_add_side_effect(obj):
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add.side_effect = mock_add_side_effect

    game = await game_service.create_game(
        game_data=sample_game_data,
        host_user_id=sample_user.id,
        access_token="token",
    )

    assert isinstance(game, game_model.GameSession)
    assert game.title == "Test Game"
    assert game.host_id == sample_user.id
    mock_db.add.assert_called()
    mock_event_publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_create_game_with_valid_participants(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game with valid initial participants."""
    sample_game_data.initial_participants = ["@user1", "Placeholder"]

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {"type": "discord", "discord_id": "444", "original_input": "@user1"},
                {
                    "type": "placeholder",
                    "display_name": "Placeholder",
                    "original_input": "Placeholder",
                },
            ],
            [],
        )
    )
    mock_participant_resolver.ensure_user_exists = AsyncMock(
        return_value=user_model.User(id=str(uuid.uuid4()), discord_id="444")
    )

    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    # Mock get_game call after commit
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(side_effect=[guild_result, channel_result, host_result, reload_result])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    def mock_add_side_effect(obj):
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add.side_effect = mock_add_side_effect

    game = await game_service.create_game(
        game_data=sample_game_data,
        host_user_id=sample_user.id,
        access_token="token",
    )

    assert isinstance(game, game_model.GameSession)
    mock_participant_resolver.resolve_initial_participants.assert_called_once()


@pytest.mark.asyncio
async def test_create_game_with_invalid_participants(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_game_data,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game with invalid @mentions raises ValidationError."""
    sample_game_data.initial_participants = ["@invalid"]

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [],
            [{"input": "@invalid", "reason": "User not found", "suggestions": []}],
        )
    )

    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(side_effect=[guild_result, channel_result, host_result])
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    with pytest.raises(resolver_module.ValidationError) as exc_info:
        await game_service.create_game(
            game_data=sample_game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert len(exc_info.value.invalid_mentions) == 1
    assert exc_info.value.invalid_mentions[0]["input"] == "@invalid"


@pytest.mark.asyncio
async def test_create_game_timezone_conversion(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that timezone-aware datetimes are properly converted to UTC."""
    # Create game with EST time (UTC-5)
    est = datetime.timezone(datetime.timedelta(hours=-5))
    # 10 AM EST = 3 PM UTC (15:00)
    scheduled_time_est = datetime.datetime(2025, 11, 20, 10, 0, 0, tzinfo=est)

    game_data = game_schemas.GameCreateRequest(
        guild_id=str(sample_guild.id),
        channel_id=str(sample_channel.id),
        title="Timezone Test",
        description="Test timezone conversion",
        scheduled_at=scheduled_time_est,
        max_players=4,
        reminder_minutes=[60],
        rules="Test rules",
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Timezone Test",
        description="Test timezone conversion",
        scheduled_at=datetime.datetime(2025, 11, 20, 15, 0, 0),  # Should be 15:00 UTC
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(side_effect=[guild_result, channel_result, host_result, reload_result])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    # Capture the game object when it's added to verify timezone conversion
    added_game = None

    def capture_add(obj):
        nonlocal added_game
        if isinstance(obj, game_model.GameSession):
            added_game = obj
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add = MagicMock(side_effect=capture_add)

    await game_service.create_game(
        game_data=game_data,
        host_user_id=sample_user.id,
        access_token="token",
    )

    # Verify the stored time was converted to UTC (15:00, not 10:00)
    assert added_game is not None
    assert added_game.scheduled_at.hour == 15  # 3 PM UTC
    assert added_game.scheduled_at.minute == 0
    assert added_game.scheduled_at.tzinfo is None  # Should be naive (UTC implied)


@pytest.mark.asyncio
async def test_get_game_found(game_service, mock_db):
    """Test getting game by ID returns game."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(id=game_id, title="Test")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=mock_result)

    game = await game_service.get_game(game_id)

    assert game is mock_game


@pytest.mark.asyncio
async def test_get_game_not_found(game_service, mock_db):
    """Test getting non-existent game returns None."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    game = await game_service.get_game(str(uuid.uuid4()))

    assert game is None


@pytest.mark.asyncio
async def test_list_games_no_filters(game_service, mock_db):
    """Test listing games without filters."""
    mock_games = [
        game_model.GameSession(id=str(uuid.uuid4()), title="Game 1"),
        game_model.GameSession(id=str(uuid.uuid4()), title="Game 2"),
    ]

    count_result = MagicMock()
    count_result.scalar.return_value = 2
    games_result = MagicMock()
    games_result.scalars.return_value.all.return_value = mock_games

    mock_db.execute = AsyncMock(side_effect=[count_result, games_result])

    games, count = await game_service.list_games()

    assert len(games) == 2
    assert count == 2


@pytest.mark.asyncio
async def test_list_games_with_filters(game_service, mock_db, sample_guild):
    """Test listing games with guild and status filters."""
    mock_games = [game_model.GameSession(id=str(uuid.uuid4()), title="Filtered")]

    count_result = MagicMock()
    count_result.scalar.return_value = 1
    games_result = MagicMock()
    games_result.scalars.return_value.all.return_value = mock_games

    mock_db.execute = AsyncMock(side_effect=[count_result, games_result])

    games, count = await game_service.list_games(guild_id=str(sample_guild.id), status="SCHEDULED")

    assert len(games) == 1
    assert count == 1


@pytest.mark.asyncio
async def test_update_game_success(game_service, mock_db, sample_user):
    """Test updating game by host."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(
        id=game_id,
        title="Old Title",
        host_id=sample_user.id,
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
    )
    mock_game.host = sample_user

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    updated = await game_service.update_game(
        game_id=game_id,
        update_data=game_schemas.GameUpdateRequest(
            title="New Title",
            description="Updated description",
            status="SCHEDULED",
        ),
        host_user_id=sample_user.id,
    )

    assert updated.title == "New Title"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_game_not_host(game_service, mock_db, sample_user):
    """Test updating game by non-host raises ValueError."""
    game_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())
    other_user = user_model.User(id=other_user_id, discord_id="otheruser123")
    mock_game = game_model.GameSession(id=game_id, title="Title", host_id=other_user_id)
    mock_game.host = other_user

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)

    with pytest.raises(ValueError, match="Only the host can update"):
        await game_service.update_game(
            game_id=game_id,
            update_data=game_schemas.GameUpdateRequest(
                title="New Title",
                description="Updated description",
                status="SCHEDULED",
            ),
            host_user_id=sample_user.id,
        )


@pytest.mark.asyncio
async def test_delete_game_success(game_service, mock_db, sample_user):
    """Test deleting game by host."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(
        id=game_id,
        title="Title",
        host_id=sample_user.id,
        status="SCHEDULED",
        guild_id=str(uuid.uuid4()),
        channel_id=str(uuid.uuid4()),
    )
    mock_game.host = sample_user

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute = AsyncMock(side_effect=[game_result, user_result])
    mock_db.commit = AsyncMock()

    await game_service.delete_game(game_id=game_id, host_user_id=sample_user.id)

    assert mock_game.status == "CANCELLED"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_join_game_success(
    game_service, mock_db, mock_participant_resolver, sample_guild, sample_channel
):
    """Test successfully joining a game."""
    game_id = str(uuid.uuid4())
    new_user = user_model.User(id=str(uuid.uuid4()), discord_id="999")
    mock_game = game_model.GameSession(
        id=game_id,
        status="SCHEDULED",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        max_players=5,
    )
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock the existing participant check (user not already joined)
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    # Mock the participant count query
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    # Mock guild/channel queries for max_players resolution
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel

    # Mock the second count query in _publish_player_joined
    count_result2 = MagicMock()
    count_result2.scalar.return_value = 1

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            existing_result,
            count_result,
            guild_result,
            channel_result,
            count_result2,
        ]
    )
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=new_user)

    await game_service.join_game(game_id=game_id, user_discord_id=new_user.discord_id)

    mock_db.add.assert_called()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_join_game_already_joined(
    game_service, mock_db, mock_participant_resolver, sample_user
):
    """Test user joining game they're already in raises ValueError."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(id=game_id, status="SCHEDULED")
    mock_participant = participant_model.GameParticipant(
        user_id=sample_user.id, game_session_id=game_id
    )
    mock_game.participants = [mock_participant]

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    with pytest.raises(ValueError, match="Already joined this game"):
        await game_service.join_game(game_id=game_id, user_discord_id=sample_user.discord_id)


@pytest.mark.asyncio
async def test_join_game_full(
    game_service, mock_db, mock_participant_resolver, sample_guild, sample_channel
):
    """Test joining full game raises ValueError."""
    game_id = str(uuid.uuid4())
    new_user = user_model.User(id=str(uuid.uuid4()), discord_id="999")
    mock_game = game_model.GameSession(id=game_id, status="SCHEDULED", max_players=2)
    mock_game.participants = []
    mock_game.guild_id = sample_guild.id
    mock_game.channel_id = sample_channel.id

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock the existing participant check (user not already joined)
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    # Mock the participant count query (2 non-placeholder participants)
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # Mock guild and channel config for max_players resolution
    guild_result = MagicMock()
    guild_result.scalar_one.return_value = sample_guild

    channel_result = MagicMock()
    channel_result.scalar_one.return_value = sample_channel

    mock_db.execute = AsyncMock(
        side_effect=[game_result, existing_result, count_result, guild_result, channel_result]
    )

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=new_user)

    with pytest.raises(ValueError, match="Game is full"):
        await game_service.join_game(game_id=game_id, user_discord_id=new_user.discord_id)


@pytest.mark.asyncio
async def test_leave_game_success(game_service, mock_db, sample_user):
    """Test user leaving game successfully."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(
        id=game_id, title="Title", guild_id=uuid.uuid4(), channel_id=uuid.uuid4()
    )
    mock_participant = participant_model.GameParticipant(id=uuid.uuid4(), user_id=sample_user.id)
    mock_game.participants = [mock_participant]

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    participant_result = MagicMock()
    participant_result.scalar_one_or_none.return_value = mock_participant
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = None
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            user_result,
            participant_result,
            count_result,
            guild_result,
            channel_result,
        ]
    )
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    await game_service.leave_game(game_id=game_id, user_discord_id=sample_user.discord_id)

    mock_db.delete.assert_called_once_with(mock_participant)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_leave_game_not_participant(game_service, mock_db, sample_user):
    """Test non-participant leaving game raises ValueError."""
    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(id=game_id, title="Title")
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    participant_result = MagicMock()
    participant_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[game_result, user_result, participant_result])

    with pytest.raises(ValueError, match="Not a participant"):
        await game_service.leave_game(game_id=game_id, user_discord_id=sample_user.discord_id)
