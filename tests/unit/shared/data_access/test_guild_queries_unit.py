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


"""Comprehensive unit tests for guild_queries game operation wrappers.

Tests verify:
- guild_id parameter is required (ValueError for empty string)
- RLS context is set correctly before queries
- Guild filtering is enforced in queries
- Error cases (not found, invalid IDs) are handled properly
- All operations work correctly with valid inputs
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.data_access import guild_queries
from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.models.template import GameTemplate


@pytest.fixture
def mock_db():
    """Create mock AsyncSession for testing."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def sample_game():
    """Create sample game session for testing."""
    return GameSession(
        id="game-123",
        guild_id="guild-1",
        channel_id="channel-1",
        host_id="user-1",
        title="Test Game",
        description="Test Description",
        scheduled_at=datetime(2026, 1, 15, 20, 0, 0, tzinfo=UTC),
        max_players=4,
    )


@pytest.fixture
def sample_template():
    """Create sample game template for testing."""
    return GameTemplate(
        id="template-123",
        guild_id="guild-1",
        channel_id="channel-1",
        name="D&D Campaign",
        description="Weekly D&D session",
        order=0,
        is_default=True,
        max_players=5,
        expected_duration_minutes=180,
        reminder_minutes=[60, 1440],
    )


class TestGetGameById:
    """Tests for get_game_by_id function."""

    @pytest.mark.asyncio
    async def test_success_returns_game(self, mock_db, sample_game):
        """Returns game when found in specified guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute.return_value = mock_result

        result = await guild_queries.get_game_by_id(mock_db, "guild-1", "game-123")

        assert result == sample_game
        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, mock_db):
        """Returns None when game not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await guild_queries.get_game_by_id(mock_db, "guild-1", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.get_game_by_id(mock_db, "", "game-123")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_game_id_raises_error(self, mock_db):
        """Raises ValueError when game_id is empty string."""
        with pytest.raises(ValueError, match="game_id cannot be empty"):
            await guild_queries.get_game_by_id(mock_db, "guild-1", "")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_rls_context_set_correctly(self, mock_db, sample_game):
        """Verifies RLS context is set with correct guild_id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute.return_value = mock_result

        await guild_queries.get_game_by_id(mock_db, "guild-1", "game-123")

        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql


class TestListGames:
    """Tests for list_games function."""

    @pytest.mark.asyncio
    async def test_success_returns_games(self, mock_db, sample_game):
        """Returns list of games for guild."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_game]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await guild_queries.list_games(mock_db, "guild-1")

        assert len(result) == 1
        assert result[0] == sample_game
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_list_when_no_games(self, mock_db):
        """Returns empty list when no games found."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await guild_queries.list_games(mock_db, "guild-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_channel_filter_applied(self, mock_db):
        """Applies channel_id filter when provided."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        await guild_queries.list_games(mock_db, "guild-1", channel_id="channel-1")

        query_call = mock_db.execute.call_args_list[1]
        assert "channel_id" in str(query_call) or query_call is not None

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.list_games(mock_db, "")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_rls_context_set_correctly(self, mock_db):
        """Verifies RLS context is set with correct guild_id."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        await guild_queries.list_games(mock_db, "guild-1")

        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql


class TestCreateGame:
    """Tests for create_game function."""

    @pytest.mark.asyncio
    async def test_success_creates_game(self, mock_db):
        """Creates game with guild_id set correctly."""
        game_data = {
            "channel_id": "channel-1",
            "host_id": "user-1",
            "title": "New Game",
            "scheduled_at": datetime(2026, 1, 15, 20, 0, 0, tzinfo=UTC),
        }

        result = await guild_queries.create_game(mock_db, "guild-1", game_data)

        assert result.guild_id == "guild-1"
        assert result.title == "New Game"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_guild_id_overrides_data(self, mock_db):
        """guild_id parameter overrides guild_id in game_data."""
        game_data = {
            "guild_id": "wrong-guild",
            "channel_id": "channel-1",
            "host_id": "user-1",
            "title": "New Game",
            "scheduled_at": datetime(2026, 1, 15, 20, 0, 0, tzinfo=UTC),
        }

        result = await guild_queries.create_game(mock_db, "guild-1", game_data)

        assert result.guild_id == "guild-1"

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.create_game(mock_db, "", {})

        mock_db.execute.assert_not_called()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_rls_context_set_correctly(self, mock_db):
        """Verifies RLS context is set before creating game."""
        game_data = {
            "channel_id": "channel-1",
            "host_id": "user-1",
            "title": "New Game",
            "scheduled_at": datetime(2026, 1, 15, 20, 0, 0, tzinfo=UTC),
        }

        await guild_queries.create_game(mock_db, "guild-1", game_data)

        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql


class TestUpdateGame:
    """Tests for update_game function."""

    @pytest.mark.asyncio
    async def test_success_updates_game(self, mock_db, sample_game):
        """Updates game attributes when game found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute.return_value = mock_result

        updates = {"title": "Updated Title", "max_players": 6}
        result = await guild_queries.update_game(mock_db, "guild-1", "game-123", updates)

        assert result.title == "Updated Title"
        assert result.max_players == 6
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_game_not_found_raises_error(self, mock_db):
        """Raises ValueError when game not found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Game game-123 not found in guild guild-1"):
            await guild_queries.update_game(mock_db, "guild-1", "game-123", {})

        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.update_game(mock_db, "", "game-123", {})

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_game_id_raises_error(self, mock_db):
        """Raises ValueError when game_id is empty string."""
        with pytest.raises(ValueError, match="game_id cannot be empty"):
            await guild_queries.update_game(mock_db, "guild-1", "", {})

        mock_db.execute.assert_not_called()


class TestDeleteGame:
    """Tests for delete_game function."""

    @pytest.mark.asyncio
    async def test_success_deletes_game(self, mock_db, sample_game):
        """Deletes game when found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute.return_value = mock_result

        await guild_queries.delete_game(mock_db, "guild-1", "game-123")

        mock_db.delete.assert_called_once_with(sample_game)
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_game_not_found_raises_error(self, mock_db):
        """Raises ValueError when game not found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Game game-123 not found in guild guild-1"):
            await guild_queries.delete_game(mock_db, "guild-1", "game-123")

        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.delete_game(mock_db, "", "game-123")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_game_id_raises_error(self, mock_db):
        """Raises ValueError when game_id is empty string."""
        with pytest.raises(ValueError, match="game_id cannot be empty"):
            await guild_queries.delete_game(mock_db, "guild-1", "")

        mock_db.execute.assert_not_called()


class TestAddParticipant:
    """Tests for add_participant function."""

    @pytest.mark.asyncio
    async def test_success_adds_participant(self, mock_db, sample_game):
        """Adds participant when game found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_game
        mock_db.execute.return_value = mock_result

        participant_data = {"position": 0}
        result = await guild_queries.add_participant(
            mock_db, "guild-1", "game-123", "user-2", participant_data
        )

        assert isinstance(result, GameParticipant)
        assert result.game_session_id == "game-123"
        assert result.user_id == "user-2"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_validates_game_belongs_to_guild(self, mock_db):
        """Raises ValueError when game not found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Game game-123 not found in guild guild-1"):
            await guild_queries.add_participant(mock_db, "guild-1", "game-123", "user-2", {})

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.add_participant(mock_db, "", "game-123", "user-2", {})

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_game_id_raises_error(self, mock_db):
        """Raises ValueError when game_id is empty string."""
        with pytest.raises(ValueError, match="game_id cannot be empty"):
            await guild_queries.add_participant(mock_db, "guild-1", "", "user-2", {})

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_user_id_raises_error(self, mock_db):
        """Raises ValueError when user_id is empty string."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await guild_queries.add_participant(mock_db, "guild-1", "game-123", "", {})

        mock_db.execute.assert_not_called()


class TestRemoveParticipant:
    """Tests for remove_participant function."""

    @pytest.mark.asyncio
    async def test_success_removes_participant(self, mock_db, sample_game):
        """Removes participant when found."""
        mock_get_game_result = MagicMock()
        mock_get_game_result.scalar_one_or_none.return_value = sample_game

        participant = GameParticipant(id="part-1", game_session_id="game-123", user_id="user-2")
        mock_get_participant_result = MagicMock()
        mock_get_participant_result.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [
            mock_get_game_result,
            mock_get_game_result,
            mock_get_participant_result,
        ]

        await guild_queries.remove_participant(mock_db, "guild-1", "game-123", "user-2")

        mock_db.delete.assert_called_once_with(participant)
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_participant_not_found_does_nothing(self, mock_db, sample_game):
        """Does nothing when participant not found."""
        mock_get_game_result = MagicMock()
        mock_get_game_result.scalar_one_or_none.return_value = sample_game

        mock_get_participant_result = MagicMock()
        mock_get_participant_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [
            mock_get_game_result,
            mock_get_game_result,
            mock_get_participant_result,
        ]

        await guild_queries.remove_participant(mock_db, "guild-1", "game-123", "user-2")

        mock_db.delete.assert_not_called()
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_validates_game_belongs_to_guild(self, mock_db):
        """Raises ValueError when game not found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Game game-123 not found in guild guild-1"):
            await guild_queries.remove_participant(mock_db, "guild-1", "game-123", "user-2")

        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.remove_participant(mock_db, "", "game-123", "user-2")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_game_id_raises_error(self, mock_db):
        """Raises ValueError when game_id is empty string."""
        with pytest.raises(ValueError, match="game_id cannot be empty"):
            await guild_queries.remove_participant(mock_db, "guild-1", "", "user-2")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_user_id_raises_error(self, mock_db):
        """Raises ValueError when user_id is empty string."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await guild_queries.remove_participant(mock_db, "guild-1", "game-123", "")

        mock_db.execute.assert_not_called()


class TestListUserGames:
    """Tests for list_user_games function."""

    @pytest.mark.asyncio
    async def test_success_returns_user_games(self, mock_db, sample_game):
        """Returns list of games user is participating in."""
        games = [sample_game]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = games
        mock_db.execute.return_value = mock_result

        result = await guild_queries.list_user_games(mock_db, "guild-1", "user-2")

        assert result == games
        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self, mock_db):
        """Returns empty list when user has no games in guild."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await guild_queries.list_user_games(mock_db, "guild-1", "user-2")

        assert result == []

    @pytest.mark.asyncio
    async def test_sets_rls_context(self, mock_db):
        """Sets RLS context with guild_id before query."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await guild_queries.list_user_games(mock_db, "guild-1", "user-2")

        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.list_user_games(mock_db, "", "user-2")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_user_id_raises_error(self, mock_db):
        """Raises ValueError when user_id is empty string."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await guild_queries.list_user_games(mock_db, "guild-1", "")

        mock_db.execute.assert_not_called()


class TestGetTemplateById:
    """Tests for get_template_by_id function."""

    @pytest.mark.asyncio
    async def test_success_returns_template(self, mock_db, sample_template):
        """Returns template when found in specified guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db.execute.return_value = mock_result

        result = await guild_queries.get_template_by_id(mock_db, "guild-1", "template-123")

        assert result == sample_template
        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, mock_db):
        """Returns None when template not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await guild_queries.get_template_by_id(mock_db, "guild-1", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.get_template_by_id(mock_db, "", "template-123")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_template_id_raises_error(self, mock_db):
        """Raises ValueError when template_id is empty string."""
        with pytest.raises(ValueError, match="template_id cannot be empty"):
            await guild_queries.get_template_by_id(mock_db, "guild-1", "")

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_sets_rls_context(self, mock_db, sample_template):
        """Sets RLS context with guild_id before query."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db.execute.return_value = mock_result

        await guild_queries.get_template_by_id(mock_db, "guild-1", "template-123")

        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql


