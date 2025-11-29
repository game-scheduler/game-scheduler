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


"""Discord UI view for game session interactions.

This module provides the persistent button view for game sessions,
allowing players to join and leave games via Discord buttons.
"""

import discord
from discord.ui import Button, View


class GameView(View):
    """Persistent view with Join and Leave buttons for game sessions.

    This view persists across bot restarts by using timeout=None and
    custom_id patterns that encode the game session ID.

    Attributes:
        game_id: UUID of the game session
        is_full: Whether the game has reached max players
        is_started: Whether the game has started (IN_PROGRESS or COMPLETED)
    """

    def __init__(self, game_id: str, is_full: bool = False, is_started: bool = False):
        """Initialize the game view with buttons.

        Args:
            game_id: Game session UUID
            is_full: Whether game is at capacity
            is_started: Whether game has started
        """
        super().__init__(timeout=None)
        self.game_id = game_id
        self.is_full = is_full
        self.is_started = is_started

        self.join_button = Button(
            style=discord.ButtonStyle.success,
            label="Join Game",
            custom_id=f"join_game_{game_id}",
            disabled=is_started,
        )
        self.join_button.callback = self._join_button_callback

        self.leave_button = Button(
            style=discord.ButtonStyle.danger,
            label="Leave Game",
            custom_id=f"leave_game_{game_id}",
            disabled=is_started,
        )
        self.leave_button.callback = self._leave_button_callback

        self.add_item(self.join_button)
        self.add_item(self.leave_button)

    async def _join_button_callback(self, interaction: discord.Interaction):
        """Handle join button click.

        This is a placeholder that will be replaced by the actual handler
        when the view is registered with the bot.
        """
        await interaction.response.defer()

    async def _leave_button_callback(self, interaction: discord.Interaction):
        """Handle leave button click.

        This is a placeholder that will be replaced by the actual handler
        when the view is registered with the bot.
        """
        await interaction.response.defer()

    def update_button_states(self, is_full: bool, is_started: bool):
        """Update button enabled/disabled states.

        Args:
            is_full: Whether game is at capacity (unused since waitlists are supported)
            is_started: Whether game has started
        """
        self.is_full = is_full
        self.is_started = is_started
        self.join_button.disabled = is_started
        self.leave_button.disabled = is_started

    @classmethod
    def from_game_data(
        cls, game_id: str, current_players: int, max_players: int, status: str
    ) -> "GameView":
        """Create a GameView from game session data.

        Args:
            game_id: Game session UUID
            current_players: Current participant count
            max_players: Maximum allowed participants
            status: Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)

        Returns:
            Configured GameView instance
        """
        is_full = current_players >= max_players
        is_started = status in ("IN_PROGRESS", "COMPLETED", "CANCELLED")
        return cls(game_id, is_full, is_started)
