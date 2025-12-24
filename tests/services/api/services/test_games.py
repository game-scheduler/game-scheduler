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
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared.discord import client as discord_client_module
from shared.messaging import publisher as messaging_publisher
from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import guild as guild_model
from shared.models import participant as participant_model
from shared.models import template as template_model
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
def mock_role_service():
    """Create mock role service."""
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    return role_service


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
    )


@pytest.fixture
def sample_channel(sample_guild):
    """Create sample channel configuration."""
    return channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="987654321",
        guild_id=sample_guild.id,
    )


@pytest.fixture
def sample_template(sample_guild, sample_channel):
    """Create sample game template."""
    template_id = str(uuid.uuid4())
    return template_model.GameTemplate(
        id=template_id,
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        name="Test Template",
        order=0,
        is_default=True,
        allowed_host_role_ids=None,
        max_players=10,
        reminder_minutes=[60, 15],
    )


@pytest.fixture
def sample_user():
    """Create sample user."""
    return user_model.User(id=str(uuid.uuid4()), discord_id="111222333")


@pytest.fixture
def sample_game_data(sample_template):
    """Create sample game creation request."""
    return game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        max_players=4,
        reminder_minutes=[60],
    )


@pytest.mark.asyncio
async def test_create_game_without_participants(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_game_data,
    sample_template,
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

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    # Mock get_game call after commit
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    def mock_add_side_effect(obj):
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add.side_effect = mock_add_side_effect

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
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
async def test_create_game_with_where_field(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test creating game with where field stores location."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        where="Discord Voice Channel #gaming",
        max_players=4,
        reminder_minutes=[60],
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        where="Discord Voice Channel #gaming",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    def mock_add_side_effect(obj):
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.where = game_data.where

    mock_db.add.side_effect = mock_add_side_effect

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert isinstance(game, game_model.GameSession)
    assert game.where == "Discord Voice Channel #gaming"
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_create_game_with_valid_participants(
    game_service,
    mock_db,
    mock_participant_resolver,
    mock_role_service,
    sample_game_data,
    sample_template,
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

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    # Mock get_game call after commit
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    def mock_add_side_effect(obj):
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add.side_effect = mock_add_side_effect

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
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
    mock_role_service,
    sample_game_data,
    sample_template,
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

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[template_result, guild_result, host_result, channel_result]
    )
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    with (
        patch("services.api.auth.roles.get_role_service", return_value=mock_role_service),
        pytest.raises(resolver_module.ValidationError) as exc_info,
    ):
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
    mock_role_service,
    sample_template,
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
        template_id=sample_template.id,
        title="Timezone Test",
        description="Test timezone conversion",
        scheduled_at=scheduled_time_est,
        max_players=4,
        reminder_minutes=[60],
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

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user

    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
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

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
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
async def test_update_game_success(game_service, mock_db, sample_user, sample_guild):
    """Test updating game by host."""
    from datetime import datetime

    from shared.schemas.auth import CurrentUser

    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=sample_guild.id,
    )
    mock_game = game_model.GameSession(
        id=game_id,
        title="Old Title",
        host_id=sample_user.id,
        guild_id=sample_guild.id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None),
        status="SCHEDULED",
    )
    mock_game.host = sample_user
    mock_game.guild = sample_guild
    mock_game.channel = mock_channel
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    # Mock current user
    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )

    # Mock role service with can_manage_game patched
    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        updated = await game_service.update_game(
            game_id=game_id,
            update_data=game_schemas.GameUpdateRequest(
                title="New Title",
                description="Updated description",
                status="SCHEDULED",
            ),
            current_user=current_user,
            role_service=mock_role_service,
        )

    assert updated.title == "New Title"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_game_where_field(game_service, mock_db, sample_user, sample_guild):
    """Test updating game where field."""
    from shared.schemas.auth import CurrentUser

    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=sample_guild.id,
    )
    mock_game = game_model.GameSession(
        id=game_id,
        title="Test Game",
        where="Old Location",
        host_id=sample_user.id,
        guild_id=sample_guild.id,
        channel_id=channel_id,
    )
    mock_game.host = sample_user
    mock_game.guild = sample_guild
    mock_game.channel = mock_channel

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )
    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        updated = await game_service.update_game(
            game_id=game_id,
            update_data=game_schemas.GameUpdateRequest(where="New Location"),
            current_user=current_user,
            role_service=mock_role_service,
        )

    assert updated.where == "New Location"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_game_not_host(game_service, mock_db, sample_user, sample_guild):
    """Test updating game by non-host raises ValueError."""
    from shared.schemas.auth import CurrentUser

    game_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())
    other_user = user_model.User(id=other_user_id, discord_id="otheruser123")
    mock_game = game_model.GameSession(
        id=game_id,
        title="Title",
        host_id=other_user_id,
        guild_id=sample_guild.id,
        channel_id=str(uuid.uuid4()),
    )
    mock_game.host = other_user
    mock_game.guild = sample_guild

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)

    # Mock current user (not the host)
    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )

    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=False):
        with pytest.raises(ValueError, match="You don't have permission to update"):
            await game_service.update_game(
                game_id=game_id,
                update_data=game_schemas.GameUpdateRequest(
                    title="New Title",
                    description="Updated description",
                    status="SCHEDULED",
                ),
                current_user=current_user,
                role_service=mock_role_service,
            )


