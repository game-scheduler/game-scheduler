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


"""Button interaction dispatcher for Discord bot."""

import logging

import discord

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.join_game import handle_join_game
from services.bot.handlers.leave_game import handle_leave_game

logger = logging.getLogger(__name__)


class ButtonHandler:
    """Handles button interaction routing."""

    def __init__(self, publisher: BotEventPublisher):
        """Initialize button handler.

        Args:
            publisher: Bot event publisher for RabbitMQ
        """
        self.publisher = publisher

    async def handle_interaction(self, interaction: discord.Interaction) -> None:
        """Route button interaction to appropriate handler.

        Args:
            interaction: Discord button interaction

        Parses custom_id to determine handler and game ID.
        Format: {action}_{game_id}
        """
        if not interaction.data or "custom_id" not in interaction.data:
            logger.warning("Interaction missing custom_id")
            return

        custom_id = interaction.data["custom_id"]

        if not custom_id.startswith(("join_game_", "leave_game_")):
            logger.debug(f"Ignoring non-game button: {custom_id}")
            return

        try:
            if custom_id.startswith("join_game_"):
                game_id = custom_id.replace("join_game_", "")
                await handle_join_game(interaction, game_id, self.publisher)
            elif custom_id.startswith("leave_game_"):
                game_id = custom_id.replace("leave_game_", "")
                await handle_leave_game(interaction, game_id, self.publisher)
            else:
                logger.warning(f"Unknown button action: {custom_id}")

        except Exception as e:
            logger.error(f"Error handling button interaction {custom_id}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again.", ephemeral=True
                )