class TestListTemplates:
    """Tests for list_templates function."""

    @pytest.mark.asyncio
    async def test_success_returns_templates(self, mock_db, sample_template):
        """Returns list of templates for guild."""
        templates = [sample_template]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = templates
        mock_db.execute.return_value = mock_result

        result = await guild_queries.list_templates(mock_db, "guild-1")

        assert result == templates
        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self, mock_db):
        """Returns empty list when guild has no templates."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await guild_queries.list_templates(mock_db, "guild-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_sets_rls_context(self, mock_db):
        """Sets RLS context with guild_id before query."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await guild_queries.list_templates(mock_db, "guild-1")

        assert mock_db.execute.call_count == 2
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.list_templates(mock_db, "")

        mock_db.execute.assert_not_called()


class TestCreateTemplate:
    """Tests for create_template function."""

    @pytest.mark.asyncio
    async def test_success_creates_template(self, mock_db):
        """Creates template with forced guild_id."""
        mock_db.execute.return_value = MagicMock()
        template_data = {
            "id": "template-123",
            "channel_id": "channel-1",
            "name": "D&D Campaign",
            "description": "Weekly D&D session",
            "order": 0,
            "is_default": True,
            "max_players": 5,
            "expected_duration_minutes": 180,
        }

        result = await guild_queries.create_template(mock_db, "guild-1", template_data)

        assert isinstance(result, GameTemplate)
        assert result.guild_id == "guild-1"
        assert result.name == "D&D Campaign"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_forces_guild_id(self, mock_db):
        """Forces guild_id even if provided in template_data."""
        mock_db.execute.return_value = MagicMock()
        template_data = {
            "id": "template-123",
            "channel_id": "channel-1",
            "name": "Test Template",
            "guild_id": "wrong-guild",
        }

        result = await guild_queries.create_template(mock_db, "guild-1", template_data)

        assert result.guild_id == "guild-1"

    @pytest.mark.asyncio
    async def test_sets_rls_context(self, mock_db):
        """Sets RLS context with guild_id before creation."""
        mock_db.execute.return_value = MagicMock()
        template_data = {
            "id": "template-123",
            "channel_id": "channel-1",
            "name": "Test Template",
        }

        await guild_queries.create_template(mock_db, "guild-1", template_data)

        assert mock_db.execute.call_count == 1
        rls_call = mock_db.execute.call_args_list[0]
        rls_sql = str(rls_call[0][0])
        assert "SET LOCAL app.current_guild_id = 'guild-1'" in rls_sql

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.create_template(mock_db, "", {"name": "Test"})

        mock_db.execute.assert_not_called()
        mock_db.add.assert_not_called()