@pytest.mark.asyncio
async def test_delete_game_success(game_service, mock_db, sample_user, sample_guild):
    """Test deleting game by host."""
    from shared.schemas.auth import CurrentUser

    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=sample_guild.id,
    )
    mock_game = game_model.GameSession(
        id=game_id,
        title="Title",
        host_id=sample_user.id,
        status="SCHEDULED",
        guild_id=sample_guild.id,
        channel_id=channel_id,
    )
    mock_game.host = sample_user
    mock_game.guild = sample_guild
    mock_game.channel = mock_channel

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game
    mock_db.execute = AsyncMock(return_value=game_result)
    mock_db.commit = AsyncMock()

    # Mock current user
    current_user = CurrentUser(
        user=sample_user, access_token="mock_token", session_token="mock_session"
    )

    mock_role_service = MagicMock()

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        await game_service.delete_game(
            game_id=game_id,
            current_user=current_user,
            role_service=mock_role_service,
        )

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
    mock_game.channel = sample_channel
    mock_game.participants = []

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock the participant count query
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    # Mock guild/channel queries for max_players resolution
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel

    # Mock the second count query in _publish_game_updated
    count_result2 = MagicMock()
    count_result2.scalar.return_value = 1

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
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
    # Commit is called twice: once for participant, once for join notification
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_join_game_already_joined(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_user,
    sample_guild,
    sample_channel,
):
    """Test joining same game twice raises ValueError due to IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    game_id = str(uuid.uuid4())
    mock_game = game_model.GameSession(
        id=game_id,
        status="SCHEDULED",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        max_players=5,
    )
    mock_participant = participant_model.GameParticipant(
        user_id=sample_user.id, game_session_id=game_id
    )
    mock_game.participants = [mock_participant]

    game_result = MagicMock()
    game_result.scalar_one_or_none.return_value = mock_game

    # Mock the participant count query
    count_result = MagicMock()
    count_result.scalar.return_value = 1

    # Mock guild/channel queries
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel

    mock_db.execute = AsyncMock(
        side_effect=[game_result, count_result, guild_result, channel_result]
    )

    # Simulate IntegrityError on commit (duplicate key violation)
    mock_db.commit = AsyncMock(side_effect=IntegrityError("statement", {}, "orig"))
    mock_db.add = MagicMock()

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    with pytest.raises(ValueError, match="User has already joined this game"):
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

    # Mock the participant count query (2 non-placeholder participants)
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # Mock guild and channel config for max_players resolution
    guild_result = MagicMock()
    guild_result.scalar_one.return_value = sample_guild

    channel_result = MagicMock()
    channel_result.scalar_one.return_value = sample_channel

    mock_db.execute = AsyncMock(
        side_effect=[game_result, count_result, guild_result, channel_result]
    )

    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=new_user)

    with pytest.raises(ValueError, match="Game is full"):
        await game_service.join_game(game_id=game_id, user_discord_id=new_user.discord_id)


@pytest.mark.asyncio
async def test_leave_game_success(game_service, mock_db, sample_user):
    """Test user leaving game successfully."""
    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=str(uuid.uuid4()),
    )
    mock_game = game_model.GameSession(
        id=game_id, title="Title", guild_id=uuid.uuid4(), channel_id=channel_id
    )
    mock_game.channel = mock_channel
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


@pytest.mark.asyncio
async def test_ensure_in_progress_schedule_creates_new(game_service, mock_db, sample_game_data):
    """Test _ensure_in_progress_schedule creates new schedule when none exists."""
    from shared.models import game_status_schedule as game_status_schedule_model

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        expected_duration_minutes=120,
        status="SCHEDULED",
    )
    existing_schedules: list[game_status_schedule_model.GameStatusSchedule] = []

    mock_db.add = MagicMock()

    await game_service._ensure_in_progress_schedule(game, existing_schedules)

    mock_db.add.assert_called_once()
    added_schedule = mock_db.add.call_args[0][0]
    assert isinstance(added_schedule, game_status_schedule_model.GameStatusSchedule)
    assert added_schedule.game_id == game.id
    assert added_schedule.target_status == game_model.GameStatus.IN_PROGRESS.value
    assert added_schedule.transition_time == game.scheduled_at
    assert added_schedule.executed is False


@pytest.mark.asyncio
async def test_ensure_in_progress_schedule_updates_existing(game_service, mock_db):
    """Test _ensure_in_progress_schedule updates existing schedule."""
    from shared.models import game_status_schedule as game_status_schedule_model

    old_time = datetime.datetime.now(datetime.UTC)
    new_time = old_time + datetime.timedelta(hours=1)

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=new_time,
        expected_duration_minutes=120,
        status="SCHEDULED",
    )

    existing_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=old_time,
        executed=True,
    )
    existing_schedules = [existing_schedule]

    mock_db.add = MagicMock()

    await game_service._ensure_in_progress_schedule(game, existing_schedules)

    mock_db.add.assert_not_called()
    assert existing_schedule.transition_time == new_time
    assert existing_schedule.executed is False


@pytest.mark.asyncio
async def test_ensure_completed_schedule_creates_new(game_service, mock_db):
    """Test _ensure_completed_schedule creates new schedule when none exists."""
    from shared.models import game_status_schedule as game_status_schedule_model

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        expected_duration_minutes=60,
        status="SCHEDULED",
    )
    existing_schedules: list[game_status_schedule_model.GameStatusSchedule] = []

    mock_db.add = MagicMock()

    await game_service._ensure_completed_schedule(game, existing_schedules)

    mock_db.add.assert_called_once()
    added_schedule = mock_db.add.call_args[0][0]
    assert isinstance(added_schedule, game_status_schedule_model.GameStatusSchedule)
    assert added_schedule.game_id == game.id
    assert added_schedule.target_status == game_model.GameStatus.COMPLETED.value
    expected_time = scheduled_time + datetime.timedelta(minutes=60)
    assert added_schedule.transition_time == expected_time
    assert added_schedule.executed is False


@pytest.mark.asyncio
async def test_ensure_completed_schedule_uses_default_duration(game_service, mock_db):
    """Test _ensure_completed_schedule uses DEFAULT_GAME_DURATION_MINUTES when duration is None."""
    from shared.models import game_status_schedule as game_status_schedule_model

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        expected_duration_minutes=None,
        status="SCHEDULED",
    )
    existing_schedules: list[game_status_schedule_model.GameStatusSchedule] = []

    mock_db.add = MagicMock()

    await game_service._ensure_completed_schedule(game, existing_schedules)

    mock_db.add.assert_called_once()
    added_schedule = mock_db.add.call_args[0][0]
    # Should use DEFAULT_GAME_DURATION_MINUTES (60)
    expected_time = scheduled_time + datetime.timedelta(minutes=60)
    assert added_schedule.transition_time == expected_time


@pytest.mark.asyncio
async def test_ensure_completed_schedule_updates_existing(game_service, mock_db):
    """Test _ensure_completed_schedule updates existing schedule."""
    from shared.models import game_status_schedule as game_status_schedule_model

    old_time = datetime.datetime.now(datetime.UTC)
    new_scheduled_time = old_time + datetime.timedelta(hours=2)

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=new_scheduled_time,
        expected_duration_minutes=90,
        status="SCHEDULED",
    )

    existing_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=old_time,
        executed=True,
    )
    existing_schedules = [existing_schedule]

    mock_db.add = MagicMock()

    await game_service._ensure_completed_schedule(game, existing_schedules)

    mock_db.add.assert_not_called()
    expected_time = new_scheduled_time + datetime.timedelta(minutes=90)
    assert existing_schedule.transition_time == expected_time
    assert existing_schedule.executed is False


@pytest.mark.asyncio
async def test_update_status_schedules_for_scheduled_game(game_service, mock_db):
    """Test _update_status_schedules ensures both schedules exist for SCHEDULED game."""

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=scheduled_time,
        expected_duration_minutes=60,
        status="SCHEDULED",
    )

    schedules_result = MagicMock()
    schedules_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=schedules_result)
    mock_db.add = MagicMock()

    await game_service._update_status_schedules(game)

    # Should add both IN_PROGRESS and COMPLETED schedules
    assert mock_db.add.call_count == 2
    added_schedules = [call[0][0] for call in mock_db.add.call_args_list]

    in_progress_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.IN_PROGRESS.value
    )
    completed_schedule = next(
        s for s in added_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )

    assert in_progress_schedule.transition_time == scheduled_time
    assert completed_schedule.transition_time == scheduled_time + datetime.timedelta(minutes=60)


@pytest.mark.asyncio
async def test_update_status_schedules_deletes_for_non_scheduled_game(game_service, mock_db):
    """Test _update_status_schedules deletes all schedules for non-SCHEDULED game."""
    from shared.models import game_status_schedule as game_status_schedule_model

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        expected_duration_minutes=60,
        status="IN_PROGRESS",
    )

    schedule1 = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=datetime.datetime.now(datetime.UTC),
        executed=False,
    )
    schedule2 = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=datetime.datetime.now(datetime.UTC),
        executed=False,
    )

    schedules_result = MagicMock()
    schedules_result.scalars.return_value.all.return_value = [schedule1, schedule2]
    mock_db.execute = AsyncMock(return_value=schedules_result)
    mock_db.delete = AsyncMock()

    await game_service._update_status_schedules(game)

    # Should delete both schedules
    assert mock_db.delete.call_count == 2
    deleted_schedules = [call[0][0] for call in mock_db.delete.call_args_list]
    assert schedule1 in deleted_schedules
    assert schedule2 in deleted_schedules


@pytest.mark.asyncio
async def test_update_status_schedules_updates_existing_schedules(game_service, mock_db):
    """Test _update_status_schedules updates existing schedules for SCHEDULED game."""
    from shared.models import game_status_schedule as game_status_schedule_model

    old_time = datetime.datetime.now(datetime.UTC)
    new_time = old_time + datetime.timedelta(days=1)

    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=new_time,
        expected_duration_minutes=120,
        status="SCHEDULED",
    )

    in_progress_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=old_time,
        executed=True,
    )
    completed_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=old_time + datetime.timedelta(minutes=60),
        executed=True,
    )

    schedules_result = MagicMock()
    schedules_result.scalars.return_value.all.return_value = [
        in_progress_schedule,
        completed_schedule,
    ]
    mock_db.execute = AsyncMock(return_value=schedules_result)
    mock_db.add = MagicMock()

    await game_service._update_status_schedules(game)

    # Should not add new schedules
    mock_db.add.assert_not_called()

    # Should update existing schedules
    assert in_progress_schedule.transition_time == new_time
    assert in_progress_schedule.executed is False
    assert completed_schedule.transition_time == new_time + datetime.timedelta(minutes=120)
    assert completed_schedule.executed is False


@pytest.mark.asyncio
async def test_create_game_creates_status_schedules(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test create_game creates both IN_PROGRESS and COMPLETED status schedules."""
    from shared.models import game_status_schedule as game_status_schedule_model

    scheduled_time = datetime.datetime.now(datetime.UTC)
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        description="Test description",
        scheduled_at=scheduled_time,
        max_players=4,
        expected_duration_minutes=90,
        reminder_minutes=[60],
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        description="Test description",
        scheduled_at=scheduled_time,
        expected_duration_minutes=90,
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_participant_resolver.ensure_user_exists = AsyncMock(return_value=sample_user)

    added_objects = []

    def mock_add_side_effect(obj):
        added_objects.append(obj)
        if isinstance(obj, game_model.GameSession):
            obj.id = created_game.id
            obj.channel_id = created_game.channel_id

    mock_db.add.side_effect = mock_add_side_effect

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="mock_token",
        )

    # Verify status schedules were created
    status_schedules = [
        obj
        for obj in added_objects
        if isinstance(obj, game_status_schedule_model.GameStatusSchedule)
    ]
    assert len(status_schedules) == 2

    in_progress_schedule = next(
        s for s in status_schedules if s.target_status == game_model.GameStatus.IN_PROGRESS.value
    )
    completed_schedule = next(
        s for s in status_schedules if s.target_status == game_model.GameStatus.COMPLETED.value
    )

    assert in_progress_schedule.game_id == created_game.id
    # Compare times without timezone (SQLAlchemy may strip timezone)
    assert in_progress_schedule.transition_time.replace(tzinfo=None) == scheduled_time.replace(
        tzinfo=None
    )
    assert in_progress_schedule.executed is False

    assert completed_schedule.game_id == created_game.id
    expected_completion = scheduled_time + datetime.timedelta(minutes=90)
    assert completed_schedule.transition_time.replace(tzinfo=None) == expected_completion.replace(
        tzinfo=None
    )
    assert completed_schedule.executed is False


