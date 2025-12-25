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


"""Unit tests for E2E Discord helper polling utilities."""

import asyncio
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from tests.e2e.helpers.discord import DiscordTestHelper, DMType, wait_for_condition


class TestWaitForCondition:
    """Tests for wait_for_condition polling utility."""

    @pytest.mark.asyncio
    async def test_immediate_success(self):
        """Should return immediately when condition met on first check."""

        async def check_func():
            return (True, "result")

        result = await wait_for_condition(check_func, timeout=5, interval=1.0)

        assert result == "result"

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Should retry until condition met."""
        attempts = 0

        async def check_func():
            nonlocal attempts
            attempts += 1
            if attempts >= 3:
                return (True, "success")
            return (False, None)

        result = await wait_for_condition(check_func, timeout=10, interval=0.1)

        assert result == "success"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Should raise AssertionError on timeout."""

        async def check_func():
            return (False, None)

        with pytest.raises(AssertionError, match="test condition not met within 1s timeout"):
            await wait_for_condition(
                check_func, timeout=1, interval=0.1, description="test condition"
            )

    @pytest.mark.asyncio
    async def test_custom_interval(self):
        """Should respect custom polling interval."""
        attempts = 0
        start_time = asyncio.get_event_loop().time()

        async def check_func():
            nonlocal attempts
            attempts += 1
            if attempts >= 3:
                return (True, "done")
            return (False, None)

        result = await wait_for_condition(check_func, timeout=10, interval=0.2)
        elapsed = asyncio.get_event_loop().time() - start_time

        assert result == "done"
        assert elapsed >= 0.4


class TestDiscordTestHelperWaitForMessage:
    """Tests for DiscordTestHelper.wait_for_message method."""

    @pytest.mark.asyncio
    async def test_message_exists_immediately(self):
        """Should return message if it exists on first check."""
        helper = DiscordTestHelper("fake_token")
        mock_message = Mock(spec=discord.Message)
        helper.get_message = AsyncMock(return_value=mock_message)

        result = await helper.wait_for_message("123", "456", timeout=5)

        assert result == mock_message
        helper.get_message.assert_called_once_with("123", "456")

    @pytest.mark.asyncio
    async def test_message_appears_after_retry(self):
        """Should retry until message appears."""
        helper = DiscordTestHelper("fake_token")
        mock_message = Mock(spec=discord.Message)

        attempts = 0

        async def get_message_side_effect(*args):
            nonlocal attempts
            attempts += 1
            if attempts >= 3:
                return mock_message
            mock_response = Mock()
            mock_response.status = 404
            mock_response.reason = "Not Found"
            raise discord.NotFound(mock_response, "message not found")

        helper.get_message = AsyncMock(side_effect=get_message_side_effect)

        result = await helper.wait_for_message("123", "456", timeout=10, interval=0.1)

        assert result == mock_message
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_message_not_found_timeout(self):
        """Should raise AssertionError if message never appears."""
        helper = DiscordTestHelper("fake_token")

        mock_response = Mock()
        mock_response.status = 404
        mock_response.reason = "Not Found"
        helper.get_message = AsyncMock(
            side_effect=discord.NotFound(mock_response, "message not found")
        )

        with pytest.raises(AssertionError, match="message 456 in channel 123 not met within"):
            await helper.wait_for_message("123", "456", timeout=1, interval=0.1)

    @pytest.mark.asyncio
    async def test_http_exception_retries(self):
        """Should retry on HTTP exceptions."""
        helper = DiscordTestHelper("fake_token")
        mock_message = Mock(spec=discord.Message)

        attempts = 0

        async def get_message_side_effect(*args):
            nonlocal attempts
            attempts += 1
            if attempts >= 2:
                return mock_message
            mock_response = Mock()
            mock_response.status = 500
            mock_response.reason = "Internal Server Error"
            raise discord.HTTPException(mock_response, "server error")

        helper.get_message = AsyncMock(side_effect=get_message_side_effect)

        result = await helper.wait_for_message("123", "456", timeout=5, interval=0.1)

        assert result == mock_message


