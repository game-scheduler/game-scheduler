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


"""Unit tests for GameService error paths and miscellaneous branches.

Tests verify:
- join_game / leave_game defensive guard paths (game/user/config not found, reload fails)
- list_games optional filter branches
- update_game / delete_game error and permission-denied paths
- _resolve_game_host host-user-not-found path
- _apply_deadline_carryover early-return path
- _update_prefilled_participants / _add_new_mentions with mentions
- _schedule_join_notifications_for_game with confirmed participants
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.schemas.clone_game import CarryoverOption, CloneGameRequest
from services.api.services import participant_resolver as resolver_module
from services.api.services.games import GameService
from shared.models import game as game_model
from shared.models import participant as participant_model
from shared.models.participant import ParticipantType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db(mock_db_unit):
    """Alias for the shared mock AsyncSession fixture."""
    return mock_db_unit


@pytest.fixture
def game_service(mock_db):
    """GameService wired with fully-mocked dependencies."""
    return GameService(
        db=mock_db,
        event_publisher=AsyncMock(),
        discord_client=AsyncMock(),
        participant_resolver=AsyncMock(),
        channel_resolver=AsyncMock(),
    )


def _make_game(
    status: str = game_model.GameStatus.SCHEDULED.value,
    guild_id: str = "guild-uuid-1",
    channel_id: str = "channel-uuid-1",
    max_players: int | None = 4,
) -> MagicMock:
    """Return a minimal game mock."""
    game = MagicMock(spec=game_model.GameSession)
    game.id = "game-uuid-1"
    game.status = status
    game.guild_id = guild_id
    game.channel_id = channel_id
    game.max_players = max_players
    game.scheduled_at = datetime.datetime(2026, 6, 1, 20, 0, tzinfo=datetime.UTC)
    guild = MagicMock()
    guild.guild_id = "discord-guild-id"
    game.guild = guild
    host = MagicMock()
    host.discord_id = "host-discord-id"
    game.host = host
    game.participants = []
    game.thumbnail_id = None
    game.banner_image_id = None
    return game


def _make_db_scalar_result(value):
    """Return a mock db.execute() result with scalar_one_or_none() set."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_db_scalar_value(value):
    """Return a mock db.execute() result with scalar() set."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_db_scalars_result(values):
    """Return a mock db.execute() result with scalars().all() set."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


# ---------------------------------------------------------------------------
# TestJoinGame
# ---------------------------------------------------------------------------


