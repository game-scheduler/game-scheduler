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


"""Tests for waitlist promotion notifications in game service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services.games import GameService
from shared.messaging.events import EventType
from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession
from shared.models.guild import GuildConfiguration
from shared.models.participant import GameParticipant
from shared.models.user import User
from shared.schemas.game import GameUpdateRequest


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher."""
    publisher = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def mock_discord_client():
    """Mock Discord API client."""
    return AsyncMock()


@pytest.fixture
def mock_participant_resolver():
    """Mock participant resolver."""
    return AsyncMock()


@pytest.fixture
def game_service(mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver):
    """Create game service with mocks."""
    return GameService(
        db=mock_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_client,
        participant_resolver=mock_participant_resolver,
    )


@pytest.fixture
def sample_guild():
    """Sample guild configuration."""
    return GuildConfiguration(
        id=str(uuid4()),
        guild_id="123456789",
        default_max_players=5,
    )


@pytest.fixture
def sample_channel(sample_guild):
    """Sample channel configuration."""
    return ChannelConfiguration(
        id=str(uuid4()),
        guild_id=sample_guild.id,
        channel_id="987654321",
        channel_name="test-channel",
        is_active=True,
    )


@pytest.fixture
def sample_host():
    """Sample host user."""
    return User(id=str(uuid4()), discord_id="111111111")


@pytest.fixture
def sample_game(sample_guild, sample_channel, sample_host):
    """Sample game session with 5 max players."""
    game = GameSession(
        id=str(uuid4()),
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None),
        max_players=5,
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_host.id,
        message_id="999999999",
        status="SCHEDULED",
        participants=[],
    )
    # Set relationships manually since we're not using database session
    game.guild = sample_guild
    game.channel = sample_channel
    game.host = sample_host
    return game


def create_participant(game_id: str, user_id: str, discord_id: str, joined_at: datetime):
    """Create a participant with user."""
    user = User(id=user_id, discord_id=discord_id)
    return GameParticipant(
        id=str(uuid4()),
        game_session_id=game_id,
        user_id=user_id,
        joined_at=joined_at,
        user=user,
    )


@pytest.mark.asyncio
async def test_promotion_when_max_players_increased(
    game_service, sample_game, mock_event_publisher, mock_db
):
    """Test promotion notification when max_players is increased."""
    # Setup: 5 confirmed + 2 overflow participants
    base_time = datetime.now(UTC).replace(tzinfo=None)
    participants = [
        create_participant(sample_game.id, str(uuid4()), f"confirmed_{i}", base_time)
        for i in range(5)
    ]
    overflow_participants = [
        create_participant(sample_game.id, str(uuid4()), f"overflow_{i}", base_time)
        for i in range(2)
    ]
    sample_game.participants = participants + overflow_participants

    # Mock database operations
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.flush = AsyncMock()

    # Mock get_game to return our sample game
    with patch.object(game_service, "get_game", return_value=sample_game):
        # Mock authorization check
        mock_role_service = AsyncMock()
        mock_current_user = MagicMock()
        mock_current_user.discord_id = sample_game.host.discord_id

        with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
            # Update max_players from 5 to 7 (promoting 2 overflow users)
            update_request = GameUpdateRequest(max_players=7)

            await game_service.update_game(
                game_id=sample_game.id,
                update_data=update_request,
                current_user=mock_current_user,
                role_service=mock_role_service,
            )

    # Verify promotion notifications were published
    publish_calls = mock_event_publisher.publish.call_args_list

    # Find notification events
    notification_calls = [
        call
        for call in publish_calls
        if call[1]["event"].event_type == EventType.NOTIFICATION_SEND_DM
    ]

    assert len(notification_calls) == 2, "Should send 2 promotion notifications"

    # Verify notification content
    for call in notification_calls:
        event_data = call[1]["event"].data
        assert event_data["notification_type"] == "waitlist_promotion"
        assert "A spot opened up" in event_data["message"]
        assert event_data["game_title"] == sample_game.title