class TestDiscordTestHelperWaitForMessageUpdate:
    """Tests for DiscordTestHelper.wait_for_message_update method."""

    @pytest.mark.asyncio
    async def test_message_matches_immediately(self):
        """Should return immediately when check_func passes."""
        helper = DiscordTestHelper("fake_token")
        mock_message = Mock(spec=discord.Message)
        mock_message.content = "expected content"
        helper.get_message = AsyncMock(return_value=mock_message)

        result = await helper.wait_for_message_update(
            "123", "456", lambda msg: msg.content == "expected content", timeout=5
        )

        assert result == mock_message

    @pytest.mark.asyncio
    async def test_message_update_after_retry(self):
        """Should retry until check_func passes."""
        helper = DiscordTestHelper("fake_token")

        attempts = 0

        async def get_message_side_effect(*args):
            nonlocal attempts
            attempts += 1
            mock_msg = Mock(spec=discord.Message)
            mock_msg.content = "updated" if attempts >= 3 else "original"
            return mock_msg

        helper.get_message = AsyncMock(side_effect=get_message_side_effect)

        result = await helper.wait_for_message_update(
            "123", "456", lambda msg: msg.content == "updated", timeout=10, interval=0.1
        )

        assert result.content == "updated"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_message_update_timeout(self):
        """Should raise AssertionError if check_func never passes."""
        helper = DiscordTestHelper("fake_token")
        mock_message = Mock(spec=discord.Message)
        mock_message.content = "original"
        helper.get_message = AsyncMock(return_value=mock_message)

        with pytest.raises(AssertionError, match="test update not met within"):
            await helper.wait_for_message_update(
                "123",
                "456",
                lambda msg: msg.content == "never",
                timeout=1,
                interval=0.1,
                description="test update",
            )