class TestJoinGame:
    """Tests for GameService.join_game error paths."""

    @pytest.mark.asyncio
    async def test_game_not_found_raises_error(self, game_service):
        """Raises ValueError when game is not found."""
        game_service.get_game = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Game not found"):
            await game_service.join_game("missing-game", "user123")

    @pytest.mark.asyncio
    async def test_game_not_scheduled_raises_error(self, game_service):
        """Raises ValueError when game is not in SCHEDULED status."""
        completed_game = _make_game(status=game_model.GameStatus.COMPLETED.value)
        game_service.get_game = AsyncMock(return_value=completed_game)

        with pytest.raises(ValueError, match="not open for joining"):
            await game_service.join_game(completed_game.id, "user123")

    @pytest.mark.asyncio
    async def test_guild_config_not_found_raises_error(self, game_service, mock_db):
        """Raises ValueError when guild configuration is missing."""
        game = _make_game()
        game_service.get_game = AsyncMock(return_value=game)

        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        game_service.participant_resolver.ensure_user_exists = AsyncMock(return_value=mock_user)

        # No existing participant, count = 0, then guild_config = None
        mock_db.execute.side_effect = [
            _make_db_scalar_result(None),  # existing_participant query
            _make_db_scalar_value(0),  # count query
            _make_db_scalar_result(None),  # guild_config query → triggers error
        ]

        with pytest.raises(ValueError, match="Guild configuration not found"):
            await game_service.join_game(game.id, "user123")

    @pytest.mark.asyncio
    async def test_channel_config_not_found_raises_error(self, game_service, mock_db):
        """Raises ValueError when channel configuration is missing."""
        game = _make_game()
        game_service.get_game = AsyncMock(return_value=game)

        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        game_service.participant_resolver.ensure_user_exists = AsyncMock(return_value=mock_user)

        mock_guild_config = MagicMock()
        mock_db.execute.side_effect = [
            _make_db_scalar_result(None),  # existing_participant
            _make_db_scalar_value(0),  # count
            _make_db_scalar_result(mock_guild_config),  # guild_config
            _make_db_scalar_result(None),  # channel_config → triggers error
        ]

        with pytest.raises(ValueError, match="Channel configuration not found"):
            await game_service.join_game(game.id, "user123")

    @pytest.mark.asyncio
    async def test_game_full_raises_error(self, game_service, mock_db):
        """Raises ValueError when game has no available spots."""
        game = _make_game(max_players=2)
        game_service.get_game = AsyncMock(return_value=game)

        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        game_service.participant_resolver.ensure_user_exists = AsyncMock(return_value=mock_user)

        mock_guild_config = MagicMock()
        mock_channel_config = MagicMock()
        mock_db.execute.side_effect = [
            _make_db_scalar_result(None),  # existing_participant
            _make_db_scalar_value(2),  # count = 2 (full)
            _make_db_scalar_result(mock_guild_config),  # guild_config
            _make_db_scalar_result(mock_channel_config),  # channel_config
        ]

        with pytest.raises(ValueError, match="Game is full"):
            await game_service.join_game(game.id, "user123")

    @pytest.mark.asyncio
    async def test_reload_failure_after_join_raises_error(self, game_service, mock_db):
        """Raises ValueError when game cannot be reloaded after joining."""
        game = _make_game(max_players=None)
        # First get_game returns valid game; second call returns None
        game_service.get_game = AsyncMock(side_effect=[game, None])

        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        game_service.participant_resolver.ensure_user_exists = AsyncMock(return_value=mock_user)

        mock_participant = MagicMock()
        mock_participant.id = "participant-uuid"
        mock_guild_config = MagicMock()
        mock_channel_config = MagicMock()
        mock_db.execute.side_effect = [
            _make_db_scalar_result(None),  # existing_participant
            _make_db_scalar_value(0),  # count
            _make_db_scalar_result(mock_guild_config),  # guild_config
            _make_db_scalar_result(mock_channel_config),  # channel_config
        ]
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        with (
            patch(
                "services.api.services.games.schedule_join_notification",
                new_callable=AsyncMock,
            ),
            pytest.raises(ValueError, match="Failed to reload game after join"),
        ):
            await game_service.join_game(game.id, "user123")


# ---------------------------------------------------------------------------
# TestLeaveGame
# ---------------------------------------------------------------------------


class TestLeaveGame:
    """Tests for GameService.leave_game error paths."""

    @pytest.mark.asyncio
    async def test_game_not_found_raises_error(self, game_service):
        """Raises ValueError when game is not found."""
        game_service.get_game = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Game not found"):
            await game_service.leave_game("missing-game", "user123")

    @pytest.mark.asyncio
    async def test_completed_game_raises_error(self, game_service):
        """Raises ValueError when trying to leave a completed game."""
        completed_game = _make_game(status=game_model.GameStatus.COMPLETED.value)
        game_service.get_game = AsyncMock(return_value=completed_game)

        with pytest.raises(ValueError, match="Cannot leave completed game"):
            await game_service.leave_game(completed_game.id, "user123")

    @pytest.mark.asyncio
    async def test_user_not_found_raises_error(self, game_service, mock_db):
        """Raises ValueError when user is not in the database."""
        game = _make_game()
        game_service.get_game = AsyncMock(return_value=game)

        # User query returns None
        mock_db.execute.return_value = _make_db_scalar_result(None)

        with pytest.raises(ValueError, match="User not found"):
            await game_service.leave_game(game.id, "unknown-discord-id")

    @pytest.mark.asyncio
    async def test_reload_failure_after_leave_raises_error(self, game_service, mock_db):
        """Raises ValueError when game cannot be reloaded after leaving."""
        game = _make_game()
        # First call returns valid game; second call (after leave) returns None
        game_service.get_game = AsyncMock(side_effect=[game, None])

        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        mock_user.discord_id = "user123"
        mock_participant = MagicMock()
        mock_participant.id = "participant-uuid"
        mock_db.execute.side_effect = [
            _make_db_scalar_result(mock_user),  # user query
            _make_db_scalar_result(mock_participant),  # participant query
        ]
        mock_db.delete = AsyncMock()

        with pytest.raises(ValueError, match="Failed to reload game after leave"):
            await game_service.leave_game(game.id, "user123")