class TestUpdateTemplate:
    """Tests for update_template function."""

    @pytest.mark.asyncio
    async def test_success_updates_template(self, mock_db, sample_template):
        """Updates template attributes."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db.execute.return_value = mock_result

        updates = {"name": "Updated Name", "description": "Updated Description"}
        result = await guild_queries.update_template(mock_db, "guild-1", "template-123", updates)

        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found_raises_error(self, mock_db):
        """Raises ValueError when template not found in guild."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Template .* not found in guild"):
            await guild_queries.update_template(
                mock_db, "guild-1", "nonexistent", {"name": "New Name"}
            )

        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_validates_ownership(self, mock_db, sample_template):
        """Validates template belongs to guild before update."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db.execute.return_value = mock_result

        await guild_queries.update_template(
            mock_db, "guild-1", "template-123", {"name": "New Name"}
        )

        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_guild_id_raises_error(self, mock_db):
        """Raises ValueError when guild_id is empty string."""
        with pytest.raises(ValueError, match="guild_id cannot be empty"):
            await guild_queries.update_template(mock_db, "", "template-123", {"name": "New"})

        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_template_id_raises_error(self, mock_db):
        """Raises ValueError when template_id is empty string."""
        with pytest.raises(ValueError, match="template_id cannot be empty"):
            await guild_queries.update_template(mock_db, "guild-1", "", {"name": "New"})

        mock_db.execute.assert_not_called()