# Host Override Tests


@pytest.mark.asyncio
async def test_create_game_with_empty_host_defaults_to_current_user(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that empty host field defaults to current user (backward compatibility)."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        host=None,
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert game.host_id == sample_user.id


@pytest.mark.asyncio
async def test_create_game_regular_user_cannot_override_host(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_template,
    sample_guild,
    sample_user,
):
    """Test that regular user cannot specify different host."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        host="@different_user",
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            requester_result,
        ]
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=False)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(ValueError, match="Only bot managers can specify the game host"):
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )


@pytest.mark.asyncio
async def test_create_game_bot_manager_can_override_host(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that bot manager can specify different user as host."""
    different_host = user_model.User(id=str(uuid.uuid4()), discord_id="999888777")

    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        host="@different_host",
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=different_host.id,
        status="SCHEDULED",
    )
    created_game.host = different_host
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    resolved_host_result = MagicMock()
    resolved_host_result.scalar_one_or_none.return_value = different_host
    final_host_result = MagicMock()
    final_host_result.scalar_one_or_none.return_value = different_host
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            requester_result,
            resolved_host_result,
            final_host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)
    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {
                    "discord_id": different_host.discord_id,
                    "username": "different_host",
                    "display_name": "Different Host",
                    "original_input": "@different_host",
                }
            ],
            [],
        )
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert game.host_id == different_host.id