# ---------------------------------------------------------------------------
# TestListGames
# ---------------------------------------------------------------------------


class TestListGames:
    """Tests for optional filter branches in GameService.list_games."""

    @pytest.mark.asyncio
    async def test_with_guild_id_filter(self, game_service, mock_db):
        """Exercises the guild_id filter branches in list_games."""
        mock_game = _make_game()
        mock_db.execute.side_effect = [
            _make_db_scalar_value(1),  # count query
            _make_db_scalars_result([mock_game]),  # games query
        ]

        games, total = await game_service.list_games(guild_id="guild-uuid-1")

        assert total == 1
        assert games == [mock_game]

    @pytest.mark.asyncio
    async def test_with_status_filter(self, game_service, mock_db):
        """Exercises the status filter branch in list_games."""
        mock_db.execute.side_effect = [
            _make_db_scalar_value(0),
            _make_db_scalars_result([]),
        ]

        games, total = await game_service.list_games(status=["SCHEDULED"])

        assert total == 0
        assert games == []

    @pytest.mark.asyncio
    async def test_with_channel_id_and_status_filter(self, game_service, mock_db):
        """Exercises channel_id and status filter branches together."""
        mock_db.execute.side_effect = [
            _make_db_scalar_value(0),
            _make_db_scalars_result([]),
        ]

        games, total = await game_service.list_games(
            channel_id="channel-uuid-1", status=["SCHEDULED"]
        )

        assert total == 0
        assert games == []

    @pytest.mark.asyncio
    async def test_list_games_multi_status_filter(self, game_service, mock_db):
        """list_games accepts a list of statuses and returns only matching games."""
        scheduled = _make_game(status=game_model.GameStatus.SCHEDULED.value)
        completed = _make_game(status=game_model.GameStatus.COMPLETED.value)
        in_progress = _make_game(status=game_model.GameStatus.IN_PROGRESS.value)

        mock_db.execute.side_effect = [
            _make_db_scalar_value(2),
            _make_db_scalars_result([scheduled, completed, in_progress]),
        ]

        games, total = await game_service.list_games(status=["SCHEDULED", "COMPLETED"])

        statuses = {g.status for g in games}
        assert statuses == {
            game_model.GameStatus.SCHEDULED.value,
            game_model.GameStatus.COMPLETED.value,
        }
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_games_single_status_as_list(self, game_service, mock_db):
        """list_games accepts a single-element list and returns only matching games."""
        scheduled = _make_game(status=game_model.GameStatus.SCHEDULED.value)
        completed = _make_game(status=game_model.GameStatus.COMPLETED.value)

        mock_db.execute.side_effect = [
            _make_db_scalar_value(1),
            _make_db_scalars_result([scheduled, completed]),
        ]

        games, total = await game_service.list_games(status=["SCHEDULED"])

        statuses = {g.status for g in games}
        assert statuses == {game_model.GameStatus.SCHEDULED.value}
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_games_sort_order(self, game_service, mock_db):
        """Games are sorted: SCHEDULED asc → IN_PROGRESS → COMPLETED desc → CANCELLED desc."""
        scheduled_soon = _make_game(status=game_model.GameStatus.SCHEDULED.value)
        scheduled_soon.scheduled_at = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)

        scheduled_later = _make_game(status=game_model.GameStatus.SCHEDULED.value)
        scheduled_later.scheduled_at = datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC)

        in_progress = _make_game(status=game_model.GameStatus.IN_PROGRESS.value)
        in_progress.scheduled_at = datetime.datetime(2026, 5, 1, tzinfo=datetime.UTC)

        completed_recent = _make_game(status=game_model.GameStatus.COMPLETED.value)
        completed_recent.scheduled_at = datetime.datetime(2026, 4, 15, tzinfo=datetime.UTC)

        completed_older = _make_game(status=game_model.GameStatus.COMPLETED.value)
        completed_older.scheduled_at = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC)

        cancelled = _make_game(status=game_model.GameStatus.CANCELLED.value)
        cancelled.scheduled_at = datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC)

        # DB returns games in unsorted order to exercise Python-side sorting.
        mock_db.execute.side_effect = [
            _make_db_scalar_value(6),
            _make_db_scalars_result([
                completed_recent,
                scheduled_soon,
                cancelled,
                in_progress,
                scheduled_later,
                completed_older,
            ]),
        ]

        games, total = await game_service.list_games()

        expected = [
            scheduled_soon,
            scheduled_later,
            in_progress,
            completed_recent,
            completed_older,
            cancelled,
        ]
        assert games == expected
        assert total == 6


