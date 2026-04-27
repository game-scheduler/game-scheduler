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


"""Unit tests for EventHandlers join notification methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.messaging.events import NotificationDueEvent
from shared.models.user import User


@pytest.mark.asyncio
async def test_handle_join_notification_with_signup_instructions(event_handlers, sample_game):
    """Test join notification sends DM with signup instructions when present."""
    participant_user = User(id=str(uuid4()), discord_id="participant123")
    sample_game.signup_instructions = "Click the link to create your character: https://example.com"
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.max_players = 5

    participant = MagicMock()
    participant.id = str(uuid4())
    participant.user_id = participant_user.id
    participant.user = participant_user
    participant.is_waitlisted = False

    sample_game.participants = [participant]

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
                mock_send_dm.return_value = True

                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant.id,
                }
                await event_handlers._handle_notification_due(data)

                assert mock_send_dm.await_count == 1
                sent_message = mock_send_dm.call_args.args[1]
                assert "joined" in sent_message.lower()
                assert sample_game.title in sent_message
                assert sample_game.signup_instructions in sent_message

                mock_db_session.assert_called_once_with()  # assert-no-args
                mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_join_notification_without_signup_instructions(event_handlers, sample_game):
    """Test join notification sends DM without signup instructions when not present."""
    participant_user = User(id=str(uuid4()), discord_id="participant123")
    sample_game.signup_instructions = None
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.max_players = 5

    participant = MagicMock()
    participant.id = str(uuid4())
    participant.user_id = participant_user.id
    participant.user = participant_user
    participant.is_waitlisted = False

    sample_game.participants = [participant]

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
                mock_send_dm.return_value = True

                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant.id,
                }
                await event_handlers._handle_notification_due(data)

                assert mock_send_dm.await_count == 1
                sent_message = mock_send_dm.call_args.args[1]
                assert "joined" in sent_message.lower()
                assert sample_game.title in sent_message
                assert "signup instructions" not in sent_message.lower()

                mock_db_session.assert_called_once_with()  # assert-no-args
                mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_join_notification_missing_participant_id(event_handlers, sample_game):
    """Test join notification handles missing participant_id gracefully."""
    data = {
        "game_id": str(uuid4()),
        "notification_type": "join_notification",
        "participant_id": None,
    }

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            await event_handlers._handle_notification_due(data)

            mock_get_game.assert_awaited_once_with(mock_db, data["game_id"])
            mock_db_session.assert_called_once_with()  # assert-no-args


@pytest.mark.asyncio
async def test_handle_join_notification_user_not_found(event_handlers, sample_game):
    """Test join notification handles missing participant gracefully."""
    participant_id = str(uuid4())

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch("services.bot.events.handlers.logger") as mock_logger:
                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant_id,
                }
                await event_handlers._handle_notification_due(data)
                mock_logger.info.assert_called()
                assert any(
                    "no longer active" in str(call) for call in mock_logger.info.call_args_list
                )

                mock_db_session.assert_called_once_with()  # assert-no-args
                mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


class TestHandleJoinNotificationHelpers:
    """Test helper methods extracted from _handle_join_notification."""

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_success(self, event_handlers, sample_game):
        """Test successful fetch of game and participant data."""
        participant_id = str(uuid4())
        participant = MagicMock()
        participant.id = participant_id
        participant.user = MagicMock()

        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

            assert game == sample_game
            assert part == participant
            mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_game_not_found(self, event_handlers):
        """Test fetch when game doesn't exist."""
        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = None

            event = NotificationDueEvent(
                game_id=str(uuid4()),
                notification_type="join_notification",
                participant_id=str(uuid4()),
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))
                mock_logger.error.assert_called_once_with("Game not found: %s", event.game_id)

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_participant_not_found(
        self, event_handlers, sample_game
    ):
        """Test fetch when participant doesn't exist."""
        participant_id = str(uuid4())
        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))
                mock_logger.info.assert_called_once_with(
                    "Participant %s no longer active for game %s",
                    event.participant_id,
                    event.game_id,
                )

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_participant_without_user(
        self, event_handlers, sample_game
    ):
        """Test fetch when participant exists but has no user."""
        participant_id = str(uuid4())
        participant = MagicMock()
        participant.id = participant_id
        participant.user = None

        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))
                mock_logger.info.assert_called_once_with(
                    "Participant %s no longer active for game %s",
                    event.participant_id,
                    event.game_id,
                )

    def test_is_participant_confirmed_when_confirmed(self, event_handlers, sample_game):
        """Test participant is confirmed (not waitlisted)."""
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = [participant]
            mock_partition.return_value = mock_partitioned

            is_confirmed = event_handlers._is_participant_confirmed(participant, sample_game)

            assert is_confirmed is True
            mock_partition.assert_called_once_with(
                sample_game.participants, sample_game.max_players
            )

    def test_is_participant_confirmed_when_waitlisted(self, event_handlers, sample_game):
        """Test participant is waitlisted (not confirmed)."""
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partition.return_value = mock_partitioned

            with patch("services.bot.events.handlers.logger") as mock_logger:
                is_confirmed = event_handlers._is_participant_confirmed(participant, sample_game)

                assert is_confirmed is False
                mock_partition.assert_called_once_with(
                    sample_game.participants, sample_game.max_players
                )
                mock_logger.info.assert_called_once_with(
                    "Participant %s is waitlisted, skipping join notification for game %s",
                    participant.id,
                    sample_game.id,
                )

    def test_format_join_notification_message_with_instructions(self, event_handlers, sample_game):
        """Test message formatting with signup instructions."""
        sample_game.signup_instructions = "Join our Discord at https://discord.gg/test"

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_with_instructions.return_value = "Test message with instructions"

            message = event_handlers._format_join_notification_message(sample_game)

            mock_formats.join_with_instructions.assert_called_once_with(
                sample_game.title,
                sample_game.signup_instructions,
                int(sample_game.scheduled_at.timestamp()),
            )
            assert message == "Test message with instructions"

    def test_format_join_notification_message_without_instructions(
        self, event_handlers, sample_game
    ):
        """Test message formatting without signup instructions."""
        sample_game.signup_instructions = None

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_simple.return_value = "Test simple message"

            message = event_handlers._format_join_notification_message(sample_game)

            mock_formats.join_simple.assert_called_once_with(sample_game.title)
            assert message == "Test simple message"

    @pytest.mark.asyncio
    async def test_send_join_notification_dm_success(self, event_handlers):
        """Test successful DM sending with success logging."""
        participant = MagicMock()
        participant.user = MagicMock()
        participant.user.discord_id = "123456789"
        message = "Test notification message"
        game_id = str(uuid4())

        with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            with patch("services.bot.events.handlers.logger") as mock_logger:
                await event_handlers._send_join_notification_dm(participant, message, game_id)

                mock_send.assert_called_once_with("123456789", message)
                mock_logger.info.assert_called_once()
                assert "✓ Sent join notification" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    async def test_send_join_notification_dm_failure(self, event_handlers):
        """Test failed DM sending with warning logging."""
        participant = MagicMock()
        participant.user = MagicMock()
        participant.user.discord_id = "123456789"
        message = "Test notification message"
        game_id = str(uuid4())

        with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False

            with patch("services.bot.events.handlers.logger") as mock_logger:
                await event_handlers._send_join_notification_dm(participant, message, game_id)

                mock_send.assert_called_once_with("123456789", message)
                mock_logger.warning.assert_called_once()
                assert "Failed to send join notification" in str(mock_logger.warning.call_args)