@pytest.mark.asyncio
async def test_promotion_when_participant_removed(
    game_service, sample_game, mock_event_publisher, mock_db
):
    """Test promotion notification when a confirmed participant is removed."""
    # Setup: 5 confirmed + 1 overflow participant
    base_time = datetime.now(UTC).replace(tzinfo=None)
    participants = [
        create_participant(sample_game.id, str(uuid4()), f"confirmed_{i}", base_time)
        for i in range(5)
    ]
    overflow_participant = create_participant(sample_game.id, str(uuid4()), "overflow_0", base_time)

    # Initially all 6 participants in the game
    sample_game.participants = participants + [overflow_participant]

    # Mock database operations
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.delete = AsyncMock()

    # Mock execute to return participant to remove
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=participants[0])
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock refresh to update participants list (simulate DB refresh after deletion)
    def mock_refresh_side_effect(game):
        # After removal, participant list has one less confirmed participant
        # This simulates what would happen after db.refresh() in real scenario
        game.participants = participants[1:] + [overflow_participant]

    mock_db.refresh = AsyncMock(side_effect=mock_refresh_side_effect)

    # Create a fresh game object with updated participants
    # (simulating what get_game would return after DB reload)
    get_game_call_count = [0]

    def get_game_side_effect(game_id):
        # Return a fresh GameSession with participants list after removal
        get_game_call_count[0] += 1

        # First call (at start of update_game): return game with all 6 participants (before removal)
        # Second call (after commit): return game with 5 participants (after removal)
        if get_game_call_count[0] == 1:
            participants_list = participants + [overflow_participant]
            print(
                f"\nget_game call #1: returning BEFORE removal - "
                f"{len(participants_list)} participants"
            )
        else:
            participants_list = participants[1:] + [overflow_participant]
            print(
                f"\nget_game call #{get_game_call_count[0]}: "
                f"returning AFTER removal - {len(participants_list)} participants"
            )

        fresh_game = GameSession(
            id=sample_game.id,
            title=sample_game.title,
            description=sample_game.description,
            scheduled_at=sample_game.scheduled_at,
            max_players=sample_game.max_players,
            guild_id=sample_game.guild_id,
            channel_id=sample_game.channel_id,
            host_id=sample_game.host_id,
            message_id=sample_game.message_id,
            status=sample_game.status,
            participants=participants_list,
        )
        fresh_game.host = sample_game.host
        fresh_game.channel = sample_game.channel
        fresh_game.guild = sample_game.guild
        print(f"Participant discord_ids: {[p.user.discord_id for p in fresh_game.participants]}")
        return fresh_game

    # Mock get_game to return fresh game with updated participants
    original_detect_promotions = game_service._detect_and_notify_promotions
    detect_calls_list = []

    async def track_detect_promotions(game, old_overflow_ids):
        detect_calls_list.append({
            'game_id': game.id,
            'old_overflow_ids': old_overflow_ids,
            'current_participants': [p.user.discord_id for p in game.participants if p.user]
        })
        print("\n_detect_and_notify_promotions called!")
        print(f"  old_overflow_ids: {old_overflow_ids}")
        print(f"  current participants: {[p.user.discord_id for p in game.participants if p.user]}")
        result = await original_detect_promotions(game, old_overflow_ids)
        print("  _detect_and_notify_promotions completed")
        return result

    with patch.object(
        game_service, '_detect_and_notify_promotions', side_effect=track_detect_promotions
    ):
        with patch.object(game_service, "get_game", side_effect=get_game_side_effect):
            # Mock authorization check
            mock_role_service = AsyncMock()
            mock_current_user = MagicMock()
            mock_current_user.discord_id = sample_game.host.discord_id

            with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
                # Remove one confirmed participant (should promote overflow)
                update_request = GameUpdateRequest(removed_participant_ids=[participants[0].id])

                try:
                    result = await game_service.update_game(
                        game_id=sample_game.id,
                        update_data=update_request,
                        current_user=mock_current_user,
                        role_service=mock_role_service,
                    )
                    print(
                        f"\nUpdate completed successfully, "
                        f"result id: {result.id if result else 'None'}"
                    )
                    print(
                        f"Result participants: "
                        f"{len(result.participants) if result else 0}"
                    )
                except Exception as e:
                    print(f"\nUpdate failed with exception: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    raise

    # Verify promotion notification was published
    publish_calls = mock_event_publisher.publish.call_args_list

    # Debug: print all publish calls
    print(f"\nTotal publish calls: {len(publish_calls)}")
    for i, call in enumerate(publish_calls):
        event = call[1]["event"]
        print(f"Call {i}: event_type={event.event_type}, data={event.data}")

    notification_calls = [
        call
        for call in publish_calls
        if call[1]["event"].event_type == EventType.NOTIFICATION_SEND_DM
    ]

    assert len(notification_calls) == 1, (
        f"Should send 1 promotion notification, got {len(notification_calls)}"
    )

    event_data = notification_calls[0][1]["event"].data
    assert event_data["notification_type"] == "waitlist_promotion"
    assert event_data["user_id"] == overflow_participant.user.discord_id


@pytest.mark.asyncio
async def test_no_promotion_when_no_overflow(
    game_service, sample_game, mock_event_publisher, mock_db
):
    """Test that no promotion notifications are sent when there's no overflow."""
    # Setup: Only 3 confirmed participants (under max_players=5)
    base_time = datetime.now(UTC).replace(tzinfo=None)
    participants = [
        create_participant(sample_game.id, str(uuid4()), f"confirmed_{i}", base_time)
        for i in range(3)
    ]
    sample_game.participants = participants

    # Mock database operations
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.flush = AsyncMock()

    # Mock get_game to return our sample game
    with patch.object(game_service, "get_game", return_value=sample_game):
        mock_role_service = AsyncMock()
        mock_current_user = MagicMock()
        mock_current_user.discord_id = sample_game.host.discord_id

        with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
            # Increase max_players (but no overflow to promote)
            update_request = GameUpdateRequest(max_players=7)

            await game_service.update_game(
                game_id=sample_game.id,
                update_data=update_request,
                current_user=mock_current_user,
                role_service=mock_role_service,
            )

    # Verify no promotion notifications were published
    publish_calls = mock_event_publisher.publish.call_args_list

    notification_calls = [
        call
        for call in publish_calls
        if call[1]["event"].event_type == EventType.NOTIFICATION_SEND_DM
    ]

    assert len(notification_calls) == 0, "Should not send promotion notifications"