# ---------------------------------------------------------------------------
# TestUpdateGame
# ---------------------------------------------------------------------------


class TestUpdateGame:
    """Tests for GameService.update_game error paths."""

    @pytest.mark.asyncio
    async def test_game_not_found_raises_error(self, game_service):
        """Raises ValueError when the target game does not exist."""
        game_service.get_game = AsyncMock(return_value=None)
        mock_user = MagicMock()
        mock_role_service = MagicMock()

        with pytest.raises(ValueError, match="Game not found"):
            await game_service.update_game(
                "missing-game",
                MagicMock(),
                mock_user,
                mock_role_service,
            )

    @pytest.mark.asyncio
    async def test_permission_denied_raises_error(self, game_service):
        """Raises ValueError when caller lacks permission to update the game."""
        game = _make_game()
        game_service.get_game = AsyncMock(return_value=game)
        mock_role_service = MagicMock()
        mock_user = MagicMock()

        with patch(
            "services.api.dependencies.permissions.can_manage_game",
            return_value=False,
        ):
            with pytest.raises(ValueError, match="don't have permission to update"):
                await game_service.update_game(
                    game.id,
                    MagicMock(),
                    mock_user,
                    mock_role_service,
                )


# ---------------------------------------------------------------------------
# TestDeleteGame
# ---------------------------------------------------------------------------


class TestDeleteGame:
    """Tests for GameService.delete_game error paths."""

    @pytest.mark.asyncio
    async def test_game_not_found_raises_error(self, game_service):
        """Raises ValueError when the target game does not exist."""
        game_service.get_game = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Game not found"):
            await game_service.delete_game("missing-game", MagicMock(), MagicMock())

    @pytest.mark.asyncio
    async def test_permission_denied_raises_error(self, game_service):
        """Raises ValueError when caller lacks permission to cancel the game."""
        game = _make_game()
        game_service.get_game = AsyncMock(return_value=game)

        with patch(
            "services.api.dependencies.permissions.can_manage_game",
            return_value=False,
        ):
            with pytest.raises(ValueError, match="don't have permission to cancel"):
                await game_service.delete_game(game.id, MagicMock(), MagicMock())


# ---------------------------------------------------------------------------
# TestResolveGameHost
# ---------------------------------------------------------------------------


class TestResolveGameHost:
    """Tests for GameService._resolve_game_host error paths."""

    @pytest.mark.asyncio
    async def test_host_user_not_found_raises_error(self, game_service, mock_db):
        """Raises ValueError when the host user record is missing."""
        mock_game_data = MagicMock()
        mock_game_data.host = None  # no host override

        mock_guild_config = MagicMock()
        mock_guild_config.guild_id = "discord-guild-id"

        # User query returns None
        mock_db.execute.return_value = _make_db_scalar_result(None)

        with pytest.raises(ValueError, match="Host user not found"):
            await game_service._resolve_game_host(mock_game_data, mock_guild_config, "user-uuid-1")