@pytest.mark.asyncio
async def test_create_game_bot_manager_invalid_host_raises_validation_error(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_template,
    sample_guild,
    sample_user,
):
    """Test that invalid host mention raises validation error."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        host="@invalid_user",
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            requester_result,
        ]
    )

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [],
            [
                {
                    "mention": "@invalid_user",
                    "error": "User not found",
                    "suggestions": [],
                }
            ],
        )
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(resolver_module.ValidationError) as exc_info:
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )

        assert len(exc_info.value.invalid_mentions) == 1
        assert exc_info.value.invalid_mentions[0]["mention"] == "@invalid_user"


@pytest.mark.asyncio
async def test_create_game_bot_manager_host_without_permissions_fails(
    game_service,
    mock_db,
    mock_participant_resolver,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that host without required role permissions fails."""
    template_with_restrictions = template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        name="Restricted Template",
        order=0,
        is_default=False,
        allowed_host_role_ids=["role123", "role456"],
        max_players=10,
        reminder_minutes=[60, 15],
    )

    different_host = user_model.User(id=str(uuid.uuid4()), discord_id="999888777")

    game_data = game_schemas.GameCreateRequest(
        template_id=template_with_restrictions.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        host="@different_host",
    )

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = template_with_restrictions
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    requester_result = MagicMock()
    requester_result.scalar_one_or_none.return_value = sample_user
    resolved_host_result = MagicMock()
    resolved_host_result.scalar_one_or_none.return_value = different_host
    final_host_result = MagicMock()
    final_host_result.scalar_one_or_none.return_value = different_host

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            requester_result,
            resolved_host_result,
            final_host_result,
        ]
    )
    mock_db.flush = AsyncMock()

    mock_role_service = AsyncMock()
    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)
    mock_role_service.check_game_host_permission = AsyncMock(return_value=False)

    mock_participant_resolver.resolve_initial_participants = AsyncMock(
        return_value=(
            [
                {
                    "discord_id": different_host.discord_id,
                    "username": "different_host",
                    "display_name": "Different Host",
                    "original_input": "@different_host",
                }
            ],
            [],
        )
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        with pytest.raises(
            ValueError,
            match="User does not have permission to create games with this template",
        ):
            await game_service.create_game(
                game_data=game_data,
                host_user_id=sample_user.id,
                access_token="token",
            )


@pytest.mark.asyncio
async def test_create_game_bot_manager_empty_host_uses_self(
    game_service,
    mock_db,
    mock_event_publisher,
    mock_participant_resolver,
    mock_role_service,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
):
    """Test that bot manager with empty host field defaults to themselves."""
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        host="",
    )

    created_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status="SCHEDULED",
    )
    created_game.host = sample_user
    created_game.participants = []

    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    host_result = MagicMock()
    host_result.scalar_one_or_none.return_value = sample_user
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = created_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            host_result,
            channel_result,
            reload_result,
        ]
    )
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    mock_role_service.check_bot_manager_permission = AsyncMock(return_value=True)

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="token",
        )

    assert game.host_id == sample_user.id