class TestDiscordTestHelperWaitForDMMatching:
    """Tests for DiscordTestHelper.wait_for_dm_matching method."""

    @pytest.mark.asyncio
    async def test_matching_dm_found_immediately(self):
        """Should return matching DM on first check."""
        helper = DiscordTestHelper("fake_token")
        mock_dm1 = Mock(spec=discord.Message, content="other message")
        mock_dm2 = Mock(spec=discord.Message, content="target message")
        helper.get_user_recent_dms = AsyncMock(return_value=[mock_dm1, mock_dm2])

        result = await helper.wait_for_dm_matching(
            "user123", lambda dm: "target" in dm.content, timeout=10
        )

        assert result == mock_dm2

    @pytest.mark.asyncio
    async def test_matching_dm_appears_after_retry(self):
        """Should retry until matching DM appears."""
        helper = DiscordTestHelper("fake_token")

        attempts = 0

        async def get_dms_side_effect(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts >= 3:
                return [Mock(spec=discord.Message, content="found it")]
            return [Mock(spec=discord.Message, content="not yet")]

        helper.get_user_recent_dms = AsyncMock(side_effect=get_dms_side_effect)

        result = await helper.wait_for_dm_matching(
            "user123", lambda dm: "found" in dm.content, timeout=10, interval=0.1
        )

        assert "found" in result.content
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_dm_not_found_timeout(self):
        """Should raise AssertionError if no matching DM found."""
        helper = DiscordTestHelper("fake_token")
        helper.get_user_recent_dms = AsyncMock(return_value=[])

        with pytest.raises(AssertionError, match="test DM not met within"):
            await helper.wait_for_dm_matching(
                "user123",
                lambda dm: True,
                timeout=1,
                interval=0.1,
                description="test DM",
            )

    @pytest.mark.asyncio
    async def test_uses_limit_15(self):
        """Should fetch recent DMs with limit=15."""
        helper = DiscordTestHelper("fake_token")
        mock_dm = Mock(spec=discord.Message, content="test")
        helper.get_user_recent_dms = AsyncMock(return_value=[mock_dm])

        await helper.wait_for_dm_matching("user123", lambda dm: True, timeout=5)

        helper.get_user_recent_dms.assert_called_with("user123", limit=15)


class TestDiscordTestHelperWaitForRecentDM:
    """Tests for DiscordTestHelper.wait_for_recent_dm convenience method."""

    @pytest.mark.asyncio
    async def test_reminder_dm_type(self):
        """Should match reminder DM with game title and timestamp."""
        helper = DiscordTestHelper("fake_token")
        mock_dm = Mock(spec=discord.Message, content="Test Game starts <t:1234567890:F>")
        helper.wait_for_dm_matching = AsyncMock(return_value=mock_dm)

        result = await helper.wait_for_recent_dm("user123", "Test Game", dm_type=DMType.REMINDER)

        assert result == mock_dm
        helper.wait_for_dm_matching.assert_called_once()
        call_args = helper.wait_for_dm_matching.call_args
        assert call_args[0][0] == "user123"
        predicate = call_args[0][1]
        assert predicate(mock_dm) is True

    @pytest.mark.asyncio
    async def test_join_dm_type(self):
        """Should match join DM with 'joined' keyword."""
        helper = DiscordTestHelper("fake_token")
        mock_dm = Mock(spec=discord.Message, content="You joined Test Game")
        helper.wait_for_dm_matching = AsyncMock(return_value=mock_dm)

        result = await helper.wait_for_recent_dm("user123", "Test Game", dm_type=DMType.JOIN)

        assert result == mock_dm
        call_args = helper.wait_for_dm_matching.call_args
        predicate = call_args[0][1]
        assert predicate(mock_dm) is True

    @pytest.mark.asyncio
    async def test_removal_dm_type(self):
        """Should match removal DM with 'removed' keyword."""
        helper = DiscordTestHelper("fake_token")
        mock_dm = Mock(spec=discord.Message, content="You were removed from Test Game")
        helper.wait_for_dm_matching = AsyncMock(return_value=mock_dm)

        result = await helper.wait_for_recent_dm("user123", "Test Game", dm_type=DMType.REMOVAL)

        assert result == mock_dm
        call_args = helper.wait_for_dm_matching.call_args
        predicate = call_args[0][1]
        assert predicate(mock_dm) is True

    @pytest.mark.asyncio
    async def test_promotion_dm_type(self):
        """Should match promotion DM with 'A spot opened up' and 'moved from the waitlist'."""
        helper = DiscordTestHelper("fake_token")
        mock_dm = Mock(
            spec=discord.Message,
            content=(
                "✅ Good news! A spot opened up in **Test Game** "
                "scheduled for <t:1234567890:F>. You've been moved from "
                "the waitlist to confirmed participants!"
            ),
        )
        helper.wait_for_dm_matching = AsyncMock(return_value=mock_dm)

        result = await helper.wait_for_recent_dm("user123", "Test Game", dm_type=DMType.PROMOTION)

        assert result == mock_dm
        call_args = helper.wait_for_dm_matching.call_args
        predicate = call_args[0][1]
        assert predicate(mock_dm) is True

    @pytest.mark.asyncio
    async def test_default_timeout_150s(self):
        """Should use 150s timeout by default for daemon delays."""
        helper = DiscordTestHelper("fake_token")
        mock_dm = Mock(spec=discord.Message, content="Test Game starts <t:1234567890:F>")
        helper.wait_for_dm_matching = AsyncMock(return_value=mock_dm)

        await helper.wait_for_recent_dm("user123", "Test Game")

        call_args = helper.wait_for_dm_matching.call_args
        assert call_args[1]["timeout"] == 150


class TestDMTypeEnum:
    """Tests for DMType StrEnum."""

    def test_enum_values(self):
        """Should have correct string values."""
        assert DMType.REMINDER == "reminder"
        assert DMType.JOIN == "join"
        assert DMType.REMOVAL == "removal"
        assert DMType.PROMOTION == "promotion"

    def test_enum_membership(self):
        """Should support membership testing."""
        assert "reminder" in [e.value for e in DMType]
        assert "join" in [e.value for e in DMType]
        assert "invalid" not in [e.value for e in DMType]

    def test_enum_iteration(self):
        """Should support iteration."""
        types = list(DMType)
        assert len(types) == 4
        assert DMType.REMINDER in types