# ---------------------------------------------------------------------------
# TestApplyDeadlineCarryover
# ---------------------------------------------------------------------------


class TestApplyDeadlineCarryover:
    """Tests for GameService._apply_deadline_carryover edge cases."""

    @pytest.mark.asyncio
    async def test_returns_early_when_no_deadline_carryover(self, game_service):
        """Returns immediately when neither player nor waitlist uses deadline carryover."""
        mock_new_game = _make_game()
        clone_data = CloneGameRequest(
            player_carryover=CarryoverOption.YES,
            waitlist_carryover=CarryoverOption.YES,
            scheduled_at=datetime.datetime(2026, 7, 1, 20, 0, tzinfo=datetime.UTC),
            max_players=4,
        )

        # Should complete without any DB calls
        await game_service._apply_deadline_carryover(mock_new_game, [], [], clone_data)

        game_service.db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_group_with_empty_source_participants(self, game_service):
        """Skips a group in the loop when source_participants is an empty list."""
        mock_new_game = _make_game()
        mock_new_game.participants = []

        clone_data = CloneGameRequest(
            player_carryover=CarryoverOption.YES_WITH_DEADLINE,
            waitlist_carryover=CarryoverOption.YES,
            scheduled_at=datetime.datetime(2026, 7, 1, 20, 0, tzinfo=datetime.UTC),
            max_players=4,
            player_deadline=datetime.datetime(2026, 6, 25, 20, 0, tzinfo=datetime.UTC),
        )

        # Empty players list triggers "not source_participants" → continue
        await game_service._apply_deadline_carryover(
            mock_new_game,
            [],  # players_to_carry is empty
            [],
            clone_data,
        )

        game_service.db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# TestScheduleJoinNotifications
# ---------------------------------------------------------------------------


class TestScheduleJoinNotifications:
    """Tests for GameService._schedule_join_notifications_for_game."""

    @pytest.mark.asyncio
    async def test_schedules_notification_for_confirmed_discord_participant(
        self, game_service, mock_db
    ):
        """Calls schedule_join_notification for each confirmed participant with a user_id."""
        game = _make_game(max_players=4)
        game.scheduled_at = datetime.datetime(2026, 6, 1, 20, 0, tzinfo=datetime.UTC)

        participant = MagicMock(spec=participant_model.GameParticipant)
        participant.id = "participant-uuid"
        participant.user_id = "user-uuid"
        participant.position_type = ParticipantType.SELF_ADDED
        participant.position = 0
        game.participants = [participant]

        with patch(
            "services.api.services.games.schedule_join_notification",
            new_callable=AsyncMock,
        ) as mock_schedule:
            await game_service._schedule_join_notifications_for_game(game)

        mock_schedule.assert_called_once_with(
            db=mock_db,
            game_id=game.id,
            participant_id=participant.id,
            game_scheduled_at=game.scheduled_at,
            delay_seconds=60,
        )

    @pytest.mark.asyncio
    async def test_skips_display_name_only_participant(self, game_service):
        """Does not schedule notifications for participants without a user_id."""
        game = _make_game(max_players=4)

        placeholder = MagicMock(spec=participant_model.GameParticipant)
        placeholder.id = "placeholder-uuid"
        placeholder.user_id = None  # display-name participant, no Discord link
        placeholder.position_type = ParticipantType.SELF_ADDED
        placeholder.position = 0
        game.participants = [placeholder]

        with patch(
            "services.api.services.games.schedule_join_notification",
            new_callable=AsyncMock,
        ) as mock_schedule:
            await game_service._schedule_join_notifications_for_game(game)

        mock_schedule.assert_not_called()


# ---------------------------------------------------------------------------
# TestAddNewMentions
# ---------------------------------------------------------------------------


