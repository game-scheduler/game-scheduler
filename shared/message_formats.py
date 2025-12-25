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


"""
Centralized Discord message format strings and predicates.

This module provides DRY format strings and matching predicates for Discord DMs
and other messages. Both production code and tests reference these to ensure
they stay in sync when message wording changes.
"""

from collections.abc import Callable
from typing import Protocol


class DiscordMessage(Protocol):
    """Protocol for Discord message objects used in predicates."""

    content: str | None


class DMFormats:
    """Format strings for Discord DMs sent by the bot."""

    @staticmethod
    def promotion(game_title: str, scheduled_at_unix: int) -> str:
        """
        Format promotion DM when user moves from waitlist to confirmed.

        Args:
            game_title: Title of the game
            scheduled_at_unix: Unix timestamp of game start time

        Returns:
            Formatted promotion message
        """
        return (
            f"✅ Good news! A spot opened up in **{game_title}** "
            f"scheduled for <t:{scheduled_at_unix}:F>. "
            f"You've been moved from the waitlist to confirmed participants!"
        )

    @staticmethod
    def removal(game_title: str) -> str:
        """
        Format removal DM when user is removed from a game.

        Args:
            game_title: Title of the game

        Returns:
            Formatted removal message
        """
        return f"❌ You were removed from **{game_title}**"

    @staticmethod
    def join_with_instructions(
        game_title: str, signup_instructions: str, scheduled_at_unix: int
    ) -> str:
        """
        Format join DM with signup instructions.

        Args:
            game_title: Title of the game
            signup_instructions: Game-specific signup instructions
            scheduled_at_unix: Unix timestamp of game start time

        Returns:
            Formatted join message with instructions
        """
        return (
            f"✅ **You've joined {game_title}**\n\n"
            f"📋 **Signup Instructions**\n"
            f"{signup_instructions}\n\n"
            f"Game starts <t:{scheduled_at_unix}:R>"
        )

    @staticmethod
    def join_simple(game_title: str) -> str:
        """
        Format simple join DM without signup instructions.

        Args:
            game_title: Title of the game

        Returns:
            Formatted join message
        """
        return f"✅ You've joined **{game_title}**!"

    @staticmethod
    def reminder_host(game_title: str, game_time_unix: int) -> str:
        """
        Format reminder DM for game host.

        Args:
            game_title: Title of the game
            game_time_unix: Unix timestamp of game start time

        Returns:
            Formatted host reminder message
        """
        return f"🎮 **[Host]** Your game '{game_title}' starts <t:{game_time_unix}:R>"

    @staticmethod
    def reminder_participant(
        game_title: str, game_time_unix: int, is_waitlist: bool
    ) -> str:
        """
        Format reminder DM for participant (confirmed or waitlist).

        Args:
            game_title: Title of the game
            game_time_unix: Unix timestamp of game start time
            is_waitlist: Whether participant is on waitlist

        Returns:
            Formatted participant reminder message
        """
        waitlist_prefix = "🎫 **[Waitlist]** " if is_waitlist else ""
        return (
            f"{waitlist_prefix}Your game '{game_title}' starts <t:{game_time_unix}:R>"
        )


class DMPredicates:
    """Predicates for matching Discord DMs in tests."""

    @staticmethod
    def promotion(game_title: str) -> Callable[[DiscordMessage], bool]:
        """
        Predicate to match promotion DMs.

        Args:
            game_title: Title of the game

        Returns:
            Predicate function for wait_for_dm_matching
        """

        def predicate(dm: DiscordMessage) -> bool:
            return bool(
                dm.content
                and game_title in dm.content
                and "A spot opened up" in dm.content
                and "moved from the waitlist" in dm.content
            )

        return predicate

    @staticmethod
    def removal(game_title: str) -> Callable[[DiscordMessage], bool]:
        """
        Predicate to match removal DMs.

        Args:
            game_title: Title of the game

        Returns:
            Predicate function for wait_for_dm_matching
        """

        def predicate(dm: DiscordMessage) -> bool:
            return bool(
                dm.content
                and game_title in dm.content
                and "removed" in dm.content.lower()
            )

        return predicate

    @staticmethod
    def join(game_title: str) -> Callable[[DiscordMessage], bool]:
        """
        Predicate to match join DMs (with or without signup instructions).

        Args:
            game_title: Title of the game

        Returns:
            Predicate function for wait_for_dm_matching
        """

        def predicate(dm: DiscordMessage) -> bool:
            return bool(
                dm.content
                and "joined" in dm.content.lower()
                and game_title in dm.content
            )

        return predicate

    @staticmethod
    def reminder(game_title: str) -> Callable[[DiscordMessage], bool]:
        """
        Predicate to match reminder DMs (host, participant, or waitlist).

        Args:
            game_title: Title of the game

        Returns:
            Predicate function for wait_for_dm_matching
        """

        def predicate(dm: DiscordMessage) -> bool:
            return bool(
                dm.content and game_title in dm.content and "starts <t:" in dm.content
            )

        return predicate
