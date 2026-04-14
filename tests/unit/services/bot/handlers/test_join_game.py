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


"""Unit tests for the join game bot handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.handlers import join_game as join_game_module
from services.bot.handlers.join_game import _resolve_bot_role_position
from shared.models.participant import ParticipantType


def _make_game(priority_role_ids: list[str] | None = None) -> MagicMock:
    game = MagicMock()
    game.template = MagicMock()
    game.template.signup_priority_role_ids = priority_role_ids
    return game


def _make_game_no_template() -> MagicMock:
    game = MagicMock()
    game.template = None
    return game


def _make_role_checker() -> MagicMock:
    checker = MagicMock()
    checker.seed_user_roles = AsyncMock()
    return checker


class TestResolveBotRolePosition:
    """Tests for _resolve_bot_role_position."""

    @pytest.mark.asyncio
    async def test_no_priority_roles_returns_self_added(self):
        """Empty priority list skips role resolution and returns SELF_ADDED."""
        interaction = MagicMock()
        game = _make_game(priority_role_ids=[])
        result = await _resolve_bot_role_position(interaction, game, _make_role_checker())
        assert result == (ParticipantType.SELF_ADDED, 0)

    @pytest.mark.asyncio
    async def test_no_template_returns_self_added(self):
        """Missing template returns SELF_ADDED without error."""
        interaction = MagicMock()
        result = await _resolve_bot_role_position(
            interaction, _make_game_no_template(), _make_role_checker()
        )
        assert result == (ParticipantType.SELF_ADDED, 0)

    @pytest.mark.asyncio
    async def test_non_member_interaction_returns_self_added(self):
        """DM / non-guild interaction (User, not Member) returns SELF_ADDED."""
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.User)  # not a Member
        game = _make_game(priority_role_ids=["role_a"])
        result = await _resolve_bot_role_position(interaction, game, _make_role_checker())
        assert result == (ParticipantType.SELF_ADDED, 0)

    @pytest.mark.asyncio
    async def test_member_with_matching_role_returns_role_matched(self):
        """Guild member whose roles match the priority list gets ROLE_MATCHED."""
        guild_id = "999"
        role_a_id = "111"

        mock_role = MagicMock()
        mock_role.id = int(role_a_id)

        interaction = MagicMock()
        interaction.guild_id = int(guild_id)
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.user.roles = [mock_role]

        game = _make_game(priority_role_ids=[role_a_id])
        checker = _make_role_checker()

        result = await _resolve_bot_role_position(interaction, game, checker)

        assert result == (ParticipantType.ROLE_MATCHED, 0)
        checker.seed_user_roles.assert_called_once_with("42", guild_id, [role_a_id])

    @pytest.mark.asyncio
    async def test_everyone_role_excluded_from_user_roles(self):
        """The @everyone pseudo-role (same id as guild) is excluded from role IDs."""
        guild_id = "999"
        role_a_id = "111"

        everyone_role = MagicMock()
        everyone_role.id = int(guild_id)

        real_role = MagicMock()
        real_role.id = int(role_a_id)

        interaction = MagicMock()
        interaction.guild_id = int(guild_id)
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.user.roles = [everyone_role, real_role]

        game = _make_game(priority_role_ids=[role_a_id])
        checker = _make_role_checker()

        result = await _resolve_bot_role_position(interaction, game, checker)

        assert result == (ParticipantType.ROLE_MATCHED, 0)
        checker.seed_user_roles.assert_called_once_with("42", guild_id, [role_a_id])

    @pytest.mark.asyncio
    async def test_member_with_no_matching_role_returns_self_added(self):
        """Guild member whose roles don't match any priority role gets SELF_ADDED."""
        guild_id = "999"

        mock_role = MagicMock()
        mock_role.id = 777

        interaction = MagicMock()
        interaction.guild_id = int(guild_id)
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.user.roles = [mock_role]

        game = _make_game(priority_role_ids=["111", "222"])
        checker = _make_role_checker()

        result = await _resolve_bot_role_position(interaction, game, checker)

        assert result == (ParticipantType.SELF_ADDED, 0)
        checker.seed_user_roles.assert_called_once()


def _make_join_interaction(nick=None, global_name=None, name="username", avatar_url=None):
    interaction = MagicMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 12345
    interaction.user.nick = nick
    interaction.user.global_name = global_name
    interaction.user.name = name
    if avatar_url:
        mock_avatar = MagicMock()
        mock_avatar.url = avatar_url
        interaction.user.display_avatar = mock_avatar
    else:
        interaction.user.display_avatar = None
    interaction.user.guild = MagicMock()
    interaction.user.guild.id = 99999
    return interaction


class TestJoinGameUpsertDisplayName:
    """Tests verifying UserDisplayNameService.upsert_one is called on join."""

    @pytest.mark.asyncio
    async def test_upsert_called_after_successful_join(self):
        """handle_join_game calls upsert_one with interaction.user data on success."""
        interaction = _make_join_interaction(nick="ServerNick", avatar_url="https://cdn/a.png")
        publisher = AsyncMock()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        game = MagicMock()
        game.guild_id = "99999"
        game.max_players = 5
        game.template = None
        game.guild_id = "99999"

        mock_participant = MagicMock()
        mock_participant.id = "pid1"

        validate_result = {
            "can_join": True,
            "game": game,
            "user": MagicMock(id="uid1"),
            "participant_count": 0,
            "error": None,
        }

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_db
        async_cm.__aexit__.return_value = None

        with (
            patch("services.bot.handlers.join_game.get_db_session", return_value=async_cm),
            patch(
                "services.bot.handlers.join_game._validate_join_game",
                new=AsyncMock(return_value=validate_result),
            ),
            patch(
                "services.bot.handlers.join_game._resolve_bot_role_position",
                new=AsyncMock(return_value=(ParticipantType.SELF_ADDED, 0)),
            ),
            patch("services.bot.handlers.utils.UserDisplayNameService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc.upsert_one = AsyncMock()
            mock_svc_cls.return_value = mock_svc

            await join_game_module.handle_join_game(
                interaction, "00000000-0000-0000-0000-000000000001", publisher
            )

        mock_svc.upsert_one.assert_awaited_once_with(
            str(interaction.user.id),
            str(interaction.user.guild.id),
            "ServerNick",
            "https://cdn/a.png",
        )