class TestAddNewMentions:
    """Tests for GameService._add_new_mentions paths."""

    @pytest.mark.asyncio
    async def test_adds_discord_participant(self, game_service, mock_db):
        """Creates a HOST_ADDED participant record for a resolved Discord mention."""
        game = _make_game()
        guild = MagicMock()
        guild.guild_id = "discord-guild-id"
        game.guild = guild
        game.participants = []

        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        game_service.participant_resolver.ensure_user_exists = AsyncMock(return_value=mock_user)
        game_service.participant_resolver.resolve_initial_participants = AsyncMock(
            return_value=(
                [
                    {
                        "type": "discord",
                        "discord_id": "discord-123",
                        "original_input": "@user",
                    }
                ],
                [],
            )
        )
        mock_db.flush = AsyncMock()

        with patch(
            "services.api.services.games.schedule_join_notification",
            new_callable=AsyncMock,
        ):
            await game_service._add_new_mentions(game, [("@user", 1)])

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.user_id == mock_user.id
        assert added.position_type == ParticipantType.HOST_ADDED

    @pytest.mark.asyncio
    async def test_adds_display_name_participant(self, game_service, mock_db):
        """Creates a HOST_ADDED participant with display_name when type is not discord."""
        game = _make_game()
        guild = MagicMock()
        guild.guild_id = "discord-guild-id"
        game.guild = guild
        game.participants = []

        game_service.participant_resolver.resolve_initial_participants = AsyncMock(
            return_value=(
                [
                    {
                        "type": "display_name",
                        "display_name": "Alice",
                        "original_input": "Alice",
                    }
                ],
                [],
            )
        )
        mock_db.flush = AsyncMock()

        with patch(
            "services.api.services.games.schedule_join_notification",
            new_callable=AsyncMock,
        ):
            await game_service._add_new_mentions(game, [("Alice", 2)])

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.user_id is None
        assert added.display_name == "Alice"
        assert added.position_type == ParticipantType.HOST_ADDED

    @pytest.mark.asyncio
    async def test_validation_error_raises(self, game_service):
        """Re-raises ValidationError when mentions cannot be resolved."""
        game = _make_game()
        guild = MagicMock()
        guild.guild_id = "discord-guild-id"
        game.guild = guild

        game_service.participant_resolver.resolve_initial_participants = AsyncMock(
            return_value=([], ["@unknown"])
        )

        with pytest.raises(resolver_module.ValidationError):
            await game_service._add_new_mentions(game, [("@unknown", 0)])


# ---------------------------------------------------------------------------
# TestUpdatePrefilledParticipants
# ---------------------------------------------------------------------------


class TestUpdatePrefilledParticipants:
    """Tests for GameService._update_prefilled_participants paths."""

    @pytest.mark.asyncio
    async def test_calls_add_new_mentions_for_mention_entries(self, game_service, mock_db):
        """Calls _add_new_mentions when participant data includes mention strings."""
        game = _make_game()
        guild = MagicMock()
        guild.guild_id = "discord-guild-id"
        game.guild = guild
        game.participants = []

        mock_db.flush = AsyncMock()
        # Return empty list as current HOST_ADDED participants
        mock_db.execute.return_value = _make_db_scalars_result([])

        game_service.participant_resolver.resolve_initial_participants = AsyncMock(
            return_value=(
                [
                    {
                        "type": "discord",
                        "discord_id": "disc-1",
                        "original_input": "@user",
                    }
                ],
                [],
            )
        )
        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        game_service.participant_resolver.ensure_user_exists = AsyncMock(return_value=mock_user)

        participant_data_list = [{"mention": "@user", "position": 1}]

        with patch(
            "services.api.services.games.schedule_join_notification",
            new_callable=AsyncMock,
        ):
            await game_service._update_prefilled_participants(game, participant_data_list)

        mock_db.add.assert_called_once()
        participant_added = mock_db.add.call_args[0][0]
        assert participant_added.game_session_id == "game-uuid-1"
        assert participant_added.user_id == "user-uuid"
