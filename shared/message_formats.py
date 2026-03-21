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
    def reminder_participant(game_title: str, game_time_unix: int, is_waitlist: bool) -> str:
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
        return f"{waitlist_prefix}Your game '{game_title}' starts <t:{game_time_unix}:R>"

    @staticmethod
    def clone_confirmation(game_title: str, deadline_unix: int) -> str:
        """
        Format clone confirmation DM asking participant to confirm their spot.

        Args:
            game_title: Title of the cloned game
            deadline_unix: Unix timestamp of the confirmation deadline

        Returns:
            Formatted clone confirmation message with confirm/decline prompt
        """
        return (
            f"🎲 You've been carried over to **{game_title}**!\n\n"
            f"Please confirm your spot by <t:{deadline_unix}:F> "
            f"(<t:{deadline_unix}:R>) using the buttons below. "
            f"If you don't confirm in time you'll be automatically removed."
        )

    @staticmethod
    def rewards_reminder(game_title: str, edit_url: str) -> str:
        """
        Format rewards reminder DM sent to the host when a game completes with no rewards set.

        Args:
            game_title: Title of the game
            edit_url: Full URL to the edit page for this game

        Returns:
            Formatted rewards reminder message
        """
        return (
            f"🏆 **{game_title}** has completed! "
            f"Don't forget to add rewards for your players.\n\n"
            f"[Edit game to add rewards]({edit_url})"
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
            return bool(dm.content and game_title in dm.content and "removed" in dm.content.lower())

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
            return bool(dm.content and "joined" in dm.content.lower() and game_title in dm.content)

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
            return bool(dm.content and game_title in dm.content and "starts <t:" in dm.content)

        return predicate

    @staticmethod
    def clone_confirmation(game_title: str) -> Callable[[DiscordMessage], bool]:
        """
        Predicate to match clone confirmation DMs.

        Args:
            game_title: Title of the cloned game

        Returns:
            Predicate function for wait_for_dm_matching
        """

        def predicate(dm: DiscordMessage) -> bool:
            return bool(dm.content and game_title in dm.content and "confirm" in dm.content.lower())

        return predicate

    @staticmethod
    def rewards_reminder(game_title: str) -> Callable[[DiscordMessage], bool]:
        """
        Predicate to match rewards reminder DMs sent to hosts on game completion.

        Args:
            game_title: Title of the game

        Returns:
            Predicate function for wait_for_dm_matching
        """

        def predicate(dm: DiscordMessage) -> bool:
            return bool(
                dm.content
                and game_title in dm.content
                and "rewards" in dm.content.lower()
                and "completed" in dm.content.lower()
            )

        return predicate
